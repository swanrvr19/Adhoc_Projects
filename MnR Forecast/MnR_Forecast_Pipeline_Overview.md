# M&R Forecast — Pipeline Overview

Summary of the Databricks notebooks (`.py`, `# Databricks notebook source` format) in
`shared-notebooks/Development Notebooks/MnR Forecast`. All tables live in
`prod_tadm.mr_cos_prod_actuarial` (catalog/schema defined once in `S00_Config.py`).

## Programs

| # | File | Role |
|---|------|------|
| S00 | [S00_Config.py](S00_Config.py) | Shared configuration loaded by every other stage via `%run`. No standalone execution. |
| S01 | [S01_Extract_TADM_Tre_Data.py](S01_Extract_TADM_Tre_Data.py) | Extracts and aggregates raw claims + membership from source event tables into two clean tables. |
| S02 | [S02_Preprocessing.py](S02_Preprocessing.py) | Joins claims + membership into a complete monthly "spine" (one row per product/claim split per month). |
| S03 | [S03 Build Model Features.py](S03%20Build%20Model%20Features.py) | Engineers the time-series features (lags, rolling stats, target encodings, slope) and target columns used by the model. |
| S04 | [S04 Train LightGBM Model Test.py](S04%20Train%20LightGBM%20Model%20Test.py) | Trains a per-segment LightGBM model, produces a recursive multi-month forecast, and computes SHAP explanations. |
| S05 | [S05 Backtest LightGBM Model.py](S05%20Backtest%20LightGBM%20Model.py) | Reuses S04's functions to walk-forward backtest the model across multiple historical training cutoffs and score forecast accuracy against realized actuals. |
| — | [M&R TADM Totals By Year.py](M%26R%20TADM%20Totals%20By%20Year.py) | Standalone reconciliation notebook. Not part of the pipeline flow — sums net paid/allowed amounts by service year across raw source event tables (Physician, Outpatient, Inpatient, Rx, Membership) as a data-quality check against multiple snapshot vintages. |

## Pipeline Flow (S00 → S05)

```
S00_Config
   │ (config constants, table names, feature lists, write_to_catalog helper)
   ▼
S01_Extract_TADM_Tre_Data
   │  Reads:  prod_tadm.mr_cos_prod_event.glxy_pr_f_* (claims), gl_rstd_gpsgalnce_f_* (membership)
   │  Writes: MnR_CLM_DATA, MnR_MBR_DATA  (partitioned by VAL_DATE)
   ▼
S02_Preprocessing
   │  Reads:  MnR_CLM_DATA, MnR_MBR_DATA
   │  Builds: a full split × month "spine" (cross-join, restricted to months with
   │          members > 0) so every product/claim slice has a contiguous timeline,
   │          even months with zero utilization.
   │  Writes: MnR_CLM_MBR_SPINE (partitioned by VAL_DATE)
   ▼
S03 Build Model Features
   │  Reads:  MnR_CLM_MBR_SPINE
   │  Adds:   TARGET_UTIL / TARGET_PMPM, target encodings (market/product/category),
   │          lags (1,2,3,12mo), rolling variance, rolling zero-count, rolling slope
   │  Writes: MnR_MODEL_DATA (partitioned by VAL_DATE)
   ▼
S04 Train LightGBM Model Test
   │  Reads:  MnR_MODEL_DATA
   │  Per model-group (cos_hccc_cd, segment_name_fnl, drug_cov_type_fnl):
   │    - trains one LightGBM (Tweedie) model per metric (UTIL, PMPM)
   │    - recursively forecasts forward month(s), feeding predictions back as history
   │    - computes adjusted SHAP contributions per feature
   │  Writes: MnR_FORECAST_OUTPUT, MnR_SHAP_OUTPUT (partitioned by VAL_DATE + TRAIN_END_MONTH)
   ▼
S05 Backtest LightGBM Model
      Loads S04 via %run (RUN_PIPELINE=False skips S04's own execution cells; only
      its function definitions are pulled in).
      Reads:  MnR_MODEL_DATA (as both training source and "actuals" for scoring)
      Loops over a range of monthly training cutoffs; for each, re-runs S04's
      train + recursive-forecast logic (no SHAP) and compares the member-weighted
      forecast to realized actuals over 3-month and 12-month horizons.
      Writes: MnR_BACKTEST_RESULTS (partitioned by VAL_DATE)
```

## Key Design Points

- **Config-driven**: `S00_Config.py` centralizes catalog/schema names, table name
  mapping (`TABLES` dict + `table_fqn()`), grouping-key lists (`ENROLL_KEYS`,
  `SERIES_GROUP`, `MODEL_GROUP`), and the feature-column list shared by S03 and S04
  so the two stages can't drift out of sync.
- **Idempotent writes**: every stage writes Delta tables via `write_to_catalog()`,
  which uses `replaceWhere` on `VAL_DATE` (and `TRAIN_END_MONTH` for S04/S05
  scenario tables) so re-running a stage only overwrites its own slice of data.
- **Two-step extract/dedup (S01)**: yearly source tables are appended directly
  (no overlap possible); rolling/incremental source tables are appended with a
  `NOT EXISTS` dedup against all prior tables in the union, keyed on
  `(site_clm_aud_nbr, fst_srvc_dt)` for claims and `(fin_hicn, fin_inc_month)` for
  membership.
- **Spine construction (S02)**: cross-joins distinct claim "splits" (product +
  category dimensions) with a contiguous month axis, then inner-joins membership
  so only months where the enrollment group actually has members survive — this
  prevents sparse claim data from corrupting lag/rolling/zero-count features later.
- **Recursive forecasting (S04)**: because features like lags and rolling stats
  depend on prior months, forecasting more than one month ahead requires
  predicting one month, appending it to history, recomputing that month's
  autoregressive features, and repeating (`_append_projected_month` /
  `_recompute_last_month_features` / `_recursive_forecast_segment`).
- **SHAP rescaling (S04)**: raw `TreeExplainer` SHAP values are rescaled so they
  sum exactly to `predicted − exp(expected_value)`, keeping the explanation
  internally consistent with the Tweedie log-link prediction.
- **Backtest reuse (S05)**: rather than duplicating training/forecast logic, S05
  `%run`s S04 with a guard flag (`RUN_PIPELINE = False`) that skips S04's own
  production run and check cells, importing only its function definitions.
- **Reconciliation script**: `M&R TADM Totals By Year.py` is independent of the
  S00–S05 pipeline. It is a raw-SQL notebook (not parameterized/config-driven)
  that builds per-year, per-component paid/allowed totals across several
  overlapping snapshot tables (e.g. `glxy_pr_f_2022`, `glxy_pr_f_202607`) for
  Physician, Outpatient (two date bases), Inpatient (three date bases), Rx, and
  Membership — used to manually verify totals are consistent across data
  vintages/migrations, not to feed the forecast.

## Assumptions / Notes

- This summary is based solely on reading the notebook source files in this
  folder; it does not verify against a live Databricks run.
- Source event tables referenced (e.g. `prod_tadm.mr_cos_prod_event.glxy_pr_f_*`)
  are outside this folder's config and were not inspected beyond their usage here.
