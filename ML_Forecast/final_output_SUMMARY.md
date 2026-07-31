# final_output — Summary

## What it is

A short Databricks notebook that turns raw model predictions into the
business-facing reporting table. It is the last step in the pipeline: everything
before it is modeling, this is presentation.

## What it does

1. Reads LightGBM predictions for one scenario `(val_date, train_end, hcc)`.
2. Reads actual claims history and collapses it to the model's grain.
3. Joins the two so every row carries both what happened and what was forecast.
4. Renames technical columns to business names (`MARKET` → `ENTY`, and so on).
5. Derives four actuals metrics and four forecast metrics from raw counts.
6. Writes to `ohc_final_output` using delete-then-append on the scenario key.
7. Prints a row-count sanity check.

## Why it exists separately

The model output table is keyed and named for modeling convenience. Analysts and
dashboards need something else: familiar column names, actuals sitting next to
forecasts in the same row, and rate metrics rather than raw counts. Keeping this
in its own notebook means the presentation layer can change without retraining
anything.

## The shape of a row

One row per product group per month, spanning both history and projection:

| Column group | Historical months | Projection months |
|---|---|---|
| `OH_ACTUALS_*` | populated | `NULL` |
| `OH_FCST_*` | populated | populated |
| `MM` | actual member months | carried forward from last known |

`MM IS NULL` is therefore the marker distinguishing a projection row from a
historical one — which is exactly what the validation query at the end counts.

## The metrics

| Column | Definition |
|---|---|
| `OH_ACTUALS_UTIL` | Raw utilization count |
| `OH_ACTUALS_UTIL_K` | Utilization per 1,000 members per year |
| `OH_ACTUALS_UNIT_COST` | Paid dollars ÷ utilization |
| `OH_ACTUALS_ALLOWED_PMPM` | Paid dollars ÷ member months |
| `OH_FCST_UTIL` | Predicted utilization, converted back to raw count |
| `OH_FCST_UTIL_K` | Predicted utilization per 1,000 |
| `OH_FCST_UNIT_COST` | Predicted PMPM ÷ predicted utilization, scaled |
| `OH_FCST_ALLOWED_PMPM` | Predicted PMPM |

Actuals and forecast metrics are defined in parallel so a dashboard can plot them
on the same axis and the comparison is apples to apples.

## Two ideas worth knowing

**Member-month carry-forward.** Future months have no actual membership. The
notebook takes each group's most recent non-null `MM` and carries it forward, so
rate metrics remain computable across the projection. This assumes flat
membership — reasonable over 21 months, and worth remembering when reading the
output.

**Divide-by-zero guard.** A small `nz()` helper turns zeros into nulls before
every division, so an empty denominator produces a null rather than an error or
an infinity.

## Inputs and output

| Table | Role |
|---|---|
| `LIGHTGBM_PMPM_UTIL_OUTPUT_ENCODED` | Model predictions (input) |
| `ohc_completed_combined` | Actual claims history (input) |
| `ohc_final_output` | Reporting table (output) |

## Parameters

The same three widgets as the training notebook — `train_end`, `hcc`, `val_date`.
They must match the training run exactly, or the filter returns nothing and the
notebook writes an empty result without complaint.

## Things to watch

- **Parameter drift is silent.** A mismatched `train_end` yields zero rows, not
  an error. The final validation query is the check — a `total_rows` of 0 means
  the parameters were wrong.
- **Grain change.** Actuals are aggregated across `SERVICE_TYPE` to match the
  model's coarser grain; that dimension is not recoverable downstream.
- **String-interpolated SQL.** Parameters are formatted directly into the delete
  predicate and validation query.
