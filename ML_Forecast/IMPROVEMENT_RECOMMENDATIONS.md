# Improvement Recommendations

Recommendations for `LIGHTGM_TRAIN`, `final_output`, and `run_stage.py`, grouped by
priority. Each item states the issue, the fix, and why it matters.

**Priority tiers:**

- **P1** — correctness, silent failure, or reproducibility risk. Fix these.
- **P2** — meaningful performance or maintainability gain.
- **P3** — cleanup and polish.

---

# LIGHTGM_TRAIN

## P1 — Trained models are discarded

`config['model_name']` builds filenames and `config['model_stage']` points at a model
registry path, but neither is ever used. No `model.save_model()` call exists. Every run
trains up to eight models, uses them, and throws them away.

Consequences: a forecast in the output table cannot be reproduced, audited, or explained
without a full retrain — and because of the seeding issue below, a retrain won't
reproduce it either.

```python
# after the training loop
for metric in config['metrics']:
    for split_name, model in trained_models[metric].items():
        path = f"{config['model_stage']}/{config['HCC']}/{config['train_end']:%Y%m}/{metric}_{split_name}.txt"
        model.save_model(path)
```

Note that `run_stage.py` is built around a `model_id` handoff between train and predict —
the notebook has no equivalent. See the architecture question at the end.

## P1 — Runs are not reproducible

```python
params = {
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    # no seed set
}
```

Both subsampling parameters are stochastic and no seed is fixed. Two runs with identical
inputs produce different forecasts. For a model whose output feeds financial planning,
that is difficult to defend.

```python
'seed': 42,
'bagging_seed': 42,
'feature_fraction_seed': 42,
'deterministic': True,
```

`deterministic: True` also removes thread-scheduling nondeterminism, at a modest speed
cost. Worth it here.

## P1 — Historical rows are labeled as predictions

The forecast output is built from `appended_source_all`, which is the *concatenation* of
historical rows and projected rows:

```python
appended_source = split_df[split_df['DATE_REPORT_MONTH'] < config['projection_start']].copy()
# ... loop appends predict_set rows ...
appended_source_all[metric] = pd.concat(appended_sources.values(), ignore_index=True)
```

For historical months, `TARGET_{metric}` holds the **observed** value. That column is then
renamed wholesale:

```python
df = df.rename(columns={f"TARGET_{metric}": f"TARGET_{metric}_PREDICTED"})
```

So every pre-`projection_start` row in `LIGHTGBM_PMPM_UTIL_OUTPUT_ENCODED` carries an
actual value in a column named `_PREDICTED`. Downstream in `final_output`, this means
`OH_FCST_ALLOWED_PMPM` equals `OH_ACTUALS_ALLOWED_PMPM` for all historical months by
construction — anyone who plots forecast against actual over history will see perfect
accuracy that isn't real.

This may be deliberate, to give dashboards a continuous unbroken line. If so it needs to
be explicit rather than implicit:

```python
forecast_df['IS_PROJECTION'] = (forecast_df['DATE_REPORT_MONTH'] >= config['projection_start'])
forecast_df['HORIZON_MONTH'] = np.where(
    forecast_df['IS_PROJECTION'],
    ((forecast_df['DATE_REPORT_MONTH'].dt.year * 12 + forecast_df['DATE_REPORT_MONTH'].dt.month) -
     (config['projection_start'].year * 12 + config['projection_start'].month) + 1),
    0,
)
```

`HORIZON_MONTH` also solves a second problem — it lets consumers discount month-21
forecasts relative to month-1, which they currently have no way to distinguish.

**Verify before acting:** confirm by querying the output table for a month before
`projection_start` and checking whether `TARGET_PMPM_PREDICTED` exactly equals the value
in `cs_forecast_signals_encoded`.

## P1 — No validation metrics are recorded

`test_offset = 1` creates a one-month holdout, but it is consumed only by LightGBM's early
stopping. No RMSE, MAPE, or bias figure is ever computed, printed, or stored. There is no
way to answer "is this month's model better or worse than last month's."

```python
from sklearn.metrics import mean_squared_error  # already imported

y_val_pred = model.predict(data_dict['X_test'], num_iteration=model.best_iteration)
rmse = mean_squared_error(data_dict['y_test'], y_val_pred, squared=False)
bias = (y_val_pred.mean() - data_dict['y_test'].values.mean()) / data_dict['y_test'].values.mean()
print(f"  {split_name} {metric}: RMSE={rmse:,.4f}  bias={bias:+.2%}  "
      f"best_iter={model.best_iteration}  n_train={len(data_dict['X_train']):,}")
```

Persist these to a small run-metrics table keyed on `(val_date, train_end, HCC, metric,
split)`. A one-month holdout is thin, but tracked over time it makes drift visible.

A proper rolling-origin backtest (train to *T*, score *T+1…T+6*, walk forward) would be the
stronger version and is worth planning for separately.

## P1 — Silently skipped splits

```python
if split_df[features].dropna(how='all').empty:
    print(f"  WARNING: {split_name} has no usable training data — skipping.")
```

`dropna(how='all')` only drops rows where *every* feature is null, so a split with three
usable rows passes and trains a model on three rows. And a skip means an entire segment of
the book silently has no forecast — a `print` in a driver log is not sufficient signal.

```python
MIN_TRAIN_ROWS = 100  # tune to the book

usable = split_df[features].dropna(how='all')
if len(usable) < MIN_TRAIN_ROWS:
    msg = f"{split_name}/{metric}: only {len(usable)} usable rows (min {MIN_TRAIN_ROWS})"
    if STRICT:
        raise ValueError(msg)
    print(f"  WARNING: {msg} — skipping.")
    skipped_splits[metric].append(split_name)
    continue
```

Then write `skipped_splits` to the run-metrics table so a skip is queryable rather than
buried in logs.

## P1 — Calendar lookup fails silently and late

```python
return config.get('calendar', {}).get(date, {}).get(item, 'Not Found')
```

If the projection horizon extends past the calendar table's coverage, `WORKDAY` becomes
the string `'Not Found'`. That flows into a numeric feature column, and the failure
surfaces much later as a dtype error or, worse, a silently coerced value.

```python
def calendar_lookup(row, item, config=config):
    date = row['DATE_REPORT_MONTH'].strftime('%Y-%m-%d')
    try:
        return config['calendar'][date][item]
    except KeyError:
        raise KeyError(
            f"Calendar has no entry for {date} (field '{item}'). "
            f"Extend ra_analytic_dev.cs_reference.calendar to cover the projection horizon."
        )
```

Better still, validate the full horizon once up front, before training starts:

```python
needed = pd.date_range(config['projection_start'], config['projection_end'], freq='MS')
missing = [d.strftime('%Y-%m-%d') for d in needed if d.strftime('%Y-%m-%d') not in config['calendar']]
assert not missing, f"Calendar missing months: {missing}"
```

## P2 — The projection loop sorts on every iteration

```python
for i in range(config['projection_months']):
    ...
    appended_source = pd.concat([appended_source, predict_set]).sort_values(by=group).reset_index(drop=True)
    predict_df      = pd.concat([predict_df, predict_set]).sort_values(by=group).reset_index(drop=True)
```

Both frames are fully re-sorted 21 times, and both grow each pass. `predict_df`'s sort is
pure waste — nothing reads its order inside the loop. `appended_source` does need group
ordering for the `groupby().shift()` calls in `new_features`, so it can't simply be
dropped, but it can be made much cheaper:

```python
# predict_df — accumulate, sort once after the loop
predict_parts = []
for i in range(config['projection_months']):
    ...
    predict_parts.append(predict_set)
    appended_source = pd.concat([appended_source, predict_set], ignore_index=True)
    appended_source.sort_values(by=group, inplace=True, kind='mergesort', ignore_index=True)

predict_df = pd.concat(predict_parts, ignore_index=True).sort_values(by=group, ignore_index=True)
```

`kind='mergesort'` is the meaningful change on `appended_source` — it's stable and
near-linear on data that is already almost sorted, which this is (one month appended to an
ordered frame). Expect a solid reduction in loop time on larger HCCs.

## P2 — Row-wise `.apply()` in the hot path

```python
new_df['DATE_REPORT_QTR'] = new_df.apply(lambda row: calendar_lookup(row, 'QUARTER'), axis=1)
new_df['MONTH']           = new_df.apply(lambda row: calendar_lookup(row, 'MONTH_NBR'), axis=1)
new_df['WORKDAY']         = new_df.apply(lambda row: calendar_lookup(row, 'WORKDAY'), axis=1)
```

Three full row-wise passes per projection month per split per metric — up to 504 passes
per notebook run. Every row within one `new_month` call shares the same date, so this is
computing the same lookup thousands of times.

```python
date_key = new_df['DATE_REPORT_MONTH'].iloc[0].strftime('%Y-%m-%d')
cal = config['calendar'][date_key]          # raises if missing — see the P1 item above
new_df['DATE_REPORT_QTR'] = cal['QUARTER']
new_df['MONTH']           = cal['MONTH_NBR']
new_df['WORKDAY']         = cal['WORKDAY']
```

Three scalar assignments instead of three row-wise applies. Add
`assert new_df['DATE_REPORT_MONTH'].nunique() == 1` to make the assumption explicit.

## P2 — Objective and early-stopping metric disagree

```python
'objective': 'tweedie',
'metric': 'rmse',
```

Training minimizes Tweedie deviance; early stopping watches RMSE. They can disagree on the
best iteration, and RMSE is far more sensitive to large-value errors than Tweedie deviance
is — so early stopping is optimizing something the model isn't.

```python
'metric': 'tweedie',
'tweedie_variance_power': 1.3,   # currently defaulting to 1.5
```

Also worth tuning `tweedie_variance_power` explicitly. It controls where the distribution
sits between Poisson (1.0) and gamma (2.0), and the default of 1.5 was never chosen — it
was inherited. A small sweep over 1.1–1.7 against holdout RMSE is cheap and often moves
the needle more than tree hyperparameters do.

## P2 — The Delta write block is duplicated three times

The four-branch delete-then-append logic appears twice in this notebook (predictions,
SHAP) and again in `final_output`, with small divergences — only the SHAP version does
type-casting against the existing schema.

```python
def write_scenario_slice(spark, sdf, table_name, keys: dict, cast_to_existing=False):
    """Delete the rows matching `keys`, then append `sdf`. Handles legacy and first-run cases."""
    from delta.tables import DeltaTable

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
    DeltaTable.forName(spark, table_name).delete(predicate)
    sdf.write.mode("append").option("mergeSchema", "true").saveAsTable(table_name)
    print(f"Replaced rows where {predicate} in {table_name}")
```

Put this in a shared module imported by both notebooks. Three copies of the same
non-trivial write semantics will drift.

## P2 — Everything runs on the driver

`.toPandas()` pulls the full HCC into driver memory, and the remaining ~500 lines are
single-node pandas. This is the ceiling on how far the pipeline scales — a larger HCC or an
attempt to train several at once will hit an OOM, not a slowdown.

Not a refactor to undertake casually. Two intermediate options:

- **Bound it explicitly.** Log `source.memory_usage(deep=True).sum()` and fail with a clear
  message above a threshold, so the failure mode is a readable error rather than a dead
  executor.
- **Parallelize across HCCs at the job level** rather than widening within the notebook —
  run *N* single-HCC tasks concurrently. Each stays within driver memory, and this matches
  the per-HCC structure already baked into the write keys.

The full Spark rewrite (`pandas_udf` over grouped data) is the real answer if volume keeps
growing, but it is a project, not a fix.

## P2 — SHAP rescaling is not standard attribution

```python
shap_values_adjusted[col] = (
    (shap_values_adjusted[col] / shap_values_adjusted['TOTAL_FEATURE_IMPACT']) *
    (shap_values_adjusted[f'TARGET_{metric}'] - shap_values_adjusted['EXPECTED_VALUE'])
)
```

The rescaling is a reasonable pragmatic choice — it makes contributions sum to the
prediction in dollar space, which is what a BI consumer needs. But the result is no longer
a SHAP value in the additive-attribution sense. Feature *ranking* survives; exact
magnitudes are a proportional projection.

Two things to add:

1. A note in the table's column comments, so a downstream analyst doesn't cite these as
   formal attributions.
2. A guard against the degenerate case:

```python
total = shap_values_adjusted['TOTAL_FEATURE_IMPACT']
safe_total = total.where(total.abs() > 1e-10)   # → NaN rather than an exploded value
```

When `TOTAL_FEATURE_IMPACT` is near zero — a row where positive and negative contributions
cancel — the current division produces enormous nonsense values. Currently unguarded.

## P3 — Cleanup

| Item | Action |
|---|---|
| `create_snowflake_table`, `load_to_snowflake`, `get_column_types` | Dead since the Databricks migration — delete |
| `train_test_split` import | Unused — delete |
| `column` parameter on `loop_train_models` | Unused — delete |
| `warnings.filterwarnings('ignore')` | Narrow to specific categories, or drop; it currently hides pandas deprecation warnings you want to see |
| `except:` in `rolling_slope` | Narrow to `except (ValueError, TypeError)` |
| `pd.api.types.is_categorical_dtype` | Deprecated in pandas 2.x. One site already uses `isinstance(dtype, pd.CategoricalDtype)` — make all of them consistent |
| `assert len(source) == pre_count` | Good check, but `assert` is stripped under `python -O`. Convert to an explicit `raise` |
| `config['one_hot_columns']` | Misleading name — nothing is one-hot encoded. Rename to `categorical_columns` |

---

# final_output

## P1 — An empty result writes successfully

If `val_date`, `train_end`, or `hcc` don't match a training run, the triple filter returns
nothing, an empty frame is written, and the job reports success. The validation query at
the end will show `total_rows = 0`, but nothing acts on it.

```python
row_count = df_final.count()
if row_count == 0:
    raise ValueError(
        f"No rows matched val_date={val_date}, train_end={train_end}, hcc={hcc} in "
        f"LIGHTGBM_PMPM_UTIL_OUTPUT_ENCODED. Check that these match the training run."
    )
print(f"Writing {row_count:,} rows")
```

Place this before the write. This is the single highest-value change in the file — it
converts the most likely operator error from a silent no-op into an immediate, readable
failure.

## P1 — Turn the validation query into an assertion

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

The four metrics are already the right ones. They just need to gate the job rather than
decorate the log — nobody reads a `display()` on a scheduled run.

## P1 — Make the carry-forward assumption visible

`LAST_MM` holds membership flat for up to 21 months. That is a material assumption, and
nothing in the output table tells a consumer which rows depend on it.

```python
F.col('MM').isNull().alias('MM_CARRIED_FORWARD'),
```

One boolean column. It lets a dashboard footnote projected rate metrics, and it lets
anyone investigating a suspicious forecast see immediately whether membership was assumed.

Longer term, consider sourcing an actual enrollment projection instead — for a market in
growth or runoff, flat membership will drift materially over the horizon in a direction the
model never sees.

## P1 — `F.first('MM')` is unguarded

```python
.agg(F.first('MM').alias('MM'), F.sum('UTIL').alias('UTIL'), F.sum('PD').alias('PD'))
```

Correct only while `MM` is constant across `SERVICE_TYPE` within a group-month. It should
be, by construction. If it ever isn't, `first` silently picks an arbitrary value and every
rate metric in the table is quietly wrong.

```python
.agg(
    F.min('MM').alias('MM_MIN'),
    F.max('MM').alias('MM_MAX'),
    F.sum('UTIL').alias('UTIL'),
    F.sum('PD').alias('PD'),
)
```

then

```python
inconsistent = actuals.filter(
    F.col('MM_MIN').isNotNull() & (F.col('MM_MIN') != F.col('MM_MAX'))
).count()
if inconsistent:
    raise ValueError(f"MM varies within {inconsistent:,} group-months — F.first() is unsafe")

actuals = actuals.withColumn('MM', F.col('MM_MAX')).drop('MM_MIN', 'MM_MAX')
```

Costs one extra aggregation and one count. Converts a silent wrong-answer failure into a
loud one.

## P2 — Reconcile the two actuals paths

`OH_ACTUALS_ALLOWED_PMPM` comes from `ohc_completed_combined` via the join.
`OH_FCST_ALLOWED_PMPM` for historical months comes from `cs_forecast_signals_encoded` via
the model output (see the P1 item in the training notebook). These are two different
lineages for the same underlying quantity, and nothing checks that they agree.

```python
recon = df_final.filter(F.col('OH_ACTUALS_ALLOWED_PMPM').isNotNull()).select(
    F.mean(F.abs(F.col('OH_ACTUALS_ALLOWED_PMPM') - F.col('OH_FCST_ALLOWED_PMPM')) /
           F.col('OH_ACTUALS_ALLOWED_PMPM')).alias('mean_abs_pct_diff')
).collect()[0]['mean_abs_pct_diff']
print(f"Historical actuals vs. model-source reconciliation: {recon:.4%}")
```

If the historical `_PREDICTED` values really are passed-through actuals, this should be
approximately zero — and a non-zero result means the two source tables have diverged, which
is worth knowing early.

## P2 — Flag the derived unit cost

```python
F.round(F.col('TARGET_PMPM_PREDICTED') * 12000 / nz(F.col('TARGET_UTIL_PREDICTED')), 4)
    .alias('OH_FCST_UNIT_COST'),
```

This is a ratio of two independently-trained models' outputs. Neither model optimizes for
it, and its error is the compounded error of both — it is the least reliable number in the
table, and nothing marks it as such.

Minimum: a column comment. Better: `ALTER TABLE ... ALTER COLUMN OH_FCST_UNIT_COST COMMENT
'Derived: PMPM prediction / UTIL prediction. Not directly modeled — compounded error from
two models.'` so the caveat travels with the data into the BI tool.

## P2 — Move hardcoded names to config

```python
table_name = 'ra_analytic_dev.ohc_forecast.ohc_final_output'
spark.table('ra_analytic_dev.ohc_forecast.ohc_completed_combined')
spark.table('ra_analytic_dev.ohc_forecast.LIGHTGBM_PMPM_UTIL_OUTPUT_ENCODED')
```

Three literals with the `ra_analytic_dev` catalog baked in, which makes promoting to a prod
catalog a find-and-replace. `run_stage.py` already establishes the right pattern —
`pipeline_config.yaml` with `write_catalog` / `write_schema`. This notebook should read
from it too.

## P2 — Parameterize the SQL

```python
delta_table.delete(f"val_date = '{val_date}' AND train_end = '{train_end}' AND MAJ_SRV_CAT = '{hcc}'")
```

Widget values are interpolated directly into a delete predicate. These are internal
operator-supplied values rather than user input, so the risk is low — but a stray
apostrophe in an HCC name breaks the job, and the `delete` is the one statement where a
malformed predicate is destructive.

At minimum, validate on the way in:

```python
import re
for name, val in [('val_date', val_date), ('train_end', train_end)]:
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', val):
        raise ValueError(f"{name} must be YYYY-MM-DD, got {val!r}")
if not re.fullmatch(r'[A-Z_]+', hcc):
    raise ValueError(f"hcc must be uppercase alphabetic, got {hcc!r}")
```

Cheap, and it catches typo'd parameters before anything is deleted.

## P3 — Cleanup

| Item | Action |
|---|---|
| Delta write block | Replace with the shared `write_scenario_slice` helper above |
| `nz` lambda | Fine as-is, but a named `def nullif(c)` with a docstring reads better for anyone unfamiliar with the SQL idiom |
| Column comments | The `ENTY` / `LOB` / `PLAN_TYPE` / `RISK_TYPE` renames are opaque without the source. Add `COMMENT` clauses documenting the mapping |

---

# run_stage.py

The strongest of the three files. Recommendations here are refinements, not repairs.

## P1 — Stage failures exit zero

```python
result = runner(spark, cfg)
print(f"{stage.upper()} Result: {result}")

if stage == 'lightgbm_train' and result.get('status') == 'SUCCESS':
    ...
```

The `status` field is checked only for `lightgbm_train`, and only to decide whether to
publish `model_id`. For every other stage, a runner returning `{'status': 'FAILED'}`
prints, falls through, and exits 0 — Databricks marks the task green and the downstream
stages run on bad data.

```python
result = runner(spark, cfg, args) if ... else ...
print(f"{stage.upper()} Result: {result}")

status = (result or {}).get('status')
if status != 'SUCCESS':
    raise RuntimeError(f"Stage '{stage}' returned status={status!r}. Full result: {result}")
```

Put this immediately after the print, before the model_id block. The existing
train-specific guard then becomes redundant and can be simplified.

This is the most consequential change in the file — the pipeline's task dependencies are
only meaningful if a failed stage actually fails.

## P1 — Validate config before starting Spark

Missing YAML keys currently surface as a `KeyError` inside the runner, after the session is
up and (for `lightgbm_train`) possibly minutes into execution.

```python
REQUIRED_KEYS = {
    'completion': ['source_table', 'target_table', 'write_catalog', 'write_schema', 'val_cf_enabled'],
    'valuation': ['source_table', 'seasonality_factors_table', 'target_table', 'write_catalog', 'write_schema'],
    'signals_units': ['source_table', 'seasonality_factors_table', 'calendar_table',
                      'population_table', 'risk_table', 'target_table', 'write_catalog', 'write_schema'],
    'lightgbm_train': ['source_table', 'metric', 'hcc', 'train_end'],
    'lightgbm_predict': ['source_table', 'seasonality_factors_table', 'calendar_table', 'hectar_table',
                         'target_table', 'shap_table', 'write_catalog', 'write_schema',
                         'metric', 'hcc', 'projection_months'],
}

def validate_config(cfg, stage):
    if stage not in cfg:
        raise KeyError(f"Config has no '{stage}' section")
    missing = [k for k in REQUIRED_KEYS[stage] if k not in cfg[stage]]
    if stage in ('lightgbm_train', 'lightgbm_predict') and 'model_store_path' not in cfg:
        missing.append('model_store_path (top level)')
    if missing:
        raise KeyError(f"Config section '{stage}' missing required keys: {missing}")
```

Call it right after `load_pipeline_config()`, before `SparkSession.builder.getOrCreate()`.
Fail in two seconds instead of two minutes.

## P2 — Uniform runner signature

```python
if stage == 'lightgbm_predict':
    result = runner(spark, cfg, args.model_id)
else:
    result = runner(spark, cfg)
```

Works fine at five stages, but it's the seam that will tear when a second stage needs an
extra parameter. Give every runner `(spark, config, args)` and let each take what it needs:

```python
def run_valuation(spark, run_config, args):    # args unused
    ...

def run_lightgbm_predict(spark, run_config, args):
    model_id = args.model_id
    ...

result = runner(spark, cfg, args)
```

The branch disappears and `STAGE_RUNNERS` becomes uniformly callable.

## P2 — Derive `VALID_STAGES` from the dispatch table

```python
VALID_STAGES = ['completion', 'valuation', ...]   # must be kept in sync manually
```

Two sources of truth for the same set. Move `STAGE_RUNNERS` above `main()` (it already is)
and derive:

```python
VALID_STAGES = list(STAGE_RUNNERS)
```

Requires moving the `VALID_STAGES` assignment below the function definitions. The ordering
documentation currently carried by the literal list is better placed in the module
docstring anyway.

## P2 — Don't swallow the fallback exception

```python
try:
    model_id = _dbutils.fs.head(model_id_path).strip()
    print(f"Read model_id from {model_id_path}: {model_id}")
except Exception:
    pass
```

A missing file is the expected case, and the code does fail clearly two lines later — so
this is defensible. But a permissions error and a missing file are currently
indistinguishable in the log, and the second one is much harder to diagnose blind.

```python
except Exception as exc:
    print(f"Could not read model_id from {model_id_path}: {type(exc).__name__}: {exc}")
```

One line, no behavior change, and it turns a confusing debugging session into an obvious
one.

## P2 — Guard against a stale model_id

The `.last_model_id` file is last-writer-wins and persists across runs. If a train task
fails today, the predict task falls back to reading the file and picks up *yesterday's*
model — then produces forecasts that look fine and are silently based on the wrong model.

The `status == 'SUCCESS'` guard prevents writing a bad ID, but not reading a stale one.
Write metadata alongside the ID:

```python
# in main(), on successful train
import json, datetime
payload = json.dumps({
    'model_id': str(model_id),
    'val_date': args.val_date,
    'written_at': datetime.datetime.utcnow().isoformat(),
})
dbutils.fs.put(f"{cfg['model_store_path']}/.last_model_id", payload, overwrite=True)
```

```python
# in run_lightgbm_predict fallback
meta = json.loads(_dbutils.fs.head(model_id_path))
if meta['val_date'] != run_config['run_val_date']:
    raise ValueError(
        f"Stored model_id is for val_date={meta['val_date']}, but this run is "
        f"{run_config['run_val_date']}. Re-run lightgbm_train or pass --model-id explicitly."
    )
model_id = meta['model_id']
```

This changes the file format, so handle both shapes during the transition (try `json.loads`,
fall back to treating the content as a bare ID).

## P2 — Require `model_store_path`

```python
model_id_path = f"{run_config.get('model_store_path', '/tmp')}/.last_model_id"
```

The `/tmp` default prevents a `KeyError` but will not contain the file, so it converts a
clear config error into a confusing "model not found." Both stages that touch this path
genuinely require it — let it raise, or better, catch it in `validate_config` above.

## P3 — Structured logging

`print()` to the driver log is adequate for Databricks and easy to grep. If these jobs are
ever monitored centrally, the standard swap is worth it:

```python
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
)
log = logging.getLogger('run_stage')
log.info("Stage %s complete: %s", stage, result)
```

Gives timestamps and levels for free, and lets warnings be filtered from info.

## P3 — Cleanup

| Item | Action |
|---|---|
| `from copy import deepcopy` | Unused — delete |
| `from pyspark.dbutils import DBUtils` inside `run_lightgbm_predict` | Duplicates the module-level import — delete |
| `Path(inspect.getfile(inspect.currentframe()))` | Keep. `Path(__file__)` is simpler but less reliable in Databricks contexts — add a one-line comment saying so, or someone will "simplify" it |
| `--val-date` | Validate the format at parse time with a `type=` callable rather than letting a malformed date reach the runners |

---

# Cross-cutting

## Reconcile the notebook path and the `run_stage.py` path

`run_stage.py` defines `lightgbm_train` and `lightgbm_predict` stages backed by
`src/pipeline/` modules, with a proper `model_id` handoff. The `LIGHTGM_TRAIN` notebook
appears to do the same work — train, project, SHAP, write — in a single monolithic script
with no model persistence.

Three possibilities, and it's worth establishing which:

1. The notebook is the legacy path, superseded by `run_stage.py` → archive it.
2. `src/pipeline/lightgbm_train.py` is a refactored extraction of the notebook → the
   notebook should be deleted or clearly marked as a reference copy.
3. They are genuinely different pipelines → they need names and docs that say so.

Two implementations of the same model that can drift apart is the failure mode to avoid
here. The most likely reading is (2), given the notebook's Snowflake-era dead code and the
absence of any model persistence that `run_stage.py`'s `model_id` contract requires.

## Shared utilities module

Three pieces of logic are duplicated across files and should live in one importable place:

| Utility | Currently duplicated in |
|---|---|
| `write_scenario_slice` (Delta delete-then-append) | `LIGHTGM_TRAIN` ×2, `final_output` ×1 |
| Scenario parameter parsing and validation | Both notebooks |
| Table name construction from catalog/schema config | Both notebooks, `run_stage.py` |

## Suggested order

1. `final_output` empty-result guard — one block, removes the most likely silent failure
2. `run_stage.py` non-`SUCCESS` raise — one block, makes task dependencies real
3. LightGBM seeds — three lines, makes runs reproducible
4. Model persistence — makes forecasts auditable
5. `IS_PROJECTION` / `HORIZON_MONTH` columns — resolves the actuals-labeled-as-predictions ambiguity
6. Validation metrics table — makes model quality trackable over time
7. Projection loop sort fix and calendar vectorization — the performance work
8. Shared write helper and config extraction — the structural cleanup
9. Notebook vs. `run_stage.py` reconciliation — needs a decision before it needs code

Items 1–3 are roughly an afternoon and address the highest-probability failures.
