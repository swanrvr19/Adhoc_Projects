# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # S00 — Shared Configuration
# MAGIC
# MAGIC **Usage** — load it at the top of each stage notebook:
# MAGIC
# MAGIC ```
# MAGIC %run "./S00_Config"
# MAGIC ```
# MAGIC

# COMMAND ----------

# DBTITLE 1,Catalog / Schema / Tables
CATALOG = "prod_tadm"
SCHEMA  = "mr_cos_prod_actuarial"

# Short key -> table name. Fully-qualify with table_fqn(key).
TABLES = {
    "clm":      "DEV_TFM_HCTA_MnR_CLM_DATA",           # S01 claims extract
    "mbr":      "DEV_TFM_HCTA_MnR_MBR_DATA",           # S01 membership extract
    "util_metric": "DEV_TFM_HCTA_MnR_UTIL_METRIC",     # S01A util metric per claim split
    "cf":       "DEV_TFM_HCTA_MnR_CF_FACTORS",         # S01B completion factors
    "spine":    "DEV_TFM_HCTA_MnR_CLM_MBR_SPINE",      # S02 claims+membership spine
    "model":    "DEV_TFM_HCTA_MnR_MODEL_DATA",         # S03 model-ready features
    "forecast": "DEV_TFM_HCTA_MnR_FORECAST_OUTPUT",    # S04 forecast output
    "shap":     "DEV_TFM_HCTA_MnR_SHAP_OUTPUT",        # S04 SHAP output
    "backtest": "DEV_TFM_HCTA_MnR_BACKTEST_RESULTS",   # S05 backtest results
}


def table_fqn(key):
    """Return the fully-qualified `catalog.schema.table` name for a TABLES key."""
    return f"{CATALOG}.{SCHEMA}.{TABLES[key]}"

# COMMAND ----------

# DBTITLE 1,Grouping-Key Lists
# Enrollment slice: the columns that together identify one product/market group.
ENROLL_KEYS = [
    "global_cap", "market_fnl", "tadmprodrollup_fnl",
    "tfm_product_fnl", "segment_name_fnl", "drug_cov_type_fnl",
]

# Claim detail appended to the enrollment slice.
CLAIM_KEYS = ["hcc","service_code"]

# S02  Modeling Grains
MM_SPINE_KEYS  = ENROLL_KEYS + ["fin_inc_month"] 
CLM_SPLIT_KEYS = ENROLL_KEYS + CLAIM_KEYS

# Grain at which S01A assigns each claim split its utilization metric. Must be a
# subset of CLM_SPLIT_KEYS so the downstream join cannot fan out.
UTIL_METRIC_KEYS = CLAIM_KEYS

# S04/S05 grains.
SERIES_GROUP = ENROLL_KEYS + ["hcc", "service_code"]  # one time series
MODEL_GROUP  = ["hcc", "segment_name_fnl", "drug_cov_type_fnl"]  # applyInPandas partition

# Target-encoding dimension mappings (must match S03 feature engineering)
ENCODING_DIMENSIONS = {
    "MARKET":   "market_fnl",
    "PRODUCT":  "tadmprodrollup_fnl",
    "CATEGORY": "service_code",
}

# Columns LightGBM model treats as native categoricals
CATEGORICAL_COLUMNS = ["seasonality_month"]

# COMMAND ----------

# DBTITLE 1,Completion-Factor Settings (S01B)
# Dollar measures that each get their own development triangle.
# Key = short measure name written to the factor table; value = S01 claims column.
CF_MEASURES = {
    "allw":  "sum_allw_amt",   
    "netpd": "sum_net_pd_amt", 
}

# Used in S01A: the first column with a positive total across all available history wins
CF_UNIT_COLUMNS = [
    "sum_tadm_hcta_util","sum_admits","sum_tadm_units", "sum_visits", "sum_srvc_unit_cnt", "sum_adj_srvc_unit_cnt",
]

# Every measure written to the factor table.
CF_MEASURE_NAMES = list(CF_MEASURES.keys()) + ["util"]

# --- Ultimate lag: S01B measures where development actually flattens for each category and uses that as the 100%-complete point. 

# Level of detail at which the ultimate lag (i.e. months where runout is complete) is derived at 
CF_ULTIMATE_LAG_KEYS = ["hcc"]

# Calibration runout depth. Only mature incurred months are included, and their cumulative value at this lag serves as the reference total
CF_CALIBRATION_LAG_MONTHS = 24

# Completeness threshold used to determine the ultimate lag; Example: 0.995 = 99.5% of dollars emerged
CF_COMPLETENESS_THRESHOLD = 0.9950

# Applies bounds to the estimated value
CF_ULTIMATE_LAG_MIN     = 12
CF_ULTIMATE_LAG_MAX     = CF_CALIBRATION_LAG_MONTHS
CF_ULTIMATE_LAG_DEFAULT = 12

# Manual max ultimate claim lag overrides
# Example: {("PHYSICIAN",): 3, ("INPATIENT",): 18}
CF_ULTIMATE_LAG_OVERRIDES = {}

# --- Chain-ladder development factors -------------------------------------
# S01B fits age-to-age (duration-to-duration) link ratios per lag, chains them into
# cumulative development factors (CDFs), and inverts: completion factor = 1 / CDF.
#
# An incurred month qualifies for lag d's link ratio as soon as it has observed lag
# d+1; it does NOT need to have reached the ultimate lag

# Incurred months averaged together to produce each lag's link ratio.
# Note: S01B always excludes the newest development diagonal before taking this
# window, because the claims extract stops mid-month and that diagonal holds only a
# partial month of adjudication. The window shifts back rather than shrinking, so
# this many observations are still used.
CF_AVG_INCURRED_MONTHS = 12

# Trimmed mean: observations dropped from each tail, and the minimum observation count before trimming applies at all (below it, the mean is untrimmed)
CF_TRIM_COUNT       = 1
CF_MIN_OBS_FOR_TRIM = 4

# Credibility thresholds a grouping level must clear to be used for a given
# lag/measure. Levels that fail fall through to the next 'cf_fallback_levels' level (defined below)
CF_MIN_OBS = 3

# Minimum volume in the link DENOMINATOR (cumulative at lag d, summed over the fitting cohort). 
# The "Credibility Threshold Calibration" cell in S01B reports the actual
# distribution of the denominator per measure so both numbers can be reviewed & set from data.
CF_MIN_ULTIMATE_DOLLARS = 50_000.0
CF_MIN_ULTIMATE_UNITS   = 50.0

# Bounds on an individual age-to-age factor.
CF_LINK_RATIO_FLOOR = 1.0
CF_LINK_RATIO_CAP   = 10.0

# Floor on the CF factor, bounding the implied gross-up (i.e. 0.05 => at most 20x)
CF_FLOOR = 0.05

# Forces factors to be monotonically increasing
CF_ENFORCE_MONOTONIC = True

# --- Partial-month interpolation -------------------------------------------
# The extract stops mid-month (~calendar day 20/21; Last Calend Day (LCD) minus 10), so the newest incurred month's observation holds only
# part of a month of adjudication at its newest lag. 
#
# f = share of a complete month's adjudication landing on or before the paid-through day-of-month. Estimated empirically from complete historical months using the
# day-level adjd_dt in the S01 extract (accounts for payment-cycle and weekday effects)
#
# S01B then interpolates linearly between adjacent monthly factors:
#     CF*[d] = CF[d-1] + f * (CF[d] - CF[d-1])

# Grain at which f is estimated. Payment-cycle rhythm may vary by category; set to [] 
CF_PARTIAL_FRAC_KEYS = ["hcc"]

# Complete adjudication months used to estimate f. Median across them, so one odd month-end close cannot move it.
CF_PARTIAL_FRAC_MONTHS = 12

def cf_fallback_levels():
    """Credibility fallback ladder for S01B, Ordered most-specific first
    """
    return [
        ("SPLIT",       CLM_SPLIT_KEYS),
        ("ENROLL_HCCC", ENROLL_KEYS + ["hcc"]),
        ("MODEL_GROUP", MODEL_GROUP),
        ("ALL",         []),
    ]

# COMMAND ----------

# DBTITLE 1,Model Feature List (source of truth for S03 + S04)
# Auxiliary columns shared by both metrics and every model.
SHARED_FEATURES = ["sum_member_cnt", "seasonality_month"]

def _metric_features(metric):
    """The metric-specific engineered features for 'UTIL' or 'PMPM'."""
    return [
        f"MARKET_ENCODED_{metric}_PRE",   f"MARKET_ENCODED_{metric}",
        f"CATEGORY_ENCODED_{metric}_PRE", f"CATEGORY_ENCODED_{metric}",
        f"PRODUCT_ENCODED_{metric}_PRE",  f"PRODUCT_ENCODED_{metric}",
        f"TARGET_{metric}_1", f"TARGET_{metric}_2", f"TARGET_{metric}_3", f"TARGET_{metric}_12",
        f"COUNT_ZEROS_{metric}", f"VARIANCE_12_MO_{metric}", f"SLOPE_12_{metric}",
    ]


def model_feature_list(metric):
    """Per-metric LightGBM input columns (used by S04/S05 training)."""
    return _metric_features(metric) + SHARED_FEATURES


def model_output_features(metrics=("UTIL", "PMPM")):
    """Flat feature-column list written by S03 (both metrics, then shared columns)."""
    columns = []
    for metric in metrics:
        columns += _metric_features(metric)
    return columns + SHARED_FEATURES

# COMMAND ----------

# DBTITLE 1,Numeric Type Normalization
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType

def cast_decimals_to_double(df):
    """Cast every DecimalType column to double.

    Catalog `decimal(p,s)` columns deserialize to python `decimal.Decimal` inside
    pandas UDFs and raise TypeError when mixed with float (e.g. `float += Decimal`).
    """
    decimal_cols = [f.name for f in df.schema.fields if isinstance(f.dataType, DecimalType)]
    if not decimal_cols:
        return df
    return df.withColumns({c: F.col(c).cast("double") for c in decimal_cols})

# COMMAND ----------

# DBTITLE 1,Utilization-Metric Helpers (shared by S01A / S01B / S02)
def util_priority_expr():
    """Returns the first positive unit column, in CF_UNIT_COLUMNS (set above) priority order.
    """
    expr = F.lit(None).cast("string")
    for col in reversed(CF_UNIT_COLUMNS):
        expr = F.when(F.col(col) > 0, F.lit(col)).otherwise(expr)
    return expr


def util_populated_count_expr():
    """Count how many candidate unit columns are positive for a given row (helps assess ambiguity)"""
    return sum((F.col(col) > 0).cast("int") for col in CF_UNIT_COLUMNS)


def util_pick_expr(source_col="util_source_col"):
    """Return the value of whichever unit column `source_col` names.

    Assumes the four CF_UNIT_COLUMNS and `source_col` are all present on the frame.
    Yields null when `source_col` is null, matching S02's original behavior for
    splits with no positive unit column.
    """
    expr = F.lit(None).cast("double")
    for col in reversed(CF_UNIT_COLUMNS):
        expr = F.when(F.col(source_col) == col, F.col(col).cast("double")).otherwise(expr)
    return expr


# COMMAND ----------

# DBTITLE 1,Completion-Factor Helpers (S01B)
def cf_min_link_base_expr(measure_col="measure"):
    """Per-measure credibility threshold for the link denominator
    """
    expr = F.lit(CF_MIN_ULTIMATE_UNITS)
    for measure in CF_MEASURES:
        expr = F.when(F.col(measure_col) == measure, F.lit(CF_MIN_ULTIMATE_DOLLARS)).otherwise(expr)
    return expr

# COMMAND ----------

# DBTITLE 1,Catalog Delta Writer
def write_to_catalog(spark, df, full_name, replace_where):
    """Write df to Delta, replacing only the rows matching `replace_where`.

    On first write the table is created; on re-run only the matching slice is
    overwritten (e.g. "VAL_DATE = DATE('2026-07-01')"). Other slices are left untouched.

    All decimal columns are cast to double before writing so every table this
    pipeline produces (and therefore every downstream read) stays in float to avoid type errors.
    """
    df = cast_decimals_to_double(df)
    writer = df.write.format("delta").option("mergeSchema", "true")
    if spark.catalog.tableExists(full_name):
        writer = writer.option("replaceWhere", replace_where)
    writer.mode("overwrite").saveAsTable(full_name)
    print(f"Wrote {full_name} WHERE {replace_where}")
