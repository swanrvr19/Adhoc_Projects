# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # S04 — Train LightGBM Model

# COMMAND ----------

# The RUN_PIPELINE variable is used by the S05 Backtesting notebook to control whether the pipeline is executed. 
# This allows the notebook to be referenced by other notebooks for function definitions without triggering a pipeline run.
# When the notebook is executed as a standalone process (outside of the backtesting framework), RUN_PIPELINE is automatically set to TRUE, which initiates 
# the pipeline execution
try:
    RUN_PIPELINE
except NameError:
    RUN_PIPELINE = True

# COMMAND ----------

# MAGIC %run "./S00_Config"

# COMMAND ----------

# DBTITLE 1,Imports
from __future__ import annotations

import numpy as np
import pandas as pd
from pyspark.sql import DataFrame, Window
from pyspark.sql import functions as F
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    StringType,
    StructField,
    StructType,
)

# COMMAND ----------

# DBTITLE 1,Configuration
def build_config(val_date, train_end_month):
    """Build the run configuration for the LightGBM forecast.

    Parameters
    ----------
    val_date : str
        Valuation date (e.g. "2026-07-01") matching the VAL_DATE in the source.
    train_end_month : int
        Last fin_inc_month to include in training (e.g. 202601).
    """
    projection_start = _next_fin_month(train_end_month)
    projection_months = 1

    config = {
        "metrics": ["PMPM", "UTIL"],
        "val_date": val_date,
        "train_end_month": train_end_month,
        "train_start_lead_months": 12,       # per-group burn-in
        "test_offset_months": 1,             # last month held out for early stopping
        "projection_months": projection_months,
        "projection_start": projection_start,
        "projection_end": _offset_fin_month(projection_start, projection_months - 1),
        "run_timestamp": pd.Timestamp.now(),

        # Source table (S03 output)
        "source_table": table_fqn("model"),

        # Output tables
        "catalog": CATALOG,
        "schema": SCHEMA,
        "forecast_table": TABLES["forecast"],
        "shap_table": TABLES["shap"],

        # Grain that identifies one product/market time series
        "series_group": SERIES_GROUP,

        # Subset of grain used to partition applyInPandas model groups
        "model_group": MODEL_GROUP,

        # Encoding dimension mappings (matches S03 feature engineering)
        "encoding_dimensions": ENCODING_DIMENSIONS,

        # Columns LightGBM treats as native categoricals
        "categorical_columns": CATEGORICAL_COLUMNS,
    }

    config["features"] = {metric: model_feature_list(metric) for metric in config["metrics"]}
    return config


# --------------------------------------------------------------------------- #
# fin_inc_month arithmetic helpers
# --------------------------------------------------------------------------- #
def _next_fin_month(fin_month):
    """Advance a fin_inc_month integer by one month (e.g. 202612 -> 202701)."""
    year, month = divmod(fin_month, 100)
    if month == 12:
        return (year + 1) * 100 + 1
    return year * 100 + month + 1


def _offset_fin_month(fin_month, n_months):
    """Offset a fin_inc_month integer by n months (positive = forward)."""
    year, month = divmod(fin_month, 100)
    total_months = (year * 12 + month - 1) + n_months
    new_year, new_month_idx = divmod(total_months, 12)
    return new_year * 100 + new_month_idx + 1


def _fin_month_to_linear(fin_month):
    """Convert fin_inc_month (YYYYMM) to a linear month index for arithmetic."""
    year, month = divmod(fin_month, 100)
    return year * 12 + month


# COMMAND ----------

# DBTITLE 1,Data Preparation
def load_source(spark, config):
    """Load the S03 model-ready data, filtered to the valuation version."""
    source = spark.table(config["source_table"]).filter(
        F.col("VAL_DATE") == F.to_date(F.lit(config["val_date"]))
    )
    source = cast_decimals_to_double(source)
    row_count = source.count()
    if row_count == 0:
        raise ValueError(
            f"No rows found in {config['source_table']} for VAL_DATE={config['val_date']}"
        )
    print(f"Loaded {row_count:,} rows from {config['source_table']}")
    return source


def apply_training_window(source, config):
    """Keep only months within the training window, per series.

    Each series starts ``train_start_lead_months`` after its first observation
    (the rolling features are unreliable before then). ``N_TRAIN_MONTHS`` records
    how many months each series contributes.
    """
    group_columns = config["series_group"]
    first_month_window = Window.partitionBy(*group_columns)
    lead = config["train_start_lead_months"]
    train_end = config["train_end_month"]

    windowed = (
        source
        .withColumn("MIN_MONTH", F.min("fin_inc_month").over(first_month_window))
        .withColumn("TRAIN_START_MONTH", _spark_offset_month(F.col("MIN_MONTH"), lead))
        .filter(F.col("fin_inc_month") >= F.col("TRAIN_START_MONTH"))
        .filter(F.col("fin_inc_month") <= F.lit(train_end))
    )

    train_end_linear = _fin_month_to_linear(train_end)
    return windowed.withColumn(
        "N_TRAIN_MONTHS",
        F.lit(train_end_linear) - _spark_fin_to_linear(F.col("TRAIN_START_MONTH")),
    )


def _spark_offset_month(col_expr, n_months):
    """Spark expression: offset a fin_inc_month column by n months."""
    year = (col_expr / 100).cast("int")
    month = col_expr % 100
    total = year * 12 + month - 1 + n_months
    new_year = (total / 12).cast("int")
    new_month = total % 12 + 1
    return (new_year * 100 + new_month).cast("int")


def _spark_fin_to_linear(col_expr):
    """Spark expression: convert fin_inc_month to a linear month index."""
    year = (col_expr / 100).cast("int")
    month = col_expr % 100
    return year * 12 + month


def clamp_negative_pmpm(df):
    """Floor negative PMPM targets at 0 (negatives hurt Tweedie)."""
    return df.withColumn(
        "TARGET_PMPM",
        F.when(F.col("TARGET_PMPM") < 0, F.lit(0.0)).otherwise(F.col("TARGET_PMPM")),
    )



def prepare_training_data(spark, config):
    """Load and prepare the model-ready training frame."""
    source = load_source(spark, config)
    windowed = apply_training_window(source, config)
    return clamp_negative_pmpm(windowed)

# COMMAND ----------

# DBTITLE 1,LightGBM Hyperparameters
def build_lightgbm_params():
    """
    The seed +
    deterministic + single-thread settings make training reproducible so the SHAP
    pass explains the same model the forecast pass used.
    """
    return {
        "objective": "tweedie",
        "metric": "rmse",
        "boosting_type": "gbdt",
        "learning_rate": 0.01,
        "num_leaves": 31,
        "max_depth": 6,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbose": -1,
        "early_stopping_rounds": 100,
        "seed": 42,
        # "deterministic": True,
        # "num_threads": 1,
    }

# COMMAND ----------

# DBTITLE 1,Fit Light GBM Model
def _cast_categoricals(frame, config):
    """Cast categoricals and coerce remaining object columns to numeric for LightGBM.

    LightGBM rejects non-categorical object columns, so any leftover string-typed
    columns are coerced to float (invalid values become NaN).
    """
    import pandas as pd
    frame = frame.copy()
    for column in config["categorical_columns"]:
        if column in frame.columns:
            frame[column] = frame[column].astype("category")
    for col in list(frame.columns):
        if col not in config.get("categorical_columns", []) and frame[col].dtype == object:
            frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame


def _train_segment_model(segment_frame, metric, config):
    """Train one LightGBM model for a segment, using the last month as an early-stop tail."""
    import lightgbm as lgb

    features = config["features"][metric]
    frame = _cast_categoricals(segment_frame, config)
    numeric_features = [f for f in features if f not in config["categorical_columns"]]
    frame[numeric_features] = frame[numeric_features].astype(float)

    # Hold out the last month for early stopping
    split_month = _offset_fin_month(config["train_end_month"], -config["test_offset_months"])
    train_frame = frame[frame["fin_inc_month"] <= split_month]
    test_frame = frame[frame["fin_inc_month"] > split_month]

    categorical_features = [c for c in config["categorical_columns"] if c in features]
    train_dataset = lgb.Dataset(
        train_frame[features], label=train_frame[f"TARGET_{metric}"],
        categorical_feature=categorical_features,
    )
    test_dataset = lgb.Dataset(
        test_frame[features], label=test_frame[f"TARGET_{metric}"],
        categorical_feature=categorical_features,
    )

    return lgb.train(
        build_lightgbm_params(),
        train_dataset,
        num_boost_round=10000,
        valid_sets=[test_dataset],
    )


def _rolling_slope(series_values):
    """OLS slope of a short series vs. time index; None if it cannot be computed."""
    from scipy.stats import linregress

    try:
        slope = linregress(range(len(series_values)), series_values).slope
    except Exception:
        return None
    return slope

# COMMAND ----------

# DBTITLE 1,Recursive Forecast Functions
def _append_projected_month(history, metric, config):
    """Append the next calendar month to a segment's history (targets left blank).

    Clone the latest month, advance fin_inc_month, null out target-derived features
    (they get recomputed from history), and keep auxiliary columns (sum_member_cnt)
    carried forward.
    """
    latest_month = history["fin_inc_month"].max()

    next_month = history[history["fin_inc_month"] == latest_month].copy()
    next_month["fin_inc_month"] = next_month["fin_inc_month"].apply(_next_fin_month)
    next_month["seasonality_month"] = next_month["fin_inc_month"] % 100

    # Recompute the "pre" target encodings for the new month.
    enc_dims = config["encoding_dimensions"]
    next_month[f"MARKET_ENCODED_{metric}_PRE"] = next_month.groupby([enc_dims["MARKET"], "fin_inc_month"])[f"TARGET_{metric}"].transform("mean")
    next_month[f"CATEGORY_ENCODED_{metric}_PRE"] = next_month.groupby([enc_dims["CATEGORY"], "fin_inc_month"])[f"TARGET_{metric}"].transform("mean")
    next_month[f"PRODUCT_ENCODED_{metric}_PRE"] = next_month.groupby([enc_dims["PRODUCT"], "fin_inc_month"])[f"TARGET_{metric}"].transform("mean")

    # These are rebuilt from history in _recompute_last_month_features; blank them now.
    columns_to_reset = [
        f"MARKET_ENCODED_{metric}", f"CATEGORY_ENCODED_{metric}", f"PRODUCT_ENCODED_{metric}",
        f"TARGET_{metric}", f"TARGET_{metric}_1", f"TARGET_{metric}_2", f"TARGET_{metric}_3", f"TARGET_{metric}_12",
        f"COUNT_ZEROS_{metric}", f"VARIANCE_12_MO_{metric}", f"SLOPE_12_{metric}",
    ]
    for column in columns_to_reset:
        next_month[column] = np.nan

    extended = pd.concat([history, next_month])
    sort_group = config["series_group"] + ["fin_inc_month"]
    return extended.sort_values(by=sort_group).reset_index(drop=True)


def _recompute_last_month_features(extended, metric, config):
    """Rebuild the autoregressive features for the newest month, then return only that month.

    Mirrors the notebook's ``new_features``: the same shift/rolling math used in
    feature engineering, applied to the growing history so the model sees features
    shaped exactly as during training.
    """
    group = config["series_group"]
    latest_month = extended["fin_inc_month"].max()
    is_last = extended["fin_inc_month"] == latest_month

    def rolling_mean_of_encoding(encoding_pre_column):
        return extended.groupby(group)[encoding_pre_column].transform(
            lambda values: values.shift(1).rolling(window=12, min_periods=3).mean()
        )

    extended.loc[is_last, f"MARKET_ENCODED_{metric}"] = rolling_mean_of_encoding(f"MARKET_ENCODED_{metric}_PRE")
    extended.loc[is_last, f"PRODUCT_ENCODED_{metric}"] = rolling_mean_of_encoding(f"PRODUCT_ENCODED_{metric}_PRE")
    extended.loc[is_last, f"CATEGORY_ENCODED_{metric}"] = rolling_mean_of_encoding(f"CATEGORY_ENCODED_{metric}_PRE")

    extended.loc[is_last, f"TARGET_{metric}_1"] = extended.groupby(group)[f"TARGET_{metric}"].shift(1)
    extended.loc[is_last, f"TARGET_{metric}_2"] = extended.groupby(group)[f"TARGET_{metric}"].shift(2)
    extended.loc[is_last, f"TARGET_{metric}_3"] = extended.groupby(group)[f"TARGET_{metric}"].shift(3)
    extended.loc[is_last, f"TARGET_{metric}_12"] = (
        extended.groupby(group)[f"TARGET_{metric}"].shift(12)
        .fillna(extended.groupby(group)[f"TARGET_{metric}"].transform("mean"))
    )

    extended.loc[is_last, f"COUNT_ZEROS_{metric}"] = extended.groupby(group)[f"TARGET_{metric}"].transform(
        lambda values: (values.shift(1) == 0).rolling(window=12, min_periods=3).sum()
    )
    extended.loc[is_last, f"VARIANCE_12_MO_{metric}"] = extended.groupby(group)[f"TARGET_{metric}"].transform(
        lambda values: values.shift(1).rolling(window=12, min_periods=3).var()
    )
    extended.loc[is_last, f"SLOPE_12_{metric}"] = extended.groupby(group)[f"TARGET_{metric}"].transform(
        lambda values: values.shift(1).rolling(window=12, min_periods=2).apply(_rolling_slope, raw=False)
    )
    extended.loc[is_last, f"SLOPE_12_{metric}"] = extended.groupby(group)[f"SLOPE_12_{metric}"].ffill()

    return extended[is_last].copy()


def _recursive_forecast_segment(segment_frame, model, metric, config):
    """
    Project ``projection_months`` forward, feeding each prediction back as history.
    """
    features = config["features"][metric]
    history = segment_frame[segment_frame["fin_inc_month"] < config["projection_start"]].copy()
    projected_months = []

    for _ in range(config["projection_months"]):
        extended = _append_projected_month(history, metric, config)
        new_month = _recompute_last_month_features(extended, metric, config)

        model_inputs = _cast_categoricals(new_month, config)[features]
        new_month[f"TARGET_{metric}"] = model.predict(model_inputs, num_iteration=model.best_iteration)

        history = pd.concat([history, new_month]).sort_values(
            by=config["series_group"] + ["fin_inc_month"]
        ).reset_index(drop=True)
        projected_months.append(new_month)

    return pd.concat(projected_months, ignore_index=True)

# COMMAND ----------

# DBTITLE 1,Forecast Output
def _forecast_output_schema(metric):
    """Schema returned by the per-segment forecast function."""
    identifier_fields = [
        StructField("global_cap", StringType()),
        StructField("market_fnl", StringType()),
        StructField("tadmprodrollup_fnl", StringType()),
        StructField("tfm_product_fnl", StringType()),
        StructField("segment_name_fnl", StringType()),
        StructField("drug_cov_type_fnl", StringType()),
        StructField("cos_hccc_cd", StringType()),
        StructField("service_code", StringType()),
        StructField("fin_inc_month", IntegerType()),
        StructField("N_TRAIN_MONTHS", IntegerType()),
        StructField("sum_member_cnt", DoubleType()),
    ]
    return StructType(identifier_fields + [StructField(f"TARGET_{metric}_PREDICTED", DoubleType())])


def combine_metric_forecasts(forecast_by_metric, config):
    """Merge the per-metric forecast tables into one wide PMPM + UTIL table."""
    key_columns = config["series_group"] + ["fin_inc_month"]
    combined = forecast_by_metric["PMPM"]
    util_predictions = forecast_by_metric["UTIL"].select(*key_columns, "TARGET_UTIL_PREDICTED")
    return combined.join(util_predictions, on=key_columns, how="left")


def add_run_metadata(output, config):
    """Stamp scenario metadata columns onto an output table."""
    return output.withColumns({
        "VAL_DATE": F.lit(config["val_date"]),
        "TRAIN_END_MONTH": F.lit(config["train_end_month"]),
        "TRAIN_START_LEAD": F.lit(config["train_start_lead_months"]),
        "PROJECTION_START": F.lit(config["projection_start"]),
        "PROJECTION_END": F.lit(config["projection_end"]),
        "RUN_TIMESTAMP": F.lit(config["run_timestamp"].strftime("%Y-%m-%d %H:%M:%S")),
    })


def _combined_output_schema(metric, config):
    """Schema for the single-pass forecast + SHAP UDF output."""
    identifier_fields = [
        StructField("global_cap", StringType()),
        StructField("market_fnl", StringType()),
        StructField("tadmprodrollup_fnl", StringType()),
        StructField("tfm_product_fnl", StringType()),
        StructField("segment_name_fnl", StringType()),
        StructField("drug_cov_type_fnl", StringType()),
        StructField("cos_hccc_cd", StringType()),
        StructField("service_code", StringType()),
        StructField("fin_inc_month", IntegerType()),
        StructField("N_TRAIN_MONTHS", IntegerType()),
        StructField("sum_member_cnt", DoubleType()),
    ]
    prediction_field = [StructField(f"TARGET_{metric}_PREDICTED", DoubleType())]
    shap_fields = [StructField(f"{feature}_SHAP", DoubleType()) for feature in config["features"][metric]]
    tail_fields = [StructField("EXPECTED_VALUE", DoubleType())]
    return StructType(identifier_fields + prediction_field + shap_fields + tail_fields)


def forecast_and_explain_all_segments(prepared_data, metric, config):
    """Train, forecast, and explain in a single pass per model group.
    """
    output_schema = _combined_output_schema(metric, config)
    output_columns = [field.name for field in output_schema.fields]

    def run_group(segment_frame: pd.DataFrame) -> pd.DataFrame:
        model = _train_segment_model(segment_frame, metric, config)
        forecast = _recursive_forecast_segment(segment_frame, model, metric, config)

        explained = _adjusted_shap_for_segment(forecast, model, metric, config)
        explained[f"TARGET_{metric}_PREDICTED"] = explained[f"TARGET_{metric}"].round(4)
        return explained[output_columns]

    return prepared_data.groupBy(*config["model_group"]).applyInPandas(run_group, schema=output_schema)


def write_scenario_table(spark, output, table_short_name, config):
    """Idempotently write a scenario: replace only this (VAL_DATE, TRAIN_END) partition.

    Delta ``replaceWhere`` overwrites just the rows matching the current scenario so
    re-running is safe and leaves other scenarios untouched. The table is created on
    first write.
    """
    full_table_name = f"{config['catalog']}.{config['schema']}.{table_short_name}"
    replace_where = (
        f"VAL_DATE = '{config['val_date']}' AND TRAIN_END_MONTH = {config['train_end_month']}"
    )
    write_to_catalog(spark, output, full_table_name, replace_where)
    return full_table_name

# COMMAND ----------

# DBTITLE 1,SHAP
# --------------------------------------------------------------------------- #
# SHAP explanation (parallel per-segment pass)
# --------------------------------------------------------------------------- #
def _explanation_output_schema(metric, config):
    """Schema for the per-segment SHAP UDF: identifiers + one <feature>_SHAP per feature."""
    identifier_fields = [
        StructField("global_cap", StringType()),
        StructField("market_fnl", StringType()),
        StructField("tadmprodrollup_fnl", StringType()),
        StructField("tfm_product_fnl", StringType()),
        StructField("segment_name_fnl", StringType()),
        StructField("drug_cov_type_fnl", StringType()),
        StructField("cos_hccc_cd", StringType()),
        StructField("service_code", StringType()),
        StructField("fin_inc_month", IntegerType()),
        StructField("N_TRAIN_MONTHS", IntegerType()),
    ]
    shap_fields = [StructField(f"{feature}_SHAP", DoubleType()) for feature in config["features"][metric]]
    tail_fields = [
        StructField(f"TARGET_{metric}_PREDICTED", DoubleType()),
        StructField("EXPECTED_VALUE", DoubleType()),
    ]
    return StructType(identifier_fields + shap_fields + tail_fields)


def _adjusted_shap_for_segment(projected_frame, model, metric, config):
    """Compute the notebook's adjusted SHAP values for one segment's projected months.

    Mirrors the notebook exactly: raw TreeExplainer values are rescaled so that,
    per row, they *distribute the residual* ``predicted - exp(expected_value)``
    across features in proportion to each feature's raw contribution. ``exp`` undoes
    the Tweedie log link so EXPECTED_VALUE is on the target's natural scale.
    """
    import shap

    features = config["features"][metric]
    shap_columns = [f"{feature}_SHAP" for feature in features]

    model_inputs = _cast_categoricals(projected_frame, config)[features]
    explainer = shap.TreeExplainer(model)
    raw_values = explainer.shap_values(model_inputs)

    expected_raw = explainer.expected_value
    if isinstance(expected_raw, (list, tuple, np.ndarray)):
        expected_raw = float(np.ravel(expected_raw)[0])
    expected_value = float(np.exp(expected_raw))

    shap_frame = pd.DataFrame(raw_values, columns=shap_columns).reset_index(drop=True)
    predicted_target = projected_frame[f"TARGET_{metric}"].reset_index(drop=True).to_numpy()
    total_feature_impact = shap_frame[shap_columns].sum(axis=1)

    # Rescale each feature's share of the residual; guard the zero-impact edge case.
    scale = (predicted_target - expected_value) / total_feature_impact.replace(0, np.nan)
    for column in shap_columns:
        shap_frame[column] = shap_frame[column] * scale
    shap_frame["EXPECTED_VALUE"] = expected_value

    explained = projected_frame.reset_index(drop=True).join(shap_frame)
    return explained


def combine_metric_explanations(explanation_by_metric, config):
    """Stack the per-metric SHAP tables into one long table with a METRIC column.

    """
    parts = [
        explanation_by_metric[metric].withColumn("METRIC", F.lit(metric))
        for metric in config["metrics"]
    ]
    stacked = parts[0]
    for part in parts[1:]:
        stacked = stacked.unionByName(part, allowMissingColumns=True)
    return stacked

# COMMAND ----------

# DBTITLE 1,Orchestration
def run(spark, val_date, train_end_month):
    """Execute the LightGBM forecast for all model groups in one distributed job.

    Uses a single-pass function per metric that trains, forecasts, and computes SHAP in
    one go. 

    Parameters
    ----------
    spark : SparkSession
    val_date : str
        Valuation date matching the VAL_DATE in the source (e.g. "2026-07-01").
    train_end_month : int
        Last fin_inc_month to include in training (e.g. 202607).

    Returns a status summary dict.
    """
    import gc

    config = build_config(val_date, train_end_month)

    # Reduce concurrent tasks to limit Python worker memory pressure.
    spark.conf.set("spark.sql.shuffle.partitions", "32")

    # 1. Load and window the training data; cache to avoid recomputation.
    prepared_data = prepare_training_data(spark, config)
    prepared_data.cache()
    prepared_data.count()

    # 2. Train + forecast + SHAP in one pass per metric (eliminates double-train).
    combined_by_metric = {}
    for metric in config["metrics"]:
        combined_by_metric[metric] = forecast_and_explain_all_segments(
            prepared_data, metric, config
        ).cache()
        combined_by_metric[metric].count()
        gc.collect()

    # 3. Extract forecast columns, combine metrics, stamp metadata, and write.
    forecast_columns = config["series_group"] + ["fin_inc_month", "N_TRAIN_MONTHS", "sum_member_cnt"]
    forecast_by_metric = {
        metric: combined_by_metric[metric].select(*forecast_columns, f"TARGET_{metric}_PREDICTED")
        for metric in config["metrics"]
    }
    combined_forecast = combine_metric_forecasts(forecast_by_metric, config)
    combined_forecast = add_run_metadata(combined_forecast, config)
    forecast_table = write_scenario_table(spark, combined_forecast, config["forecast_table"], config)
    rows_written = spark.read.table(forecast_table).count()

    # 4. Extract SHAP columns, combine metrics, stamp metadata, and write.
    shap_base_columns = config["series_group"] + ["fin_inc_month", "N_TRAIN_MONTHS"]
    explanation_by_metric = {}
    for metric in config["metrics"]:
        features = config["features"][metric]
        shap_cols = [f"{f}_SHAP" for f in features]
        select_cols = shap_base_columns + shap_cols + [f"TARGET_{metric}_PREDICTED", "EXPECTED_VALUE"]
        explanation_by_metric[metric] = combined_by_metric[metric].select(*select_cols)

    combined_shap = combine_metric_explanations(explanation_by_metric, config)
    combined_shap = add_run_metadata(combined_shap, config)
    shap_table = write_scenario_table(spark, combined_shap, config["shap_table"], config)
    shap_rows_written = spark.read.table(shap_table).count()

    # Cleanup.
    for c in combined_by_metric.values():
        c.unpersist()
    prepared_data.unpersist()

    return {
        "status": "SUCCESS",
        "forecast_table": forecast_table,
        "forecast_rows": int(rows_written),
        "shap_table": shap_table,
        "shap_rows": int(shap_rows_written),
    }

# COMMAND ----------

# DBTITLE 1,Execute
if RUN_PIPELINE:
    result = run(spark, val_date="2026-07-01", train_end_month=202607)
    print(result)

# COMMAND ----------

# DBTITLE 1,Check: Monthly Forecast Rollup
# Member-weighted monthly rollup of forecast PMPM and utilization.
# Membership is duplicated across claim splits (cos_hccc_cd, service_code),
# so deduplicate to the enrollment-group grain before summing.

if RUN_PIPELINE:

    forecast = spark.read.table(table_fqn("forecast")).filter(
        (F.col("VAL_DATE") == "2026-07-01") & (F.col("TRAIN_END_MONTH") == 202607)
    )

    # Deduplicate membership to enrollment-group + month grain
    members_by_month = (
        forecast
        .select(*ENROLL_KEYS, "fin_inc_month", "sum_member_cnt")
        .distinct()
        .groupBy("fin_inc_month")
        .agg(F.sum("sum_member_cnt").alias("total_members"))
    )

    # Weighted numerators: TARGET_*_PREDICTED are per-split per-member metrics.
    # Multiplying by sum_member_cnt recovers the underlying totals across all splits.
    numerators_by_month = (
        forecast
        .groupBy("fin_inc_month")
        .agg(
            F.sum(F.col("TARGET_PMPM_PREDICTED") * F.col("sum_member_cnt")).alias("total_pmpm_weighted"),
            F.sum(F.col("TARGET_UTIL_PREDICTED") * F.col("sum_member_cnt")).alias("total_util_weighted"),
        )
    )

    # Join and calculate member-weighted averages
    monthly_rollup = (
        numerators_by_month
        .join(members_by_month, on="fin_inc_month")
        .withColumn("forecast_pmpm", F.col("total_pmpm_weighted") / F.col("total_members"))
        .withColumn("forecast_utilization", F.col("total_util_weighted") / F.col("total_members"))
        .select("fin_inc_month", "forecast_pmpm", "forecast_utilization")
        .orderBy("fin_inc_month")
    )

    display(monthly_rollup)
