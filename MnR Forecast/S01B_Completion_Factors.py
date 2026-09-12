# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # S01B — Completion Factors
# MAGIC
# MAGIC Builds paid-development triangles from the S01 claims extract
# MAGIC
# MAGIC **Comments**
# MAGIC
# MAGIC Method = standard chain-ladder:
# MAGIC 1. age-to-age (duration-to-duration) factor at each lag: trimmed mean over incurred months of C[d+1] / C[d]`
# MAGIC 2. Note, an incurred month contributes to lag `d` as soon as it has observed lag `d+1`; it does not need to have reached the ultimate lag.

# COMMAND ----------

# DBTITLE 1,Imports
from datetime import date

from pyspark.sql import Window
from pyspark.sql import functions as F

# COMMAND ----------

# DBTITLE 1,Define S0 Config
# MAGIC %run "./S00_Config"

# COMMAND ----------

# DBTITLE 1,Read S01 Claims and Validate Configured Keys
temp_df_clm_all = spark.table(table_fqn("clm"))

#TEMPORARY FILTER
df_clm_all = temp_df_clm_all.filter(F.col("hcc")=='PH')

val_date = df_clm_all.agg(F.max("VAL_DATE").alias("v")).collect()[0]["v"]
val_date_str = val_date.strftime("%Y-%m-%d")
print(f"Valuation Date : {val_date_str}")

# Check: every configured CLM_SPLIT_KEYS column must exist in the S01 output.
missing_keys = [c for c in CLM_SPLIT_KEYS if c not in df_clm_all.columns]
if missing_keys:
    raise ValueError(
        f"S01B: CLM_SPLIT_KEYS columns missing from {table_fqn('clm')}: {missing_keys}. "
        f"Available columns: {sorted(df_clm_all.columns)}"
    )

# Check: The ultimate-lag grain must be a subset of the split grain
bad_ult_keys = [c for c in CF_ULTIMATE_LAG_KEYS if c not in CLM_SPLIT_KEYS]
if bad_ult_keys:
    raise ValueError(
        f"S01B: CF_ULTIMATE_LAG_KEYS must be a subset of CLM_SPLIT_KEYS; "
        f"offending: {bad_ult_keys}"
    )

#Check: Required columns
required_cols = ["fin_inc_month", "adjd_dt"] + list(CF_MEASURES.values()) + CF_UNIT_COLUMNS
missing_cols = [c for c in required_cols if c not in df_clm_all.columns]
if missing_cols:
    raise ValueError(
        f"S01B: required source columns missing from {table_fqn('clm')}: {missing_cols}"
    )

print(f"Split keys ({len(CLM_SPLIT_KEYS)})     : {CLM_SPLIT_KEYS}")
print(f"Ultimate-lag grain     : {CF_ULTIMATE_LAG_KEYS} + measure")
print(f"Measures               : {CF_MEASURE_NAMES}")

df_clm = df_clm_all.filter(F.col("VAL_DATE") == F.lit(val_date_str).cast("date"))

# COMMAND ----------

# DBTITLE 1,Derive Incurred Month, Adjudication Month, and Development Lag
# lag_months is 0-based: a claim adjudicated inside its own incurred month is lag 0
df_lagged = (
    df_clm
    .withColumn("inc_month_dt", F.to_date(F.col("fin_inc_month").cast("string"), "yyyyMM"))
    .withColumn("adjd_month_dt", F.trunc(F.col("adjd_dt").cast("date"), "MM"))
    .withColumn(
        "lag_months",
        F.months_between(F.col("adjd_month_dt"), F.col("inc_month_dt")).cast("int"),
    )
)

# Max paid-through date 
_wm = df_lagged.agg(
    F.max("adjd_dt").alias("paid_through_dt"),
    F.max("adjd_month_dt").alias("paid_through_month_dt"),
).collect()[0]
paid_through_dt = _wm["paid_through_dt"]
paid_through_month_dt = _wm["paid_through_month_dt"]
print(f"Paid through (max adjd_dt) : {paid_through_dt}")
print(f"Paid-through month         : {paid_through_month_dt}")

# Check: unusable lag rows are excluded
n_src = df_lagged.count()
n_null_lag = df_lagged.filter(F.col("lag_months").isNull()).count()
n_neg_lag = df_lagged.filter(F.col("lag_months") < 0).count()
print(f"Source rows                : {n_src:,}")
print(f"  null lag (bad adjd_dt)   : {n_null_lag:,}")
print(f"  negative lag (adjd < inc): {n_neg_lag:,}")

df_valid = df_lagged.filter(F.col("lag_months").isNotNull() & (F.col("lag_months") >= 0))

#Preview Data
display(df_lagged.limit(10))

# COMMAND ----------

# DBTITLE 1,Read the Assigned Utilization Metric (S01A)
# One metric per UTIL_METRIC_KEYS, assigned once in S01A
unit_choice = (
    spark.table(table_fqn("util_metric"))
    .filter(F.col("VAL_DATE") == F.lit(val_date_str).cast("date"))
    .select(*UTIL_METRIC_KEYS, "util_source_col")
)

#Checks
n_assigned = unit_choice.count()
n_assigned_distinct = unit_choice.select(*UTIL_METRIC_KEYS).distinct().count()
if n_assigned == 0:
    raise ValueError(
        f"S01B: no rows in {table_fqn('util_metric')} for VAL_DATE {val_date_str}. "
        f"Run S01A first."
    )
if n_assigned != n_assigned_distinct:
    raise ValueError(
        f"S01B: {table_fqn('util_metric')} is not unique per {UTIL_METRIC_KEYS} "
        f"({n_assigned:,} rows vs {n_assigned_distinct:,} keys) - the util join would fan out."
    )
print(f"Utilization metrics read : {n_assigned:,} claim keys ({UTIL_METRIC_KEYS})")

# COMMAND ----------

# DBTITLE 1,Estimate the Intra-Month Adjudication Fraction (f)
# f = share of a COMPLETE month's adjudication that lands on or before the paid-through day-of-month. 
# Measured from history rather than assumed

paid_through_day = paid_through_dt.day
print(f"Paid-through day of month : {paid_through_day}")

# Day-level amounts per measure, COMPLETE adjudication months only.
_daily_long = (
    df_valid
    .filter(F.col("adjd_month_dt") < F.lit(paid_through_month_dt))
    .join(unit_choice, on=UTIL_METRIC_KEYS, how="left")
    .withColumn("util", F.coalesce(util_pick_expr(), F.lit(0.0)))
    .withColumn("adjd_day", F.dayofmonth(F.col("adjd_dt").cast("date")))
    .groupBy(*CF_PARTIAL_FRAC_KEYS, "adjd_month_dt", "adjd_day")
    .agg(
        *[F.sum(src).alias(name) for name, src in CF_MEASURES.items()],
        F.sum("util").alias("util"),
    )
    .unpivot(
        ids=[*CF_PARTIAL_FRAC_KEYS, "adjd_month_dt", "adjd_day"],
        values=CF_MEASURE_NAMES,
        variableColumnName="measure",
        valueColumnName="amt",
    )
)

# Per complete month: share of that month's total landing by the paid-through day.
_frac_by_month = (
    _daily_long
    .groupBy(*CF_PARTIAL_FRAC_KEYS, "measure", "adjd_month_dt")
    .agg(
        F.sum("amt").alias("month_total"),
        F.sum(
            F.when(F.col("adjd_day") <= F.lit(paid_through_day), F.col("amt"))
             .otherwise(F.lit(0.0))
        ).alias("through_day"),
    )
    .filter(F.col("month_total") > 0)
    .withColumn("frac", F.col("through_day") / F.col("month_total"))
)

_w_frac = (
    Window.partitionBy(*CF_PARTIAL_FRAC_KEYS, "measure")
    .orderBy(F.col("adjd_month_dt").desc())
)
_frac_recent = (
    _frac_by_month
    .withColumn("mo_rank", F.dense_rank().over(_w_frac))
    .filter(F.col("mo_rank") <= F.lit(CF_PARTIAL_FRAC_MONTHS))
)

# Global median backfills any key with no usable history.
_global_frac = (
    _frac_recent.agg(F.expr("percentile_approx(frac, 0.5)").alias("f")).collect()[0]["f"]
)
if _global_frac is None:
    raise ValueError(
        "S01B: cannot estimate the intra-month adjudication fraction -- no complete "
        f"adjudication months before {paid_through_month_dt}."
    )
print(f"Global median fraction    : {_global_frac:.4f}")

partial_frac = (
    _frac_recent
    .groupBy(*CF_PARTIAL_FRAC_KEYS, "measure")
    .agg(
        F.expr("percentile_approx(frac, 0.5)").alias("frac_median"),
        F.count(F.lit(1)).alias("frac_nobs"),
        F.min("frac").alias("frac_min"),
        F.max("frac").alias("frac_max"),
    )
    .withColumn(
        "partial_month_frac",
        F.least(
            F.lit(1.0),
            F.greatest(F.lit(0.0), F.coalesce(F.col("frac_median"), F.lit(_global_frac))),
        ),
    )
    .withColumn(
        "partial_frac_source",
        F.when(F.col("frac_median").isNull(), F.lit("GLOBAL_MEDIAN")).otherwise(F.lit("MEASURED")),
    )
)

print("Estimated f by key and measure")
display(partial_frac.orderBy("measure", *CF_PARTIAL_FRAC_KEYS))

# COMMAND ----------

# DBTITLE 1,Build the Triangle: Incremental Amounts by Split x Incurred Month x Lag
tri_base = (
    df_valid
    .join(unit_choice, on=UTIL_METRIC_KEYS, how="left")
    .withColumn("util_row", F.coalesce(util_pick_expr(), F.lit(0.0)))
    .groupBy(*CLM_SPLIT_KEYS, "fin_inc_month", "lag_months")
    .agg(
        *[F.sum(src).alias(name) for name, src in CF_MEASURES.items()],
        F.sum("util_row").alias("util"),
    )
)

# Long format: one row per measure
tri_long = tri_base.unpivot(
    ids=[*CLM_SPLIT_KEYS, "fin_inc_month", "lag_months"],
    values=CF_MEASURE_NAMES,
    variableColumnName="measure",
    valueColumnName="incr_amt",
)

# Each incurred month's own maturity
inc_periods = (
    tri_long
    .select(*CLM_SPLIT_KEYS, "fin_inc_month").distinct()
    .withColumn("inc_month_dt", F.to_date(F.col("fin_inc_month").cast("string"), "yyyyMM"))
    .withColumn(
        "current_lag",
        F.months_between(
            F.lit(paid_through_month_dt).cast("date"), F.col("inc_month_dt")
        ).cast("int"),
    )
)

#Preview Data
print(f"Preview Table: tri_long")
display(tri_long.limit(100))

print(f"Preview Table: inc_periods")
display(inc_periods.limit(100))


# COMMAND ----------

# DBTITLE 1,Derive the Ultimate Lag per Category (i.e. where claim development actually flattens)
# Resolve the "percent of ultimate" circularity by calibrating on the deepest available runout history.
# The first lag exceeding CF_COMPLETENESS_THRESHOLD is assigned as the category's ultimate lag

calib_periods = (
    inc_periods
    .filter(F.col("current_lag") >= F.lit(CF_CALIBRATION_LAG_MONTHS))
    .select(*CLM_SPLIT_KEYS, "fin_inc_month", "current_lag")
)

n_calib_months = calib_periods.select("fin_inc_month").distinct().count()
print(f"Calibration cohort: {n_calib_months:,} incurred months with >= "
      f"{CF_CALIBRATION_LAG_MONTHS} months of runout")

calib_curve = (
    tri_long
    .join(calib_periods, on=[*CLM_SPLIT_KEYS, "fin_inc_month"], how="inner")
    .filter(
        (F.col("lag_months") <= F.lit(CF_CALIBRATION_LAG_MONTHS))
        # (lag == current_lag)
        & (F.col("lag_months") < F.col("current_lag")) # Drop the newest cell, which sits in the partial adjudication month (i.e. lag == current_lag)
    )
    .groupBy(*CF_ULTIMATE_LAG_KEYS, "measure", "lag_months")
    .agg(F.sum("incr_amt").alias("incr_amt"))
)

_w_cal = (
    Window.partitionBy(*CF_ULTIMATE_LAG_KEYS, "measure")
    .orderBy("lag_months")
    .rowsBetween(Window.unboundedPreceding, Window.currentRow)
)
_w_cal_tot = Window.partitionBy(*CF_ULTIMATE_LAG_KEYS, "measure")

calib_curve = (
    calib_curve
    .withColumn("cum_amt", F.sum("incr_amt").over(_w_cal))
    .withColumn("calib_total", F.sum("incr_amt").over(_w_cal_tot))
    .filter(F.col("calib_total") > 0)
    .withColumn("pct_of_calibrated_total", F.col("cum_amt") / F.col("calib_total"))
)

print(f"Calibrated development curve (threshold = {CF_COMPLETENESS_THRESHOLD}):")
display(calib_curve.orderBy(*CF_ULTIMATE_LAG_KEYS, "measure", "lag_months"))

# Earliest lag clearing the threshold set in S00
derived_lag = (
    calib_curve
    .filter(F.col("pct_of_calibrated_total") >= F.lit(CF_COMPLETENESS_THRESHOLD))
    .groupBy(*CF_ULTIMATE_LAG_KEYS, "measure")
    .agg(F.min("lag_months").alias("derived_lag"))
)

# Every category/measure present in the triangle needs a value, including those with no calibration cohort at all
all_cats = tri_long.select(*CF_ULTIMATE_LAG_KEYS, "measure").distinct()
ultimate_lag = all_cats.join(derived_lag, on=[*CF_ULTIMATE_LAG_KEYS, "measure"], how="left")

# Manual override from S00
if CF_ULTIMATE_LAG_OVERRIDES:
    _ovr_rows = []
    for keys, lag in CF_ULTIMATE_LAG_OVERRIDES.items():
        keys = keys if isinstance(keys, tuple) else (keys,)
        _ovr_rows.append(tuple(keys) + (int(lag),))
    _ovr_cols = CF_ULTIMATE_LAG_KEYS[: len(_ovr_rows[0]) - 1] + ["override_lag"]
    df_override = spark.createDataFrame(_ovr_rows, _ovr_cols)
    ultimate_lag = ultimate_lag.join(
        df_override, on=CF_ULTIMATE_LAG_KEYS[: len(_ovr_cols) - 1], how="left"
    )
else:
    ultimate_lag = ultimate_lag.withColumn("override_lag", F.lit(None).cast("int"))

ultimate_lag = (
    ultimate_lag
    .withColumn(
        "ultimate_lag_source",
        F.when(F.col("override_lag").isNotNull(), F.lit("OVERRIDE"))
         .when(F.col("derived_lag").isNotNull(), F.lit("DERIVED"))
         .otherwise(F.lit("DEFAULT_NO_CALIBRATION")),
    )
    .withColumn(
        "ultimate_lag_months",
        F.coalesce(
            F.col("override_lag"),
            F.col("derived_lag"),
            F.lit(CF_ULTIMATE_LAG_DEFAULT),
        ),
    )
    # Guard rails: a category cannot converge before MIN, and we cannot observe convergence beyond the calibration depth.
    .withColumn(
        "ultimate_lag_months",
        F.least(
            F.lit(CF_ULTIMATE_LAG_MAX),
            F.greatest(F.lit(CF_ULTIMATE_LAG_MIN), F.col("ultimate_lag_months")),
        ),
    )
    .select(*CF_ULTIMATE_LAG_KEYS, "measure", "ultimate_lag_months", "ultimate_lag_source")
)

print("Ultimate lag in force this run:")
display(ultimate_lag.orderBy("measure", *CF_ULTIMATE_LAG_KEYS))

# A category that never crosses the threshold inside the calibration window is still
# developing at CF_CALIBRATION_LAG_MONTHS -- the window itself is too short for it.
n_no_calib = ultimate_lag.filter(
    F.col("ultimate_lag_source") == "DEFAULT_NO_CALIBRATION"
).count()

if n_no_calib:
    print(f"  WARN: {n_no_calib} category/measure pairs had no calibration cohort and "
          f"fell back to CF_ULTIMATE_LAG_DEFAULT={CF_ULTIMATE_LAG_DEFAULT}.")


# COMMAND ----------

# DBTITLE 1,Densify to a Complete Lag Axis and Cumulate
# Generate a complete lag skeleton up to each category's ultimate lag and incurred-month maturity before joining incremental amounts

lag_axis = (
    spark.range(0, CF_ULTIMATE_LAG_MAX + 1)
    .select(F.col("id").cast("int").alias("lag_months"))
)

measure_axis = spark.createDataFrame([(m,) for m in CF_MEASURE_NAMES], "measure string")

skeleton = (
    inc_periods
    .crossJoin(lag_axis)
    .crossJoin(measure_axis)
    .join(ultimate_lag, on=[*CF_ULTIMATE_LAG_KEYS, "measure"], how="left")
    .filter(
        (F.col("lag_months") <= F.col("current_lag"))
        & (F.col("lag_months") <= F.col("ultimate_lag_months"))
    )
)

_w_cum = (
    Window.partitionBy(*CLM_SPLIT_KEYS, "fin_inc_month", "measure")
    .orderBy("lag_months")
    .rowsBetween(Window.unboundedPreceding, Window.currentRow)
)
_w_grp = Window.partitionBy(*CLM_SPLIT_KEYS, "fin_inc_month", "measure")

tri = (
    skeleton
    .join(
        tri_long,
        on=[*CLM_SPLIT_KEYS, "fin_inc_month", "lag_months", "measure"],
        how="left",
    )
    .withColumn("incr_amt", F.coalesce(F.col("incr_amt"), F.lit(0.0)))
    .withColumn("cum_amt", F.sum("incr_amt").over(_w_cum))
    .withColumn(
        "ult_amt",
        F.max(
            F.when(F.col("lag_months") == F.col("ultimate_lag_months"), F.col("cum_amt"))
        ).over(_w_grp),
    )
    .withColumn("is_mature", F.col("current_lag") >= F.col("ultimate_lag_months"))
    .withColumn(
        "pct_complete",
        F.when(F.col("ult_amt") > 0, F.col("cum_amt") / F.col("ult_amt")),
    )
)

# Preview table
print("Preview table: tri")
display(tri.limit(100))


# COMMAND ----------

# DBTITLE 1,Age-to-Age Link Ratio Observations
# An incurred month qualifies for lag d as soon as it has observed lag d+1 ---> it does NOT need to have reached the ultimate lag

_w_lead = (
    Window.partitionBy(*CLM_SPLIT_KEYS, "fin_inc_month", "measure")
    .orderBy("lag_months")
)

links_obs = (
    tri
    .withColumn("cum_next", F.lead("cum_amt").over(_w_lead))
    .filter(F.col("cum_next").isNotNull() & (F.col("cum_amt") > 0))
    # Exclude the newest development diagonal since the numerator sits in
    # the partial adjudication month exactly when current_lag == lag + 1
    .filter(F.col("current_lag") > F.col("lag_months") + F.lit(1))
)


#Information about the newest diagonal
def _shift_month(d, n):
    """First of the month n months before date d."""
    total = d.year * 12 + (d.month - 1) - n
    return date(total // 12, total % 12 + 1, 1)

print(f"Paid through {paid_through_dt} (month {paid_through_month_dt}); "
      f"newest diagonal excluded from fitting.")
print("Newest incurred month usable per lag:")
for _d in range(0, min(6, CF_ULTIMATE_LAG_MAX + 1)):
    print(f"    lag {_d}: through {_shift_month(paid_through_month_dt, _d + 2)}")

_w_link_rank = (
    Window.partitionBy(*CF_ULTIMATE_LAG_KEYS, "measure", "lag_months")
    .orderBy(F.col("fin_inc_month").desc())
)

links = (
    links_obs
    .withColumn("inc_rank", F.dense_rank().over(_w_link_rank))
    .filter(F.col("inc_rank") <= F.lit(CF_AVG_INCURRED_MONTHS))
    .select(
        *CLM_SPLIT_KEYS, "fin_inc_month", "lag_months", "measure",
        F.col("cum_amt").alias("cum_amt_base"),
        "cum_next",
    )
)

#Check to make sure the number of observations is greater than zero
n_fit_rows = links.count()
if n_fit_rows == 0:
    raise ValueError(
        "S01B: no age-to-age link ratio observations available for fitting."
    )
print(f"Link ratio observations: {n_fit_rows:,}")

print("Fitting cohort by lag:")
display(
    links.groupBy(*CF_ULTIMATE_LAG_KEYS, "measure", "lag_months")
    .agg(
        F.min("fin_inc_month").alias("first_inc_month"),
        F.max("fin_inc_month").alias("last_inc_month"),
        F.countDistinct("fin_inc_month").alias("n_inc_months"),
    )
    .orderBy("measure", *CF_ULTIMATE_LAG_KEYS, "lag_months")
)

print("Preview Link Observations:")
display(links.limit(1000))

# COMMAND ----------

# DBTITLE 1,Trimmed-Average Link Ratios with Credibility Fallback Ladder
def build_level_link_ratios(link_df, level_keys, level_name, apply_credibility):
    """Trimmed-mean age-to-age factor at `level_keys` x lag x measure.

    The trim drops CF_TRIM_COUNT observations from each tail, but only once at least
    CF_MIN_OBS_FOR_TRIM (set in S00) observations exist. Below that the mean is untrimmed.
    """
    agg = (
        link_df
        .groupBy(*level_keys, "fin_inc_month", "lag_months", "measure")
        .agg(
            F.sum("cum_amt_base").alias("cum_amt_base"),
            F.sum("cum_next").alias("cum_next"),
        )
        .filter(F.col("cum_amt_base") > 0)
        .withColumn("link_ratio", F.col("cum_next") / F.col("cum_amt_base"))
    )

    part = Window.partitionBy(*level_keys, "lag_months", "measure")
    ranked = (
        agg
        .withColumn("n_obs", F.count(F.lit(1)).over(part))
        .withColumn(
            "rn_low",
            F.row_number().over(
                part.orderBy(F.col("link_ratio").asc(), F.col("fin_inc_month").asc())
            ),
        )
        .withColumn(
            "rn_high",
            F.row_number().over(
                part.orderBy(F.col("link_ratio").desc(), F.col("fin_inc_month").asc())
            ),
        )
    )

    trimmed = ranked.filter(
        (F.col("n_obs") < F.lit(CF_MIN_OBS_FOR_TRIM))
        | (
            (F.col("rn_low") > F.lit(CF_TRIM_COUNT))
            & (F.col("rn_high") > F.lit(CF_TRIM_COUNT))
        )
    )

    out = (
        trimmed
        .groupBy(*level_keys, "lag_months", "measure")
        .agg(
            F.avg("link_ratio").alias("ldf"),
            F.count(F.lit(1)).alias("ldf_nobs"),
            F.sum("cum_amt_base").alias("ldf_base_amt"),
        )
        .withColumn("ldf_source", F.lit(level_name))
    )

    if apply_credibility:
        out = out.filter(
            (F.col("ldf_nobs") >= F.lit(CF_MIN_OBS))
            # Threshold is per measure: the denominator is dollars for CF_MEASURES
            # and raw counts for util, so they cannot share one number.
            & (F.col("ldf_base_amt") >= cf_min_link_base_expr())
        )
    return out


link_curve = (
    tri_long.select(*CLM_SPLIT_KEYS, "measure").distinct()
    .join(ultimate_lag, on=[*CF_ULTIMATE_LAG_KEYS, "measure"], how="left")
    .crossJoin(lag_axis)
    .filter(F.col("lag_months") <= F.col("ultimate_lag_months"))
)

levels = cf_fallback_levels()  # Defined in S00
for i, (level_name, level_keys) in enumerate(levels):
    is_last = i == len(levels) - 1
    level_df = build_level_link_ratios(
        links, level_keys, level_name, apply_credibility=not is_last
    ).select(
        *level_keys,
        "lag_months",
        "measure",
        F.col("ldf").alias(f"ldf_l{i}"),
        F.col("ldf_nobs").alias(f"nobs_l{i}"),
        F.col("ldf_source").alias(f"src_l{i}"),
    )
    link_curve = link_curve.join(
        level_df, on=[*level_keys, "lag_months", "measure"], how="left"
    )
    print(f"  level {i}: {level_name:<12} keys={level_keys if level_keys else '[all]'}")

# First level with a value wins.
_ldf_expr = F.coalesce(*[F.col(f"ldf_l{i}") for i in range(len(levels))])
_src_expr = F.col(f"src_l{len(levels) - 1}")
_nobs_expr = F.col(f"nobs_l{len(levels) - 1}")
for i in reversed(range(len(levels) - 1)):
    _src_expr = F.when(F.col(f"ldf_l{i}").isNotNull(), F.col(f"src_l{i}")).otherwise(_src_expr)
    _nobs_expr = F.when(F.col(f"ldf_l{i}").isNotNull(), F.col(f"nobs_l{i}")).otherwise(_nobs_expr)

link_curve = (
    link_curve
    .withColumn("is_ultimate_lag", F.col("lag_months") == F.col("ultimate_lag_months"))
    .withColumn("link_ratio_raw", _ldf_expr)
    .withColumn(
        "link_ratio_source",
        F.when(F.col("is_ultimate_lag"), F.lit("ULTIMATE_LAG_START"))
         .when(F.col("link_ratio_raw").isNull(), F.lit("NO_DATA_ASSUMED_1"))
         .otherwise(_src_expr),
    )
    .withColumn(
        "link_ratio_nobs",
        F.when(F.col("is_ultimate_lag"), F.lit(None).cast("long")).otherwise(_nobs_expr),
    )
    .withColumn(
        "link_ratio",
        F.when(F.col("is_ultimate_lag"), F.lit(1.0)).otherwise(
            F.least(
                F.lit(CF_LINK_RATIO_CAP),
                F.greatest(
                    F.lit(CF_LINK_RATIO_FLOOR),
                    F.coalesce(F.col("link_ratio_raw"), F.lit(1.0)),
                ),
            )
        ),
    )
)

print("Preview table: link_curve (age-to-age factors)")
display(
    link_curve
    .orderBy(*CLM_SPLIT_KEYS, "measure", *CF_ULTIMATE_LAG_KEYS, "lag_months")
    .limit(1000)
)


# COMMAND ----------

# DBTITLE 1,Chain the CDF, Invert to Completion Factors, Apply Caps and Monotonicity

# CDF at lag d = product of age-to-age factors from lag d through ultimate lag - Implement as exp(sum(log(link_ratio))) over a descending lag window since Spark has no product aggregate.
# Completion factor = 1 / CDF

_w_cdf = (
    Window.partitionBy(*CLM_SPLIT_KEYS, "measure")
    .orderBy(F.col("lag_months").desc())
    .rowsBetween(Window.unboundedPreceding, Window.currentRow)
)

link_curve = (
    link_curve
    .withColumn("cdf", F.exp(F.sum(F.log("link_ratio")).over(_w_cdf)))
    .withColumn("completion_factor_raw", F.lit(1.0) / F.col("cdf"))
    .withColumn(
        "completion_factor_capped",
        F.least(
            F.lit(1.0),
            F.greatest(F.lit(CF_FLOOR), F.col("completion_factor_raw")),
        ),
    )
)

if CF_ENFORCE_MONOTONIC:
    _w_mono = (
        Window.partitionBy(*CLM_SPLIT_KEYS, "measure")
        .orderBy("lag_months")
        .rowsBetween(Window.unboundedPreceding, Window.currentRow)
    )
    link_curve = link_curve.withColumn(
        "completion_factor", F.max("completion_factor_capped").over(_w_mono)
    )
else:
    link_curve = link_curve.withColumn(
        "completion_factor", F.col("completion_factor_capped")
    )

# CF at the PREVIOUS lag, carried on the curve so the partial-month interpolation can happen (using factor f derived above)
# downstream has both endpoints. Must be taken here: link_curve holds every lag,
# whereas `factors` is filtered to one row per incurred month. CF[-1] = 0 at lag 0
# (nothing is adjudicated before the incurred month opens).
_w_prev_lag = Window.partitionBy(*CLM_SPLIT_KEYS, "measure").orderBy("lag_months")
link_curve = link_curve.withColumn(
    "completion_factor_prev_lag",
    F.coalesce(F.lag("completion_factor").over(_w_prev_lag), F.lit(0.0)),
)

print("Preview table: link_curve (chained)")
display(
    link_curve
    .select(*CLM_SPLIT_KEYS, "measure", "lag_months", "link_ratio", "cdf",
            "completion_factor_raw", "completion_factor", "link_ratio_source")
    .orderBy(*CLM_SPLIT_KEYS, "measure", "lag_months")
    .limit(1000)
)

# COMMAND ----------

# DBTITLE 1,Attach Factors and Interpolate the Partial Month
factors = (
    tri
    .join(
        link_curve.select(
            *CLM_SPLIT_KEYS, "measure", "lag_months",
            "link_ratio_raw", "link_ratio", "link_ratio_source", "link_ratio_nobs",
            "cdf", "completion_factor_raw", "completion_factor_capped",
            "completion_factor", "completion_factor_prev_lag",
        ),
        on=[*CLM_SPLIT_KEYS, "measure", "lag_months"],
        how="left",
    )
    # The newest lag available for this incurred month. Capped at the ultimate lag:
    # a month more developed than its ultimate lag has no row at lag == current_lag,
    # so keying only on current_lag would drop it from the table entirely.
    .withColumn(
        "current_lag_ind",
        F.col("lag_months") == F.least(F.col("current_lag"), F.col("ultimate_lag_months")),
    )
    .filter(F.col("current_lag_ind"))  # Only need most recent lag for remaining steps
    # This row's cumulative reaches into the partial adjudication month only when its
    # lag IS the current lag. If it was capped at the ultimate lag the partial month
    # lies beyond it, every adjudication month in the cumulative is complete, and no
    # interpolation applies.
    .withColumn("is_partial_lag", F.col("lag_months") == F.col("current_lag"))
    .join(partial_frac.select(*CF_PARTIAL_FRAC_KEYS, "measure", "partial_month_frac",
                              "partial_frac_source"),
          on=[*CF_PARTIAL_FRAC_KEYS, "measure"], how="left")
    .withColumn(
        "partial_month_frac",
        F.coalesce(F.col("partial_month_frac"), F.lit(_global_frac)),
    )
    # CF*[d] = CF[d-1] + f * (CF[d] - CF[d-1]).  A factor on the same truncated basis
    # as the observation S02 will divide, instead of a full-month factor applied to a
    # part-month observation.
    .withColumn(
        "completion_factor_applied",
        F.when(
            F.col("is_partial_lag"),
            F.col("completion_factor_prev_lag")
            + F.col("partial_month_frac")
            * (F.col("completion_factor") - F.col("completion_factor_prev_lag")),
        ).otherwise(F.col("completion_factor")),
    )
    # Same floor as the monthly factor, so the implied gross-up stays bounded.
    .withColumn(
        "completion_factor_applied",
        F.least(F.lit(1.0), F.greatest(F.lit(CF_FLOOR), F.col("completion_factor_applied"))),
    )
)

# Preview Table
print("Preview table: factors")
display(factors.limit(1000))

print("Interpolation effect on the current diagonal (avg by measure and lag):")
display(
    factors.filter(F.col("is_partial_lag"))
    .groupBy("measure", "lag_months")
    .agg(
        F.count(F.lit(1)).alias("rows"),
        F.avg("partial_month_frac").alias("avg_f"),
        F.avg("completion_factor_prev_lag").alias("avg_cf_prev"),
        F.avg("completion_factor").alias("avg_cf_full_month"),
        F.avg("completion_factor_applied").alias("avg_cf_applied"),
        F.avg(F.col("completion_factor") / F.col("completion_factor_applied") - 1.0)
            .alias("avg_uplift_to_ultimate"),
    )
    .orderBy("measure", "lag_months")
)

# COMMAND ----------

# MAGIC %md
# MAGIC # Validation

# COMMAND ----------

# DBTITLE 1,Review Credibility Thresholds
# This reports the actual distribution at the SPLIT level against the threshold in
# force (set in S00), plus how much of the book each gate admits.

_split_base = (
    links
    .groupBy(*CLM_SPLIT_KEYS, "lag_months", "measure")
    .agg(
        F.sum("cum_amt_base").alias("ldf_base_amt"),
        F.countDistinct("fin_inc_month").alias("n_obs"),
    )
)

display(
    _split_base
    .groupBy("measure")
    .agg(
        F.count(F.lit(1)).alias("n_split_lag_cells"),
        F.expr("percentile_approx(ldf_base_amt, 0.10)").alias("p10_base"),
        F.expr("percentile_approx(ldf_base_amt, 0.50)").alias("p50_base"),
        F.expr("percentile_approx(ldf_base_amt, 0.90)").alias("p90_base"),
        F.avg((F.col("ldf_base_amt") >= cf_min_link_base_expr()).cast("int"))
            .alias("pct_clearing_volume"),
        F.avg((F.col("n_obs") >= F.lit(CF_MIN_OBS)).cast("int"))
            .alias("pct_clearing_min_obs"),
        F.avg(
            ((F.col("ldf_base_amt") >= cf_min_link_base_expr())
             & (F.col("n_obs") >= F.lit(CF_MIN_OBS))).cast("int")
        ).alias("pct_clearing_both"),
    )
    .withColumn("threshold_in_force", cf_min_link_base_expr())
    .orderBy("measure")
)

# COMMAND ----------

# DBTITLE 1,Basic Validation
def check(label, count, fail=False):
    """Report a validation count; raise when `fail` and the count is non-zero."""
    status = "OK  " if count == 0 else ("FAIL" if fail else "WARN")
    print(f"  [{status}] {label}: {count:,}")
    if fail and count:
        raise ValueError(f"S01B validation failed - {label}: {count:,}")


print("Validation")

# Duplicates at the declared output grain.
_grain = [*CLM_SPLIT_KEYS, "fin_inc_month", "lag_months", "measure"]
n_rows = factors.count()
n_distinct = factors.select(*_grain).distinct().count()
check("duplicate rows at output grain", n_rows - n_distinct, fail=True)

# Every row must carry a usable factor.
check(
    "null completion_factor",
    factors.filter(F.col("completion_factor").isNull()).count(),
    fail=True,
)
check(
    "non-positive completion_factor",
    factors.filter(F.col("completion_factor") <= 0).count(),
    fail=True,
)
check(
    "completion_factor > 1 after cap",
    factors.filter(F.col("completion_factor") > 1.0).count(),
    fail=True,
)
check(
    "null ultimate_lag_months",
    factors.filter(F.col("ultimate_lag_months").isNull()).count(),
    fail=True,
)

# Unreasonable factors before capping, and how often the cap/floor actually bound.
check(
    "raw factor outside [CF_FLOOR, 1] (capped)",
    factors.filter(
        (F.col("completion_factor_raw") < F.lit(CF_FLOOR))
        | (F.col("completion_factor_raw") > 1.0)
    ).count(),
)
check(
    "negative cumulative amount",
    factors.filter(F.col("cum_amt") < 0).count(),
)
check(
    "mature month with zero ultimate (no observable pct_complete)",
    factors.filter(F.col("is_mature") & (F.coalesce(F.col("ult_amt"), F.lit(0.0)) <= 0)).count(),
)

# Exactly one current-lag row per split-month-measure, so the S02 join stays 1:1.
# Must be measured on the current_lag_ind subset: `factors` holds every lag, so
# comparing all rows against distinct split-month-measure always differs.
_cur = factors.filter(F.col("current_lag_ind"))
n_cur = _cur.count()
n_cur_distinct = _cur.select(*CLM_SPLIT_KEYS, "fin_inc_month", "measure").distinct().count()
check("current_lag_ind rows not 1:1 per split-month-measure", n_cur - n_cur_distinct, fail=True)

# --- Partial-month exclusion actually took effect ---
# Verified from the data rather than by trusting the filter, so a later edit cannot
# silently reintroduce the bias. Every numerator feeding the FIT must come from an
# adjudication month strictly earlier than the paid-through month.
_fit_adjd = links.withColumn(
    "numer_adjd_month",
    F.expr("add_months(to_date(cast(fin_inc_month as string),'yyyyMM'), lag_months + 1)"),
)
_max_fit_adjd = _fit_adjd.agg(F.max("numer_adjd_month").alias("m")).collect()[0]["m"]
print(f"  [INFO] newest adjudication month in fitting data: {_max_fit_adjd} "
      f"(paid-through month {paid_through_month_dt})")
check(
    "fitting observations reaching into the partial adjudication month",
    _fit_adjd.filter(
        F.col("numer_adjd_month") >= F.lit(paid_through_month_dt)
    ).count(),
    fail=True,
)

# --- Partial-month interpolation ---
check(
    "null completion_factor_applied",
    factors.filter(F.col("completion_factor_applied").isNull()).count(),
    fail=True,
)
check(
    "partial_month_frac outside [0, 1]",
    factors.filter(
        (F.col("partial_month_frac") < 0) | (F.col("partial_month_frac") > 1)
    ).count(),
    fail=True,
)
# f <= 1, so the interpolated factor can never exceed the full-month factor, and it
# must sit at or above the previous lag's factor. Either breach means the endpoints
# were mismatched.
check(
    "interpolated factor above the full-month factor",
    factors.filter(
        F.col("completion_factor_applied") > F.col("completion_factor") + F.lit(1e-9)
    ).count(),
    fail=True,
)
check(
    "interpolated factor below the previous lag's factor",
    factors.filter(
        F.col("is_partial_lag")
        & (F.col("completion_factor_applied")
           < F.col("completion_factor_prev_lag") - F.lit(1e-9))
    ).count(),
    fail=True,
)
check(
    "f fell back to the global median (no measured history for that key)",
    factors.filter(F.col("partial_frac_source") == "GLOBAL_MEDIAN").count(),
)

# Fallback usage: how much of the book could not be fitted at its own grain.
print("\nFallback level usage for link ratios (current-lag rows):")
display(
    _cur.groupBy("measure", "link_ratio_source")
    .agg(F.count(F.lit(1)).alias("rows"), F.sum("cum_amt").alias("cum_amt"))
    .orderBy("measure", "link_ratio_source")
)

# COMMAND ----------

# DBTITLE 1,Validation: Goodness of Fit vs Observed Percent Complete
# For mature months, compare pct_complete vs completion factor to assess fit
fit_check = (
    factors
    .filter(F.col("is_mature") & F.col("pct_complete").isNotNull())
    .withColumn("resid", F.col("completion_factor") - F.col("pct_complete"))
    .groupBy("measure", "lag_months")
    .agg(
        F.count(F.lit(1)).alias("n_obs"),
        F.avg("pct_complete").alias("avg_observed"),
        F.avg("completion_factor").alias("avg_fitted"),
        F.avg("resid").alias("mean_resid"),
        F.avg(F.abs(F.col("resid"))).alias("mean_abs_resid"),
    )
    .withColumn("mean_resid_bps", F.col("mean_resid") * 10000)
    .orderBy("measure", "lag_months")
)
print("Fitted vs observed by lag (mean_resid_bps > 0 => factor too high => ultimate too low):")
display(fit_check)

# COMMAND ----------

# DBTITLE 1,Validation: Dollar Reconciliation
# The triangle only carries lags up to each category's ultimate lag, so it will not
# tie to the full S01 extract. Reconcile against the same lag window and report the
# excluded tail separately -> a large tail means an ultimate lag is too short
recon = (
    tri_long
    .join(ultimate_lag, on=[*CF_ULTIMATE_LAG_KEYS, "measure"], how="left")
    .withColumn(
        "in_window", F.col("lag_months") <= F.col("ultimate_lag_months")
    )
    .groupBy("measure", "in_window")
    .agg(F.sum("incr_amt").alias("source_amt"))
)

print("Excluded-tail share by measure (large values indicate => ultimate lag too short):")
display(
    recon.groupBy("measure")
    .agg(
        F.sum(F.when(~F.col("in_window"), F.col("source_amt")).otherwise(F.lit(0.0))).alias("tail_amt"),
        F.sum("source_amt").alias("total_amt"),
    )
    .withColumn("tail_pct", F.col("tail_amt") / F.col("total_amt"))
    .orderBy("measure")
)

# COMMAND ----------

# DBTITLE 1,Check: Development Triangle by Category
# Generally looking for: Each curve should rise with lag and reach 1.0
# 1.0 exactly at its own ultimate lag, with link ratios decaying toward 1.0.
display(
    spark.read.table(table_fqn("cf"))
    .filter(F.col("VAL_DATE") == F.lit(val_date_str).cast("date"))
    .groupBy("measure", *CF_ULTIMATE_LAG_KEYS, "lag_months")
    .agg(
        F.avg("link_ratio").alias("age_to_age_factor"),
        F.avg("cdf").alias("cdf"),
        F.avg("completion_factor").alias("completion_factor"),
        F.max("ultimate_lag_months").alias("ultimate_lag_months"),
        F.max("ultimate_lag_source").alias("ultimate_lag_source"),
        F.max("link_ratio_source").alias("link_ratio_source"),
        F.count(F.lit(1)).alias("rows"),
    )
    .orderBy("measure", *CF_ULTIMATE_LAG_KEYS, "lag_months")
)

# COMMAND ----------

# DBTITLE 1,Assemble and Write Factor Table
out_cols = [
    *CLM_SPLIT_KEYS,
    "fin_inc_month",
    "lag_months",
    "measure",
    "incr_amt",
    "cum_amt",
    "ult_amt",
    "pct_complete",            # observed, diagnostic only
    "link_ratio_raw",          # fitted age-to-age factor before floor/cap
    "link_ratio",              # age-to-age factor in force
    "link_ratio_source",       # fallback rung, or ULTIMATE_LAG_PINNED / NO_DATA_ASSUMED_1
    "link_ratio_nobs",
    "cdf",                     # cumulative development factor = prod(link_ratio, d..D)
    "completion_factor_raw",   # 1 / cdf
    "completion_factor",       # full-month factor at this discrete lag
    "completion_factor_prev_lag",
    "partial_month_frac",      # measured share of the partial month received
    "partial_frac_source",
    "is_partial_lag",          # true when this row's cumulative includes the partial month
    "completion_factor_applied",  # interpolated -- what S02 divides by
    "is_mature",
    "current_lag",
    "current_lag_ind",
    "ultimate_lag_months",
    "ultimate_lag_source",
]

df_factors = (
    factors
    .select(*out_cols)
    .withColumn("completeness_threshold", F.lit(CF_COMPLETENESS_THRESHOLD))
    .withColumn("paid_through_dt", F.lit(paid_through_dt).cast("date"))
    .withColumn("VAL_DATE", F.lit(val_date_str).cast("date"))
)

print(f"Factor table: {df_factors.count():,} rows x {len(df_factors.columns)} cols")
display(df_factors.limit(1000))

write_to_catalog(
    spark, df_factors, table_fqn("cf"), f"VAL_DATE = DATE('{val_date_str}')"
)
