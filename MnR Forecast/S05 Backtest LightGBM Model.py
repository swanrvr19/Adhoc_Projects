# Databricks notebook source
# MAGIC %md
# MAGIC # S05 — LightGBM Forecast Backtest
# MAGIC
# MAGIC Walk-forward backtest of the S04 LightGBM forecast. For each training-end month
# MAGIC (monthly, example: `202412` → `202603`) the model is trained on all data through that
# MAGIC month, forecast 12 months forward, and the forecast is compared
# MAGIC to realized actuals over the next **3** and **12** months for both metrics
# MAGIC (UTIL, PMPM).
# MAGIC
# MAGIC Model logic is **reused** from `S04 Train LightGBM Model Test` via `%run` — this
# MAGIC notebook only adds the backtest loop and the comparison rollups.
# MAGIC
# MAGIC Notes:
# MAGIC - Actuals come from the latest matured `MODEL_DATA` snapshot (`VAL_DATE`), subset
# MAGIC   by month. Windows extending past the last available actual month are compared
# MAGIC   over the **available months only**; `*_MONTHS_USED` records the coverage.
# MAGIC - Forecast and actual are aggregated over the *same* available months so each
# MAGIC   `*_ERROR` is an apples-to-apples absolute difference.

# COMMAND ----------

# DBTITLE 1,Load S04 functions only (skip its production run)
# Set BEFORE the %run so S04's guarded side-effect cells (install, training run,
# rollup displays) are skipped and only its function definitions load.
RUN_PIPELINE = False

# COMMAND ----------

# MAGIC %run "./S04 Train LightGBM Model Test"

# COMMAND ----------

# DBTITLE 1,Imports & backtest configuration
import gc
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType, IntegerType, StringType, StructField, StructType

BACKTEST = {
    "val_date": "2026-07-01",           # matured snapshot supplying training + actuals
    "first_train_end": 202412,          # first training-end month
    "last_train_end": 202501,           # last training-end month (inclusive)
    "projection_months": 12,            # forecast horizon per iteration
    "horizons": [3,12],                # summary windows (months)
    "metrics": ["UTIL", "PMPM"],        # column order in the output
    "catalog": CATALOG,
    "schema": SCHEMA,
    "results_table": TABLES["backtest"],
}

spark.conf.set("spark.sql.shuffle.partitions", "32")

# COMMAND ----------

# DBTITLE 1,Backtest helpers
def build_backtest_config(val_date, train_end_month, projection_months):
    """Reuse S04's build_config but override the horizon to the backtest length."""
    config = build_config(val_date, train_end_month)
    config["projection_months"] = projection_months
    config["projection_start"] = _next_fin_month(train_end_month)
    config["projection_end"] = _offset_fin_month(config["projection_start"], projection_months - 1)
    return config


def backtest_forecast_segments(prepared_data, metric, config):
    """Forecast-only distribution (no SHAP): train + recursive forecast per model group.

    Reuses S04's ``_train_segment_model`` and ``_recursive_forecast_segment`` so the
    projected values match a real S04 run; skips the SHAP pass the backtest doesn't need.
    """
    output_schema = _forecast_output_schema(metric)
    output_columns = [field.name for field in output_schema.fields]

    def run_group(segment_frame):
        model = _train_segment_model(segment_frame, metric, config)
        forecast = _recursive_forecast_segment(segment_frame, model, metric, config)
        forecast[f"TARGET_{metric}_PREDICTED"] = forecast[f"TARGET_{metric}"].round(4)
        return forecast[output_columns]

    return prepared_data.groupBy(*config["model_group"]).applyInPandas(run_group, schema=output_schema)


def month_window(projection_start, n_months):
    """List of fin_inc_month integers: projection_start, +1, ... for n_months."""
    return [_offset_fin_month(projection_start, i) for i in range(n_months)]


def member_weighted(monthly_map, months, num_key):
    """Pooled member-weighted metric over ``months``: sum(value*mbr) / sum(mbr)."""
    numerator = 0.0
    denominator = 0.0
    for month in months:
        row = monthly_map.get(month)
        if row is not None and row["den"]:
            numerator += row[num_key]
            denominator += row["den"]
    return (numerator / denominator) if denominator else None


def abs_error(actual, predicted):
    """Absolute difference, or None if either side is missing."""
    if actual is None or predicted is None:
        return None
    return abs(actual - predicted)


# Membership is duplicated across claim splits (cos_hccc_cd, service_code), so the
# denominator must be deduplicated to the enrollment-group grain (mirrors the S04
# Monthly Forecast Rollup fix). ENROLL_KEYS comes from S00_Config.
def rollup_monthly_numerators_and_members(df, metric_to_col):
    """Per-month member-weighted numerators + deduplicated member denominator.

    Numerator = sum(metric * sum_member_cnt) across all split rows (recovers totals).
    Denominator = member count deduplicated to (ENROLL_KEYS, month) so duplicated
    membership across claim splits does not inflate the weight. Returns
    ``{fin_inc_month: Row(num_<METRIC>..., den)}``.
    """
    numerators = df.groupBy("fin_inc_month").agg(*[
        F.sum(F.col(col) * F.col("sum_member_cnt")).alias(f"num_{metric}")
        for metric, col in metric_to_col.items()
    ])
    members = (
        df.select(*ENROLL_KEYS, "fin_inc_month", "sum_member_cnt")
        .distinct()
        .groupBy("fin_inc_month")
        .agg(F.sum("sum_member_cnt").alias("den"))
    )
    rows = numerators.join(members, on="fin_inc_month").collect()
    return {r["fin_inc_month"]: r for r in rows}

# COMMAND ----------

# DBTITLE 1,Precompute monthly actuals (one time)
source_table = table_fqn("model")

actual_full = spark.table(source_table).filter(F.col("VAL_DATE") == F.to_date(F.lit(BACKTEST["val_date"])))
max_actual_month = actual_full.agg(F.max("fin_inc_month")).collect()[0][0]
print(f"Latest available actual month: {max_actual_month}")

# Per-month member-weighted numerators + deduplicated member denominator.
actual_map = rollup_monthly_numerators_and_members(
    actual_full, {"PMPM": "TARGET_PMPM", "UTIL": "TARGET_UTIL"}
)

# COMMAND ----------

next(iter(actual_map.items()))

# COMMAND ----------

# DBTITLE 1,Walk-forward backtest loop
train_end_months = []
_m = BACKTEST["first_train_end"]
while _m <= BACKTEST["last_train_end"]:
    train_end_months.append(_m)
    _m = _next_fin_month(_m)
print(f"Backtesting {len(train_end_months)} training-end months: {train_end_months}")

results = []
for train_end in train_end_months:
    config = build_backtest_config(BACKTEST["val_date"], train_end, BACKTEST["projection_months"])
    projection_start = config["projection_start"]

    prepared = prepare_training_data(spark, config).cache()
    prepared.count()

    # Exclude model groups with no training-period rows (segments first appearing
    # after the early-stopping split) to prevent empty-DataFrame LightGBM errors.
    split_month = _offset_fin_month(config["train_end_month"], -config["test_offset_months"])
    groups_with_training = (
        prepared.filter(F.col("fin_inc_month") <= split_month)
        .select(*config["model_group"])
        .distinct()
    )
    prepared_valid = prepared.join(groups_with_training, on=config["model_group"], how="left_semi")

    # Forecast-only, per metric.
    forecast_by_metric = {
        metric: backtest_forecast_segments(prepared_valid, metric, config)
        for metric in ["PMPM", "UTIL"]
    }

    # Join metrics and roll up to per-month member-weighted forecast numerators.
    key_columns = config["series_group"] + ["fin_inc_month"]
    pmpm_fc = forecast_by_metric["PMPM"].select(*key_columns, "sum_member_cnt", "TARGET_PMPM_PREDICTED")
    util_fc = forecast_by_metric["UTIL"].select(*key_columns, "TARGET_UTIL_PREDICTED")
    forecast = pmpm_fc.join(util_fc, on=key_columns, how="inner")

    # Same member-dedup rollup as the actuals so forecast and actual align.
    forecast_map = rollup_monthly_numerators_and_members(
        forecast, {"PMPM": "TARGET_PMPM_PREDICTED", "UTIL": "TARGET_UTIL_PREDICTED"}
    )

    row = {"DATA_THRU": train_end}
    for horizon in BACKTEST["horizons"]:
        window = month_window(projection_start, horizon)
        # Compare over months that actually have realized actuals.
        available = [mo for mo in window if mo <= max_actual_month and mo in actual_map]

        for metric in BACKTEST["metrics"]:
            predicted = member_weighted(forecast_map, available, f"num_{metric}")
            actual = member_weighted(actual_map, available, f"num_{metric}")
            row[f"NEXT_{horizon}_MONTHS_{metric}_PRED"] = predicted
            row[f"NEXT_{horizon}_MONTHS_{metric}_ACTUAL"] = actual
            row[f"NEXT_{horizon}_MONTHS_{metric}_ERROR"] = abs_error(actual, predicted)

        row[f"NEXT_{horizon}_MONTHS_ACTUAL_MONTHS_USED"] = len(available)

    results.append(row)
    print(f"  train_end={train_end}: {row}")

    prepared.unpersist()
    gc.collect()

# COMMAND ----------

# DBTITLE 1,Assemble results table
# Explicit column order (matches the requested sample output), then metadata.
ordered_columns = [("DATA_THRU", IntegerType())]
for horizon in BACKTEST["horizons"]:
    for metric in BACKTEST["metrics"]:
        ordered_columns += [
            (f"NEXT_{horizon}_MONTHS_{metric}_PRED", DoubleType()),
            (f"NEXT_{horizon}_MONTHS_{metric}_ACTUAL", DoubleType()),
            (f"NEXT_{horizon}_MONTHS_{metric}_ERROR", DoubleType()),
        ]
    ordered_columns.append((f"NEXT_{horizon}_MONTHS_ACTUAL_MONTHS_USED", IntegerType()))
ordered_columns += [
    ("VAL_DATE", StringType()),
    ("RUN_TIMESTAMP", StringType()),
]

run_timestamp = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
for row in results:
    row["VAL_DATE"] = BACKTEST["val_date"]
    row["RUN_TIMESTAMP"] = run_timestamp

results_schema = StructType([StructField(name, dtype) for name, dtype in ordered_columns])
results_rows = [tuple(row.get(name) for name, _ in ordered_columns) for row in results]
results_df = spark.createDataFrame(results_rows, schema=results_schema).orderBy("DATA_THRU")

display(results_df)

# COMMAND ----------

# DBTITLE 1,Write backtest results (idempotent by VAL_DATE)
results_full_name = table_fqn("backtest")
write_to_catalog(spark, results_df, results_full_name, f"VAL_DATE = '{BACKTEST['val_date']}'")
print(f"Backtest rows written: {len(results)}")
