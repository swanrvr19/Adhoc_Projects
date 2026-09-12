# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # S01A — Utilization Metric Assignment
# MAGIC
# MAGIC Purpose: Assigns **one** utilization column per `UTIL_METRIC_KEYS` (default
# MAGIC `CLAIM_KEYS` = `service_code` + `cos_hccc_cd`), using the priority order in
# MAGIC `CF_UNIT_COLUMNS`: the first column with a positive total across all available
# MAGIC history wins.

# COMMAND ----------

# DBTITLE 1,Imports
from pyspark.sql import functions as F

# COMMAND ----------

# DBTITLE 1,Define S0 Config
# MAGIC %run "./S00_Config"

# COMMAND ----------

# DBTITLE 1,Read S01 Claims and Validate
df_clm_all = spark.table(table_fqn("clm"))

val_date = df_clm_all.agg(F.max("VAL_DATE").alias("v")).collect()[0]["v"]
val_date_str = val_date.strftime("%Y-%m-%d")
print(f"Valuation Date : {val_date_str}")

#Check for missing columns  
missing_keys = [c for c in CLM_SPLIT_KEYS if c not in df_clm_all.columns]
if missing_keys:
    raise ValueError(
        f"S01A: CLM_SPLIT_KEYS columns missing from {table_fqn('clm')}: {missing_keys}. "
        f"Available columns: {sorted(df_clm_all.columns)}"
    )

# The UTIL assignment grain must be a subset of the downstream jobs/joins split grain
bad_metric_keys = [c for c in UTIL_METRIC_KEYS if c not in CLM_SPLIT_KEYS]
if bad_metric_keys:
    raise ValueError(
        f"S01A: UTIL_METRIC_KEYS must be a subset of CLM_SPLIT_KEYS; "
        f"offending: {bad_metric_keys}"
    )

#Check for unit columns in the claims table
missing_units = [c for c in CF_UNIT_COLUMNS if c not in df_clm_all.columns]
if missing_units:
    raise ValueError(
        f"S01A: CF_UNIT_COLUMNS missing from {table_fqn('clm')}: {missing_units}"
    )

print(f"Assignment grain   : {UTIL_METRIC_KEYS}")
print(f"Split grain        : {CLM_SPLIT_KEYS}")
print(f"Candidate columns  : {CF_UNIT_COLUMNS}  (priority order, first positive wins)")

df_clm = df_clm_all.filter(F.col("VAL_DATE") == F.lit(val_date_str).cast("date"))

# COMMAND ----------

# DBTITLE 1,Assign One Utilization Metric per Claim Key
# Totals span all incurred months and all adjudication lags present in the extract -> may need revisting/monitoring 
metric_totals = (
    df_clm
    .groupBy(*UTIL_METRIC_KEYS)
    .agg(
        *[F.sum(c).alias(c) for c in CF_UNIT_COLUMNS],
        F.countDistinct("fin_inc_month").alias("n_inc_months"),
        F.countDistinct(*CLM_SPLIT_KEYS).alias("n_splits_covered"),
    )
)

df_util_metric = (
    metric_totals
    .withColumn("util_source_col", util_priority_expr())
    .withColumn("n_populated_cols", util_populated_count_expr())
    .withColumn(
        "util_metric_status",
        F.when(F.col("util_source_col").isNull(), F.lit("NO_POSITIVE_UNITS"))
         .when(F.col("n_populated_cols") > 1, F.lit("ASSIGNED_MULTIPLE_POSITIVE_UNITS"))
         .otherwise(F.lit("ASSIGNED_UNAMBIGUOUS")),
    )
    # Priority rank of the winning column: 1 = highest priority (based on ordering of CF_UNIT_COLUMNS)
    .withColumn(
        "util_source_rank",
        F.when(F.col("util_source_col").isNull(), F.lit(None).cast("int")).otherwise(
            F.array_position(
                F.array(*[F.lit(c) for c in CF_UNIT_COLUMNS]), F.col("util_source_col")
            ).cast("int")
        ),
    )
    .withColumn("VAL_DATE", F.lit(val_date_str).cast("date"))
)

# COMMAND ----------

# DBTITLE 1,Preview Metric Assignments
display(df_util_metric.limit(100))

# COMMAND ----------

# MAGIC %md
# MAGIC # Validation Steps

# COMMAND ----------

# DBTITLE 1,Basic Validation
def check(label, count, fail=False):
    """Report a validation count; raise when `fail` and the count is non-zero."""
    status = "OK  " if count == 0 else ("FAIL" if fail else "WARN")
    print(f"  [{status}] {label}: {count:,}")
    if fail and count:
        raise ValueError(f"S01A validation failed - {label}: {count:,}")


print("Validation")

def any_of(conditions):
    """OR a list of boolean Columns together."""
    combined = conditions[0]
    for cond in conditions[1:]:
        combined = combined | cond
    return combined


n_keys = df_util_metric.count()
n_distinct = df_util_metric.select(*UTIL_METRIC_KEYS).distinct().count()
check("duplicate rows per claim key", n_keys - n_distinct, fail=True)

check(
    "null in a UTIL_METRIC_KEYS column",
    df_util_metric.filter(any_of([F.col(c).isNull() for c in UTIL_METRIC_KEYS])).count(),
)
check(
    "claim keys with no positive unit column (util will be null/0 downstream)",
    df_util_metric.filter(F.col("util_metric_status") == "NO_POSITIVE_UNITS").count(),
)
check(
    "negative unit totals",
    df_util_metric.filter(any_of([F.col(c) < 0 for c in CF_UNIT_COLUMNS])).count(),
)

print(f"\nClaim keys assigned: {n_keys:,}")
print("Assignment breakdown by chosen column:")
display(
    df_util_metric
    .groupBy("util_source_col", "util_source_rank", "util_metric_status")
    .agg(
        F.count(F.lit(1)).alias("n_claim_keys"),
        F.sum("n_splits_covered").alias("n_splits_covered"),
        F.avg("n_inc_months").alias("avg_inc_months"),
    )
    .orderBy("util_source_rank", "util_source_col")
)

print("Full assignment table:")
display(
    df_util_metric
    .select(*UTIL_METRIC_KEYS, "util_source_col", "util_metric_status",
            "n_populated_cols", "n_splits_covered", "n_inc_months", *CF_UNIT_COLUMNS)
    .orderBy(*UTIL_METRIC_KEYS)
)

# COMMAND ----------

# DBTITLE 1,Coverage Risk from the Coarser Grain

# Category-level util assignment improves consistency but can produce zero utilization for some splits. 
# Assess materiality and add fallback logic if needed

split_totals = (
    df_clm
    .groupBy(*CLM_SPLIT_KEYS)
    .agg(*[F.sum(c).alias(c) for c in CF_UNIT_COLUMNS])
    .join(
        df_util_metric.select(*UTIL_METRIC_KEYS, "util_source_col"),
        on=UTIL_METRIC_KEYS,
        how="left",
    )
    .withColumn("assigned_total", F.coalesce(util_pick_expr(), F.lit(0.0)))
    .withColumn("n_populated_cols", util_populated_count_expr())
    .withColumn(
        "loses_util",
        (F.col("assigned_total") <= 0) & (F.col("n_populated_cols") > 0),
    )
)

n_split_rows = split_totals.count()
n_loses = split_totals.filter(F.col("loses_util")).count()
print(f"Claim splits                          : {n_split_rows:,}")
print(f"Rows where assigned column has no volume for them: {n_loses:,} "
      f"({n_loses / n_split_rows:.2%}) -> util = 0 under the claim-grain rule")

print("Example Rows Affected splits by category, with the volume that goes to zero:")
display(
    split_totals.filter(F.col("loses_util"))
    .groupBy(*CLAIM_KEYS, "util_source_col")
    .agg(
        F.count(F.lit(1)).alias("n_splits"),
        *[F.sum(c).alias(f"orphaned_{c}") for c in CF_UNIT_COLUMNS],
    )
    .orderBy(F.col("n_splits").desc())
)

# COMMAND ----------

# DBTITLE 1,Write Utilization Metric Table
out_cols = [
    *UTIL_METRIC_KEYS,
    "util_source_col",
    "util_source_rank",
    "util_metric_status",
    "n_populated_cols",
    "n_splits_covered",
    "n_inc_months",
    *CF_UNIT_COLUMNS,
    "VAL_DATE",
]

df_out = df_util_metric.select(*out_cols)

print(f"Utilization metric table: {df_out.count():,} rows x {len(df_out.columns)} cols")
display(df_out)

write_to_catalog(
    spark, df_out, table_fqn("util_metric"), f"VAL_DATE = DATE('{val_date_str}')"
)

# COMMAND ----------

# DBTITLE 1,Check: Assignment Drift Across VAL_DATE Versions
# A claim key whose assigned metric flips between vintages will show a level shift in
# the util series of every split it covers. Worth reviewing before it reaches the model.
display(
    spark.read.table(table_fqn("util_metric"))
    .groupBy(*UTIL_METRIC_KEYS)
    .agg(
        F.countDistinct("util_source_col").alias("n_distinct_metrics"),
        F.collect_set("util_source_col").alias("metrics_used"),
        F.min("VAL_DATE").alias("first_val_date"),
        F.max("VAL_DATE").alias("last_val_date"),
    )
    .filter(F.col("n_distinct_metrics") > 1)
    .orderBy(F.col("n_distinct_metrics").desc())
)
