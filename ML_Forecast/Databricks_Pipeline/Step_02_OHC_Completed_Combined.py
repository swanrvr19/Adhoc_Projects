f_raw = spark.table('ra_analytic_dev.ohc_forecast.dev_tfm_hcta_oh_data')

# Prefer VAL_DATE from upstream extract_hcta task value; fall back to deriving
# from the source table when running the notebook interactively outside a job.
try:
    VAL_DATE = dbutils.jobs.taskValues.get(taskKey="extract_hcta", key="val_date")
    print(f"VAL_DATE from task value: {VAL_DATE}")
except (AttributeError, TypeError):
    _max_yrmo = (
        df_raw
        .filter("MAJ_SRV_CAT != 'MBR'")
        .selectExpr("MAX(YR_MO) AS max_yrmo")
        .collect()[0]["max_yrmo"]
    )
    VAL_DATE = f"{_max_yrmo[:4]}-{_max_yrmo[4:6]}-01"
    print(f"Derived VAL_DATE from claim-rows MAX(YR_MO)={_max_yrmo}: {VAL_DATE}")

# Filter to the current snapshot only — prevents mixing val_dates once the source stacks
df_raw = df_raw.filter(f"VAL_DATE = TO_DATE('{VAL_DATE}')")

     

from pyspark.sql import functions as F

# Matches ra_analytic_dev.cs_enriched_data.completed_hectar_combined column order
TARGET_COLS = [
    'MARKET', 'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_2_TADM', 'PRODUCT_LEVEL_3_TADM', 'SEGMENT',
    'IS_DUAL', 'HCC', 'SERVICE_TYPE', 'SERVICE_CATEGORY',
    'DATE_REPORT_QTR', 'DATE_REPORT_MONTH', 'DURATION', 'VAL_DATE',
    'MM', 'UTIL', 'PD', 'UTIL_K', 'PMPM', 'BF_ESTIMATE_UTIL_K', 'BF_ESTIMATE_PMPM',
]

# MBR_COUNT only exists on MAJ_SRV_CAT = 'MBR' rows — not on claim rows.
# Join key per mapping table: YR_MO + LOB + PLAN_TYPE + RISK_TYPE + ENTY + SEGMENT
# (CONTR_NBR excluded — format mismatches between MBR and claim rows)
MM_JOIN_KEYS = ['YR_MO', 'LOB', 'PLAN_TYPE', 'RISK_TYPE', 'ENTY', 'SEGMENT']

# Enrollment grain in pipeline column names — one MM value per group per month.
ENROLL_KEYS = [
    'SEGMENT', 'MARKET',
    'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_2_TADM', 'PRODUCT_LEVEL_3_TADM',
]
MM_SPINE_KEYS = ENROLL_KEYS + ['DATE_REPORT_MONTH']

# Claim-split identity — the tuple that defines one longitudinal time series.
# SEGMENT is part of the key, so the OHC and OC claim taxonomies are never mixed:
# a split only ever pairs a segment's products with that same segment's categories.
SPLIT_KEYS = ENROLL_KEYS + ['HCC', 'SERVICE_TYPE', 'SERVICE_CATEGORY']
CLAIM_GRAIN = SPLIT_KEYS + ['DATE_REPORT_MONTH']


def _yr_mo_to_month(col):
    """YYYYMM (string or int) -> first-of-month DATE."""
    s = col.cast('string')
    return F.make_date(s.substr(1, 4).cast('int'), s.substr(5, 2).cast('int'), F.lit(1))


def _add_derived_keys(sdf):
    """Attach key columns that are pure functions of the split tuple + month."""
    return (
        sdf
        # --- IS_DUAL: bigint 1 when DSNP/MMP, else 0 ---
        .withColumn('IS_DUAL',
            F.when(F.col('PRODUCT_LEVEL_2_TADM').isin('MA DSNP', 'DSNP', 'MA MMP'), F.lit(1))
             .otherwise(F.lit(0))
             .cast('long')
        )
        # --- DATE_REPORT_QTR: 'YYYYQn' string e.g. '2025Q4' ---
        .withColumn('DATE_REPORT_QTR',
            F.concat(
                F.year('DATE_REPORT_MONTH').cast('string'),
                F.lit('Q'),
                F.quarter('DATE_REPORT_MONTH').cast('string')
            )
        )
        # --- DURATION: bigint 0 (HCTA data is pre-completed) ---
        .withColumn('DURATION', F.lit(0).cast('long'))
        # --- VAL_DATE: derived from source MAX(YR_MO) — not a real completion date ---
        .withColumn('VAL_DATE', F.lit(VAL_DATE).cast('date'))
    )


# --- Step 1: aggregate MM from MBR rows, expressed in pipeline column names ---
# MM > 0 is the membership existence test that bounds the spine (a split only gets a
# month if its enrollment group actually had members that month).
df_mm = (
    df_raw
    .filter(F.col('MAJ_SRV_CAT') == 'MBR')
    .groupBy(*MM_JOIN_KEYS)
    .agg(F.sum('MBR_COUNT').cast('double').alias('MM'))
    .withColumnsRenamed({
        'ENTY':      'MARKET',
        'LOB':       'PRODUCT_LEVEL_1_TADM',
        'PLAN_TYPE': 'PRODUCT_LEVEL_2_TADM',
        'RISK_TYPE': 'PRODUCT_LEVEL_3_TADM',
    })
    .withColumn('DATE_REPORT_MONTH', _yr_mo_to_month(F.col('YR_MO')))
    .filter(F.col('MM') > 0)
    .select(*MM_SPINE_KEYS, 'MM')
)

# --- Step 2: claim rows only (everything except MBR), renamed to pipeline columns ---
df_claims = (
    df_raw
    .filter(F.col('MAJ_SRV_CAT') != 'MBR')
    # --- direct renames (category columns passed through as-is) ---
    .withColumnsRenamed({
        'ENTY':          'MARKET',
        'LOB':           'PRODUCT_LEVEL_1_TADM',
        'PLAN_TYPE':     'PRODUCT_LEVEL_2_TADM',
        'RISK_TYPE':     'PRODUCT_LEVEL_3_TADM',
        'MIN_SRV_CAT':   'SERVICE_TYPE',
        'HCE_SRVC_CAT':  'SERVICE_CATEGORY',
        'NET_AMT_COMP':  'PD',
    })
    # --- HCC: collapse OHC schema names to OC equivalents so the training
    #     notebook's single HCC filter (e.g. hcc: PHYSICIAN) covers both sources ---
    .withColumn('HCC',
        F.when(F.col('MAJ_SRV_CAT').isin('INPATIENT', 'IP'),      F.lit('INPATIENT'))
         .when(F.col('MAJ_SRV_CAT').isin('OUTPATIENT', 'OP'),     F.lit('OUTPATIENT'))
         .when(F.col('MAJ_SRV_CAT').isin('PH', 'PHYSICIAN'),      F.lit('PHYSICIAN'))
         .when(F.col('MAJ_SRV_CAT') == 'RX',                      F.lit('PHARMACY'))
         .otherwise(F.col('MAJ_SRV_CAT'))
    )
    # --- DATE_REPORT_MONTH: date from YYYYMM string ---
    .withColumn('DATE_REPORT_MONTH', _yr_mo_to_month(F.col('YR_MO')))
    # --- UTIL: first non-zero count column across all util types ---
    # Mirrors the EDA bypass logic; safe regardless of HCC schema (OHC or OC)
    .withColumn('UTIL',
        F.when(F.col('IP_ADMITS_UNITS_TREND') > 0, F.col('IP_ADMITS_UNITS_TREND'))
         .when(F.col('IP_DAYS_UNITS_TREND')   > 0, F.col('IP_DAYS_UNITS_TREND'))
         .when(F.col('OP_VISITS_UNITS_TREND')    > 0, F.col('OP_VISITS_UNITS_TREND'))
         .when(F.col('OP_PROC_UNITS_TREND')     > 0, F.col('OP_PROC_UNITS_TREND'))
         .when(F.col('PH_PROC_UNITS_TREND')     > 0, F.col('PH_PROC_UNITS_TREND'))
         .when(F.col('RX_SCRIPT_UNITS_TREND')   > 0, F.col('RX_SCRIPT_UNITS_TREND'))
         .otherwise(F.lit(None).cast('double'))
    )
)

# --- Step 3: aggregate claim rows to the split x month grain ---
# Distinct on CLAIM_GRAIN, so joining it onto the spine cannot fan rows out.
df_claims_agg = (
    df_claims
    .groupBy(*CLAIM_GRAIN)
    .agg(
        F.sum('UTIL').cast('double').alias('UTIL'),
        F.sum('PD').cast('double').alias('PD'),
    )
)

     

# --- Step 4: build the spine (cartesian product of splits x months) ---------------
#
# The model needs a clear longitudinal series per split: one row per month for every
# split, including the many months with zero utilization.  Claim rows alone are sparse,
# which silently corrupts every lag / rolling / zero-count feature built downstream in
# signals_units (TARGET_*_1/2/3/12, COUNT_ZEROS_*, VARIANCE_12_MO_*, SLOPE_12_*).
#
# Spine  = DISTINCT observed split tuples  x  contiguous month axis
#          restricted to months where the split's enrollment group has MM > 0.
#
# Only split tuples that were actually observed are used, so no impossible
# product x category combination is invented, and OHC/OC taxonomies stay separate.

# Contiguous month axis spanning the whole claims history
_bounds = (
    df_claims_agg
    .agg(
        F.min('DATE_REPORT_MONTH').alias('min_mo'),
        F.max('DATE_REPORT_MONTH').alias('max_mo'),
    )
    .collect()[0]
)
MIN_MONTH, MAX_MONTH = _bounds['min_mo'], _bounds['max_mo']

df_months = spark.sql(
    f"SELECT explode(sequence(DATE'{MIN_MONTH}', DATE'{MAX_MONTH}', INTERVAL 1 MONTH))"
    " AS DATE_REPORT_MONTH"
)

# Split tuples actually observed in the claims data
df_splits = df_claims_agg.select(*SPLIT_KEYS).distinct()

n_splits = df_splits.count()
n_months = df_months.count()
print(f'Split tuples observed  : {n_splits:>12,}')
print(f'Month axis             : {MIN_MONTH} -> {MAX_MONTH}  ({n_months:,} months)')
print(f'Full cartesian product : {n_splits * n_months:>12,} rows (before the MM > 0 restriction)')

# Spine: cross-join, then inner-join MM so only months with members survive
df_spine = (
    df_splits
    .crossJoin(df_months)
    .join(df_mm, on=MM_SPINE_KEYS, how='inner')
)

     

# --- Step 5: attach actual claims to the spine, zero-fill, derive rates ----------
#
# Matches the C&S pattern (cf_combined_source_view):
#   spine LEFT JOIN claims  →  zero-fill sparse months  →  derive PMPM / UTIL_K
#
# The INNER JOIN on membership in step 4 (df_spine) already guarantees MM > 0 for
# every row.  Claims whose enrollment group has no MBR match ("orphans") are
# intentionally excluded — you cannot compute a per-member rate without members.
# The orphan dollar gap is reported in the control totals below as an info metric.
df = (
    _add_derived_keys(df_spine)
    .join(df_claims_agg, on=CLAIM_GRAIN, how='left')
    .withColumn('UTIL', F.coalesce(F.col('UTIL'), F.lit(0.0)))
    .withColumn('PD',   F.coalesce(F.col('PD'),   F.lit(0.0)))
    .withColumn('UTIL_K', F.col('UTIL') * 12000 / F.col('MM'))
    .withColumn('PMPM',   F.col('PD') / F.col('MM'))
    .withColumn('BF_ESTIMATE_UTIL_K', F.col('UTIL_K'))
    .withColumn('BF_ESTIMATE_PMPM',   F.col('PMPM'))
    .select(*TARGET_COLS)
)

     

display(df)
     

# Control Totals: verify the densified transform is structurally sound
#
# The output is spine-driven (C&S pattern): spine LEFT JOIN claims, INNER JOIN
# membership.  Claims whose enrollment group has no MBR match ("orphans") are
# excluded — you cannot compute a per-member rate without members.
#
# Consequences for control totals:
#   PD / UTIL will NOT tie exactly to the raw source — the orphan gap is expected
#   and reported as an info metric.  Hard-asserted: output <= source (no inflation).
#
#   MM in source: only on MAJ_SRV_CAT='MBR' rows -- one per (enrollment group x month).
#   In the output MM is repeated across every claim category in that group, so a raw
#   sum(MM) is inflated.  Fix: deduplicate at the enrollment grain before summing.
#   Expected value = MM of the enrollment groups that appear in the observed split set;
#   groups that never produced a claim in any month are still excluded by design.
#
#   Row count: expected to grow by a large multiple.  Reported, not asserted.


# 1. Source totals

# MM: sum MBR_COUNT from MBR rows -- each (enrollment group x month) contributes once
src_mm = (
    df_raw
    .filter(F.col('MAJ_SRV_CAT') == 'MBR')
    .agg(F.sum('MBR_COUNT').alias('v'))
    .collect()[0]['v']
)

# PD: sum net allowed amount from all claim (non-MBR) rows
src_pd = (
    df_raw
    .filter(F.col('MAJ_SRV_CAT') != 'MBR')
    .agg(F.sum('NET_AMT_COMP').alias('v'))
    .collect()[0]['v']
)

# UTIL: apply the same first-non-zero column selection as the transform
src_util = (
    df_raw
    .filter(F.col('MAJ_SRV_CAT') != 'MBR')
    .select(
        F.when(F.col('IP_ADMITS_UNITS_TREND') > 0, F.col('IP_ADMITS_UNITS_TREND'))
         .when(F.col('IP_DAYS_UNITS_TREND')   > 0, F.col('IP_DAYS_UNITS_TREND'))
         .when(F.col('OP_VISITS_UNITS_TREND') > 0, F.col('OP_VISITS_UNITS_TREND'))
         .when(F.col('OP_PROC_UNITS_TREND')   > 0, F.col('OP_PROC_UNITS_TREND'))
         .when(F.col('PH_PROC_UNITS_TREND')   > 0, F.col('PH_PROC_UNITS_TREND'))
         .when(F.col('RX_SCRIPT_UNITS_TREND') > 0, F.col('RX_SCRIPT_UNITS_TREND'))
         .otherwise(F.lit(None).cast('double'))
         .alias('util_row')
    )
    .agg(F.sum('util_row').alias('v'))
    .collect()[0]['v']
)

src_rows = df_raw.filter(F.col('MAJ_SRV_CAT') != 'MBR').count()

# Expected output MM: enrollment group-months reachable from the observed split set,
# bounded by the spine's month axis (MBR rows outside the claims history are not spined).
_split_groups = df_splits.select(*ENROLL_KEYS).distinct()
_exp = (
    df_mm
    .filter(F.col('DATE_REPORT_MONTH').between(F.lit(MIN_MONTH), F.lit(MAX_MONTH)))
    .join(_split_groups, on=ENROLL_KEYS, how='inner')
    .agg(F.sum('MM').alias('mm'), F.count(F.lit(1)).alias('groups'))
    .collect()[0]
)
exp_mm, exp_mm_groups = _exp['mm'], _exp['groups']


# 2. Output totals -- single pass over df

_out = (
    df
    .agg(
        F.count(F.lit(1)).alias('rows'),
        F.sum('PD').alias('pd'),
        F.sum('UTIL').alias('util'),
        F.sum(F.when((F.col('UTIL') == 0) & (F.col('PD') == 0), 1).otherwise(0)).alias('zero_rows'),
    )
    .collect()[0]
)
out_rows, out_pd, out_util = _out['rows'], _out['pd'], _out['util']
out_zero_rows = _out['zero_rows']

# MM: deduplicate at the enrollment grain so each (group x month) contributes once
_out_mm = (
    df
    .select(*MM_SPINE_KEYS, 'MM')
    .dropDuplicates(MM_SPINE_KEYS)
    .agg(F.sum('MM').alias('mm'), F.sum(F.when(F.col('MM').isNotNull(), 1).otherwise(0)).alias('groups'))
    .collect()[0]
)
out_mm, out_mm_groups = _out_mm['mm'], _out_mm['groups']


# 3. Report

def _fmt(v):
    if v is None:
        return 'None'
    return f'{v:>20,.2f}'

def _pct(src, out):
    if src is None or out is None or src == 0:
        return 'n/a'
    return f'{abs(out - src) / abs(src) * 100:.4f}%'

# Orphan gap: claims excluded because their enrollment group has no MBR match.
# This is the expected difference between source PD/UTIL and output PD/UTIL.
_orphan_pd   = (src_pd   or 0) - (out_pd   or 0)
_orphan_util = (src_util or 0) - (out_util or 0)

# (label, expected, output, hard_assert)
check_rows = [
    ('MM  (deduped at enrollment grain)', exp_mm,        out_mm,        True),
    ('MM  (enrollment group-months)',     exp_mm_groups, out_mm_groups, True),
    ('PD  (sum NET_AMT_COMP)',            src_pd,        out_pd,        False),
    ('UTIL (health-claim utilization)',   src_util,      out_util,      False),
    ('Row count (source claim rows)',     src_rows,      out_rows,      False),
]

hdr = f"{'Metric':<34}  {'Expected':>20}  {'Output':>20}  {'Abs diff':>20}  {'% diff':>10}  Assert"
sep = '-' * len(hdr)
print(sep)
print(hdr)
print(sep)
for label, s, o, hard in check_rows:
    diff = None if (s is None or o is None) else abs(s - o)
    flag = 'YES' if hard else 'info'
    print(f"{label:<34}  {_fmt(s)}  {_fmt(o)}  {_fmt(diff)}  {_pct(s, o):>10}  {flag}")
print(sep)

# Enrollment coverage: groups with members but no claim in any month stay excluded
if src_mm and exp_mm is not None and src_mm > exp_mm:
    print(
        f'\nINFO enrollment coverage: {exp_mm / src_mm * 100:.1f}% of source MM is reachable'
        ' from the observed split set; the remainder belongs to enrollment groups that'
        ' never produced a claim row and are intentionally excluded.'
    )

# Orphan gap: claims with no enrollment match are excluded (C&S pattern)
if _orphan_pd:
    print(
        f'\nINFO orphan exclusion: ${_orphan_pd:,.2f} PD'
        f' ({abs(_orphan_pd) / abs(src_pd) * 100:.4f}% of source) and'
        f' {_orphan_util:,.1f} UTIL excluded — claims had no matching MBR row.'
    )


# 4. Densification diagnostics

_dup_grain = df.groupBy(*CLAIM_GRAIN).count().filter(F.col('count') > 1).count()

_per_split = (
    df
    .filter(F.col('MM').isNotNull())
    .groupBy(*SPLIT_KEYS)
    .agg(
        F.countDistinct('DATE_REPORT_MONTH').alias('n_months'),
        F.min('DATE_REPORT_MONTH').alias('min_mo'),
        F.max('DATE_REPORT_MONTH').alias('max_mo'),
    )
    .withColumn('span_months', F.months_between('max_mo', 'min_mo').cast('int') + 1)
    .withColumn('gap_months', F.col('span_months') - F.col('n_months'))
)
_dens = (
    _per_split
    .agg(
        F.count(F.lit(1)).alias('splits'),
        F.min('n_months').alias('min_months'),
        F.expr('percentile_approx(n_months, 0.5)').alias('median_months'),
        F.max('n_months').alias('max_months'),
        F.sum(F.when(F.col('gap_months') > 0, 1).otherwise(0)).alias('splits_with_gaps'),
        F.sum(F.when(F.col('n_months') < 24, 1).otherwise(0)).alias('splits_under_24_mo'),
    )
    .collect()[0]
)

print()
print(sep)
print('Densification diagnostics')
print(sep)
print(f"  Output rows                       : {out_rows:>15,}")
print(f"  Zero-utilization rows             : {out_zero_rows:>15,}  ({out_zero_rows / out_rows * 100:.1f}%)")
print(f"  Orphan claims excluded (no MBR)   : PD ${_orphan_pd:,.2f}"
      f" ({abs(_orphan_pd) / abs(src_pd) * 100 if src_pd else 0:.4f}% of source)")
print(f"  Splits on the spine               : {_dens['splits']:>15,}  of {n_splits:,} observed")
print(f"  Months per split  min / med / max : {_dens['min_months']:>5,} / {_dens['median_months']:>5,} / {_dens['max_months']:>5,}")
print(f"  Splits with interior month gaps   : {_dens['splits_with_gaps']:>15,}  (months where the group had no members)")
print(f"  Splits with < 24 months           : {_dens['splits_under_24_mo']:>15,}")
print(f"  Duplicate grain rows              : {_dup_grain:>15,}")
print(sep)


# 5. Hard assertions

TOL = 0.001  # 0.1%

def _assert_tie(label, src, out, tol=TOL):
    if src is None or out is None:
        print(f'WARN: {label} has a None side -- skipping assertion')
        return
    pct = abs(out - src) / max(abs(src), 1)
    assert pct < tol, (
        f'{label} MISMATCH  expected={src:,.2f}  output={out:,.2f}  '
        f'diff={abs(out - src):,.2f} ({pct * 100:.4f}%)'
    )

# PD / UTIL: output must be <= source (orphan claims excluded, never inflated)
assert out_pd <= src_pd + 0.01, (
    f'PD INFLATION  source={src_pd:,.2f}  output={out_pd:,.2f} — '
    'output exceeds source, which should be impossible'
)
assert out_util <= src_util + 0.01, (
    f'UTIL INFLATION  source={src_util:,.2f}  output={out_util:,.2f} — '
    'output exceeds source, which should be impossible'
)

# MM: catches spine fan-out (a duplicated MM row would inflate these)
_assert_tie('MM (deduped)',           exp_mm,        out_mm)
_assert_tie('MM (group-month count)', exp_mm_groups, out_mm_groups)

# Grain integrity: one row per split per month
assert _dup_grain == 0, f'{_dup_grain:,} duplicate rows at the split x month grain'

print('\nAll assertions passed -- MM is fan-out free, PD/UTIL not inflated,'
      ' and the split x month grain is unique.')

     
Write to table

_target = 'ra_analytic_dev.ohc_forecast.ohc_completed_combined'
_writer = df.write.format("delta").option("mergeSchema", "true")
if spark.catalog.tableExists(_target):
    _writer = _writer.option("replaceWhere", f"VAL_DATE = DATE('{VAL_DATE}')")
_writer.mode("overwrite").saveAsTable(_target)

# Emit VAL_DATE as a task value so downstream workflow tasks (signals_units) can consume it.
# Silently skipped when running the notebook interactively outside a Databricks job.
try:
    dbutils.jobs.taskValues.set(key="val_date", value=VAL_DATE)
    print(f"Task value set: val_date = {VAL_DATE}")
except AttributeError:
    pass  # not running in a Databricks Workflows job context

     

from pyspark.sql import functions as F
df = spark.table('ra_analytic_dev.ohc_forecast.ohc_completed_combined')


coverage = (
    df
    .groupBy('SEGMENT', 'HCC')
    .agg(
        F.min('DATE_REPORT_MONTH').alias('min_mo'),
        F.max('DATE_REPORT_MONTH').alias('max_mo'),
        F.countDistinct('DATE_REPORT_MONTH').alias('n_months')
    )
    .orderBy('SEGMENT', 'min_mo')
)
display(coverage)

     

# Split-level density -- how complete is each longitudinal series after densification?
# A healthy split has a month row for every month its enrollment group had members,
# most of which will legitimately carry zero utilization.
SPLIT_KEYS = [
    'SEGMENT', 'MARKET',
    'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_2_TADM', 'PRODUCT_LEVEL_3_TADM',
    'HCC', 'SERVICE_TYPE', 'SERVICE_CATEGORY',
]

density = (
    df
    .groupBy(*SPLIT_KEYS)
    .agg(
        F.countDistinct('DATE_REPORT_MONTH').alias('n_months'),
        F.sum(F.when((F.col('UTIL') == 0) & (F.col('PD') == 0), 1).otherwise(0)).alias('n_zero_months'),
        F.min('DATE_REPORT_MONTH').alias('min_mo'),
        F.max('DATE_REPORT_MONTH').alias('max_mo'),
    )
    .withColumn('pct_zero_months', F.round(F.col('n_zero_months') / F.col('n_months') * 100, 1))
)

summary = (
    density
    .groupBy('SEGMENT', 'HCC')
    .agg(
        F.count(F.lit(1)).alias('splits'),
        F.min('n_months').alias('min_months'),
        F.expr('percentile_approx(n_months, 0.5)').alias('median_months'),
        F.max('n_months').alias('max_months'),
        F.sum(F.when(F.col('n_months') < 24, 1).otherwise(0)).alias('splits_under_24_mo'),
        F.round(F.avg('pct_zero_months'), 1).alias('avg_pct_zero_months'),
    )
    .orderBy('SEGMENT', 'HCC')
)
display(summary)
