# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # S03 — Build Model Features

# COMMAND ----------

# DBTITLE 1,Define S0 Config
# MAGIC %run "./S00_Config"

# COMMAND ----------

# DBTITLE 1,Imports, Constants & Helpers
import numpy as np
import pandas as pd
from pyspark.sql import Window
from pyspark.sql import functions as F

# --------------------------------------------------------------------------- #
# Data Inputs (table names come from S00_Config)
# --------------------------------------------------------------------------- #

catalog = CATALOG
schema  = SCHEMA
in_table_name = TABLES["spine"]
out_table_name = TABLES["model"]


# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
ROLLING_FEATURE_WINDOW = 12
ROLLING_FEATURE_MIN_PERIODS = 3
ZERO_FLOOR_EPSILON = 1e-9
ORDER_COLUMNS = ("fin_inc_month",)


# --------------------------------------------------------------------------- #
# Small column-expression helpers
# --------------------------------------------------------------------------- #
def nan_inf_to_null(column):
    """Return a column where NaN and +/-inf become NULL.
    """
    return F.when(F.isnan(column) | (F.abs(column) == float("inf")), None).otherwise(column)


def floor_near_zero(column, epsilon=ZERO_FLOOR_EPSILON):
    """Snap values whose magnitude is below ``epsilon`` to exactly 0.0 so floating-point noise is treated
    as a true zero by the zero-count and slope features.
    """
    return F.when(F.abs(column) < F.lit(epsilon), F.lit(0.0)).otherwise(column)

# COMMAND ----------

# DBTITLE 1,Config
# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
def build_stage_config(
    run_val_date,
    source_table,
    target_table,
    write_catalog,
    write_schema,
):
    """
    Build the configuration dict that drives the whole stage.
    """
    val_date_ts = pd.to_datetime(run_val_date)
    val_date_str = val_date_ts.strftime("%Y-%m-%d")

    return {
        "val_date_str": val_date_str,
        "source": source_table,
        "catalog": write_catalog,
        "schema": write_schema,
        "output_table": target_table,
        # Columns that together identify a product/enrollment slice
        "cf_product_level": ENROLL_KEYS,
        "cf_claim_level": ["cos_hccc_cd", "service_code"],
        # Columns used for target encoding partitions
        "product_column": "segment_name_fnl",
        "category_column": "service_code",
        # Date columns that make one monthly observation.
        "cf_dates": ["fin_inc_month"],
        # Final model input columns selected into the output table.
        "features": model_output_features(),
    }


# COMMAND ----------

# DBTITLE 1,Source Load & Claim Aggregation
# --------------------------------------------------------------------------- #
# Source load (reads the pre-aggregated SPINE from S02)
# --------------------------------------------------------------------------- #
def load_source(spark, config):
    """Load the CLM_MBR_SPINE table and derive target columns.

    The SPINE already contains aggregated util_k, pmpm, bf_estimate_util_k,
    bf_estimate_pmpm from S02. We just add TARGET columns used by feature
    engineering.
    """
    source = spark.table(config["source"]).filter(
        F.col("VAL_DATE") == F.to_date(F.lit(config["val_date_str"]))
    )
    source = cast_decimals_to_double(source)

    row_count = source.count()
    if row_count == 0:
        raise ValueError(
            f"No rows found in {config['source']} for VAL_DATE={config['val_date_str']}"
        )
    print(f"Loaded {row_count:,} rows from {config['source']}")

    # Derive target columns (BF estimates ARE the targets)
    source = source.withColumns({
        "TARGET_UTIL": F.col("bf_estimate_util_k"),
        "TARGET_PMPM": F.col("bf_estimate_pmpm"),
    })

    return source

# COMMAND ----------

# DBTITLE 1,Feature Engineering
# --------------------------------------------------------------------------- #
# Feature engineering
# --------------------------------------------------------------------------- #

def add_metric_features(claims, group_columns, metric, product_column, category_column):
    """Add every native-window feature for one metric ('UTIL' or 'PMPM').

    Produces target encodings, lags, rolling encoding means, rolling variance, and
    the rolling zero count. The rolling SLOPE is added separately by
    :func:`add_slope_feature` because it is not a native window aggregate.
    """
    target_column = f"TARGET_{metric}"
    bf_column = "bf_estimate_util_k" if metric == "UTIL" else "bf_estimate_pmpm"

    features = claims

    # --- Step 1: target encodings (mean target per slice/month) ---------------
    encoding_dimensions = {"MARKET": "market_fnl", "PRODUCT": product_column, "CATEGORY": category_column}
    for encoding_label, first_dimension in encoding_dimensions.items():
        encoding_window = Window.partitionBy(
            first_dimension, "tadmprodrollup_fnl", "cos_hccc_cd", "fin_inc_month"
        )
        features = features.withColumn(
            f"{encoding_label}_ENCODED_{metric}_PRE",
            F.avg(target_column).over(encoding_window),
        )

    # --- Windows for per-time-series features ---------------------------------
    ordered_window = Window.partitionBy(*group_columns).orderBy(*ORDER_COLUMNS)
    # Trailing 12 rows, current row excluded (== pandas shift(1).rolling(12)).
    rolling_window = ordered_window.rowsBetween(-ROLLING_FEATURE_WINDOW, -1)

    # --- Step 2: lagged targets (value k months ago) --------------------------
    for lag_months in (1, 2, 3, 12):
        features = features.withColumn(
            f"TARGET_{metric}_{lag_months}",
            F.lag(target_column, lag_months).over(ordered_window),
        )

    # --- Step 3: rolling mean of each encoding (leakage-safe) -----------------
    for encoding_label in encoding_dimensions:
        encoding_values = nan_inf_to_null(F.col(f"{encoding_label}_ENCODED_{metric}_PRE"))
        observed_count = F.count(encoding_values).over(rolling_window)
        features = features.withColumn(
            f"{encoding_label}_ENCODED_{metric}",
            F.when(
                observed_count >= ROLLING_FEATURE_MIN_PERIODS,
                F.avg(encoding_values).over(rolling_window),
            ),
        )

    # --- Step 4: rolling sample variance of the target ------------------------
    # var_samp is Bessel-corrected (denominator n-1), matching pandas .var().
    target_values = nan_inf_to_null(F.col(target_column))
    target_count = F.count(target_values).over(rolling_window)
    features = features.withColumn(
        f"VARIANCE_12_MO_{metric}",
        F.when(
            target_count >= ROLLING_FEATURE_MIN_PERIODS,
            F.var_samp(target_values).over(rolling_window),
        ),
    )

    # --- Step 5: rolling count of zero months in the BF estimate --------------
    zero_indicator = F.when(floor_near_zero(F.col(bf_column)) == 0, 1).otherwise(0)
    # Parity note: the legacy zero-count's min_periods counts window slots
    # (including a phantom leading position), so it emits once the row's ordinal
    # position reaches the threshold. row_number reproduces that exactly.
    ordinal_position = F.row_number().over(ordered_window)
    features = features.withColumn(
        f"COUNT_ZEROS_{metric}",
        F.when(
            ordinal_position >= ROLLING_FEATURE_MIN_PERIODS,
            F.sum(zero_indicator).over(rolling_window),
        ).cast("double"),
    )

    return features


def _legacy_rolling_slope_shift1(values, window, min_periods):
    """Rolling OLS slope over the prior-row-shifted series (legacy behavior).

    Copied from the original ``numpy_time_series_utils.rolling_slope_shift1`` so
    this file has no cross-repo dependency. Preserves the legacy rule where zeros
    in a window are replaced by that window's non-zero mean, and the replacement
    persists into later overlapping windows (stateful/order-dependent). That
    statefulness is exactly why this cannot be a native Spark window aggregate.
    """
    shifted = np.full(values.shape[0], np.nan, dtype=np.float64)
    if values.shape[0] > 1:
        shifted[1:] = values[:-1]

    result = np.full(values.shape[0], np.nan, dtype=np.float64)
    if window <= 0 or min_periods < 2 or min_periods > window:
        return result

    for end in range(shifted.shape[0]):
        start = max(0, end - window + 1)
        window_values = shifted[start:end + 1]

        finite_mask = np.isfinite(window_values)
        if finite_mask.sum() < min_periods or not finite_mask.all():
            continue

        window_values = window_values.copy()
        if np.any(window_values != 0):
            replacement = window_values[window_values != 0].mean()
            zero_mask = window_values == 0
            if np.any(zero_mask):
                positions = np.arange(start, end + 1, dtype=np.int64)
                shifted[positions[zero_mask]] = replacement  # persist for later windows
                window_values[zero_mask] = replacement

        length = window_values.shape[0]
        if length < 2:
            continue

        x = np.arange(length, dtype=np.float64)
        x_centered = x - x.mean()
        denominator = np.sum(x_centered * x_centered)
        if denominator == 0.0:
            continue

        y_centered = window_values - window_values.mean()
        result[end] = np.sum(y_centered * x_centered) / denominator

    return result


def add_slope_feature(claims, group_columns, metric):
    """
    Add ``SLOPE_12_{metric}`` using ``applyInPandas`` and the legacy numpy routine.
    """
    bf_column = "bf_estimate_util_k" if metric == "UTIL" else "bf_estimate_pmpm"
    slope_column = f"SLOPE_12_{metric}"
    order_columns = list(ORDER_COLUMNS)

    output_schema = claims.schema.add(slope_column, "double")

    def compute_group_slope(group_frame: pd.DataFrame) -> pd.DataFrame:
        # applyInPandas does not guarantee row order, so sort chronologically first.
        group_frame = group_frame.sort_values(order_columns).reset_index(drop=True)
        bf_values = group_frame[bf_column].to_numpy(dtype=np.float64)
        near_zero = np.isfinite(bf_values) & (np.abs(bf_values) < ZERO_FLOOR_EPSILON)
        bf_values[near_zero] = 0.0
        group_frame[slope_column] = _legacy_rolling_slope_shift1(
            bf_values, window=ROLLING_FEATURE_WINDOW, min_periods=ROLLING_FEATURE_MIN_PERIODS
        )
        return group_frame

    return claims.groupby(*group_columns).applyInPandas(compute_group_slope, schema=output_schema)

# COMMAND ----------

# DBTITLE 1,Join Features & Build Output
# --------------------------------------------------------------------------- #
# Build output & write
# --------------------------------------------------------------------------- #

def build_final_output(claims, config):
    """Select the identifier + target + feature columns for the output table."""
    claims = claims.withColumn("VAL_DATE", F.to_date(F.lit(config["val_date_str"])))

    identifier_columns = (
        config["cf_product_level"] + config["cf_claim_level"] + config["cf_dates"] + ["VAL_DATE"]
    )
    value_columns = ["TARGET_UTIL", "TARGET_PMPM"] + config["features"]

    return claims.select(*(identifier_columns + value_columns))


def write_val_date_delta(spark, output, config):
    """Atomically write the stage output, replacing only this VAL_DATE partition.

    Uses Delta ``replaceWhere`` so re-running a valuation date overwrites just that
    date's rows and leaves other dates untouched. On first run the table is created.
    """
    full_table_name = f"{config['catalog']}.{config['schema']}.{config['output_table']}"
    write_to_catalog(
        spark, output, full_table_name, f"VAL_DATE = DATE('{config['val_date_str']}')"
    )
    return full_table_name

# COMMAND ----------

# DBTITLE 1,Orchestration (run)
# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def run(
    spark,
    run_val_date,
    source_table,
    target_table,
    write_catalog,
    write_schema,
):
    """Execute the feature engineering stage end to end and return a status summary."""
    config = build_stage_config(
        run_val_date,
        source_table,
        target_table,
        write_catalog,
        write_schema,
    )

    # 1. Load the pre-aggregated SPINE (renames columns, derives targets).
    claims = load_source(spark, config)

    # Derive seasonality feature (month-of-year 1-12) for the downstream model.
    claims = claims.withColumn("seasonality_month", (F.col("fin_inc_month") % 100).cast("int"))

    # 2. Engineer time-series features per product/claim slice.
    group_columns = config["cf_product_level"] + config["cf_claim_level"]

    product_column = config["product_column"]
    category_column = config["category_column"]
    for metric in ["UTIL", "PMPM"]:
        claims = add_metric_features(claims, group_columns, metric, product_column, category_column)
        claims = add_slope_feature(claims, group_columns, metric)

    # 3. Assemble and write the output table.
    output = build_final_output(claims, config)
    rows_written = output.count()
    full_table_name = f"{config['catalog']}.{config['schema']}.{config['output_table']}"
    write_val_date_delta(spark, output, config)

    return {
        "status": "SUCCESS",
        "target_table": full_table_name,
        "rows_written": int(rows_written),
    }

# COMMAND ----------

# DBTITLE 1,Execute
# --------------------------------------------------------------------------- #
# Run the feature engineering pipeline
# --------------------------------------------------------------------------- #
result = run(
    spark=spark,
    run_val_date="2026-07-01",
    source_table=f"{catalog}.{schema}.{in_table_name}",
    target_table=out_table_name,
    write_catalog=catalog,
    write_schema=schema,
)
print(result)

display(spark.table(f"{catalog}.{schema}.{out_table_name}"))
