# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # S02 — Preprocessing

# COMMAND ----------

# DBTITLE 1,Imports
from pyspark.sql import functions as F
from datetime import datetime

# COMMAND ----------

# DBTITLE 1,Define S0 Config
# MAGIC %run "./S00_Config"

# COMMAND ----------

# DBTITLE 1,Join and aggregate claims + membership
# --- 1. Read source tables ---
df_members = spark.table(table_fqn("mbr"))
df_claims  = spark.table(table_fqn("clm"))

# Claims + membership share the month dimension for the spine
CLM_MONTH_KEYS = CLM_SPLIT_KEYS + ['fin_inc_month']

UPSTREAM_VAL_DATE = df_claims.agg(F.max("VAL_DATE").alias("v")).collect()[0]["v"]
print(f"Upstream VAL_DATE: {UPSTREAM_VAL_DATE}")

# --- 2. Aggregate members to the MM_SPINE_KEYS grain (enrollment + month) ---
df_members_agg = (
    df_members
    .groupBy(MM_SPINE_KEYS)
    .agg(F.sum("sum_member_cnt").alias("sum_member_cnt"))
)

# --- 3. Aggregate claims to CLM_SPLIT_KEYS + month grain ---
claims_agg_cols = [
    'sum_tadm_units', 'sum_visits', 'sum_srvc_unit_cnt',
    'sum_adj_srvc_unit_cnt', 'sum_allw_amt', 'sum_net_pd_amt',
]

df_claims_agg = (
    df_claims
    .groupBy(CLM_MONTH_KEYS)
    .agg(*[F.sum(c).alias(c) for c in claims_agg_cols])
)

# --- 3b. Derive util from the metric S01A assigned to each claim key ---
df_util_metric = (
    spark.table(table_fqn("util_metric"))
    .filter(F.col('VAL_DATE') == F.lit(UPSTREAM_VAL_DATE))
    .select(*UTIL_METRIC_KEYS, 'util_source_col')
)

#Checks
_n_um = df_util_metric.count()
_n_um_distinct = df_util_metric.select(*UTIL_METRIC_KEYS).distinct().count()
if _n_um == 0:
    raise ValueError(
        f"S02: no rows in {table_fqn('util_metric')} for VAL_DATE {UPSTREAM_VAL_DATE}. Run S01A first."
    )
if _n_um != _n_um_distinct:
    raise ValueError(
        f"S02: {table_fqn('util_metric')} is not unique per {UTIL_METRIC_KEYS} "
        f"({_n_um:,} rows vs {_n_um_distinct:,} keys) - the util join would fan out."
    )

df_claims_agg = (
    df_claims_agg
    .join(df_util_metric, on=UTIL_METRIC_KEYS, how='left')
    .withColumn('util', util_pick_expr())
    .select(*CLM_MONTH_KEYS, 'util', 'sum_allw_amt', 'sum_net_pd_amt')
)

# Measures to carry forward into the spine
claims_measure_cols = ['util', 'sum_allw_amt', 'sum_net_pd_amt']

# --- 4. Build the spine (cartesian product of splits × months) ---
# The model needs a complete longitudinal series per split: one row per month
# for every split, including months with zero utilization.  Claim rows alone are
# sparse, which will silently corrupts lag / rolling / zero-count features downstream.
#
# Spine = DISTINCT observed split combinations × contiguous month axis
#         restricted to months where the split's enrollment group has MM > 0.

# Month bounds from claims
_bounds = (
    df_claims_agg
    .agg(
        F.min('fin_inc_month').alias('min_mo'),
        F.max('fin_inc_month').alias('max_mo'),
    )
    .collect()[0]
)
MIN_MONTH, MAX_MONTH = _bounds['min_mo'], _bounds['max_mo']

# Contiguous month axis (fin_inc_month is int YYYYMM)
df_months = spark.sql(f"""
    SELECT CAST(DATE_FORMAT(month_dt, 'yyyyMM') AS INT) AS fin_inc_month
    FROM (
        SELECT explode(
            sequence(
                TO_DATE(CAST({MIN_MONTH} AS STRING), 'yyyyMM'),
                TO_DATE(CAST({MAX_MONTH} AS STRING), 'yyyyMM'),
                INTERVAL 1 MONTH
            )
        ) AS month_dt
    )
""")

# Split tuples actually observed in the claims data (excluding month)
df_splits = df_claims_agg.select(*CLM_SPLIT_KEYS).distinct()

n_splits = df_splits.count()
n_months = df_months.count()
print(f'Split tuples observed  : {n_splits:>12,}')
print(f'Month axis             : {MIN_MONTH} -> {MAX_MONTH}  ({n_months:,} months)')
print(f'Full cartesian product : {n_splits * n_months:>12,} rows (before MM > 0 restriction)')

# Spine: cross-join splits × months, then inner-join membership so only
# months where the enrollment group has members survive.
df_spine = (
    df_splits
    .crossJoin(df_months)
    .join(df_members_agg, on=MM_SPINE_KEYS, how='inner')
)

# --- 4b. Completion factors from S01B ---
df_cf = (
    spark.table(table_fqn("cf"))
    .filter(
        (F.col('VAL_DATE') == F.lit(UPSTREAM_VAL_DATE))
    )
    # completion_factor_applied, not completion_factor: the interpolated factor is on
    # the same partial-month basis as the observation being grossed up here. The
    # full-month factor would understate ultimate for the newest incurred month.
    .select(*CLM_MONTH_KEYS, 'measure',
            F.col('completion_factor_applied').alias('completion_factor'))
)

#Checks
_n_cf = df_cf.count()
_n_cf_distinct = df_cf.select(*CLM_MONTH_KEYS, 'measure').distinct().count()
if _n_cf == 0:
    raise ValueError(
        f"S02: no rows in {table_fqn('cf')} for VAL_DATE {UPSTREAM_VAL_DATE}. Run S01B first."
    )
if _n_cf != _n_cf_distinct:
    raise ValueError(
        f"S02: {table_fqn('cf')} is not 1:1 per split-month-measure at current_lag_ind "
        f"({_n_cf:,} rows vs {_n_cf_distinct:,} keys) - the factor join would fan out."
    )

cf_pmpm = (
    df_cf.filter(F.col('measure') == 'allw')
    .select(*CLM_MONTH_KEYS, F.col('completion_factor').alias('cf_pmpm'))
)
cf_util = (
    df_cf.filter(F.col('measure') == 'util')
    .select(*CLM_MONTH_KEYS, F.col('completion_factor').alias('cf_util'))
)

# --- 5. Left-join claims onto the spine and derive per-member metrics ---
df_combined = (
    df_spine
    .join(df_claims_agg, on=CLM_MONTH_KEYS, how='left')
    .fillna(0, subset=claims_measure_cols)
    .join(cf_pmpm, on=CLM_MONTH_KEYS, how='left')
    .join(cf_util, on=CLM_MONTH_KEYS, how='left')
    .withColumn('cf_pmpm',            F.coalesce(F.col('cf_pmpm'), F.lit(1.0)))
    .withColumn('cf_util',            F.coalesce(F.col('cf_util'), F.lit(1.0)))
    .withColumn('util_k',             F.col('util') * 12000 / F.col('sum_member_cnt'))
    .withColumn('pmpm',               F.col('sum_allw_amt') / F.col('sum_member_cnt'))
    .withColumn('bf_estimate_util_k', F.col('util_k') / F.col('cf_util'))
    .withColumn('bf_estimate_pmpm',   F.col('pmpm') / F.col('cf_pmpm'))
)

print(f"\nCombined dataset: {df_combined.count():,} rows x {len(df_combined.columns)} cols")
display(df_combined)

# COMMAND ----------

# DBTITLE 1,Derive val_date & Write Spine
# Derive val_date from max claim YR_MO (exclude MBR rows, which carry prospective enrollment)
_max_yrmo = df_combined.selectExpr("MAX(fin_inc_month) AS m").collect()[0]["m"]
print(f"Max Year Month: {_max_yrmo}")
val_date = datetime.strptime(str(_max_yrmo), "%Y%m").strftime("%Y-%m-01")
print(f"Valuation Date: {val_date}")

df_combined = df_combined.withColumn("VAL_DATE", F.lit(val_date).cast("date"))

write_to_catalog(spark, df_combined, table_fqn("spine"), f"VAL_DATE = DATE('{val_date}')")

# COMMAND ----------

# DBTITLE 1,Check: Monthly PMPM and Utilization Rollup
# Monthly rollup: member-weighted PMPM and utilization.
# Membership is duplicated across claim splits (service_code, cos_hccc_cd),
# so deduplicate back to the enrollment-group grain before summing.

members_by_month = (
    df_combined
    .select(*ENROLL_KEYS, "fin_inc_month", "sum_member_cnt")
    .distinct()
    .groupBy("fin_inc_month")
    .agg(F.sum("sum_member_cnt").alias("total_members"))
)

claims_by_month = (
    df_combined
    .groupBy("fin_inc_month")
    .agg(
        F.sum("sum_allw_amt").alias("total_allowed"),
        F.sum("util").alias("total_util"),
    )
)

monthly_rollup = (
    claims_by_month
    .join(members_by_month, on="fin_inc_month")
    .withColumn("pmpm", F.col("total_allowed") / F.col("total_members"))
    .withColumn("util_k", F.col("total_util") * 12000 / F.col("total_members"))
    .select("fin_inc_month", "pmpm", "util_k")
    .orderBy("fin_inc_month")
)

display(monthly_rollup)
