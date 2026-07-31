# LIGHTGM_TRAIN — Detailed Walkthrough

A section-by-section reading of the training notebook. Sections follow the cell
boundaries in the source file.

---

## 1. Scenario parameters

```python
dbutils.widgets.text("train_end", "2026-03-01")
dbutils.widgets.text("hcc",       "PHYSICIAN")
dbutils.widgets.text("val_date",  "2026-03-01")
```

Three Databricks widgets define the scenario. Defaults are set here so the notebook is
runnable interactively; when driven by `RUN_FORECAST_SCENARIOS.ipynb` via
`dbutils.notebook.run()`, the caller's values win.

| Widget | Meaning | Consequence of changing it |
|---|---|---|
| `train_end` | Last experience month included in training | Shifts the whole projection window; also changes the model filename |
| `hcc` | Which major service category to train | Filters every source read; one notebook run = one HCC |
| `val_date` | Data-vintage marker from upstream prep | Pure provenance — never affects the math, only the output key |

`val_date` and `train_end` are distinct on purpose. `train_end` is a modeling decision
("how much history do I use"); `val_date` identifies which snapshot of the underlying
claims data was used. Two runs with the same `train_end` but different `val_date`
represent the same model spec applied to differently-complete data.

---

## 2. Imports

Standard stack — pandas, numpy, `lightgbm`, plus `scipy.stats.linregress` (used for the
rolling-slope feature). `warnings.filterwarnings('ignore')` is blanket-applied, which
keeps the output readable but will also swallow pandas deprecation warnings you might
want to see. `train_test_split` and `mean_squared_error` are imported but unused —
leftovers from an earlier iteration.

---

## 3. The `config` dictionary

Everything configurable lives in one dict rather than scattered globals. Worth reading
in four groups.

### Metrics and dates

```python
config['metrics']           = ['PMPM', 'UTIL']
config['train_end']         = pd.to_datetime(dbutils.widgets.get("train_end"))
config['train_start_lead']  = 12
config['projection_months'] = 21
config['projection_start']  = config['train_end'] + pd.DateOffset(months=1)
config['projection_end']    = config['projection_start'] + pd.DateOffset(months=20)
```

`train_start_lead = 12` is the burn-in. Every market/product group throws away its first
12 months of history. The reason: features like `TARGET_PMPM_12` (the 12-month lag) and
`VARIANCE_12_MO_PMPM` need a year of data to exist. Training on rows where they are null
teaches the model that null means something, which it doesn't.

`projection_months = 21` gives roughly a rolling 21-month forward view. The window is
derived, not hardcoded, so moving `train_end` slides the whole projection with it.

`run_timestamp` is captured once, at config time — so every row written by a single
notebook execution carries an identical timestamp, which makes it a usable run identifier.

### Source and output tables

```python
config['source']      = 'ra_analytic_dev.ohc_forecast.cs_forecast_signals_encoded'
config['seasonality'] = 'ra_analytic_dev.ohc_forecast.cs_cf_seasonality_factors'
config['output_table_name'] = 'LIGHTGBM_PMPM_UTIL_OUTPUT_ENCODED'
config['shap_table_name']   = 'LIGHTGBM_PMPM_UTIL_SHAP_ENCODED'
```

The `_ENCODED` suffix signals these tables carry target-encoded categorical features
rather than raw labels.

### Training parameters

```python
config['model_name'] = {m: f"CS_FINAL_{m}_{config['HCC']}_{config['train_end'].strftime('%Y%m')}.txt"
                        for m in config['metrics']}
config['test_offset'] = 1
config['one_hot_columns'] = ['MONTH', 'MARKET', 'PRODUCT_LEVEL_1_TADM',
                             'PRODUCT_LEVEL_2_TADM', 'PRODUCT_LEVEL_3_TADM',
                             'HCC', 'SERVICE_CATEGORY']
```

`test_offset = 1` means the final month before `train_end` is held out as a validation
set for early stopping. It is a one-month holdout, not a proper backtest — its only job
is to tell LightGBM when to stop boosting.

`one_hot_columns` is a slight misnomer. These columns are never one-hot encoded; they
are cast to pandas `category` dtype and handed to LightGBM as native categorical
features, which splits on category groupings directly rather than expanding to dummies.

### Features

```python
def get_metric_features(metric):
    return [
        f'MARKET_ENCODED_{metric}', f'CATEGORY_ENCODED_{metric}', f'PRODUCT_ENCODED_{metric}',
        f'TARGET_{metric}_1', f'TARGET_{metric}_2', f'TARGET_{metric}_3', f'TARGET_{metric}_12',
        f'COUNT_ZEROS_{metric}', f'VARIANCE_12_MO_{metric}', f'SLOPE_12_{metric}',
        'MM', 'WORKDAY',
        'PEDIATRIC_PERCENTAGE', 'ADULT_PERCENTAGE', ...
    ]
```

The feature set is built per metric via f-string templating, so PMPM and UTIL get
structurally identical but numerically distinct feature lists. Four families:

| Family | Features | What it captures |
|---|---|---|
| Target encodings | `MARKET_ENCODED_*`, `CATEGORY_ENCODED_*`, `PRODUCT_ENCODED_*` | Historical mean of the target for that dimension — a learned prior |
| Lags | `TARGET_*_1`, `_2`, `_3`, `_12` | Recent momentum plus year-over-year anchor |
| Rolling statistics | `COUNT_ZEROS_*`, `VARIANCE_12_MO_*`, `SLOPE_12_*` | Sparsity, volatility, trend direction |
| Exogenous | `MM`, `WORKDAY`, demographic percentages, `PROSP_RISK` | Exposure, calendar effects, population mix |

`MM` (member months) is the exposure variable. `WORKDAY` matters because a month with
more business days mechanically produces more claims.

### Calendar lookup

```python
def quarter_map():
    qtr = spark.table('ra_analytic_dev.cs_reference.calendar').toPandas()
    ...
    return qtr.to_dict('index')
```

The calendar table is pulled once, aggregated to month grain, and converted to a dict
keyed by `'YYYY-MM-01'`. This becomes a fast in-memory lookup for the recursive
projection loop, which needs `WORKDAY` and `MONTH_NBR` for future months that don't
exist in the source data yet. Doing this as a dict rather than repeated joins is a
meaningful speedup given how many times the loop calls it.

---

## 4. Loading the source data

```python
segment_lookup = (spark.table('...ohc_completed_combined')
                  .filter(f"HCC = '{config['HCC']}'")
                  .select(*join_keys, 'SEGMENT'))

src_sdf = (spark.table(config['source'])
           .filter(f"HCC = '{config['HCC']}'")
           .drop('seasonal_factor_pmpm', 'seasonal_factor_util'))

pre_count = src_sdf.count()
source = src_sdf.join(segment_lookup, on=join_keys, how='left').toPandas()
assert len(source) == pre_count, f"Join fan-out detected: ..."
```

The `SEGMENT` label (`OHC` vs `OC`) lives in the completed-claims table, not the feature
table, so it has to be joined in. The nine-column `join_keys` list is the full grain of
the completed table.

The assertion is the important line. If `ohc_completed_combined` ever has duplicate rows
at that grain, the left join silently multiplies the training set — inflating some groups'
weight in the loss function with no error raised. Comparing row counts before and after
catches it immediately. This is a good pattern; the alternative is discovering it weeks
later as inexplicable model drift.

Note `.toPandas()` — from here on everything is single-node pandas on the driver.

The pre-existing `seasonal_factor_*` columns are dropped because seasonality gets
re-joined below in a metric-specific form.

### Burn-in and training window

```python
source['MINDATE'] = source.groupby(group)['DATE_REPORT_MONTH'].transform('min')
source['TRAIN_START'] = source['MINDATE'] + pd.DateOffset(months=12)
source = source[(source['DATE_REPORT_MONTH'] >= source['TRAIN_START']) &
                (source['DATE_REPORT_MONTH'] <= config['train_end'])]
```

Per-group (market × three product levels) first-observation date, plus 12 months, becomes
that group's training start. Groups are filtered independently, so a market that launched
in 2023 contributes fewer rows than one with a decade of history — which is correct.

```python
source['N_TRAIN_MONTHS'] = ((train_end.year*12 + train_end.month) -
                            (TRAIN_START.dt.year*12 + TRAIN_START.dt.month))
```

Month-arithmetic instead of a timedelta, avoiding calendar-length ambiguity. This column
rides all the way through to the output table, so a downstream consumer can see how much
history backed any given forecast row. A projection with `N_TRAIN_MONTHS = 6` should be
read more skeptically than one with 60.

---

## 5. Seasonality join

```python
for m in config['metrics']:
    sf = (seasonality_factors[seasonality_factors['METRIC'] == m][keys + ['FINAL_NORM_FACTOR']]
          .rename(columns={'FINAL_NORM_FACTOR': f'FINAL_NORM_FACTOR_{m}'}))
    source = source.merge(sf, on=seasonality_merge_keys, how='left')
    source[f'FINAL_NORM_FACTOR_{m}'] = source[f'FINAL_NORM_FACTOR_{m}'].astype('float64')
    config['features'][m].append(f'FINAL_NORM_FACTOR_{m}')
```

The seasonality table is long-format (one row per metric); this pivots it into two wide
columns. Each metric's factor is then appended to that metric's feature list.

The explicit `astype('float64')` has a comment explaining it, and the comment is worth
keeping: if every row matches and every factor happens to be a whole number, pandas
infers `int64`. LightGBM then treats the column differently across runs — a
non-reproducibility bug that only appears with certain data, which is the worst kind.
The cast forces consistency.

```python
source.loc[source['TARGET_PMPM'] < 0, 'TARGET_PMPM'] = 0
```

Negative PMPM values (refunds, claim reversals) are floored at zero. Required by the
Tweedie objective, which is undefined for negative targets.

---

## 6. Population splits

```python
splits = {
    "OHC_DUAL":    source[(source['SEGMENT'] == 'OHC') & (source['IS_DUAL'] == 1)],
    "OHC_NONDUAL": source[(source['SEGMENT'] == 'OHC') & (source['IS_DUAL'] == 0)],
    "OC_DUAL":     source[(source['SEGMENT'] == 'OC')  & (source['IS_DUAL'] == 1)],
    "OC_NONDUAL":  source[(source['SEGMENT'] == 'OC')  & (source['IS_DUAL'] == 0)],
}
```

Four disjoint subsets, each getting its own model per metric — up to eight models per
notebook run. The rationale: dual-eligible members (Medicare + Medicaid) have materially
different cost and utilization patterns, and OHC vs OC represents a distinct
organizational split. Pooling would force the model to spend splits recovering a
distinction you already know.

The cost is fewer rows per model. If a split is thin, the burn-in filter can empty it out
entirely — handled explicitly in the training loop.

---

## 7. Training functions

### `get_train_data`

```python
for col in config['one_hot_columns']:
    df[col] = df[col].astype('category')

end_date = config['train_end'] - pd.DateOffset(months=config['test_offset'])
train = df[df['DATE_REPORT_MONTH'] <= end_date]
test  = df[df['DATE_REPORT_MONTH'] >  end_date]
```

Chronological split, not random — mandatory for time series. A random split would let the
model see future months while predicting past ones, producing validation metrics that
look excellent and forecasts that don't.

The `test` set here is a single month (`test_offset = 1`).

### `train_model`

```python
params = {
    'objective': 'tweedie',
    'metric': 'rmse',
    'boosting_type': 'gbdt',
    'learning_rate': 0.01,
    'num_leaves': 31,
    'max_depth': 6,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'verbose': -1,
    'early_stopping_rounds': 100,
}
model = lgb.train(params, train_data, num_boost_round=10000, valid_sets=[test_data])
```

| Parameter | Why |
|---|---|
| `objective: tweedie` | Compound Poisson-gamma — handles the zero mass plus continuous positive tail of claims data |
| `learning_rate: 0.01` | Deliberately slow; paired with up to 10,000 rounds and early stopping |
| `num_leaves: 31` / `max_depth: 6` | Modest capacity, guards against overfitting thin splits |
| `feature_fraction` / `bagging_fraction: 0.8` | Column and row subsampling for variance reduction |
| `early_stopping_rounds: 100` | Stops when the one-month holdout RMSE plateaus |

Note the tension between the Tweedie objective and the RMSE evaluation metric. Training
optimizes Tweedie deviance; early stopping watches RMSE. Not wrong, but they can disagree
about the best iteration — RMSE is more sensitive to large-value errors than Tweedie
deviance is.

`categoricals` is built by intersecting `one_hot_columns` with the actual feature list,
so a categorical column that isn't a model feature won't be passed through.

### `loop_train_models`

Trains one model, then predicts on both train and test and concatenates the results.
The `column` parameter is unused — dead signature from an earlier design.

---

## 8. Training loop

```python
for metric in config['metrics']:
    for split_name, split_df in splits.items():
        if split_df[features].dropna(how='all').empty:
            print(f"  WARNING: {split_name} has no usable training data — skipping.")
            skipped_splits[metric].append(split_name)
            continue
        model_dict, data_dict = loop_train_models(split_df, metric, config=config)
        trained_models[metric][split_name] = model_dict['final']['model']
```

Nested loop, up to eight models. The emptiness guard uses `dropna(how='all')` — a split
survives if any feature column has any value in any row, which is a fairly permissive
test. It catches the genuinely-empty case but would let through a split with, say, three
usable rows.

Skipped splits are recorded and honored by both the prediction and SHAP loops, so a skip
propagates cleanly rather than raising a `KeyError` later. **Read the
`skipped_splits` printout after every run** — a silently skipped split means a segment of
the book has no forecast at all.

---

## 9. Recursive projection helpers

This is the most intricate part of the notebook. The models predict one month ahead, but
the output needs 21 months. The solution: predict month 1, append the prediction to the
history as if it were an actual, recompute features, predict month 2, and so on.

### `calendar_lookup`

```python
def calendar_lookup(row, item, config=config):
    date = row['DATE_REPORT_MONTH'].strftime('%Y-%m-%d')
    return config.get('calendar', {}).get(date, {}).get(item, 'Not Found')
```

Chained `.get()` with a `'Not Found'` default. Note that the default is a *string* — if a
projection month is missing from the calendar table, `WORKDAY` becomes `'Not Found'`
rather than raising or producing NaN, and the failure surfaces downstream as a dtype
error rather than at the point of the problem. Worth knowing if you extend the horizon
past the calendar table's coverage.

### `rolling_slope`

```python
def rolling_slope(x):
    try:
        slope, intercept, _, _, _ = linregress(range(len(x)), x)
    except:
        return None
    return slope
```

OLS slope over a rolling window — the trend feature. Bare `except` returning `None`
handles degenerate windows (constant values, insufficient points), at the cost of hiding
any other failure.

### `new_month`

Builds the skeleton row for the next projection month:

1. Copy the last month's rows, advance `DATE_REPORT_MONTH` by one month.
2. Populate `DATE_REPORT_QTR`, `MONTH`, `WORKDAY` from the calendar dict.
3. Decrement `DURATION`.
4. Compute `*_ENCODED_*_PRE` columns — group means of the target, the raw inputs the
   rolling encodings are built from.
5. **Null out every lag, rolling, and encoding feature.** These get recomputed in
   `new_features`; leaving stale values would leak the previous month's numbers forward.
6. Drop and re-join the seasonality factor for the new calendar month.
7. Concatenate onto history and re-sort.

Step 5 is the subtle one. The row is copied from the prior month, so it arrives carrying
that month's feature values. Nulling them is what forces an honest recomputation.

The `.apply(lambda row: ..., axis=1)` calls are row-wise Python and are the main cost
center in this loop — they run once per projection month per split.

### `new_features`

Recomputes every derived feature for the new month, always via `.groupby(group).shift(...)`
so a value only ever comes from strictly earlier months:

```python
df.loc[df['DATE_REPORT_MONTH'] == last_date, f'MARKET_ENCODED_{metric}'] = (
    df.groupby(group)[f'MARKET_ENCODED_{metric}_PRE']
      .transform(lambda x: x.shift(1).rolling(window=12, min_periods=3).mean()))
```

The `.shift(1)` before `.rolling()` is the leakage guard — without it, the window would
include the current month, and the encoding for month *t* would be partly built from
month *t*'s own target.

| Feature | Computation |
|---|---|
| `*_ENCODED_*` | 12-month rolling mean of group means, shifted 1, min 3 periods |
| `TARGET_*_1/2/3` | Direct lags |
| `TARGET_*_12` | 12-month lag, falling back to the group mean when unavailable |
| `COUNT_ZEROS_*` | Rolling count of zero months |
| `VARIANCE_12_MO_*` | Rolling variance |
| `SLOPE_12_*` | Rolling OLS slope, then forward-filled |

The `min_periods=3` on rolling windows means a feature appears once three observations
exist rather than waiting for a full twelve — a deliberate coverage/stability trade.

`SLOPE_12_*` is forward-filled after computation because `linregress` returns `None` more
often than the other aggregations fail; ffill carries the last known trend rather than
handing the model a null.

Returns only the new month's rows.

### `get_prediction_data` / `loop_run_models`

Cast categoricals, select the feature columns, predict at `model.best_iteration` (the
early-stopping optimum, not the final boosting round).

---

## 10. Prediction loop

```python
appended_source = split_df[split_df['DATE_REPORT_MONTH'] < config['projection_start']].copy()
model = trained_models[metric][split_name]

for i in range(config['projection_months']):
    new_source    = new_month(df=appended_source, metric=metric, config=config)
    calc_features = new_features(df=new_source, metric=metric, config=config)
    y_predicted   = loop_run_models(calc_features, model, metric)
    calc_features = calc_features.drop(f"TARGET_{metric}", axis=1)
    predict_set   = y_predicted.join(calc_features)

    appended_source = pd.concat([appended_source, predict_set]).sort_values(by=group).reset_index(drop=True)
    predict_df      = pd.concat([predict_df, predict_set]).sort_values(by=group).reset_index(drop=True)
```

Twenty-one iterations of: extend → recompute → predict → append. The prediction is
written back as `TARGET_{metric}` — the same column name as the actuals — which is what
makes the next iteration's lag features work without special-casing.

`appended_source` is the growing history (actuals + predictions). `predict_df` accumulates
only the projected rows, and is what gets written out.

Two consequences worth internalizing:

- **Error compounds.** Month 21's features are built almost entirely from predicted
  values. Confidence should decay with horizon, and the output carries no interval to
  express that.
- **The sort inside the loop is redundant work.** `sort_values` runs on the full
  accumulated frame every iteration. Sorting once at the end would be equivalent and
  cheaper; the current form is the clearest optimization target if runtime becomes a
  problem.

---

## 11. SHAP attribution

```python
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X)
shap_values['EV_RAW'] = explainer.expected_value

shap_values_adjusted['EXPECTED_VALUE']       = np.exp(shap_values_adjusted['EV_RAW'])
shap_values_adjusted['TOTAL_FEATURE_IMPACT'] = shap_values_adjusted[column_names].sum(axis=1)
for col in column_names:
    shap_values_adjusted[col] = (
        (shap_values_adjusted[col] / shap_values_adjusted['TOTAL_FEATURE_IMPACT']) *
        (shap_values_adjusted[f'TARGET_{metric}'] - shap_values_adjusted['EXPECTED_VALUE'])
    )
```

SHAP is computed per split, using that split's own model, over the projection window only.

The rescaling deserves explanation. Tweedie uses a log link, so raw SHAP values live in
log space and don't sum to the prediction in dollar space. `np.exp(expected_value)`
converts the base value back, and each feature's contribution is then rewritten as its
*share* of total impact applied to the actual gap between prediction and base.

The result: contributions sum exactly to `prediction − expected_value` in the units
business users read. That is what makes the SHAP table usable in a BI tool.

The trade-off is that these are no longer SHAP values in the strict additive-attribution
sense — they are proportionally-rescaled approximations. The ranking of features is
preserved; the exact magnitudes are a projection into dollar space, not a theoretical
guarantee. Fine for "what drove this forecast," not appropriate for formal attribution
analysis.

Categorical columns are cast to `category` before the explainer runs and back to `object`
after, because `TreeExplainer` needs the categorical encoding but the Spark writer does not
handle pandas categoricals.

---

## 12. Building the forecast output

Per metric, a slim column set is selected, predictions are rounded to 4 decimals, and
`TARGET_{metric}` is renamed to `TARGET_{metric}_PREDICTED` — a rename that matters,
because it is how `final_output` distinguishes model output from actuals.

### Combining PMPM and UTIL

```python
pmpm_base = dfs['PMPM'].copy()
util_join = dfs['UTIL'][key_cols + ['TARGET_UTIL_PREDICTED']].copy()
df_combined = pmpm_base.merge(util_join, on=key_cols, how='left')
```

PMPM is the base (it carries the shared reference columns); UTIL contributes only its
prediction column. A left join means a group present in PMPM but absent from UTIL gets a
null utilization forecast rather than being dropped — which can happen if a split was
skipped for one metric but not the other.

### Run metadata

```python
df_combined['VAL_DATE']         = config['val_date']
df_combined['TRAIN_END']        = config['train_end'].strftime('%Y-%m-%d')
df_combined['TRAIN_START_LEAD'] = config['train_start_lead']
df_combined['PROJECTION_START'] = ...
df_combined['PROJECTION_END']   = ...
df_combined['RUN_TIMESTAMP']    = ...
```

Six columns stamped on every row. This is what makes multiple scenarios coexist in one
table and makes any given row traceable to the run that produced it.

---

## 13. Writing to Delta

`get_column_types`, `create_snowflake_table`, and `load_to_snowflake` are Snowflake-era
functions retained after the Databricks migration — `create_snowflake_table` now only
prints, and neither loader is called by the write path below. Candidates for deletion.

The actual write, used for both the prediction and SHAP tables:

```python
if spark.catalog.tableExists(table_name):
    existing_cols_upper = {f.name.upper() for f in spark.table(table_name).schema.fields}
    if 'VAL_DATE' in existing_cols_upper:
        delta_table.delete(f"val_date = '{val_date_str}' AND train_end = '{train_end_str}' AND HCC = '{hcc_str}'")
        spark_df.write.mode("append").option("mergeSchema", "true").saveAsTable(table_name)
    elif 'TRAIN_END' in existing_cols_upper:
        # legacy path — no val_date column yet
        delta_table.delete(f"train_end = '{train_end_str}' AND HCC = '{hcc_str}'")
        spark_df.write.mode("append")...
    else:
        spark_df.write.mode("overwrite").option("overwriteSchema", "true")...
else:
    spark_df.write.saveAsTable(table_name)
```

Four branches:

| Condition | Behavior |
|---|---|
| Table has `VAL_DATE` | Delete this `(val_date, train_end, HCC)` slice, append |
| Table has `TRAIN_END` only | Legacy — delete on `(train_end, HCC)`, append |
| Table has neither | Schema migration — full overwrite |
| Table absent | Create |

**Delete-then-append is the pattern to understand here.** It gives idempotent
re-runs: running the same scenario twice leaves the table identical, and running a
different scenario adds to it without disturbing existing rows. It is not atomic —
between the delete and the append, that slice is missing. Acceptable for a batch job,
not for anything a live dashboard reads during the window.

The SHAP write adds a step the prediction write doesn't:

```python
for field in spark_shap_df.schema.fields:
    if field.name in existing_fields and field.dataType != existing_fields[field.name]:
        spark_shap_df = spark_shap_df.withColumn(field.name,
                            spark_shap_df[field.name].cast(existing_fields[field.name]))
```

Every incoming column is cast to match the existing table's type. SHAP output has many
more columns, all float-derived, and pandas type inference can drift between runs; without
this, `mergeSchema` would create duplicate columns with conflicting types.

The two SHAP metric frames are stacked long-format with a `METRIC` discriminator column
rather than joined wide — the right call given each metric has its own feature set.

---

## Summary of concerns

| Area | Note |
|---|---|
| Driver memory | Everything post-`toPandas()` is single-node. This is the scaling ceiling. |
| Loop cost | 21 iterations × splits × metrics, with row-wise `.apply()` and a redundant per-iteration sort |
| Error compounding | Late-horizon months are built almost entirely on predictions; no uncertainty bands |
| Silent skips | Empty splits are skipped with a print, not a failure — check `skipped_splits` |
| SHAP rescaling | Proportional approximation, not strict additive attribution |
| Bare `except` | `rolling_slope` swallows all exceptions |
| Dead code | Snowflake writers, unused sklearn imports, unused `column` parameter |
| Calendar default | `'Not Found'` string default fails downstream rather than at the source |
