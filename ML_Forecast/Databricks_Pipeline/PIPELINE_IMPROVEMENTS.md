# Pipeline Improvement Recommendations

Recommendations for the five-step OHC forecast pipeline, organized by theme. Each
carries a stable ID (`C-1`, `E-3`, …) that `PIPELINE_ROADMAP.md` references for
sequencing.

**Themes**

- **[C] Correctness** — wrong or silently-wrong output
- **[R] Reliability** — reproducibility, observability, operational safety
- **[M] Modeling** — accuracy, model choice, validation
- **[E] Efficiency** — runtime, memory, cost
- **[S] Structure** — simplification, deduplication, architecture

---

# [C] Correctness

## C-1 — Step 2 fails on any clean run

**Step 2, lines 1–19.**

```python
f_raw = spark.table('ra_analytic_dev.ohc_forecast.dev_tfm_hcta_oh_data')   # ← typo
...
try:
    VAL_DATE = dbutils.jobs.taskValues.get(taskKey="extract_hcta", key="val_date")
except (AttributeError, TypeError):
    _max_yrmo = (df_raw...)          # ← df_raw, never assigned
...
df_raw = df_raw.filter(f"VAL_DATE = TO_DATE('{VAL_DATE}')")   # ← NameError
```

Line 1 assigns `f_raw`. Every subsequent reference is `df_raw`. In a job context
the `try` succeeds, so control reaches line 19 and raises `NameError: name 'df_raw'
is not defined`.

This currently "works" only because the notebook kernel retains `df_raw` from an
earlier interactive session. **Any fresh cluster, any scheduled run, any restarted
kernel fails.**

```python
df_raw = spark.table('ra_analytic_dev.ohc_forecast.dev_tfm_hcta_oh_data')
```

One character. Highest-value fix in the repository.

## C-2 — Step 2 is not valid Python

**Step 2, line 456.**

```python
Write to table
```

A markdown cell that survived notebook export. Two juxtaposed names are a syntax
error, so the file cannot be imported, linted, unit-tested, or invoked from
`run_stage.py`.

```python
# Write to table
```

Verified: Steps 1, 3, 4, and 5 all parse cleanly. Step 2 is the only offender.

## C-3 — `val_date` propagation stops after Step 2

**Steps 4 and 5.**

Steps 1 and 2 chain correctly via task values. Steps 4 and 5 read widgets whose
defaults are hardcoded:

```python
dbutils.widgets.text("val_date", "2026-03-01")
```

Neither consumes `taskValues`. If an operator forgets to update them, Step 4 trains
on a stale vintage and Step 5's triple filter matches zero rows — writing an empty
table and reporting success.

```python
# Steps 4 and 5 — prefer the upstream task value, fall back to the widget
try:
    val_date = dbutils.jobs.taskValues.get(taskKey="ohc_completed_combined", key="val_date")
    print(f"val_date from task value: {val_date}")
except (AttributeError, TypeError):
    val_date = dbutils.widgets.get("val_date")
    print(f"val_date from widget: {val_date}")
```

This is the same two-tier pattern Step 2 already uses — apply it consistently.
`train_end` and `hcc` remain genuine per-run choices and stay as widgets.

## C-4 — Step 5 writes empty results successfully

**Step 5, before the write.**

```python
row_count = df_final.count()
if row_count == 0:
    raise ValueError(
        f"No rows matched val_date={val_date}, train_end={train_end}, hcc={hcc} in "
        f"LIGHTGBM_PMPM_UTIL_OUTPUT_ENCODED. Check that these match the training run."
    )
print(f"Writing {row_count:,} rows")
```

Converts the most likely operator error from a silent no-op into an immediate,
readable failure. Pairs with C-3 — that fix reduces the frequency, this one makes
the residual case loud.

## C-5 — Turn Step 5's validation query into an assertion

**Step 5, final cell.**

The four metrics computed are exactly the right ones; they just decorate the log
rather than gating the job. Nobody reads a `display()` on a scheduled run.

```python
checks = spark.sql(f"""...""").collect()[0]

problems = []
if checks['total_rows'] == 0:
    problems.append("no rows written")
if checks['rows_missing_forecast'] > 0:
    problems.append(f"{checks['rows_missing_forecast']:,} rows missing a forecast value")
if checks['rows_forecast_only'] == 0:
    problems.append("no projection rows — expected ~21 months per group")

if problems:
    raise ValueError(f"Validation failed for {val_date}/{train_end}/{hcc}: " + "; ".join(problems))

display(spark.createDataFrame([checks]))
```

## C-6 — Historical rows are labeled as predictions

**Step 4, forecast output construction.**

The output is built from `appended_source_all`, which concatenates history with
projections *before* the rename:

```python
df = df.rename(columns={f"TARGET_{metric}": f"TARGET_{metric}_PREDICTED"})
```

For pre-`projection_start` months, `TARGET_{metric}` holds the **observed** value.
So in Step 5, `OH_FCST_ALLOWED_PMPM` equals `OH_ACTUALS_ALLOWED_PMPM` for every
historical month by construction. Anyone assessing accuracy from `ohc_final_output`
sees perfect fit that isn't real.

This may be deliberate — a continuous unbroken line for dashboards. If so, make it
explicit:

```python
forecast_df['IS_PROJECTION'] = forecast_df['DATE_REPORT_MONTH'] >= config['projection_start']
forecast_df['HORIZON_MONTH'] = np.where(
    forecast_df['IS_PROJECTION'],
    ((forecast_df['DATE_REPORT_MONTH'].dt.year * 12 + forecast_df['DATE_REPORT_MONTH'].dt.month) -
     (config['projection_start'].year * 12 + config['projection_start'].month) + 1),
    0,
)
```

`HORIZON_MONTH` solves a second problem too — consumers currently cannot distinguish
a month-1 forecast from a month-21 forecast, which have very different reliability.

**Verify first:** query the output table for a month before `projection_start` and
check whether `TARGET_PMPM_PREDICTED` exactly equals the source value.

## C-7 — `F.first('MM')` is unguarded in Step 5

```python
.agg(F.first('MM').alias('MM'), F.sum('UTIL').alias('UTIL'), F.sum('PD').alias('PD'))
```

Correct only while `MM` is constant across `SERVICE_TYPE` within a group-month. It
should be — but if it ever isn't, `first` picks arbitrarily and every rate metric in
the reporting table is quietly wrong.

```python
.agg(F.min('MM').alias('MM_MIN'), F.max('MM').alias('MM_MAX'),
     F.sum('UTIL').alias('UTIL'), F.sum('PD').alias('PD'))
```

```python
inconsistent = actuals.filter(
    F.col('MM_MIN').isNotNull() & (F.col('MM_MIN') != F.col('MM_MAX'))
).count()
if inconsistent:
    raise ValueError(f"MM varies within {inconsistent:,} group-months — F.first() is unsafe")
actuals = actuals.withColumn('MM', F.col('MM_MAX')).drop('MM_MIN', 'MM_MAX')
```

## C-8 — No zero guards in Step 3

Six divisions by `MM` across `_aggregate_and_normalize_claims`, `_fetch_population`,
and `_fetch_risk`, none checked:

```python
df['UTIL_K'] = df['UTIL'] * (12000 / df['MM'])
df['PMPM'] = df['PD'] / df['MM']
```

Step 2's `INNER JOIN` on `MM > 0` makes this safe *today*, but the guarantee lives
in a different file and nothing in Step 3 asserts it. An `inf` here propagates
through every lag, rolling mean, and variance downstream.

```python
if (df['MM'] <= 0).any():
    raise ValueError(f"{(df['MM'] <= 0).sum():,} rows with MM <= 0 — upstream spine guarantee violated")
```

One assertion is better than six guards — it validates the invariant rather than
papering over its absence.

## C-9 — Step 3 has no post-merge row-count checks

Four sequential left joins on keys coarser than the frame's grain. Only the
seasonality table is duplicate-checked; calendar, population, and risk are not.

```python
def _merge_checked(df, right, on, how='left', name=''):
    pre = len(df)
    out = df.merge(right, on=on, how=how)
    if len(out) != pre:
        raise ValueError(f"{name} merge fanned out: {pre:,} → {len(out):,} rows")
    return out.reset_index(drop=True)
```

Step 2 asserts on exactly this failure mode and Step 4 has a fan-out assertion.
Step 3 is the gap.

## C-10 — Lag fallback differs between Step 3 and Step 4

Step 4's projection loop mean-fills a missing 12-month lag:

```python
.shift(12).fillna(df.groupby(group)[f'TARGET_{metric}'].transform('mean'))
```

Step 3's `shift_array(group_target, 12)` leaves `NaN`.

So `TARGET_*_12` is null in training data and mean-filled at projection time. The
model learns one distribution and is scored against another. LightGBM tolerates
`NaN` natively so nothing errors — it just quietly degrades. Pick one convention and
apply it in both places.

---

# [R] Reliability

## R-1 — Runs are not reproducible

**Step 4.** `feature_fraction` and `bagging_fraction` are stochastic and no seed is
set. Two runs on identical inputs produce different forecasts.

```python
'seed': 42,
'bagging_seed': 42,
'feature_fraction_seed': 42,
'deterministic': True,
```

For a model feeding financial planning, this is difficult to defend. `deterministic:
True` also removes thread-scheduling nondeterminism at a modest speed cost.

## R-2 — Trained models are discarded

**Step 4.** `config['model_name']` builds filenames and `config['model_stage']`
points at a registry path. Neither is used; no `save_model()` call exists.

Every run trains up to eight models, uses them, and throws them away. Combined with
R-1, a forecast cannot be reproduced even by retraining.

```python
for metric in config['metrics']:
    for split_name, model in trained_models[metric].items():
        path = f"{config['model_stage']}/{config['HCC']}/{config['train_end']:%Y%m}/{metric}_{split_name}.txt"
        model.save_model(path)
```

Note `run_stage.py` is built around a `model_id` handoff between train and predict —
the notebook path has no equivalent, so the two architectures disagree on whether
models are artifacts.

## R-3 — Seasonality factors have no version history

`cs_cf_seasonality_factors` is written with a full overwrite and carries no
`VAL_DATE`. Every other table in the pipeline is scenario-keyed.

The consequence: **you cannot determine which factors a past forecast used.** A
March forecast in `ohc_final_output` joins to whatever is in the table today.

Add a `VAL_DATE` column, switch to `replaceWhere`, and have Steps 3 and 4 filter to
the matching vintage rather than reading whatever is current.

## R-4 — Adopt `replaceWhere` in Steps 4 and 5

Steps 1 and 2 already use the atomic idiom:

```python
writer.option("replaceWhere", f"VAL_DATE = DATE('{val_date}')").mode("overwrite")
```

Steps 4 and 5 use delete-then-append, which leaves the slice **briefly missing**
between the two operations. Acceptable for batch, not for anything a live dashboard
reads during the window.

Migrating gives atomic scenario replacement and removes ~40 lines of branching
logic per site.

## R-5 — Snowflake connection uses a personal account

**Step 1.**

```python
"sfUser": "ryan_shannon@optum.com",
```

The PAT is correctly stored in `dbutils.secrets`, but the identity is a named
individual. When that person's access changes, the pipeline breaks. Move to a
service principal and put the username in secrets alongside the token.

## R-6 — No "source hasn't advanced" detection

**Step 1.** If the Snowflake table hasn't been refreshed, `val_date` is unchanged
and the same slice is rewritten with identical data. The pipeline runs green and
produces a forecast identical to last month's.

```python
if spark.catalog.tableExists(full_name):
    prior = spark.table(full_name).agg(F.max('VAL_DATE')).collect()[0][0]
    if prior is not None and str(prior) >= val_date:
        raise ValueError(
            f"Source has not advanced: derived val_date={val_date}, "
            f"existing max VAL_DATE={prior}. Re-run when upstream refreshes."
        )
```

## R-7 — Config validation before Spark starts

Missing YAML keys currently surface as a `KeyError` inside a runner, after the
session is up and potentially minutes into execution. Validate the required key set
immediately after `load_pipeline_config()` and before
`SparkSession.builder.getOrCreate()`. Fails in seconds instead of minutes.

## R-8 — Stage failures should exit non-zero

`run_stage.py` checks `result['status']` only for `lightgbm_train`, and only to
decide whether to publish `model_id`. Any other stage returning `FAILED` prints and
exits 0 — Databricks marks the task green and downstream stages run on bad data.

```python
status = (result or {}).get('status')
if status != 'SUCCESS':
    raise RuntimeError(f"Stage '{stage}' returned status={status!r}. Full result: {result}")
```

Task dependencies are only meaningful if a failed stage actually fails.

---

# [M] Modeling

## M-1 — Resolve the seasonality state

Every `k` in `SEASONALITY_ADJUSTMENT.py` is `0`, so published factors are uniformly
`1.0` and the clustering code never runs. Downstream, `SEASONAL_FACTOR_*` and
`FINAL_NORM_FACTOR_*` are zero-variance columns that LightGBM cannot split on.

The comment above the `k` lists claims the values were *"selected via silhouette +
elbow analysis"* — which describes a state the code is not in.

Whichever way this resolves, make the state observable:

```python
n_nonflat = (final_df['FINAL_NORM_FACTOR'] != 1.0).sum()
print(f"Non-neutral factors: {n_nonflat:,} of {len(final_df):,}")
if n_nonflat == 0:
    print("WARNING: all seasonality factors are 1.0 — seasonality is effectively disabled.")
```

And in Step 3, fail fast rather than silently shipping a dead feature:

```python
if seasonality_df['SEASONAL_FACTOR_UTIL'].nunique() == 1:
    print("WARNING: SEASONAL_FACTOR_UTIL has no variance — the feature will not contribute.")
```

Healthcare utilization has real seasonality (respiratory season, deductible resets in
January, elective procedure timing before year-end). If it is genuinely off, the
models are missing a signal that domain knowledge says exists.

## M-2 — No validation metrics anywhere

`test_offset = 1` creates a one-month holdout consumed only by early stopping. No
RMSE, MAPE, or bias is computed, printed, or stored. There is no way to answer
"is this month's model better or worse than last month's."

```python
y_val_pred = model.predict(data_dict['X_test'], num_iteration=model.best_iteration)
rmse = mean_squared_error(data_dict['y_test'], y_val_pred, squared=False)
bias = (y_val_pred.mean() - data_dict['y_test'].values.mean()) / data_dict['y_test'].values.mean()
print(f"  {split_name} {metric}: RMSE={rmse:,.4f}  bias={bias:+.2%}  "
      f"best_iter={model.best_iteration}  n_train={len(data_dict['X_train']):,}")
```

Persist to a run-metrics table keyed on `(val_date, train_end, HCC, metric, split)`.
A one-month holdout is thin, but tracked over time it makes drift visible.

## M-3 — Add a rolling-origin backtest

The stronger version of M-2, and the only way to know whether the 21-month horizon
is trustworthy at all.

Train to month *T*, score *T+1 … T+6*, walk forward, repeat. Report error by horizon
month. This directly answers the question the current output cannot: how fast does
accuracy decay as the recursive projection compounds?

Expect a clear degradation curve. If month 18 error is unusable, that is worth
knowing before someone plans against it.

## M-4 — Align objective and evaluation metric

```python
'objective': 'tweedie',
'metric': 'rmse',
```

Training minimizes Tweedie deviance; early stopping watches RMSE. They can disagree
on the best iteration, and RMSE is far more sensitive to large-value errors — so
early stopping optimizes something the model isn't.

```python
'metric': 'tweedie',
'tweedie_variance_power': 1.3,   # currently defaulting to 1.5
```

`tweedie_variance_power` was never chosen — it was inherited. It controls where the
distribution sits between Poisson (1.0) and gamma (2.0). A sweep over 1.1–1.7 against
holdout RMSE is cheap and often moves the needle more than tree hyperparameters do.

## M-5 — Reconsider the recursive projection

The current design predicts one month ahead and feeds predictions back as history for
21 iterations. Error compounds, and month 21's features are built almost entirely from
predicted values.

Two alternatives worth evaluating against M-3's backtest:

- **Direct multi-horizon.** Train a separate model per horizon *h*, each predicting
  *T+h* from features known at *T*. No compounding. Costs 21× the models, but they
  train independently and in parallel, and each is honest about what it knows.
- **Hybrid.** Recursive for months 1–6 where lag features carry real signal, direct
  for 7–21 where they've degraded to noise.

Direct multi-horizon is standard practice for long forecast horizons precisely
because of the compounding problem. Worth a comparison before committing further to
the current approach.

## M-6 — Quantify uncertainty

The output is a point forecast with no interval. Month 1 and month 21 are presented
identically despite very different reliability.

LightGBM supports quantile regression directly:

```python
for alpha in (0.1, 0.5, 0.9):
    params_q = {**params, 'objective': 'quantile', 'alpha': alpha}
```

Three models per metric per split instead of one, producing an 80% interval. Combined
with `HORIZON_MONTH` from C-6, consumers can finally see the fan widen.

## M-7 — Address `UTIL` unit mixing

```python
F.when(F.col('IP_ADMITS_UNITS_TREND') > 0, F.col('IP_ADMITS_UNITS_TREND'))
 .when(F.col('IP_DAYS_UNITS_TREND')   > 0, F.col('IP_DAYS_UNITS_TREND'))
 ...
```

Six unit types collapse into one column. Within inpatient specifically, a split with
`IP_ADMITS = 0` and `IP_DAYS = 5` silently switches from admissions to bed days — so
the same time series can change units month to month, and `UTIL_K` is not comparable
across those months.

At minimum, record which column was selected:

```python
.withColumn('UTIL_SOURCE',
    F.when(F.col('IP_ADMITS_UNITS_TREND') > 0, F.lit('IP_ADMITS'))
     .when(F.col('IP_DAYS_UNITS_TREND')   > 0, F.lit('IP_DAYS'))
     ...
)
```

Then check whether any split has more than one distinct `UTIL_SOURCE` over its
history. If the count is material, the unit choice should be fixed per HCC rather
than resolved per row.

## M-8 — Reconsider the four-way split

Four splits × two metrics = up to eight models per HCC, each trained on a quarter of
the data. Thin splits get skipped entirely.

LightGBM handles categorical features natively — `SEGMENT` and `IS_DUAL` could be
model features rather than partition keys, letting one model per metric borrow
strength across the full population while still learning the distinction.

This is an empirical question, not a principled one. Test it against M-3's backtest:
one pooled model with `SEGMENT` and `IS_DUAL` as categoricals versus the current four.
If pooling wins, it removes the skipped-split failure mode entirely and cuts training
time 4×.

## M-9 — Guard the SHAP rescaling

```python
shap_adjusted[col] = (shap_adjusted[col] / shap_adjusted['TOTAL_FEATURE_IMPACT']) * (target - expected)
```

When `TOTAL_FEATURE_IMPACT` is near zero — positive and negative contributions
canceling — this produces enormous nonsense values. Currently unguarded.

```python
total = shap_adjusted['TOTAL_FEATURE_IMPACT']
safe_total = total.where(total.abs() > 1e-10)   # → NaN rather than an explosion
```

Also document in the table's column comments that these are proportionally rescaled
approximations, not strict additive attributions — feature ranking is preserved,
exact magnitudes are a projection into dollar space.

---

# [E] Efficiency

## E-1 — Remove dead computation in Step 3

`_add_rolling_quarter_fields` produces seven columns via three groupby-rolling
operations. **None appear in `config['features']` or the output selection** — all are
discarded by `_build_final_output`.

Worse, these are the slow pandas `.apply()`-style rollings that the rest of the module
deliberately avoids.

Either wire them into the feature list — rolling-quarter smoothing is reasonable for
noisy monthly data, and the `_SHIFTED` variants are already leakage-safe — or delete
the function and its call site.

## E-2 — Fix the Step 4 projection loop sorting

```python
for i in range(config['projection_months']):
    appended_source = pd.concat([appended_source, predict_set]).sort_values(by=group).reset_index(drop=True)
    predict_df      = pd.concat([predict_df, predict_set]).sort_values(by=group).reset_index(drop=True)
```

Both frames are fully re-sorted 21 times, and both grow each pass. `predict_df`'s sort
is pure waste — nothing reads its order inside the loop.

```python
predict_parts = []
for i in range(config['projection_months']):
    ...
    predict_parts.append(predict_set)
    appended_source = pd.concat([appended_source, predict_set], ignore_index=True)
    appended_source.sort_values(by=group, inplace=True, kind='mergesort', ignore_index=True)

predict_df = pd.concat(predict_parts, ignore_index=True).sort_values(by=group, ignore_index=True)
```

`kind='mergesort'` is the meaningful change — stable and near-linear on nearly-sorted
data, which this is (one month appended to an ordered frame).

## E-3 — Vectorize Step 4's calendar lookups

```python
new_df['DATE_REPORT_QTR'] = new_df.apply(lambda row: calendar_lookup(row, 'QUARTER'), axis=1)
new_df['MONTH']           = new_df.apply(lambda row: calendar_lookup(row, 'MONTH_NBR'), axis=1)
new_df['WORKDAY']         = new_df.apply(lambda row: calendar_lookup(row, 'WORKDAY'), axis=1)
```

Three row-wise passes per projection month per split per metric — up to 504 passes per
run. Every row in one `new_month` call shares the same date, so the same lookup is
recomputed thousands of times.

```python
assert new_df['DATE_REPORT_MONTH'].nunique() == 1
cal = config['calendar'][new_df['DATE_REPORT_MONTH'].iloc[0].strftime('%Y-%m-%d')]
new_df['DATE_REPORT_QTR'] = cal['QUARTER']
new_df['MONTH']           = cal['MONTH_NBR']
new_df['WORKDAY']         = cal['WORKDAY']
```

Three scalar assignments instead of three row-wise applies.

## E-4 — Column-prune the Snowflake extract

**Step 1.** `select *` transfers every column on every run, with no incremental
predicate. Enumerate the columns Step 2 actually consumes and select only those.

If the source carries a reliable load timestamp, an incremental predicate would avoid
re-transferring history entirely.

## E-5 — Bound driver memory

Both Step 3 and Step 4 call `.toPandas()` and then run entirely on the driver. Step 3
is the larger risk — it pulls the **whole book** for a valuation date, where Step 4
processes one HCC at a time.

This is the pipeline's scaling ceiling, and it fails as an OOM rather than a slowdown.

Two intermediate options short of a full Spark rewrite:

```python
mem_gb = source.memory_usage(deep=True).sum() / 1e9
print(f"Source frame: {len(source):,} rows, {mem_gb:.2f} GB")
if mem_gb > DRIVER_MEM_THRESHOLD_GB:
    raise MemoryError(f"Source frame {mem_gb:.2f} GB exceeds threshold — partition by HCC")
```

- **Bound it explicitly** so the failure is a readable error, not a dead executor.
- **Partition Step 3 by HCC** the way Step 4 already is, and run the parts
  concurrently as separate tasks.

## E-6 — Parallelize Steps 4 and 5 across HCCs

Both process one HCC per run, and the four HCCs are fully independent. If they are
currently sequential, running them as four concurrent Workflow tasks cuts wall-clock
time roughly 4× at no correctness cost — and each stays within driver memory.

## E-7 — Push Step 3's population regroup into SQL

```python
pop_df = spark.sql(pop_sql).toPandas()
group = [c for c in config['cf_product_level'] if c != 'IS_DUAL'] + ['DATE_REPORT_QTR', 'DATE_REPORT_MONTH']
pop_df = pop_df.groupby(group)[sumcols].sum().reset_index()
```

The SQL already grouped by exactly these columns — the pandas regroup is a no-op on
data already at target grain. Delete it, or if it is defensive, make that explicit
with an assertion instead.

Similarly, `_fetch_risk` pulls the entire risk table into pandas with no date filter,
unlike the calendar (bounded) and source (val_date filtered).

---

# [S] Structure

## S-1 — Decide between the notebook path and the module path

Two architectures coexist and partly overlap:

| | Notebook pipeline | `run_stage.py` |
|---|---|---|
| Steps | 5 (extract → completed → signals → train → output) | 5 (completion → valuation → signals_units → train → predict) |
| Overlap | `signals_units` only | `signals_units` only |
| Parameters | Task values + widgets | CLI args + YAML |
| Model artifacts | None | `model_id` handoff |
| Completion / valuation | Upstream in Snowflake | Explicit stages |

Step 3 is a module and **cannot run as a notebook** — its relative imports require
package context, so it must go through `run_stage.py`. The pipeline therefore needs
both mechanisms to execute, which is why the `val_date` chain breaks at that seam
(C-3).

Three possible resolutions:

1. **Notebook path is authoritative** → convert Step 3 to a notebook, or add a thin
   notebook wrapper that imports and calls `run()`. Archive `run_stage.py`.
2. **Module path is authoritative** → extract Steps 1, 2, 4, 5 into
   `src/pipeline/*.py` modules with `run()` signatures, and drive everything through
   `run_stage.py`. Notebooks become thin callers.
3. **Genuinely different pipelines** → name and document them so.

Option 2 is the stronger target: it makes every step testable, removes widget-based
parameter passing entirely, and gives one place for shared write logic. Option 1 is
faster to reach.

Deciding this unblocks S-2 and S-3, so it should come before either.

## S-2 — Extract a shared write helper

The delete-then-append / `replaceWhere` logic appears **five times** with small
divergences — Step 1, Step 2, Step 4 (twice: predictions and SHAP), Step 5. Only the
SHAP version does type-casting against the existing schema.

```python
def write_scenario_slice(spark, sdf, table_name, keys: dict, cast_to_existing=False):
    """Atomically replace the rows matching `keys`. Handles legacy and first-run cases."""
    if not spark.catalog.tableExists(table_name):
        sdf.write.saveAsTable(table_name)
        print(f"Created new table: {table_name}")
        return

    existing = {f.name: f.dataType for f in spark.table(table_name).schema.fields}
    existing_upper = {k.upper() for k in existing}

    if cast_to_existing:
        for field in sdf.schema.fields:
            if field.name in existing and field.dataType != existing[field.name]:
                sdf = sdf.withColumn(field.name, sdf[field.name].cast(existing[field.name]))

    active = {k: v for k, v in keys.items() if k.upper() in existing_upper}
    if not active:
        sdf.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table_name)
        print(f"Schema migration: overwrote {table_name}")
        return

    predicate = " AND ".join(f"{k} = '{v}'" for k, v in active.items())
    (sdf.write.format("delta")
        .option("replaceWhere", predicate)
        .option("mergeSchema", "true")
        .mode("overwrite")
        .saveAsTable(table_name))
    print(f"Replaced rows where {predicate} in {table_name}")
```

Five copies of non-trivial write semantics will drift. Folding R-4 into this helper
means the atomic idiom lands everywhere at once.

## S-3 — Centralize configuration

Step 3 is fully config-driven. Steps 1, 2, 4, and 5 hardcode catalog, schema, and
table names throughout — so promoting `ra_analytic_dev` to a production catalog is a
find-and-replace across four files.

Extend `pipeline_config.yaml` to cover every step and have the notebooks read from it.
This also makes dev/prod promotion a config change rather than a code change.

## S-4 — Separate exploration from production in the seasonality notebook

`SEASONALITY_ADJUSTMENT.py` runs ~250 lines of analysis scaffolding on every
execution that feeds nothing: the Friedman test, elbow and silhouette sweeps, violin
plots, and the slope/R² comparison.

Split it in two:

- `seasonality_analysis.ipynb` — the exploratory work, run when re-tuning
- `seasonality_build.py` — extract → calculate → cluster → write

Three functions (`get_month_name`, `calc_factor`, `check_cluster_size`) are currently
**defined twice** with different signatures ~250 lines apart, and the second silently
wins. Anyone editing the first version to change production behavior will change
nothing. The split resolves this structurally.

## S-5 — Wire the unused validation into the seasonality gate

Three genuinely good checks exist and none gate anything:

| Check | What it answers | Natural use |
|---|---|---|
| Friedman test | Is monthly variation statistically significant? | Only apply factors to groups where it is |
| Slope / R² on residuals | Did the factor remove seasonality or add a trend? | Release gate for new factors |
| Elbow / silhouette | What is the right `k`? | Feed the `k` values directly instead of hand-setting |

The residual check is the strongest — a well-constructed factor should leave a series
with slope near zero and low R². That is exactly the "are these factors safe to
publish" test, already written.

## S-6 — Fix the seasonality dedup before enabling clustering

```python
extra_cols = ['SEGMENT', 'DUAL_IND', 'SERVICE_TYPE', 'PRODUCT_LEVEL_2_TADM']
final_df = final_df.drop(columns=extra_cols)
final_df = final_df.drop_duplicates(subset=key_cols)
```

Factors are computed at a nine-column grain; the pipeline joins on seven. Four columns
are dropped and **an arbitrary survivor is kept per key**.

Harmless while everything is 1.0. The moment M-1 enables clustering, this silently
discards real variation that was just computed.

```python
final_df = (final_df.groupby(key_cols, as_index=False)
                    .agg(FINAL_NORM_FACTOR=('FINAL_NORM_FACTOR', 'median'),
                         CLUSTER_LABEL=('CLUSTER_LABEL', 'first')))
```

Makes the collapse a stated decision rather than an accident of row order. **This is a
prerequisite for M-1**, not an independent cleanup.

## S-7 — General code hygiene

| Item | Location | Action |
|---|---|---|
| Snowflake writers, `get_column_types` | Step 4 | Dead since the Databricks migration — delete |
| `train_test_split` import | Step 4 | Unused |
| `column` parameter on `loop_train_models` | Step 4 | Unused |
| `'runout': 3` | Step 3 | Never read |
| `_resolve_product_and_category` fallbacks | Step 3 | Unreachable against hardcoded config |
| `deepcopy` import | `run_stage.py` | Unused |
| Duplicate `DBUtils` import | `run_stage.py` | Redundant |
| `SPLIT_KEYS` redefined | Step 2, line 495 | Identical to line 48 — redundant |
| `warnings.filterwarnings('ignore')` | Step 4, seasonality | Narrow or drop; hides pandas deprecations |
| `except:` in `rolling_slope` | Step 4 | Narrow to `(ValueError, TypeError)` |
| `pd.api.types.is_categorical_dtype` | Step 4 | Deprecated in pandas 2.x; one site already uses the modern form |
| `assert` for data checks | Steps 2, 4 | Stripped under `python -O` — convert to explicit `raise` |
| `config['one_hot_columns']` | Step 4 | Misleading — nothing is one-hot encoded. Rename to `categorical_columns` |
| `VALID_STAGES` duplication | `run_stage.py` | Derive via `list(STAGE_RUNNERS)` |
| `except Exception: pass` | `run_stage.py` | Log the exception type — a permissions error and a missing file are currently indistinguishable |

## S-8 — Add column comments to published tables

`ohc_final_output` uses business names (`ENTY`, `LOB`, `PLAN_TYPE`, `RISK_TYPE`) that
are opaque without the source. Two facts especially need to travel with the data:

```sql
ALTER TABLE ra_analytic_dev.ohc_forecast.ohc_final_output
  ALTER COLUMN OH_FCST_UNIT_COST COMMENT
  'Derived: PMPM prediction / UTIL prediction. Not directly modeled — compounded error from two models.';
```

`OH_FCST_UNIT_COST` is a ratio of two independently-trained models' outputs. Neither
optimizes for it, and its error is the compounded error of both — the least reliable
number in the table, currently unmarked.

The `MM` carry-forward assumption deserves the same treatment, or better, an explicit
flag:

```python
F.col('MM').isNull().alias('MM_CARRIED_FORWARD'),
```

One boolean that lets a dashboard footnote projected rate metrics.
