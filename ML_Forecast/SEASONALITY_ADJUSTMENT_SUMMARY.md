# SEASONALITY_ADJUSTMENT — Summary

## What it is

An exploratory Databricks notebook (exported as `.py`) that derives monthly
seasonality normalization factors and writes them to
`ra_analytic_dev.ohc_forecast.cs_cf_seasonality_factors` — the table both
`signals_units` and `LIGHTGM_TRAIN` read from.

It is the only file in this directory that is genuinely exploratory rather than
production. Roughly half of it is analysis scaffolding whose output feeds nothing.

## The method

For each dimensional group, compare each month's rate against that group's annual
average:

```
NORM_FACTOR = (month's utilization per member) / (year's utilization per member)
```

A factor of 1.15 means that month runs 15% above the group's annual baseline.

Individual group-level factors are noisy, so the intended pipeline clusters groups
by their 12-month seasonality shape (k-means over a month-pivoted matrix), then
takes the **median factor per cluster per month** as the final published value.
Clustering acts as the smoothing step.

## Current state — factors are all 1.0

```python
hcc_list_pmpm = [['PHYSICIAN',0], ['OUTPATIENT',0], ['INPATIENT',0], ['PHARMACY',0]]
hcc_list_util = [['PHYSICIAN',0], ['OUTPATIENT',0], ['INPATIENT',0], ['PHARMACY',0]]
```

Every `k` is `0`, and the loop routes `k == 0` to `final_data_no_factors`, which
sets `FINAL_NORM_FACTOR = 1` unconditionally. So:

- `run_cluster` and `get_final_data` never execute
- The published table contains 1.0 for every group, month, and metric
- `SEASONAL_FACTOR_UTIL` / `SEASONAL_FACTOR_PMPM` in `signals_units` are constants
- `FINAL_NORM_FACTOR_*` in `LIGHTGM_TRAIN` is a constant feature, contributing
  nothing to the model

The comment directly above those lines reads *"k values selected via silhouette +
elbow analysis"*, which describes a state the code is not in. Either the values
were reset deliberately and the comment is stale, or the tuning was never applied.
**Worth confirming before anything else in this file is changed** — most other
observations here are downstream of that decision.

## Structure

| Lines | Section | Feeds production? |
|---|---|---|
| 19–93 | Val-date resolution, data extraction | Yes |
| 97–150 | First factor calc, Friedman significance test | No |
| 155–298 | Elbow/silhouette k selection, violin plots | No |
| 301–348 | Slope/R² comparison of clustered vs. raw factors | No |
| 360–485 | Second (production) definitions of the same functions | Yes |
| 488–521 | The actual factor build loop | Yes |
| 525–602 | Diagnostic plots, reference table comparison | No |
| 605–634 | Write to Unity Catalog | Yes |

The exploratory sections were the analysis that justified the approach. They now
run on every execution without affecting the output.

## Three functions are defined twice

`get_month_name`, `calc_factor`, and `check_cluster_size` each appear twice, and
the second definition shadows the first. The signatures differ:

| Function | First | Second |
|---|---|---|
| `calc_factor` | `(df1, group_list)` | `(df1, group_list, hcc)` — also trims columns |
| `check_cluster_size` | `(kmeans, min_size)`, returns `(kmeans, inertia)`, reads a global | `(kmeans, min_size, pivot_df)`, returns `kmeans` |

The exploratory section calls the first; production calls the second. Anyone
editing the first version to fix production behavior will change nothing.

## The file does not run as Python

Line 31 is a bare `Extract data` — a markdown cell that wasn't commented out
during notebook export. That is a syntax error, so the file cannot be imported or
executed with `python`. It works only when pasted back into a notebook.

## Guardrails that are in place

- Factors are clipped to `[0.5, 2.0]`, bounding the effect of a bad estimate
- Groups with fewer than 24 complete months are excluded from the calculation
- `k` is capped at the available sample count, with a warning
- Groups showing no variation are separated out rather than clustered
- Unmatched groups are filled with 1.0 and labeled `{HCC}_unmatched`
- A duplicate-key assertion runs immediately before the write

## Things to watch

- **Hardcoded date window.** `'2024-04-01' AND '2026-03-01'` with a
  `COUNT(DISTINCT) = 24` completeness filter. This does not roll forward — the
  window must be edited by hand each cycle.
- **Full overwrite, no versioning.** Unlike every other table in the pipeline,
  this one is written with `mode("overwrite")` and carries no `VAL_DATE`. There is
  no history and no way to reproduce which factors a past forecast used.
- **The dedup discards real variation.** Factors are computed at a nine-column
  grain, then four columns are dropped and `drop_duplicates` keeps an arbitrary
  survivor per seven-column key. With `k = 0` this is harmless (everything is 1.0);
  with clustering enabled it would silently discard distinctions that were just
  computed.
- **Two tables, similar names.** The notebook writes to
  `ohc_forecast.cs_cf_seasonality_factors` but compares against
  `cs_reference.cs_cf_seasonality_factors`. The downstream pipeline reads the
  former.
- **The Friedman test result is displayed but never used.** It tests whether
  monthly variation is statistically significant — the natural gate for whether a
  group should receive factors at all — and nothing acts on it.
