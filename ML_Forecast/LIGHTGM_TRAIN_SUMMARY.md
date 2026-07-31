# LIGHTGM_TRAIN — Summary

## What it is

A Databricks notebook that trains LightGBM models to forecast healthcare cost and
utilization, then produces 21 months of forward projections plus SHAP attributions.
It is the modeling core of the OHC forecast pipeline — everything upstream prepares
its inputs, everything downstream consumes its outputs.

## What it does

For a single HCC (major service category, e.g. `PHYSICIAN`) it:

1. Pulls encoded feature data and joins on segment labels and seasonality factors.
2. Splits the population four ways — `OHC`/`OC` crossed with dual/non-dual.
3. Trains one LightGBM model per **metric × split** (2 metrics × 4 splits = up to 8 models).
4. Rolls forward month by month, generating one prediction at a time and feeding it
   back in as history so the next month's lag features are available.
5. Computes SHAP values on the projection window and rescales them so contributions
   sum to the actual prediction.
6. Writes two Delta tables — combined predictions and combined SHAP.

## The two metrics

| Metric | Meaning |
|---|---|
| `PMPM` | Allowed dollars per member per month |
| `UTIL` | Utilization per 1,000 members per year |

Both are modeled independently and merged into one wide output row at the end.

## Key design choices

- **Tweedie objective.** Healthcare claims data is zero-inflated and right-skewed;
  Tweedie handles the point mass at zero better than plain regression.
- **Recursive forecasting.** Predictions become inputs for the next month. This lets
  lag and rolling-window features stay populated across the whole 21-month horizon,
  at the cost of compounding error the further out you go.
- **Burn-in period.** Each market/product group discards its first 12 months so the
  model never trains on rows whose rolling features are half-empty.
- **Four separate models per metric.** Dual-eligible and OHC/OC populations behave
  differently enough that one pooled model would blur the signal.

## Inputs

| Table | Role |
|---|---|
| `cs_forecast_signals_encoded` | Feature matrix — lags, encodings, demographics |
| `ohc_completed_combined` | Segment lookup (`OHC` vs `OC`) |
| `cs_cf_seasonality_factors` | Per-metric monthly normalization factors |
| `cs_reference.calendar` | Workday counts and quarter mapping |

## Outputs

| Table | Contents |
|---|---|
| `LIGHTGBM_PMPM_UTIL_OUTPUT_ENCODED` | One row per group × month with both predictions |
| `LIGHTGBM_PMPM_UTIL_SHAP_ENCODED` | Per-feature SHAP contribution, stacked by metric |

Both are keyed on `(val_date, train_end, HCC)` and written with delete-then-append so
re-running a scenario replaces its own rows without touching others.

## Parameters

Three widgets, all overridable from `RUN_FORECAST_SCENARIOS.ipynb`:

- `train_end` — last experience month in training
- `hcc` — which service category to train
- `val_date` — data-vintage marker

## Where it fits

```
data prep → cs_forecast_signals_encoded
              ↓
         LIGHTGM_TRAIN  ← you are here
              ↓
   LIGHTGBM_PMPM_UTIL_OUTPUT_ENCODED
              ↓
         final_output → ohc_final_output (BI layer)
```

## Things to watch

- Runtime scales with `projection_months × splits × metrics` — the recursive loop
  rebuilds features 21 times per split.
- Everything after the initial Spark read runs in pandas on the driver. Memory is the
  practical ceiling on how many HCCs you can widen this to.
- A split with no usable training rows is skipped, not failed. Check the
  `skipped_splits` printout before trusting a run.
