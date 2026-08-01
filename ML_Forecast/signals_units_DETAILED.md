# signals_units.py — Detailed Walkthrough

A function-by-function reading of the feature engineering module.

---

## 1. Imports and module constants

```python
from .numpy_time_series_utils import (
    build_group_position_arrays, rolling_mean_shift1, rolling_slope_shift1,
    rolling_var_shift1, rolling_zero_count_shift1, shift_array,
)
from .databricks_io import assert_val_date_rows
from .databricks_utils import finalize_val_date_table, to_date_columns

ROLLING_FEATURE_WINDOW = 12
ROLLING_FEATURE_MIN_PERIODS = 3
ZERO_FLOOR_EPSILON = 1e-9
```

Relative imports (`.numpy_time_series_utils`) confirm this lives inside a package —
`src/pipeline/`, matching `run_stage.py`'s `from src.pipeline import signals_units`.

The three shared modules represent a clean separation:

| Module | Responsibility |
|---|---|
| `numpy_time_series_utils` | Vectorized rolling/shift kernels |
| `databricks_io` | Input validation |
| `databricks_utils` | Output formatting and Delta writes |

Window parameters are module constants rather than buried in config, which makes
them greppable and consistent across both metrics. `min_periods=3` matches
`LIGHTGM_TRAIN`'s behavior — a rolling feature appears once three observations
exist rather than waiting for a full twelve.

---

## 2. `_floor_near_zero`

```python
def _floor_near_zero(values, epsilon):
    floored = values.copy()
    finite_mask = np.isfinite(floored)
    near_zero_mask = finite_mask & (np.abs(floored) < epsilon)
    floored[near_zero_mask] = 0.0
    return floored
```

Snaps values below `1e-9` to exactly zero. Applied to the BF estimate array before
`rolling_zero_count_shift1` runs.

The problem it solves: `COUNT_ZEROS` counts months with no activity, but BF
estimates are the product of several floating-point operations, so a genuinely
empty month can land at `3.7e-16` rather than `0.0`. Without flooring, that month
is counted as non-zero and the sparsity feature quietly understates.

The `np.isfinite` guard matters — it leaves `NaN` and `inf` untouched rather than
letting the comparison silently misbehave. `.copy()` avoids mutating the caller's
array.

---

## 3. `_build_config`

```python
val_date_ts = pd.to_datetime(run_val_date)
val_date_str = val_date_ts.strftime("%Y-%m-%d")
return {
    'val_date_str': val_date_str,
    'val_date': val_date_ts,
    ...
}
```

Normalizes the incoming date once and keeps both representations — the string for
SQL predicates and output stamping, the timestamp for any arithmetic. This is a
small thing that prevents a recurring class of bug where a date is re-parsed
inconsistently at three different call sites.

### Grain definitions

```python
'cf_product_level': ['MARKET', 'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_2_TADM',
                     'PRODUCT_LEVEL_3_TADM', 'IS_DUAL'],
'cf_claim_level': ['HCC', 'SERVICE_TYPE', 'SERVICE_CATEGORY'],
'cf_dates': ['DATE_REPORT_QTR', 'DATE_REPORT_MONTH', 'DURATION'],
```

Three grain components, composed at each use site. Note `IS_DUAL` sits in the
product-level list — it is treated as a population dimension, which is why the
population and risk merges have to explicitly strip it out later.

`SERVICE_TYPE` is present here but absent from `LIGHTGM_TRAIN`'s group keys. This
table is finer-grained than the model consumes; the collapse happens downstream.

### The `runout` key

```python
'runout': 3,
```

Set and never read anywhere in the module. Likely a leftover from a completion-lag
concept that moved to the `completion` stage. Dead.

### Feature list

Forty-three entries, listed explicitly rather than generated. Note that both the
`_PRE` columns and their rolling counterparts are included:

```python
'MARKET_ENCODED_UTIL_PRE', 'MARKET_ENCODED_UTIL', ...
```

Shipping both is a deliberate choice — `LIGHTGM_TRAIN` only uses the non-`_PRE`
versions in its feature list, but it needs the `_PRE` columns present because its
recursive projection loop recomputes rolling encodings from them month by month.
Dropping the `_PRE` columns here would break that loop.

---

## 4. `_load_source`

```python
assert_val_date_rows(spark, config['source'], config['val_date_str'], stage_name='SIGNALS_UNITS')
source = spark.table(config['source']).filter(f"VAL_DATE = TO_DATE('{config['val_date_str']}')").toPandas()
source['BF_ESTIMATE_UTIL'] = source['BF_ESTIMATE_UTIL_K'] * (source['MM'] / 12000)
source['BF_ESTIMATE_PD'] = source['BF_ESTIMATE_PMPM'] * source['MM']
source['DURATION'] = source['DURATION'].astype(int)
return source
```

The validation call is the pattern the notebooks lack — it fails immediately and
by name if the requested valuation date has no rows, rather than proceeding to
write an empty table.

The two derived columns convert **rates back to counts**:

- `BF_ESTIMATE_UTIL_K` is per-1,000-per-year → multiply by `MM/12000` to get a
  raw service count
- `BF_ESTIMATE_PMPM` is per-member-per-month → multiply by `MM` to get dollars

This matters because the next step aggregates across `SERVICE_TYPE`, and **rates
are not additive while counts are.** Summing PMPM across service types would be
meaningless; summing dollars and re-dividing is correct. The conversion here and
the re-normalization in `_aggregate_and_normalize_claims` are two halves of one
operation.

`.toPandas()` — everything downstream is driver-side. Note there is no HCC filter,
so this pulls the entire book for the valuation date.

---

## 5. `_aggregate_and_normalize_claims`

```python
group = config['cf_product_level'] + config['cf_claim_level'] + config['cf_dates']
sumcols = [col for col in source.columns if col not in group and pd.api.types.is_numeric_dtype(source[col])]
df = source.groupby(group)[sumcols].sum().reset_index()

df['UTIL_K'] = df['UTIL'] * (12000 / df['MM'])
df['PMPM'] = df['PD'] / df['MM']
df['BF_ESTIMATE_UTIL_K'] = df['BF_ESTIMATE_UTIL'] * (12000 / df['MM'])
df['BF_ESTIMATE_PMPM'] = df['BF_ESTIMATE_PD'] / df['MM']
```

Aggregate on counts, then re-derive rates. The inverse of `_load_source`'s
conversion.

`sumcols` is computed dynamically — every numeric column not in the group key gets
summed. Convenient, and it means a new numeric column added upstream flows through
without a code change. The flip side: a numeric column that *shouldn't* be summed
(a ratio, a flag, an ID) would be silently summed. Worth knowing when adding
columns upstream.

**No division guard.** Four divisions by `MM`, none checked for zero. If a
group-month has `MM = 0` — plausible for a product in its first or last month —
the result is `inf`, which propagates into every lag, rolling mean, and variance
computed downstream and eventually into the model. `final_output` guards every
denominator with its `nz()` helper; this module does not.

```python
df['TARGET_UTIL'] = df['BF_ESTIMATE_UTIL_K'].copy()
df['TARGET_PMPM'] = df['BF_ESTIMATE_PMPM'].copy()
```

**The targets are the BF estimates, not the raw actuals.** The model is trained to
predict completed/valued estimates rather than as-reported claims — which is
correct, since recent months are incomplete and raw values would teach the model
that claims decline near the reporting boundary.

---

## 6. `_fetch_seasonality_factors`

```python
factors['METRIC'] = factors['METRIC'].astype(str).str.upper()
factors = factors[factors['METRIC'].isin(['UTIL', 'PMPM'])].reset_index(drop=True)
factors['MONTH'] = factors['MONTH'].astype(int)
factors['FINAL_NORM_FACTOR'] = pd.to_numeric(factors['FINAL_NORM_FACTOR'], errors='coerce')
```

Defensive normalization on every field before use — case-folding the metric,
forcing `MONTH` to int, coercing the factor to numeric. This module clearly does
not trust its upstream, and given that upstream is an exploratory notebook
(`SEASONALITY_ADJUSTMENT.py`), that is well judged.

`errors='coerce'` turns unparseable factors into `NaN` rather than raising. Silent,
but the left join downstream would produce `NaN` anyway.

```python
dup_keys = ['MARKET', 'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_3_TADM',
            'HCC', 'SERVICE_CATEGORY', 'METRIC', 'MONTH']
if factors.duplicated(subset=dup_keys, keep=False).any():
    raise ValueError(f"SIGNALS_UNITS: duplicate seasonality factor keys in {...}")
```

Explicit fan-out guard, raising by name with the offending table. This is the same
class of check as `LIGHTGM_TRAIN`'s row-count assertion, done better — an explicit
`raise` rather than an `assert` (which `python -O` strips), and a message that
names the table.

It is also the constraint that forces the awkward dedup logic at the end of
`SEASONALITY_ADJUSTMENT.py`. The two files are coupled through this check.

```python
util_factors = factors[factors['METRIC'] == 'UTIL'][...].rename(...)
pmpm_factors = factors[factors['METRIC'] == 'PMPM'][...].rename(...)
return util_factors.merge(pmpm_factors, on=join_keys, how='outer')
```

Long-to-wide pivot via self-merge. The `outer` join is the right choice — a key
present for only one metric survives with a null for the other, rather than being
dropped entirely.

Note `join_keys` omits `PRODUCT_LEVEL_2_TADM` and `SERVICE_TYPE`, so seasonality is
applied at a coarser grain than the data. One factor covers multiple rows by
design.

---

## 7. `_fetch_calendar`

```python
mindate = df['DATE_REPORT_MONTH'].min().strftime('%Y-%m-%d')
maxdate = df['DATE_REPORT_MONTH'].max().strftime('%Y-%m-%d')
cal_sql = f"""
    SELECT FIRST_DAY_MONTH as DATE_REPORT_MONTH, LINEAR_MONTH, MONTH_NBR as MONTH,
           sum(WORKDAY) as WORKDAY
    FROM {config['calendar_table']}
    WHERE FIRST_DAY_MONTH between '{mindate}' and '{maxdate}'
    GROUP BY ALL
"""
```

Bounds the calendar pull to the data's actual date range rather than loading the
whole table. The `GROUP BY ALL` aggregates workdays to month grain.

The date bounds are derived from data, not user input, so the string interpolation
is low-risk here.

`MONTH_NBR` is aliased to `MONTH`, and this is where the `MONTH` column enters the
frame — which the seasonality merge depends on. That ordering dependency is real
but implicit; see `_merge_auxiliary_features`.

---

## 8. `_fetch_population`

```sql
sum(CASE WHEN AGE_GROUP = 'Pediatric' then MED_MM else 0 end) as PEDIATRIC_COUNT,
...
sum(FEMALE_IND * MED_MM) as FEMALE_COUNT,
sum(DUAL_ALIGNED * MED_MM) as DUAL_ALIGNED_COUNT,
sum(MED_MM) as MM
```

Every demographic is weighted by member months rather than counted as a headcount.
That is the correct construction — a member enrolled two months should contribute
twice what a member enrolled one month does. The subsequent division by total `MM`
yields a genuine member-month-weighted share.

```python
group = [c for c in config['cf_product_level'] if c != 'IS_DUAL'] + ['DATE_REPORT_QTR', 'DATE_REPORT_MONTH']
sumcols = [col for col in pop_df.columns if col not in group]
pop_df = pop_df.groupby(group)[sumcols].sum().reset_index()
```

The SQL already grouped by exactly these columns, so this pandas regroup is a
**no-op** — it re-aggregates data that is already at the target grain. Harmless but
wasted; the `IS_DUAL` exclusion it appears to implement is already true of the SQL
output, which never selected `IS_DUAL` in the first place.

```python
for col in sumcols:
    if col != 'MM':
        col_name = col.replace('COUNT', 'PERCENTAGE')
        pop_df[col_name] = pop_df[col] / pop_df['MM']
        pop_df.drop(col, axis=1, inplace=True)
pop_df.drop('MM', axis=1, inplace=True)
```

Counts become shares by string-replacing `COUNT` with `PERCENTAGE` in the column
name. Concise, and it keeps the SQL and Python naming in lockstep — but it is
positional-by-convention: a column named `ACCOUNT_TOTAL` would become
`APERCENTAGE_TOTAL`. Fine given the current naming, fragile against additions.

`MM` is dropped at the end so the population merge doesn't collide with the claims
frame's own `MM` column. Necessary, and easy to overlook when modifying.

---

## 9. `_fetch_risk`

```python
risk_df = spark.table(config['risk_table']).toPandas()
group = [c for c in config['cf_product_level'] if c != 'IS_DUAL'] + ['DATE_REPORT_MONTH']
sumcols = [col for col in risk_df.columns if col not in group]
risk_df = risk_df.groupby(group)[sumcols].sum().reset_index()
risk_df['PROSP_RISK'] = risk_df['PROSP_RISK_AGG'] / risk_df['MM']
risk_df.drop(['PROSP_RISK_AGG', 'MM'], axis=1, inplace=True)
```

Same member-month weighting pattern — an aggregate risk score divided by member
months to get an average.

Two differences from `_fetch_population` worth noting:

1. **No date filter.** The full risk table is pulled into pandas, unlike the
   calendar (bounded) and the source (val_date filtered). If the risk table has
   deep history, this is unnecessary memory.
2. **No zero guard** on the `MM` division, same as elsewhere.

The `IS_DUAL` exclusion here is real, not a no-op — the risk table's own grain is
unknown, so this genuinely collapses it.

---

## 10. `_resolve_product_and_category`

```python
if 'PRODUCT_LEVEL_3_TADM' in config['cf_product_level']:
    product = 'PRODUCT_LEVEL_3_TADM'
elif 'PRODUCT_LEVEL_2_TADM' in config['cf_product_level']:
    product = 'PRODUCT_LEVEL_2_TADM'
else:
    product = 'PRODUCT_LEVEL_1_TADM'
category = 'SERVICE_CATEGORY' if 'SERVICE_CATEGORY' in config['cf_claim_level'] else 'HCC'
```

Picks the finest available product and category level for target encoding. Sensible
in principle — but `cf_product_level` and `cf_claim_level` are hardcoded literals
in `_build_config`, so the first branch always wins and the fallbacks are
unreachable.

This is defensive code for a configurability that doesn't exist. Either make the
grain lists configurable (in which case this earns its place) or inline the
constants.

---

## 11. `_add_rolling_quarter_fields`

```python
df['UTIL_ROLLING_QTR'] = df.groupby(group)['BF_ESTIMATE_UTIL'].transform(lambda x: x.rolling(window=3).sum())
df['MEM_ROLLING_QTR'] = df.groupby(group)['MM'].transform(lambda x: x.rolling(window=3).sum())
df['PD_ROLLING_QTR'] = df.groupby(group)['BF_ESTIMATE_PD'].transform(lambda x: x.rolling(window=3).sum())
df['UTILK_ROLLING_QTR'] = df['UTIL_ROLLING_QTR'] / df['MEM_ROLLING_QTR'] * 12000
df['PMPM_ROLLING_QTR'] = df['PD_ROLLING_QTR'] / df['MEM_ROLLING_QTR']
df['UTILK_ROLLING_QTR_SHIFTED'] = df.groupby(group)['UTILK_ROLLING_QTR'].shift(1)
df['PMPM_ROLLING_QTR_SHIFTED'] = df.groupby(group)['PMPM_ROLLING_QTR'].shift(1)
```

Seven columns, three of them groupby-rolling operations over the full frame.

**None of them are used.** They appear in neither `config['features']` nor the
column selection in `_build_final_output`, so every one is dropped before the
write. This is dead computation on the critical path — and it is the *slowest*
kind, since these are the pandas `.apply()`-style rolling operations the rest of
the module deliberately avoids.

Either wire these into the feature list (rolling-quarter smoothing is a reasonable
feature for noisy monthly data, and `_SHIFTED` versions are already leakage-safe)
or delete the function and its call site. Currently it is pure cost.

---

## 12. `_add_metric_features` — the core

The most substantial function, and the one that justifies the module's existence.

### Step 1 — `_PRE` encodings

```python
out[f'MARKET_ENCODED_{metric}_PRE'] = (
    out.groupby(['MARKET', 'PRODUCT_LEVEL_1_TADM', 'HCC', 'DATE_REPORT_MONTH'])[f'TARGET_{metric}'].transform('mean')
)
out[f'PRODUCT_ENCODED_{metric}_PRE'] = (
    out.groupby([product, 'PRODUCT_LEVEL_1_TADM', 'HCC', 'DATE_REPORT_MONTH'])[f'TARGET_{metric}'].transform('mean')
)
out[f'CATEGORY_ENCODED_{metric}_PRE'] = (
    out.groupby([category, 'PRODUCT_LEVEL_1_TADM', 'HCC', 'DATE_REPORT_MONTH'])[f'TARGET_{metric}'].transform('mean')
)
```

Cross-sectional means — for each month, the average target across all rows sharing
that market (or product, or category). These are *not* yet safe to use as features:
each row's own target is included in its own group mean. The `_shift1` rolling step
below is what makes them safe.

### Step 2 — position arrays

```python
row_count = len(out)
group_positions = build_group_position_arrays(out, group)
```

The key optimization. Rather than repeatedly calling `groupby().transform()` — which
re-derives group membership every time — this computes each group's integer row
positions **once**, then reuses them across all ten features.

The frame must be sorted by group and date for this to be correct. It is, by
`_aggregate_and_normalize_claims`, but the dependency is implicit and unasserted.

### Step 3 — numpy extraction

```python
target_values = out[f'TARGET_{metric}'].to_numpy(dtype=np.float64)
bf_values = out[f'BF_ESTIMATE_{metric_source_suffix}'].to_numpy(dtype=np.float64)
bf_values = _floor_near_zero(bf_values, ZERO_FLOOR_EPSILON)
```

Explicit `dtype=np.float64` avoids the integer-inference problem that
`LIGHTGM_TRAIN` had to patch with a manual cast — solved structurally here rather
than defensively.

**Note the two source arrays.** Lags and variance are computed from
`target_values`; zero-counts and slope are computed from `bf_values`:

```python
count_zeros[pos] = rolling_zero_count_shift1(group_bf, ...)
variance_12_mo[pos] = rolling_var_shift1(group_target, ...)
slope_12[pos] = rolling_slope_shift1(group_bf, ...)
```

Currently these are the same numbers — `TARGET_UTIL` is a copy of
`BF_ESTIMATE_UTIL_K` and `TARGET_PMPM` a copy of `BF_ESTIMATE_PMPM`. So the split
is invisible today. But if the target definition ever diverges from the BF estimate
(applying a trend adjustment, say), three features would silently keep tracking the
old quantity while the rest follow the new one. Either unify the source or add a
comment explaining why they differ.

### Step 4 — the per-group loop

```python
for pos in group_positions:
    group_target = target_values[pos]
    group_bf = bf_values[pos]

    target_1_group = shift_array(group_target, 1)
    ...
    market_encoded[pos] = rolling_mean_shift1(market_pre_values[pos], window=12, min_periods=3)
```

Numpy fancy indexing both ways — `values[pos]` to read the group's slice,
`output[pos] = ...` to scatter results back. Preallocated `np.full(..., np.nan)`
arrays mean any position not written stays `NaN`, which is the correct default for
an unfillable feature.

Every kernel carries `_shift1` in its name, making the leakage guarantee visible at
the call site. This is a genuine improvement over `LIGHTGM_TRAIN`, where the same
guarantee lives inside `.transform(lambda x: x.shift(1).rolling(...))` and has to be
verified by reading.

### One asymmetry with `LIGHTGM_TRAIN`

`LIGHTGM_TRAIN`'s `new_features` fills a missing 12-month lag with the group mean:

```python
.shift(12).fillna(df.groupby(group)[f'TARGET_{metric}'].transform('mean'))
```

`shift_array(group_target, 12)` here has no such fallback — it leaves `NaN`.

So `TARGET_*_12` is null in training data but mean-filled during projection. The
model learns one distribution and is scored against another. LightGBM handles NaN
natively, so this doesn't error, but the two paths should agree. Worth reconciling.

---

## 13. `_merge_auxiliary_features`

```python
df = df.merge(calendar, on='DATE_REPORT_MONTH', how='left').reset_index(drop=True)

_product_level_no_dual = [c for c in config['cf_product_level'] if c != 'IS_DUAL']
pop_group = _product_level_no_dual + ['DATE_REPORT_QTR', 'DATE_REPORT_MONTH']
df = df.merge(pop_df, on=pop_group, how='left').reset_index(drop=True)

risk_group = _product_level_no_dual + ['DATE_REPORT_MONTH']
df = df.merge(risk_df, on=risk_group, how='left').reset_index(drop=True)

seasonality_keys = ['MARKET', 'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_3_TADM',
                    'HCC', 'SERVICE_CATEGORY', 'MONTH']
df = df.merge(seasonality_df, on=seasonality_keys, how='left').reset_index(drop=True)
```

Four sequential left joins. Two things to flag.

**Ordering is load-bearing and implicit.** The seasonality merge requires a `MONTH`
column, which only exists because the calendar merge created it two lines earlier.
Reorder these and the last merge raises a `KeyError`. A one-line comment would cost
nothing.

**No row-count validation.** All four are left joins on keys coarser than the
frame's grain, and any duplicate on the right side multiplies rows. The seasonality
table is explicitly checked in `_fetch_seasonality_factors`; the calendar,
population, and risk tables are not. Given `LIGHTGM_TRAIN` was careful enough to
assert on exactly this failure mode, the omission stands out:

```python
pre = len(df)
df = df.merge(pop_df, on=pop_group, how='left')
if len(df) != pre:
    raise ValueError(f"Population merge fanned out: {pre} → {len(df)} rows")
```

**The `IS_DUAL` exclusion**, documented in the comments, means dual and non-dual
rows in the same product-month receive identical demographics and risk. Since
`LIGHTGM_TRAIN` trains separate models per `IS_DUAL` value, these features are
constant within each model's training set along that dimension — so they carry no
dual-specific signal, by construction. Not wrong, but a real ceiling on what those
features can contribute.

---

## 14. `_build_final_output`

```python
df['VAL_DATE'] = config['val_date_str']
signals_level_cols = config['cf_product_level'] + config['cf_claim_level'] + config['cf_dates'] + ['VAL_DATE']
signals_calc_cols = ['TARGET_UTIL', 'TARGET_PMPM'] + config['features']
signals_table_final = df[signals_level_cols + signals_calc_cols].reset_index(drop=True)
return to_date_columns(signals_table_final, ['DATE_REPORT_MONTH', 'VAL_DATE'])
```

Explicit column selection — grain columns, then targets, then features. Everything
else (including all seven rolling-quarter columns) is discarded here.

Selecting by explicit list rather than dropping unwanted columns is the right
default: a stray column added upstream can't leak into the output.

`to_date_columns` centralizes date typing for the Delta write, avoiding the ad-hoc
`strftime` loops that appear in both notebooks.

---

## 15. `run`

```python
def run(spark, run_val_date, source_table, seasonality_factors_table, calendar_table,
        population_table, risk_table, target_table, write_catalog, write_schema):
    config = _build_config(...)
    source = _load_source(spark, config)
    df = _aggregate_and_normalize_claims(source, config)
    calendar = _fetch_calendar(spark, df, config)
    pop_df = _fetch_population(spark, config)
    risk_df = _fetch_risk(spark, config)
    seasonality_df = _fetch_seasonality_factors(spark, config)

    group = config['cf_product_level'] + config['cf_claim_level']
    df = _add_rolling_quarter_fields(df, group)

    product, category = _resolve_product_and_category(config)
    for metric in ['UTIL', 'PMPM']:
        df = _add_metric_features(df, group, metric, product, category)

    df = _merge_auxiliary_features(df, calendar, pop_df, risk_df, seasonality_df, config)
    signals_table_final = _build_final_output(df, config)

    finalize_val_date_table(spark, signals_table_final, config['output_table'],
                            config['catalog'], config['schema'], config['val_date_str'],
                            ['DATE_REPORT_MONTH', 'VAL_DATE'])

    return {'status': 'SUCCESS', 'target_table': f"{...}", 'rows_written': int(len(signals_table_final))}
```

The public function reads as a table of contents — load, aggregate, fetch, engineer,
merge, select, write. Each step is one named call. This is the clearest code in the
directory.

Two observations:

**The signature matches `run_stage.py` exactly**, including the return contract
(`status` / `target_table` / `rows_written`). Combined with the argument order in
`run_signals_units`, the coupling is clean.

**`status` is hardcoded to `'SUCCESS'`.** Failure is signaled by exception rather
than by return value — reasonable, but note it means the `status != 'SUCCESS'` check
recommended for `run_stage.py` will never fire for this stage. That's fine as long
as every stage follows the same convention; if some return `'FAILED'` and others
raise, the caller has to handle both.

The write is delegated to `finalize_val_date_table`, which presumably implements the
same delete-then-append pattern the notebooks inline three times. This is where that
logic belongs.

`_add_rolling_quarter_fields` is called before the metric loop and its output is
never read — confirming the dead-code finding from a second angle.

---

## Comparison with `LIGHTGM_TRAIN`

The two files implement overlapping feature logic. Where they differ:

| Aspect | `signals_units.py` | `LIGHTGM_TRAIN` |
|---|---|---|
| Structure | Named functions, single public entry | One long linear script |
| Rolling computation | Vectorized numpy kernels | `groupby().transform(lambda ...)` |
| Leakage guard | Named in the kernel (`_shift1`) | Inline `.shift(1).rolling(...)` |
| Float dtype | `dtype=np.float64` at extraction | Manual `.astype('float64')` patch |
| Input validation | `assert_val_date_rows` | None |
| Fan-out guard | On seasonality only | On the segment join only |
| Config | Injected from YAML | Hardcoded literals |
| Write | Delegated to shared utility | Inlined twice |
| Scope | Whole book, one val_date | One HCC |
| 12-month lag fallback | `NaN` | Mean-filled |

`signals_units.py` is the better code by a wide margin. The main open question is
architectural: `LIGHTGM_TRAIN` recomputes several of these same features inside its
projection loop, so the two implementations must stay behaviorally identical or
forecasts will diverge from training. The lag-fallback difference above is one place
they already have.

---

## Summary of observations

| Area | Note |
|---|---|
| Dead computation | `_add_rolling_quarter_fields` — 7 columns, 3 rolling ops, zero consumers |
| Division guards | Six divisions by `MM` across three functions, none zero-checked |
| Merge validation | No row-count assertion on the calendar, population, or risk joins |
| Merge ordering | Seasonality depends on `MONTH` from the calendar merge; undocumented |
| Lag inconsistency | `TARGET_*_12` is `NaN` here, mean-filled in `LIGHTGM_TRAIN`'s projection |
| Feature source split | Zero-count and slope read `BF_ESTIMATE`, others read `TARGET` — identical today, fragile tomorrow |
| Risk table scope | Pulled unfiltered into pandas |
| Redundant regroup | `_fetch_population`'s pandas groupby duplicates the SQL's `GROUP BY ALL` |
| Unreachable branches | `_resolve_product_and_category` fallbacks can't trigger against hardcoded config |
| Dead config | `'runout': 3` never read |
| Memory | Whole-book `.toPandas()` — larger footprint than the per-HCC notebooks |
| Naming convention | `COUNT` → `PERCENTAGE` string replacement is positionally fragile |
| Constant features | `SEASONAL_FACTOR_*` are currently 1.0 throughout — see `SEASONALITY_ADJUSTMENT` |
