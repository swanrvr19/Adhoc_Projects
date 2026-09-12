# M&R Forecast Process Guide

This folder contains a Databricks/Spark pipeline that turns Medicare claims and
membership data into monthly medical-and-Rx (M&R) utilization and PMPM forecasts.
The pipeline is configuration-driven and writes versioned Delta tables in
`prod_tadm.mr_cos_prod_actuarial`.

## End-to-end process

Run the stages in this order:

```text
S00  Shared configuration
  ↓
S01  Claims and membership extracts
  ↓
S01A Utilization-metric assignment
  ↓
S01B Completion-factor estimation
  ↓
S02  Complete claims × membership monthly spine
  ↓
S03  Time-series feature engineering
  ↓
S04  LightGBM forecast and SHAP explanations
  ↓
S05  Walk-forward backtest and accuracy results
```

Each stage uses the prior stage's Delta table. `VAL_DATE` identifies the data
vintage; forecast and backtest scenario tables also use `TRAIN_END_MONTH` to
keep different forecast runs separate. The shared writer uses `replaceWhere`,
so rerunning a stage replaces only the relevant vintage/scenario slice.

## What each program does

### `S00_Config.py` — shared configuration

Defines the catalog/schema, short names for every input/output table, grouping
keys, model grains, completion-factor settings, feature lists, and common Spark
helpers. Other notebooks load it with `%run`; it is not a standalone processing
stage.

### `S01A_Extract_TADM_Tre_Data.py` — source extract

Reads the Physician, Outpatient, Inpatient, Rx, and membership event tables.
It standardizes their dimensions and measures, appends yearly snapshots, and
deduplicates overlapping rolling/incremental snapshots. It writes:

- `DEV_TFM_HCTA_MnR_CLM_DATA` — consolidated claims/utilization data
- `DEV_TFM_HCTA_MnR_MBR_DATA` — consolidated monthly membership

The extract also derives the `VAL_DATE` for the data vintage.

### `S01A_Utilization_Metric.py` — utilization metric assignment

Assigns one utilization measure to each configured claim split. It checks the
available unit columns in priority order and selects the first measure with a
positive historical total. The result is written to
`DEV_TFM_HCTA_MnR_UTIL_METRIC` so downstream stages use a consistent utilization
definition.

### `S01B_Completion_Factors.py` — claims runout adjustment

Builds paid-development triangles by incurred month and adjudication lag for
allowed dollars, paid dollars, and utilization. It estimates ultimate lag,
age-to-age chain-ladder factors, credibility fallbacks, caps/floors, monotonic
factors, and a partial-month interpolation. The resulting factors are written
to `DEV_TFM_HCTA_MnR_CF_FACTORS` and allow immature claims to be grossed up to
an estimated completed value.

### `S02_Preprocessing.py` — claims/membership spine

Aggregates claims and membership to the configured grains, applies the
completion factors, and creates a contiguous month axis for every observed
claim split. It keeps months where the enrollment group has members, including
months with zero utilization, so lag and rolling features are not corrupted by
sparse claim rows. It writes `DEV_TFM_HCTA_MnR_CLM_MBR_SPINE`.

### `S03 Build Model Features.py` — model-ready features

Reads the spine and creates the modeling data set. For utilization and PMPM it
adds target values, market/product/category encodings, seasonal fields,
1/2/3/12-month lags, rolling statistics, zero-count measures, and trend/slope
features. It writes `DEV_TFM_HCTA_MnR_MODEL_DATA`.

### `S04 Train LightGBM Model Test.py` — forecast generation

Trains separate LightGBM Tweedie models for utilization and PMPM within each
configured model group (`hcc`, segment, and drug coverage type). It forecasts
future months recursively: each prediction is appended to history, the
autoregressive features are recomputed, and the next month is predicted. It
also calculates adjusted SHAP feature contributions. Outputs are written to:

- `DEV_TFM_HCTA_MnR_FORECAST_OUTPUT` — forecast values and run metadata
- `DEV_TFM_HCTA_MnR_SHAP_OUTPUT` — feature-level explanations

### `S05 Backtest LightGBM Model.py` — historical validation

Loads S04's functions without triggering its production run, then repeats the
training/forecast process at a sequence of historical training cutoffs. It
compares forecasts with realized actuals over three- and twelve-month horizons,
using member-weighted rollups for both metrics. Results are written to
`DEV_TFM_HCTA_MnR_BACKTEST_RESULTS`.

### `M&R TADM Totals By Year.py` — independent reconciliation

This SQL-heavy notebook is not part of the S00–S05 execution chain. It sums
paid and allowed amounts by service year across multiple source-table snapshots
for Physician, Outpatient, Inpatient, Rx, and membership data. Use it to check
that source totals agree across snapshot vintages and migrations before relying
on forecast results.

## Legacy / alternate notebooks

`zzS01A_Utilization_Metric.py` and `zzS01B_Completion_Factors.py` are earlier or
alternate versions of the S01A/S01B logic. Treat the non-`zz` files as the
current pipeline entry points unless a specific comparison or recovery task
requires the older versions.

## Operating notes

1. Run in a Databricks environment with Spark, Delta tables, LightGBM, and SHAP
   dependencies available.
2. Review the validation cells in S01B, S02, S04, and S05 after each new
   `VAL_DATE` or model scenario.
3. Check the backtest coverage columns when the requested forecast horizon
   extends beyond the latest available actual month.
4. This guide describes the source code in this folder; it does not verify a
   live Databricks execution or the current contents of the external tables.
