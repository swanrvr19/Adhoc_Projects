# Databricks notebook source
# MAGIC %md
# MAGIC # Work Calendar Day (WCD) Index
# MAGIC
# MAGIC **Purpose:** Normalize medical expense for the day-of-week (DOW) content of a given month.
# MAGIC
# MAGIC **Methodology:**
# MAGIC 1. Aggregate paid medical expense to daily totals over a training window.
# MAGIC 2. Compute the average daily spend for each day of the week (Mon–Sun).
# MAGIC 3. Normalize those averages so the simple mean across all 7 DOWs = 1.0 → these are the **DOW relativities**.
# MAGIC 4. For each target month, count how many of each DOW fall in that month.
# MAGIC 5. Take the DOW-count-weighted average of the relativities → this is the **WCD monthly index**.
# MAGIC
# MAGIC A WCD index of 1.05 means the month is expected to run 5% above the average daily rate
# MAGIC purely due to its day composition (e.g., more Mondays than average).
# MAGIC
# MAGIC **Outputs:**
# MAGIC - `{output_catalog}.{output_schema}.wcd_dow_relativities` — DOW-level index values
# MAGIC - `{output_catalog}.{output_schema}.wcd_monthly_factors` — Monthly WCD index

# COMMAND ----------
# MAGIC %md ## 0. Widgets

# COMMAND ----------

dbutils.widgets.removeAll()

# Input data
dbutils.widgets.text("input_table",    "",           "Input table (catalog.schema.table)")
dbutils.widgets.text("date_col",       "service_date","Date column name")
dbutils.widgets.text("amount_col",     "paid_amount", "Paid amount column name")

# Training window (used to derive DOW relativities)
dbutils.widgets.text("train_start",    "2020-01-01",  "Training window start (YYYY-MM-DD)")
dbutils.widgets.text("train_end",      "2023-12-31",  "Training window end   (YYYY-MM-DD)")

# Target months to produce WCD factors for
dbutils.widgets.text("factor_start_month", "2020-01",  "Factor start month (YYYY-MM)")
dbutils.widgets.text("factor_end_month",   "2025-12",  "Factor end month   (YYYY-MM)")

# Output location
dbutils.widgets.text("output_catalog", "",  "Output catalog")
dbutils.widgets.text("output_schema",  "",  "Output schema")

# COMMAND ----------
# MAGIC %md ## 1. Imports & Configuration

# COMMAND ----------

import calendar
import datetime
from pyspark.sql import functions as F, Window
from pyspark.sql.types import DoubleType, IntegerType, StringType

# Read widgets
INPUT_TABLE        = dbutils.widgets.get("input_table")
DATE_COL           = dbutils.widgets.get("date_col")
AMOUNT_COL         = dbutils.widgets.get("amount_col")
TRAIN_START        = dbutils.widgets.get("train_start")
TRAIN_END          = dbutils.widgets.get("train_end")
FACTOR_START_MONTH = dbutils.widgets.get("factor_start_month")
FACTOR_END_MONTH   = dbutils.widgets.get("factor_end_month")
OUTPUT_CATALOG     = dbutils.widgets.get("output_catalog")
OUTPUT_SCHEMA      = dbutils.widgets.get("output_schema")

OUTPUT_REL_TABLE     = f"{OUTPUT_CATALOG}.{OUTPUT_SCHEMA}.wcd_dow_relativities"
OUTPUT_MONTHLY_TABLE = f"{OUTPUT_CATALOG}.{OUTPUT_SCHEMA}.wcd_monthly_factors"

RUN_DATE = datetime.date.today().isoformat()

# Spark dayofweek convention: 1=Sunday, 2=Monday, ..., 7=Saturday
DOW_MAP = {1: "Sunday", 2: "Monday", 3: "Tuesday", 4: "Wednesday",
           5: "Thursday", 6: "Friday", 7: "Saturday"}

print(f"Input table   : {INPUT_TABLE}")
print(f"Date column   : {DATE_COL}")
print(f"Amount column : {AMOUNT_COL}")
print(f"Training window: {TRAIN_START} → {TRAIN_END}")
print(f"Factor months : {FACTOR_START_MONTH} → {FACTOR_END_MONTH}")
print(f"Output rel    : {OUTPUT_REL_TABLE}")
print(f"Output monthly: {OUTPUT_MONTHLY_TABLE}")
print(f"Run date      : {RUN_DATE}")

# COMMAND ----------
# MAGIC %md ## 2. Load & Validate Input Data

# COMMAND ----------

raw = (
    spark.table(INPUT_TABLE)
    .select(
        F.col(DATE_COL).cast("date").alias("service_date"),
        F.col(AMOUNT_COL).cast(DoubleType()).alias("paid_amount"),
    )
    .filter(
        (F.col("service_date") >= F.lit(TRAIN_START)) &
        (F.col("service_date") <= F.lit(TRAIN_END))  &
        F.col("paid_amount").isNotNull()              &
        (F.col("paid_amount") >= 0)
    )
)

row_count = raw.count()
assert row_count > 0, f"No rows found in {INPUT_TABLE} for the training window {TRAIN_START}→{TRAIN_END}"

date_range = raw.agg(F.min("service_date").alias("min_date"), F.max("service_date").alias("max_date")).collect()[0]
print(f"Rows loaded      : {row_count:,}")
print(f"Actual date range: {date_range['min_date']} → {date_range['max_date']}")

# COMMAND ----------
# MAGIC %md ## 3. Aggregate to Daily Totals

# COMMAND ----------

# Sum all paid amounts to one row per calendar date, then tag with day-of-week.
# Spark dayofweek: 1=Sunday, 2=Monday, ..., 7=Saturday
daily = (
    raw
    .groupBy("service_date")
    .agg(F.sum("paid_amount").alias("daily_paid"))
    .withColumn("day_of_week", F.dayofweek("service_date"))
    .withColumn("year_month", F.date_format("service_date", "yyyy-MM"))
)

# Quick sanity check — expect 7 distinct DOW values
distinct_dows = daily.select("day_of_week").distinct().count()
print(f"Distinct DOW values: {distinct_dows}  (expect 7 for a multi-year window)")
display(daily.orderBy("service_date"))

# COMMAND ----------
# MAGIC %md ## 4. Compute DOW Relativities
# MAGIC
# MAGIC **Formula:**
# MAGIC - `mu_d` = average daily paid amount for day-of-week *d* across the training window
# MAGIC - `grand_avg` = simple mean of the 7 `mu_d` values (equal weight, not weighted by occurrence count)
# MAGIC - `relativity_d` = `mu_d / grand_avg`
# MAGIC
# MAGIC By construction, the simple average of the 7 relativities equals 1.0, meaning a hypothetical
# MAGIC month with exactly 1/7 of each DOW would produce a WCD index of exactly 1.0.

# COMMAND ----------

# Step 4a: average daily paid per DOW
dow_stats = (
    daily
    .groupBy("day_of_week")
    .agg(
        F.avg("daily_paid").alias("avg_daily_paid"),
        F.count("*").alias("day_count"),          # number of that DOW in training window
        F.stddev("daily_paid").alias("std_daily_paid"),
    )
)

# Step 4b: grand average = simple mean across all 7 DOWs
# We collect the 7-row frame; it's tiny.
grand_avg = dow_stats.agg(F.avg("avg_daily_paid")).collect()[0][0]
print(f"Grand average daily paid (mean of 7 DOW avgs): ${grand_avg:,.2f}")

# Step 4c: relativities
# Map integer DOW to name using a Spark map literal
dow_name_map = F.create_map(*[item for pair in
    [(F.lit(k), F.lit(v)) for k, v in DOW_MAP.items()]
    for item in pair])

dow_relativities = (
    dow_stats
    .withColumn("relativity", F.col("avg_daily_paid") / F.lit(grand_avg))
    .withColumn("dow_name", dow_name_map[F.col("day_of_week")])
    .withColumn("run_date", F.lit(RUN_DATE).cast("date"))
    .select(
        "run_date",
        "day_of_week",
        "dow_name",
        "day_count",
        F.round("avg_daily_paid", 2).alias("avg_daily_paid"),
        F.round("std_daily_paid", 2).alias("std_daily_paid"),
        F.round("relativity", 6).alias("relativity"),
    )
    .orderBy("day_of_week")
)

# Verify relativities average to 1.0
avg_rel = dow_relativities.agg(F.avg("relativity")).collect()[0][0]
print(f"Mean of all 7 relativities (should = 1.0): {avg_rel:.6f}")

display(dow_relativities)

# COMMAND ----------
# MAGIC %md ## 5. Compute Monthly WCD Factors
# MAGIC
# MAGIC For each target month:
# MAGIC 1. Count how many of each DOW occur in that month.
# MAGIC 2. WCD index = Σ(count_d × relativity_d) / total_days_in_month
# MAGIC    = weighted average of relativities where weights are the actual DOW counts.

# COMMAND ----------

# Step 5a: Build a calendar table covering all days in the factor month range.
# Parse YYYY-MM widgets into first/last dates.
def parse_ym(ym_str: str, last_day=False) -> str:
    y, m = int(ym_str[:4]), int(ym_str[5:7])
    if last_day:
        d = calendar.monthrange(y, m)[1]
    else:
        d = 1
    return f"{y:04d}-{m:02d}-{d:02d}"

cal_start = parse_ym(FACTOR_START_MONTH, last_day=False)
cal_end   = parse_ym(FACTOR_END_MONTH,   last_day=True)
print(f"Calendar range: {cal_start} → {cal_end}")

calendar_df = (
    spark.sql(f"SELECT explode(sequence(date'{cal_start}', date'{cal_end}', interval 1 day)) AS calendar_date")
    .withColumn("day_of_week",  F.dayofweek("calendar_date"))
    .withColumn("year_month",   F.date_format("calendar_date", "yyyy-MM"))
)

# Step 5b: Count DOW occurrences per year-month
dow_counts_monthly = (
    calendar_df
    .groupBy("year_month", "day_of_week")
    .agg(F.count("*").alias("dow_count"))
)

total_days_monthly = (
    calendar_df
    .groupBy("year_month")
    .agg(F.count("*").alias("total_days_in_month"))
)

# Step 5c: Join relativities and compute weighted average
monthly_factors = (
    dow_counts_monthly
    .join(dow_relativities.select("day_of_week", "dow_name", "relativity"), "day_of_week", "left")
    .join(total_days_monthly, "year_month", "left")
    .withColumn("weighted_rel", F.col("dow_count") * F.col("relativity") / F.col("total_days_in_month"))
    .groupBy("year_month", "total_days_in_month")
    .agg(F.round(F.sum("weighted_rel"), 6).alias("wcd_index"))
    .orderBy("year_month")
)

# Step 5d: Pivot DOW counts into columns for auditability
dow_counts_pivot = (
    dow_counts_monthly
    .withColumn("dow_name", dow_name_map[F.col("day_of_week")])
    .groupBy("year_month")
    .pivot("dow_name", list(DOW_MAP.values()))
    .agg(F.first("dow_count"))
)

monthly_factors_full = (
    monthly_factors
    .join(dow_counts_pivot, "year_month", "left")
    .withColumn("run_date", F.lit(RUN_DATE).cast("date"))
    .select(
        "run_date", "year_month", "total_days_in_month", "wcd_index",
        "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"
    )
    .orderBy("year_month")
)

display(monthly_factors_full)

# COMMAND ----------
# MAGIC %md ## 6. Write Output Delta Tables

# COMMAND ----------

# Ensure output schema exists
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {OUTPUT_CATALOG}.{OUTPUT_SCHEMA}")

# ── DOW Relativities ──────────────────────────────────────────────────────────
# Overwrite on each run (relativities are re-derived from scratch each time).
# If you want a history of relativity runs, change to append mode and use run_date as a partition.
(
    dow_relativities
    .write
    .format("delta")
    .mode("overwrite")
    .option("overwriteSchema", "true")
    .saveAsTable(OUTPUT_REL_TABLE)
)
print(f"Written: {OUTPUT_REL_TABLE}")

# ── Monthly Factors ───────────────────────────────────────────────────────────
# MERGE strategy: update existing year-months, insert new ones.
# This allows the job to be re-run safely without duplicating rows.
monthly_factors_full.createOrReplaceTempView("new_monthly_factors")

spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {OUTPUT_MONTHLY_TABLE}
    USING DELTA
    AS SELECT * FROM new_monthly_factors WHERE 1=0
""")

spark.sql(f"""
    MERGE INTO {OUTPUT_MONTHLY_TABLE} AS target
    USING new_monthly_factors AS source
    ON target.year_month = source.year_month
    WHEN MATCHED THEN UPDATE SET *
    WHEN NOT MATCHED THEN INSERT *
""")
print(f"Merged: {OUTPUT_MONTHLY_TABLE}")

# COMMAND ----------
# MAGIC %md ## 7. Summary

# COMMAND ----------

print("=" * 60)
print("WCD Index Pipeline Complete")
print("=" * 60)
print(f"  Training window   : {TRAIN_START} → {TRAIN_END}")
print(f"  Factor months     : {FACTOR_START_MONTH} → {FACTOR_END_MONTH}")
print(f"  Run date          : {RUN_DATE}")
print()
print("DOW Relativities:")
dow_relativities.select("dow_name", "avg_daily_paid", "relativity").orderBy("day_of_week").show(7, truncate=False)
print()
print("Sample Monthly Factors (first 6 months):")
monthly_factors_full.select("year_month", "wcd_index", "total_days_in_month").show(6, truncate=False)
print(f"\nOutputs written to:")
print(f"  {OUTPUT_REL_TABLE}")
print(f"  {OUTPUT_MONTHLY_TABLE}")
