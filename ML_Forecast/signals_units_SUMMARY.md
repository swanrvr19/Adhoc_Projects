# signals_units.py — Summary

## What it is

The feature engineering stage of the pipeline. It takes completed, valued claims
data and produces the model-ready feature matrix that `lightgbm_train` consumes.

Unlike the notebooks in this directory, this is a proper Python module — private
helpers plus a single public `run()` function, invoked by `run_stage.py` as the
`signals_units` stage.

## What it does

For one valuation date, across the entire book:

1. Loads valued claims and converts Bornhuetter-Ferguson estimates from rates
   back to counts and dollars.
2. Aggregates to the modeling grain and computes normalized targets
   (`TARGET_UTIL`, `TARGET_PMPM`).
3. Builds lag, rolling, and target-encoding features for both metrics.
4. Merges in calendar, population demographics, risk scores, and seasonality
   factors.
5. Selects the final column set and writes it, keyed on `VAL_DATE`.

## The feature set

Forty-three columns, in four families, built symmetrically for `UTIL` and `PMPM`:

| Family | Examples | Captures |
|---|---|---|
| Target encodings | `MARKET_ENCODED_*`, `PRODUCT_ENCODED_*`, `CATEGORY_ENCODED_*` | Rolling historical mean for that dimension |
| Lags | `TARGET_*_1`, `_2`, `_3`, `_12` | Recent momentum plus a year-over-year anchor |
| Rolling statistics | `COUNT_ZEROS_*`, `VARIANCE_12_MO_*`, `SLOPE_12_*` | Sparsity, volatility, trend |
| Exogenous | `MM`, `WORKDAY`, `MONTH`, demographics, `PROSP_RISK`, `SEASONAL_FACTOR_*` | Exposure, calendar, population mix, risk |

Each encoding is a two-step build: a `_PRE` column holding the raw group mean,
then a 12-month rolling mean of that column shifted by one period. The shift is
what prevents a month's own target from leaking into its own feature.

## Notable engineering

**Vectorized rolling computation.** Rather than pandas `.apply()`, the module
builds integer position arrays per group once and dispatches to numpy kernels
(`rolling_mean_shift1`, `rolling_slope_shift1`, and so on) from
`numpy_time_series_utils`. This is a meaningfully faster implementation of the
same logic that `LIGHTGM_TRAIN` performs row-wise.

**Input validation up front.** `assert_val_date_rows` fails immediately if the
source has no rows for the requested valuation date, rather than writing an empty
result.

**Duplicate detection on seasonality.** The factor table is checked for duplicate
keys before joining, raising rather than silently fanning out the row count.

**Near-zero flooring.** Values below `1e-9` are snapped to exactly zero before
zero-counting, so floating-point residue isn't miscounted as a real value.

## Inputs and output

| Table | Role |
|---|---|
| `source_table` | Valued claims with BF estimates (from the `valuation` stage) |
| `seasonality_factors_table` | Per-metric monthly normalization factors |
| `calendar_table` | Workday counts and month numbers |
| `population_table` | Member demographics by age, sex, race, dual status, rural, ACO |
| `risk_table` | Prospective risk scores |
| `target_table` | Output — the model-ready signal table |

All names come from `pipeline_config.yaml`; nothing is hardcoded.

## Interface

```python
run(spark, run_val_date, source_table, seasonality_factors_table,
    calendar_table, population_table, risk_table, target_table,
    write_catalog, write_schema) -> dict
```

Returns `{'status': 'SUCCESS', 'target_table': ..., 'rows_written': ...}` —
the contract `run_stage.py` expects.

## Things to watch

- **`_add_rolling_quarter_fields` produces five columns that nothing consumes.**
  They appear in neither the feature list nor the output selection. Five
  groupby-rolling operations of pure waste.
- **No division guards.** `UTIL_K` and `PMPM` divide by `MM` with no zero check,
  unlike `final_output`, which guards every denominator.
- **Population and risk are not stratified by `IS_DUAL`.** Both merges drop that
  key, so dual and non-dual rows within a product-month receive identical
  demographic values. This is documented in comments, but it does mean those
  features carry no dual-specific signal.
- **No post-merge row count check.** A fan-out in the population or risk join
  would silently inflate the training set.
- **Whole-book memory footprint.** `.toPandas()` pulls every HCC at once — a
  larger footprint than `LIGHTGM_TRAIN`, which processes one HCC at a time.
- **`SEASONAL_FACTOR_UTIL` and `SEASONAL_FACTOR_PMPM` are currently constant
  1.0** as a consequence of the upstream `SEASONALITY_ADJUSTMENT` configuration.
  Constant features contribute nothing to the model. See that file's write-up.
