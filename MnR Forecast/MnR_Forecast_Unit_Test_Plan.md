# M&R Forecast — Unit Test Plan

Recommended unit tests for the S00–S05 pipeline, based on reading the notebook
sources in this folder. No test framework or dependencies (`pytest`, `pyspark`,
etc.) are currently installed; this document also lists the refactors needed
before any of these tests can run, and a phased roadmap for implementing them.

**Scope note:** this is a static read of the source, not a verified Databricks
run. Six items below are flagged **suspected defect** — behavior inferred from
the code that should be confirmed against a live run before treating it as
fixed.

## Where things stand

S01A, S01B and S02 carry genuinely good in-notebook validation — duplicate-grain
checks, null-factor checks, a proof that the partial adjudication month was
excluded from fitting. That machinery only fires against live Databricks
tables, after a full Spark run, and only for data that happens to exercise the
path. It catches bad *data*. It cannot catch bad *code*, because the code and
the assertions ship together and there is no way to run either without a
cluster.

Everything below is aimed at the gap that leaves: logic that is wrong in a way
real data will not reliably reveal.

### Fix before anything else: `S01B_Completion_Factors.py:36`

A filter labelled `#TEMPORARY FILTER` restricts the entire completion-factor
build to `hcc == 'PH'`. Every other claim category then misses the CF join in
S02, where `coalesce(cf, 1.0)` silently treats it as *fully complete* — raw,
immature claims published as if they were ultimate. S02's guards check that the
factor table is non-empty and unique; neither fires. This is a one-line change
with pipeline-wide consequences (see test **E6**).

## Prerequisite: nothing is importable yet

These are Databricks notebooks in `.py` source format. Three things make
`import` impossible today, and every test below assumes they are resolved.

| Obstacle | Where | Effect |
|---|---|---|
| `%run` magic | Every stage loads `S00_Config` via `# MAGIC %run` | A comment outside Databricks. Config names resolve to `NameError` under pytest. |
| Top-level execution | S01B has ~67 module-level statements and 3 functions; S02 has ~22 and none | Importing the module runs the pipeline. `spark.table()` fires at import time. |
| Implicit globals | `spark`, `display`, `dbutils` | Injected by the notebook runtime; undefined in a plain interpreter. |

S04 already shows the way out: its `RUN_PIPELINE` flag (`S04:15-18`) guards
every side-effecting cell so S05 can `%run` it for definitions only.
Generalize that pattern — move pure logic into an importable
`mnr_forecast/` package and leave the notebooks as thin drivers.

Nothing is installed locally either — no `pyspark`, `pandas`, `pytest`. Phase 1
of the roadmap starts with a virtualenv, built from tests that need none of the
heavy dependencies.

---

## Group A — Month arithmetic (3 tests, no Spark required)

Four functions in S04 do integer date math on `YYYYMM` values, and every
training window, projection horizon and backtest cutoff in the pipeline is
built from them. They are pure, have no dependencies, and are the cheapest
correctness win available. Start here on day one.

### A1 — Month stepping rolls the year correctly · **Critical**

**Target:** `S04 Train LightGBM Model Test.py:97–116` —
`_next_fin_month`, `_offset_fin_month`, `_fin_month_to_linear`

- **Validates:** December wraps to January of the next year rather than
  producing month 13; offsets and their inverses compose; the linear index
  differs by exactly the month count.
- **Edge cases:**
  - `202612 → 202701` and `202601 → 202512` (backward across the boundary)
  - Negative offsets, used by S05 to find the early-stopping split month
  - Zero offset is the identity
  - Century roll: `209912 → 210001`
- **Fixtures:** None. Parametrized integer literals only.

```python
# tests/test_month_math.py
import pytest
from mnr_forecast.dates import (
    _next_fin_month, _offset_fin_month, _fin_month_to_linear,
)

@pytest.mark.parametrize("start,expected", [
    (202601, 202602),
    (202611, 202612),
    (202612, 202701),   # year rollover
    (209912, 210001),   # century rollover
])
def test_next_fin_month_rolls_the_year(start, expected):
    assert _next_fin_month(start) == expected


@pytest.mark.parametrize("start,n,expected", [
    (202601,   0, 202601),
    (202601,  -1, 202512),   # backward across the year boundary
    (202612,   1, 202701),
    (202601,  12, 202701),
    (202607, -19, 202412),   # BACKTEST first_train_end from val_date
])
def test_offset_fin_month(start, n, expected):
    assert _offset_fin_month(start, n) == expected


def test_offset_by_one_agrees_with_next():
    for m in (202601, 202606, 202611, 202612):
        assert _offset_fin_month(m, 1) == _next_fin_month(m)


def test_linear_index_difference_is_a_month_count():
    assert _fin_month_to_linear(202701) - _fin_month_to_linear(202601) == 12
    assert _fin_month_to_linear(202601) - _fin_month_to_linear(202512) == 1


@pytest.mark.parametrize("n", range(-36, 37))
def test_offset_is_invertible(n):
    assert _offset_fin_month(_offset_fin_month(202607, n), -n) == 202607
```

### A2 — The Spark and Python month math agree · **Critical**

**Target:** `S04:164–178` — `_spark_offset_month`, `_spark_fin_to_linear` vs
their Python twins

- **Validates:** The duplicated implementations never diverge.
  `_spark_offset_month` builds the training-window start for every series;
  `_offset_fin_month` builds the projection horizon. A disagreement silently
  shifts the window relative to the forecast.
- **Edge cases:**
  - The `(col / 100).cast("int")` truncation versus Python's `divmod`
  - Spark's `%` on a negative intermediate, reachable if `train_start_lead_months`
    is ever set negative
  - Month 12 inputs, where `total % 12` lands on 0
- **Fixtures:** Session-scoped local Spark (`master("local[1]")`). One tiny
  DataFrame of boundary months.

```python
def test_spark_month_offset_matches_python(spark):
    months = [202401, 202411, 202412, 202501, 202506, 202512]
    df = spark.createDataFrame([(m,) for m in months], "fin_inc_month int")

    for lead in (0, 1, 12, 13):
        rows = (
            df.withColumn("out", _spark_offset_month(F.col("fin_inc_month"), lead))
              .collect()
        )
        for r in rows:
            assert r["out"] == _offset_fin_month(r["fin_inc_month"], lead), (
                f"lead={lead} month={r['fin_inc_month']}: "
                f"spark={r['out']} python={_offset_fin_month(r['fin_inc_month'], lead)}"
            )
```

### A3 — The training window includes its boundary months · **Recommended**

**Target:** `S04:137–161` — `apply_training_window`, and the `N_TRAIN_MONTHS`
it derives

- **Validates:** A series is kept from `first_month + 12` through
  `train_end_month` inclusive on both ends, and `N_TRAIN_MONTHS` counts what
  was actually retained.
- **Edge cases:**
  - A series with exactly 12 months — currently retains one row or zero; pin
    which
  - A series shorter than the 12-month burn-in, which drops out entirely and
    silently shrinks the model group
  - A series starting after `train_end_month`, which S05 works around with a
    `left_semi` join (`S05:169-175`) rather than fixing here
- **Fixtures:** A `make_series(start, n_months, **overrides)` builder producing
  a Spark DataFrame at the `SERIES_GROUP` grain. This becomes the workhorse
  fixture for groups D and F too.

---

## Group B — Backtest scoring (4 tests, no Spark required)

S05's accuracy numbers are what tells you whether the model works. Three of
its scoring helpers are pure Python over plain dicts, which makes them
trivially testable — and one of them has a coverage asymmetry that inflates
reported error.

### B1 — Pooled metrics are membership-weighted, not averaged · **Critical**

**Target:** `S05 Backtest LightGBM Model.py:88–97` — `member_weighted`

- **Validates:** The function pools as `sum(value × members) / sum(members)`
  across months rather than taking a mean of monthly rates — the difference is
  large whenever membership moves, which is the whole point of a
  member-weighted rollup.
- **Edge cases:**
  - Zero total membership returns `None`, never `ZeroDivisionError`
  - A month absent from the map is skipped, not counted as zero
  - An empty month list returns `None`
  - A month present with `den = 0` contributes to neither side
- **Fixtures:** Hand-built `{month: {"num_PMPM": ..., "den": ...}}` dicts. No
  Spark, no pandas.

```python
def test_member_weighted_weights_by_membership():
    monthly = {
        202602: {"num_PMPM": 100.0 * 1_000, "den": 1_000.0},   # PMPM 100, 1k members
        202603: {"num_PMPM": 200.0 * 9_000, "den": 9_000.0},   # PMPM 200, 9k members
    }
    # Weighted: 1.9M / 10k = 190. A simple average would say 150.
    assert member_weighted(monthly, [202602, 202603], "num_PMPM") == pytest.approx(190.0)


def test_member_weighted_returns_none_without_membership():
    monthly = {202602: {"num_PMPM": 0.0, "den": 0.0}}
    assert member_weighted(monthly, [202602], "num_PMPM") is None
    assert member_weighted(monthly, [], "num_PMPM") is None


def test_member_weighted_skips_months_missing_from_the_map():
    monthly = {202602: {"num_PMPM": 100.0 * 1_000, "den": 1_000.0}}
    assert member_weighted(monthly, [202602, 202603], "num_PMPM") == pytest.approx(100.0)
```

### B2 — Forecast and actual are scored over the same months · **Critical**

**Target:** `S05:196–207` — the `available` month list, applied to both
`forecast_map` and `actual_map`

- **Suspected defect:** `available` is derived from `actual_map` and
  `max_actual_month` only. If the forecast is missing a month the actuals
  have — a model group dropped by the `left_semi` filter, a segment that
  failed to train — `member_weighted` silently omits it from the predicted
  side while the actual side still includes it. The two sides are then pooled
  over different windows, and the level difference is written out as
  `*_ERROR`, indistinguishable from real model error. The header comment
  promises these are "apples-to-apples"; nothing enforces it.
- **Validates:** Either both sides cover the same months, or the mismatch
  surfaces as a coverage number rather than as error.
- **Edge cases:**
  - Forecast missing the last month of the horizon, where the actual level has
    shifted
  - Forecast missing a month entirely in the middle of the window
  - Forecast covering months the actuals do not — currently ignored, which is
    the correct direction
- **Fixtures:** Two dicts with deliberately different key sets.

```python
def test_a_month_missing_from_the_forecast_is_not_scored_as_error():
    """Both sides run at a flat 100 PMPM for two months; the actuals then step
    up in a third month the forecast never produced. Today the predicted side
    pools over 2 months and the actual side over 3, and the 100-point gap is
    reported as model error."""
    months = [202602, 202603, 202604]
    actual_map = {
        202602: {"num_PMPM": 100.0 * 1_000, "den": 1_000.0},
        202603: {"num_PMPM": 100.0 * 1_000, "den": 1_000.0},
        202604: {"num_PMPM": 400.0 * 1_000, "den": 1_000.0},
    }
    forecast_map = {m: actual_map[m] for m in months[:2]}

    scored_actual   = [m for m in months if actual_map.get(m, {}).get("den")]
    scored_forecast = [m for m in months if forecast_map.get(m, {}).get("den")]

    assert scored_actual == scored_forecast, (
        "forecast and actual pooled over different months - the difference "
        "lands in *_ERROR and reads as model inaccuracy"
    )
```

### B3 — Horizon truncation is reported, not hidden · **Recommended**

**Target:** `S05:198, 207` — `available` and
`NEXT_{h}_MONTHS_ACTUAL_MONTHS_USED`

- **Validates:** A 12-month horizon with only 3 months of realized actuals
  scores over 3 and records `MONTHS_USED = 3`. This column is the only signal
  that a headline 12-month error is really a 3-month error.
- **Edge cases:**
  - Zero available months: both sides `None`, error `None`, `MONTHS_USED = 0`
    — not a crash, not a zero error
  - A horizon fully inside the actuals, where `MONTHS_USED` equals the horizon
  - A gap in the middle of the actual months rather than truncation at the end
- **Fixtures:** `month_window()` output plus a `max_actual_month` parameter.

### B4 — Missing inputs propagate as null, never as zero error · **Recommended**

**Target:** `S05:100–104` — `abs_error`

- **Validates:** `None` on either side yields `None`. A missing forecast must
  never read as a perfect one.
- **Edge cases:** Both `None`; actual zero with a real prediction; negative
  predictions, which PMPM clamping (`S04:181-186`) should have prevented
  upstream but which the metric should still handle.
- **Fixtures:** None.

---

## Group C — Configuration contracts (4 tests, no Spark required)

S00 exists so S03 and S04 cannot drift apart. Two of them already have. These
tests are the highest value-per-line in the whole plan: pure assertions over
lists and dicts, catching failures that otherwise appear as a `KeyError` deep
inside an `applyInPandas` worker after an hour of cluster time.

### C1 — Every feature S04 trains on is a column S03 writes · **Critical**

**Target:** `S00_Config.py:182–203` — `model_feature_list` vs
`model_output_features`

- **Validates:** The feature contract S00's own comment calls the "source of
  truth for S03 + S04". S03 writes `model_output_features()`; S04 selects
  `model_feature_list(metric)`. The second must be a subset of the first, for
  both metrics.
- **Edge cases:**
  - Adding a metric-specific feature to `_metric_features` without rerunning
    S03 — caught by the subset check
  - Orphan columns S03 writes that nothing consumes, which cost storage and
    confuse readers
  - `SHARED_FEATURES` appearing twice when both metrics are requested
- **Fixtures:** None. Pure set algebra over the config module.

```python
def test_every_feature_s04_trains_on_is_written_by_s03():
    written = set(model_output_features())
    for metric in ("UTIL", "PMPM"):
        missing = set(model_feature_list(metric)) - written
        assert not missing, (
            f"S04 trains {metric} on columns S03 never writes: {sorted(missing)}"
        )


def test_s03_writes_no_orphan_feature_columns():
    written = set(model_output_features())
    consumed = set(model_feature_list("UTIL")) | set(model_feature_list("PMPM"))
    assert written - consumed == set()


def test_shared_features_are_not_duplicated():
    cols = model_output_features()
    assert len(cols) == len(set(cols))
```

### C2 — The claim-grain column is named consistently across stages · **Critical**

**Target:** `S00:50, 61–62` (`hcc`) vs `S03:83, 150` and `S04:396, 434, 492`
(`cos_hccc_cd`)

- **Suspected defect:** S00 declares the claim grain as
  `CLAIM_KEYS = ["hcc", "service_code"]`, and builds `SERIES_GROUP` and
  `MODEL_GROUP` from `hcc`. But S03 hardcodes
  `"cf_claim_level": ["cos_hccc_cd", "service_code"]` and partitions its
  target-encoding window on `cos_hccc_cd`, and all three of S04's output
  schemas declare a `cos_hccc_cd` field while its `series_group` comes from
  S00 and says `hcc`. One of these names is stale. Whichever it is, S03 is
  grouping on a different column than S04 is modelling on, and S04's
  `applyInPandas` schema does not match the frame its own `series_group`
  produces.
- **Validates:** Exactly one spelling appears anywhere in the pipeline, and
  the output schemas are derived from `SERIES_GROUP` rather than retyped.
- **Fixtures:** Source text of the stage files. Once the schemas are derived
  rather than literal (refactor R7), this becomes a structural assertion
  instead of a grep.

```python
from pathlib import Path

STAGES = Path(__file__).parents[1]

@pytest.mark.parametrize("stage", [
    "S03 Build Model Features.py",
    "S04 Train LightGBM Model Test.py",
])
def test_stages_use_the_claim_key_declared_in_s00(stage):
    """S00 CLAIM_KEYS uses 'hcc'. A stage hardcoding 'cos_hccc_cd' groups and
    shapes its output on a column the model grain does not contain."""
    assert "hcc" in CLAIM_KEYS
    source = (STAGES / stage).read_text()
    assert "cos_hccc_cd" not in source, (
        f"{stage} hardcodes cos_hccc_cd while S00 declares 'hcc' - "
        "encoding window and output schema will not match SERIES_GROUP"
    )


def test_forecast_schema_matches_the_series_group():
    # After R7: schemas derived from config, not retyped per function.
    fields = [f.name for f in _forecast_output_schema("UTIL").fields]
    for key in SERIES_GROUP:
        assert key in fields, f"series_group key {key!r} absent from output schema"
```

### C3 — Grain subset invariants hold · **Critical**

**Target:** `S00:53–62, 95, 161` — `UTIL_METRIC_KEYS`, `CF_ULTIMATE_LAG_KEYS`,
`CF_PARTIAL_FRAC_KEYS`, `MODEL_GROUP`

- **Validates:** Each of these must be a subset of `CLM_SPLIT_KEYS` or the
  downstream join fans out and every metric silently multiplies. S01A and
  S01B assert this at runtime (`S01A:42-47`, `S01B:51-56`); the assertion
  belongs in config tests where it costs milliseconds instead of a cluster
  start.
- **Edge cases:**
  - An empty key list — legal for the `ALL` fallback rung, must not be
    rejected
  - `MODEL_GROUP ⊆ SERIES_GROUP`, required for `applyInPandas` partitioning to
    be well-defined
  - Every rung of `cf_fallback_levels()` ordered most-specific first, since
    the coalesce ladder depends on that order
- **Fixtures:** None.

```python
@pytest.mark.parametrize("name,keys", [
    ("UTIL_METRIC_KEYS",     UTIL_METRIC_KEYS),
    ("CF_ULTIMATE_LAG_KEYS", CF_ULTIMATE_LAG_KEYS),
    ("CF_PARTIAL_FRAC_KEYS", CF_PARTIAL_FRAC_KEYS),
])
def test_grain_is_a_subset_of_the_split_grain(name, keys):
    assert set(keys) <= set(CLM_SPLIT_KEYS), (
        f"{name} is not a subset of CLM_SPLIT_KEYS - the join will fan out"
    )


def test_model_group_partitions_the_series_grain():
    assert set(MODEL_GROUP) <= set(SERIES_GROUP)


def test_fallback_ladder_runs_most_specific_first():
    sizes = [len(keys) for _name, keys in cf_fallback_levels()]
    assert sizes == sorted(sizes, reverse=True)
    assert cf_fallback_levels()[-1][1] == []   # ALL catches everything
```

### C4 — Table naming is total and unambiguous · **Nice-to-have**

**Target:** `S00:23–38` — `TABLES`, `table_fqn`

- **Validates:** Every key produces a three-part `catalog.schema.table` name;
  table names are distinct so two stages cannot write the same Delta table; an
  unknown key raises rather than producing a malformed name.
- **Edge cases:** A key typo; a duplicated table name across two keys; the
  `DEV_` prefix, which should be asserted deliberately so a promotion to
  production is a visible diff.
- **Fixtures:** None.

---

## Group D — Train/serve skew (4 tests — the highest-value correctness work)

S03 engineers features in Spark for training. S04's
`_recompute_last_month_features` re-engineers the same features in pandas
during the recursive forecast. They are two independent implementations of one
specification, and there are four places where they disagree. Every
disagreement means the model is scored on inputs shaped differently from the
ones it learned on — the classic silent forecasting failure, invisible in
every validation cell the pipeline has.

> **The structural fix is worth more than the tests.** These four tests pin
> real bugs and should be written, but the durable fix is refactor **R6**: one
> implementation of each feature, called from both stages. Once the Spark path
> and the pandas path are the same code, this entire class of defect stops
> being possible and these tests become regression guards rather than a
> permanent surface to maintain.

### D1 — Lag-12 missing history is encoded the same way in both paths · **Critical**

**Target:** `S03:163–167` (`F.lag(target, 12)`) vs `S04:343–346`
(`.shift(12).fillna(group mean)`)

- **Suspected defect:** S03 leaves `TARGET_{metric}_12` null when a series has
  fewer than 12 prior months — LightGBM learns a split for "missing". S04's
  forecast path fills the same column with the series mean. The model was
  trained to treat absent year-ago history as a distinct signal and is then
  handed a plausible-looking central value instead. Series near the 12-month
  burn-in boundary are affected most, which is exactly where the training
  window already makes data thin.
- **Validates:** Both paths produce the same value — null or mean — for a
  series with under 12 months of history.
- **Edge cases:**
  - Exactly 12 months of history, where the lag first becomes available
  - A series whose 12-month-ago value is itself null
  - A group mean computed over a history that already contains recursive
    predictions, which compounds the fill across projection months
- **Fixtures:** A single-series pandas frame plus its Spark twin, built from
  one `make_series()` helper so both paths see byte-identical input.

```python
def test_lag12_fallback_agrees_between_training_and_forecast(spark):
    """8 months of history: S03 emits NULL for TARGET_UTIL_12, S04 emits the
    series mean. The model is trained on one and scored on the other."""
    history = make_series(start=202601, n_months=8, target=10.0)

    training = s03_features(spark, history, metric="UTIL").toPandas()
    forecast = _recompute_last_month_features(
        _append_projected_month(history, "UTIL", CONFIG), "UTIL", CONFIG
    )

    assert pd.isna(training["TARGET_UTIL_12"].iloc[-1]) == \
           pd.isna(forecast["TARGET_UTIL_12"].iloc[0]), (
        "lag-12 missing-history handling differs between S03 and S04"
    )
```

### D2 — SLOPE_12 is the same function in both paths · **Critical**

**Target:** `S03:210–281` (`_legacy_rolling_slope_shift1`) vs `S04:354–357`
(`rolling(min_periods=2).apply(_rolling_slope)`)

- **Suspected defect:** These are materially different calculations wearing
  one column name. S03's legacy routine replaces zeros in a window with that
  window's non-zero mean and *persists the replacement into later overlapping
  windows*, requires `min_periods=3`, and skips any window containing a
  non-finite value. S04 uses `scipy.stats.linregress` over a plain shifted
  rolling window with `min_periods=2`, no zero replacement, then
  forward-fills. On any series containing zero months — common for sparse
  claim splits, which is precisely why the spine exists — they return
  different numbers.
- **Validates:** Identical slope values for identical input, including series
  with interior zeros and short histories.
- **Edge cases:**
  - A window of all zeros — S03's replacement is a no-op, S04 returns slope 0
  - Exactly 2 observations — S04 emits a slope, S03 emits NaN
  - A window containing NaN — S03 skips it entirely, S04's `min_periods`
    tolerates it
  - The stateful zero-replacement, which makes S03 order-dependent: the same
    window computed twice can differ
- **Fixtures:** numpy arrays only. No Spark needed to compare the two
  functions directly.

```python
import numpy as np, pandas as pd

@pytest.mark.parametrize("values", [
    np.array([0.0, 4.0, 0.0, 8.0, 12.0, 16.0, 20.0]),   # interior zeros
    np.array([5.0, 5.0]),                                # min_periods boundary
    np.array([0.0, 0.0, 0.0, 0.0]),                      # all zero
    np.array([1.0, 2.0, np.nan, 4.0, 5.0]),              # interior gap
])
def test_slope_definition_is_shared(values):
    s03 = _legacy_rolling_slope_shift1(values.copy(), window=12, min_periods=3)
    s04 = (pd.Series(values)
             .shift(1)
             .rolling(window=12, min_periods=2)
             .apply(_rolling_slope, raw=False)
             .to_numpy())

    np.testing.assert_allclose(s03, s04, equal_nan=True, err_msg=(
        "S04 recomputes SLOPE_12 with different zero-handling and min_periods "
        "than S03 trained on"
    ))


def test_legacy_slope_is_not_order_dependent():
    """The zero-replacement writes back into the shifted array, so calling it
    twice on the same input must still agree."""
    values = np.array([0.0, 4.0, 0.0, 8.0, 12.0, 16.0])
    first  = _legacy_rolling_slope_shift1(values.copy(), 12, 3)
    second = _legacy_rolling_slope_shift1(values.copy(), 12, 3)
    np.testing.assert_allclose(first, second, equal_nan=True)
```

### D3 — Target encodings are computed at the same grain · **Critical**

**Target:** `S03:148–155` (4-key window) vs `S04:302–304` (2-key groupby,
inside an `applyInPandas` partition)

- **Suspected defect:** S03 computes `*_ENCODED_{metric}_PRE` over a window
  partitioned by four columns — the encoding dimension, `tadmprodrollup_fnl`,
  `cos_hccc_cd` and `fin_inc_month` — across the whole dataset. S04 recomputes
  it grouping by two, the encoding dimension and `fin_inc_month`, and does so
  *inside* an `applyInPandas` partition keyed on `MODEL_GROUP`. So the
  forecast's "market encoding" is a mean over whatever markets happen to fall
  in one model group, at a coarser grain than training. The values are not
  comparable.
- **Validates:** The same partition keys on both sides, and an encoding
  computed over the same population.
- **Edge cases:**
  - A model group containing exactly one market, where the two grains
    coincide and the bug hides
  - A model group spanning many markets, where it does not
  - The encoding being computed on `TARGET` just before that column is reset
    to NaN (`S04:302-313`) — worth pinning deliberately, since it means the
    projected month's encoding reflects the *previous* month's target
- **Fixtures:** A two-market, two-product frame inside one model group — the
  minimum shape that separates the grains.

### D4 — Zero counting uses the same zero test · **Recommended**

**Target:** `S03:194–205` (`floor_near_zero` on the BF column, gated by
`row_number`) vs `S04:348–350` (exact `== 0` on TARGET)

- **Validates:** S03 snaps values under `1e-9` to zero before counting; S04
  compares exactly. A completion-factor gross-up of a near-zero month
  produces exactly the float noise `floor_near_zero` exists to absorb, so the
  two paths will disagree on sparse splits.
- **Edge cases:**
  - A value of `1e-12`: counted as zero by S03, not by S04
  - Exactly `1e-9`, the epsilon boundary itself
  - S03's `row_number() >= 3` emission gate versus S04's `min_periods=3`,
    which count different things at the start of a series
- **Fixtures:** A series seeded with `0.0`, `1e-12` and `1e-9` values.

---

## Group E — Completion factors (6 tests)

S01B is the actuarial core: a chain-ladder that turns paid-development
triangles into the factors S02 divides by. It is 1,061 lines with three
functions, and it is the stage where a quiet arithmetic error does the most
damage — a completion factor is a multiplier on every dollar and unit in the
forecast.

The extract stops around calendar day 20, so every cell on the newest
development diagonal holds a partial month of adjudication. S01B excludes that
diagonal from link-ratio fitting (`S01B:453`) and instead interpolates it back
in at the end using the measured intra-month fraction `f`. Tests E1 and E3 pin
those two halves.

### E1 — Chained link ratios invert to the right completion factors · **Critical**

**Target:** `S01B:650–691` — the `cdf` window, `completion_factor_raw`, the
cap and the monotonic pass

- **Validates:** The central actuarial identity, on a triangle small enough to
  verify by hand: `CDF(d) = Π link_ratio(d..ultimate)` and `CF(d) = 1 / CDF(d)`,
  with `CF = 1.0` exactly at the ultimate lag. The implementation computes the
  product as `exp(sum(log(...)))` over a descending-lag window because Spark
  has no product aggregate — worth testing precisely because it is not the
  obvious formula.
- **Edge cases:**
  - A link ratio of exactly `1.0` at ultimate, which must leave the CDF
    unchanged
  - A link ratio of `0`, where `log(0) = -inf` collapses the CDF to zero and
    the factor to infinity — `CF_LINK_RATIO_FLOOR = 1.0` is the only guard, so
    test that removing it breaks
  - Floating-point drift in `exp(sum(log))` versus a direct product over a
    deep triangle
  - Monotonicity: `CF_ENFORCE_MONOTONIC` applies a running max, so a dip
    mid-curve must be flattened upward, not smoothed
- **Fixtures:** A hand-built 3-lag triangle with round link ratios, so every
  expected value is exact.

```python
def test_completion_factors_invert_the_chained_link_ratios():
    """Link ratios 2.0, 1.5, 1.0 at lags 0, 1, 2 (ultimate).
         CDF(0) = 2.0 * 1.5 * 1.0 = 3.0  ->  CF(0) = 1/3
         CDF(1) =       1.5 * 1.0 = 1.5  ->  CF(1) = 2/3
         CDF(2) =             1.0 = 1.0  ->  CF(2) = 1.0
    """
    curve = chain_to_completion_factors(
        pd.DataFrame({"lag_months": [0, 1, 2], "link_ratio": [2.0, 1.5, 1.0]})
    )
    assert curve["cdf"].tolist() == pytest.approx([3.0, 1.5, 1.0])
    assert curve["completion_factor"].tolist() == pytest.approx([1/3, 2/3, 1.0])


def test_completion_factor_is_exactly_one_at_the_ultimate_lag():
    curve = chain_to_completion_factors(
        pd.DataFrame({"lag_months": [0, 1, 2], "link_ratio": [1.8, 1.2, 1.0]})
    )
    assert curve["completion_factor"].iloc[-1] == pytest.approx(1.0)


def test_link_ratio_floor_prevents_an_infinite_factor():
    """cdf = exp(sum(log(link_ratio))). A zero ratio makes log(0) = -inf and
    the factor infinite. CF_LINK_RATIO_FLOOR = 1.0 is the whole defence."""
    curve = chain_to_completion_factors(
        pd.DataFrame({"lag_months": [0, 1], "link_ratio": [0.0, 1.0]})
    )
    assert np.isfinite(curve["completion_factor"]).all()
    assert (curve["completion_factor"] > 0).all()


def test_monotonicity_lifts_dips_rather_than_smoothing():
    curve = chain_to_completion_factors(
        pd.DataFrame({"lag_months": [0, 1, 2, 3],
                      "link_ratio": [2.0, 1.0, 1.4, 1.0]}),
        enforce_monotonic=True,
    )
    cf = curve["completion_factor"].tolist()
    assert cf == sorted(cf), "completion factors must not decrease with lag"
```

### E2 — Partial-month interpolation stays between its endpoints · **Critical**

**Target:** `S01B:740–753` — `completion_factor_applied` =
`CF[d-1] + f × (CF[d] − CF[d-1])`

- **Validates:** With `f ∈ [0, 1]` the interpolated factor always lands in
  `[CF[d-1], CF[d]]`. This is the invariant that makes the whole partial-month
  correction safe, and it is what S02 actually divides by — the factor
  applied to real dollars.
- **Edge cases:**
  - `f = 0` and `f = 1`, the exact endpoints
  - Lag 0, where `CF[d-1]` is coalesced to `0.0` (`S01B:688-691`) — nothing
    adjudicated before the month opens
  - The `CF_FLOOR = 0.05` re-application afterwards, which can push the result
    back *above* `CF[d-1]` and technically breach the invariant
  - A row where `is_partial_lag` is false, which must pass the full-month
    factor through untouched
- **Fixtures:** Hypothesis over `f`, `CF[d-1]`, `CF[d]`. The notebook already
  asserts this on live data (`S01B:918-933`); a property test proves it for
  inputs the data has not produced yet.

```python
from hypothesis import given, assume, strategies as st

@given(
    cf_prev=st.floats(min_value=0.0, max_value=1.0),
    cf_full=st.floats(min_value=0.0, max_value=1.0),
    f=st.floats(min_value=0.0, max_value=1.0),
)
def test_interpolated_factor_lands_between_its_endpoints(cf_prev, cf_full, f):
    assume(cf_prev <= cf_full)
    applied = interpolate_partial_month(cf_prev, cf_full, f)
    assert cf_prev - 1e-9 <= applied <= cf_full + 1e-9


def test_floor_reapplication_does_not_breach_the_lower_endpoint():
    """CF_FLOOR is re-applied after interpolation (S01B:751-753). When both
    endpoints sit below the floor the result is lifted above CF[d-1], which
    the notebook's own validation would flag. Pin the intended behaviour."""
    applied = interpolate_partial_month(cf_prev=0.01, cf_full=0.03, f=0.5)
    assert applied == pytest.approx(CF_FLOOR)


def test_full_month_rows_pass_the_factor_through():
    assert interpolate_partial_month(0.4, 0.9, f=1.0) == pytest.approx(0.9)
```

### E3 — The newest diagonal never reaches the fitting cohort · **Critical**

**Target:** `S01B:447–454` — the `current_lag > lag_months + 1` filter on
`links_obs`

- **Validates:** Every link-ratio numerator comes from an adjudication month
  strictly earlier than the paid-through month. If a partial month leaks into
  the fit, every factor is biased low and the whole book is under-reserved.
- **Edge cases:**
  - An incurred month whose `current_lag` equals `lag + 1` exactly — the
    boundary the filter excludes
  - A paid-through date landing on the last day of a month, where the
    "partial" month is actually complete and the exclusion costs a full
    diagonal of data
  - An incurred month more mature than its ultimate lag, which has no row at
    `lag == current_lag`
- **Fixtures:** A triangle with a known paid-through date. The notebook
  already derives this check from the data (`S01B:887-900`) rather than
  trusting the filter — a good instinct that should be promoted to a unit
  test with a constructed triangle.

### E4 — The trimmed mean trims at the right thresholds · **Recommended**

**Target:** `S01B:510–571` — `build_level_link_ratios`

- **Validates:** With `n_obs < CF_MIN_OBS_FOR_TRIM` (4) the mean is
  untrimmed; at or above it, `CF_TRIM_COUNT` (1) observation is dropped from
  each tail. The dual `row_number` construction — `rn_low` ascending and
  `rn_high` descending — is subtle enough to deserve a direct test.
- **Edge cases:**
  - `n_obs = 3` (untrimmed) and `n_obs = 4` (trims to 2) — the exact boundary
  - Tied link ratios: both rankings tiebreak on `fin_inc_month` ascending, so
    they are not exact reverses and the trim can drop the wrong observation
  - `n_obs = 2` with trimming somehow enabled, which would empty the group
  - The credibility gate: `ldf_nobs >= CF_MIN_OBS` counts rows *after* the
    trim, so a group of 4 becomes 2 and fails a threshold of 3, falling
    through a rung unexpectedly
- **Fixtures:** A small frame of link observations with a deliberate outlier
  at each tail.

### E5 — Ultimate-lag overrides are honoured or rejected, never silently clamped · **Recommended**

**Target:** `S01B:326–364` — `CF_ULTIMATE_LAG_OVERRIDES` resolution and the
`least/greatest` guard rails

- **Suspected defect:** S00's own documented example is
  `{("PHYSICIAN",): 3, ("INPATIENT",): 18}`, but the guard rail
  `greatest(CF_ULTIMATE_LAG_MIN=12, ...)` silently raises 3 to 12. An analyst
  setting a documented override gets a different number with no warning.
  Separately, the override frame takes its column count from `_ovr_rows[0]`
  only (`S01B:331`), so a dict mixing key-tuple lengths mis-maps or throws.
- **Validates:** An out-of-range override either applies or raises — not
  quietly becomes something else. Mixed-arity override dicts are rejected
  with a clear message.
- **Edge cases:** Override below `MIN`; above `MAX`; empty dict (the current
  default path); a key matching no category in the triangle.
- **Fixtures:** Parametrized override dicts.

### E6 — No category filter ships in S01B · **Critical**

**Target:** `S01B:35–36` — `#TEMPORARY FILTER` /
`filter(F.col("hcc") == 'PH')`

- **Suspected defect:** Live in the current source. Restricts the
  completion-factor build to one category; every other category then misses
  the S02 join and is coalesced to a factor of `1.0`, publishing immature
  claims as complete.
- **Validates:** The filter is gone, and — more usefully — that S02 refuses
  to proceed when the factor table does not cover every category present in
  the claims extract. The second check is what makes the first one
  unnecessary.
- **Edge cases:** A category legitimately absent from claims in one vintage;
  a category present in claims but with no credible triangle, which should
  fall through the ladder to `ALL` rather than vanish.
- **Fixtures:** Source text for the guard; a two-category spine for the
  coverage assertion.

```python
def test_s01b_ships_no_category_filter():
    source = (STAGES / "S01B_Completion_Factors.py").read_text()
    assert "TEMPORARY FILTER" not in source
    assert 'F.col("hcc")==' not in source.replace(" ", "")


def test_s02_rejects_a_factor_table_missing_a_claim_category(spark):
    """The real guard: coalesce(cf, 1.0) is correct for a mature month and
    silently wrong for an immature one. Coverage must be asserted, not assumed."""
    claims = make_claims(spark, categories=["PH", "IP"])
    factors = make_factors(spark, categories=["PH"])          # IP missing

    with pytest.raises(ValueError, match="categories without completion factors"):
        assert_factor_coverage(claims, factors)
```

---

## Group F — Spine construction and data quality (3 tests)

S02 is 231 lines of top-level Spark with no functions at all, and it computes
every model target. Two divisions there can produce infinities that travel
all the way into LightGBM.

### F1 — Zero membership cannot produce an infinite target · **Critical**

**Target:** `S02_Preprocessing.py:176–179` — `util_k`, `pmpm`, `bf_estimate_*`

- **Suspected defect:** `util_k = util * 12000 / sum_member_cnt` with no zero
  guard. The spine inner-joins membership, which the comments treat as proof
  that members are positive — but that join only requires a *row*, and an
  enrollment group whose monthly counts sum to zero survives it. The result
  is `inf`, which becomes `TARGET_UTIL` in S03. S03's `nan_inf_to_null` is
  applied to encoding inputs and the variance input, never to the target
  itself, so the infinity reaches training.
- **Validates:** No row leaves S02 with a null, NaN or infinite target,
  whatever the membership column contains.
- **Edge cases:**
  - `sum_member_cnt = 0` exactly
  - Negative membership from a retro-termination adjustment, which flips the
    sign of the metric
  - `cf_util = 0`, giving `bf_estimate_util_k = inf` — S01B's validation
    rejects non-positive factors upstream, but S02 re-derives nothing and
    trusts the join
  - A missing CF join, coalesced to `1.0` (see F2)
- **Fixtures:** A three-row spine: healthy, zero-membership,
  negative-membership.

```python
def test_zero_membership_never_reaches_the_model_target(spark):
    spine = spark.createDataFrame(
        [
            ("M1", 202601, 5.0,    0.0, 1.0),   # zero membership
            ("M2", 202601, 5.0, 1000.0, 1.0),   # healthy
            ("M3", 202601, 5.0,  -50.0, 1.0),   # retro-term
        ],
        "market_fnl string, fin_inc_month int, util double, "
        "sum_member_cnt double, cf_util double",
    )
    out = derive_spine_metrics(spine)

    bad = out.filter(
        F.col("util_k").isNull()
        | F.isnan("util_k")
        | (F.abs(F.col("util_k")) == float("inf"))
    )
    assert bad.count() == 0, (
        "zero or negative membership leaked a non-finite value into TARGET_UTIL"
    )
```

### F2 — Joins stay 1:1 and a missing factor is not treated as complete · **Critical**

**Target:** `S02:59–70, 145–156, 172–175` — the util-metric and CF joins, and
`coalesce(cf, 1.0)`

- **Validates:** A duplicated key in either lookup table multiplies claim
  rows, silently inflating every downstream total. S02 guards this with
  row-count-versus-distinct checks; those guards should be tested with a
  deliberately duplicated fixture rather than trusted. Separately:
  `coalesce(cf, 1.0)` means a missed CF join is indistinguishable from a
  fully mature month.
- **Edge cases:**
  - A duplicate in `util_metric` — the guard at `S02:66-70` should raise
  - A duplicate in the CF table at `(split, month, measure)` — guard at
    `S02:152-156`
  - An immature month with no factor row, which must not coalesce to 1.0
  - An empty factor table, which raises today — confirm the message names
    S01B
- **Fixtures:** Lookup tables with an injected duplicate key and an injected
  missing key.

### F3 — The spine is contiguous and keeps zero-utilization months · **Recommended**

**Target:** `S02:82–130` — the cross-join month axis and the membership
inner join

- **Validates:** The spine's whole purpose: every split gets an unbroken
  month series so lag, rolling and zero-count features are not corrupted by
  sparse claims. A month with members but no claims must appear with
  `util = 0`, not be absent.
- **Edge cases:**
  - A split whose claims skip a month entirely
  - A split whose enrollment group has no members in some months — correctly
    dropped, and the series is then genuinely discontinuous
  - A single-month dataset, where `MIN_MONTH == MAX_MONTH` and the
    `sequence()` call must still emit one row
  - The `fillna(0)` ordering: it runs before the CF joins (`S02:171`), so a
    zero-claim month gets `util = 0` and then a factor — confirm that is
    intended rather than incidental
- **Fixtures:** Two splits, one with a deliberate month gap, plus a
  membership frame covering all months.

---

## Group G — Utilization-metric assignment (2 tests)

S00's three `util_*` helpers build nested `when/otherwise` chains by
iterating `CF_UNIT_COLUMNS` in reverse. The construction is clever and the
priority semantics are not obvious from reading it — which is exactly the
profile of code that should be pinned.

### G1 — Priority order picks the first positive column · **Recommended**

**Target:** `S00:225–249` — `util_priority_expr`, `util_populated_count_expr`,
`util_pick_expr`

- **Validates:** The first column in `CF_UNIT_COLUMNS` with a positive total
  wins, and `util_pick_expr` returns that column's value. The `reversed()`
  loop means the first-listed column ends up outermost in the chain —
  correct, but only readable by testing it.
- **Edge cases:**
  - All columns zero: source is null, status `NO_POSITIVE_UNITS`, picked
    value null — this is the case that silently zeroes a split's utilization
  - Several columns positive: highest priority wins, status
    `ASSIGNED_MULTIPLE_POSITIVE_UNITS`
  - Exactly zero versus a small positive, since the test is `> 0` not `!= 0`
  - Negative values, which must not count as positive
  - `util_source_col` naming a column absent from the frame
- **Fixtures:** One row per scenario, with all six unit columns present.

```python
@pytest.mark.parametrize("row,expected_col,expected_value", [
    # CF_UNIT_COLUMNS order: tadm_hcta_util, admits, tadm_units,
    #                        visits, srvc_unit_cnt, adj_srvc_unit_cnt
    ({"sum_tadm_hcta_util": 5.0, "sum_admits": 9.0}, "sum_tadm_hcta_util", 5.0),
    ({"sum_admits": 9.0, "sum_visits": 3.0},         "sum_admits",         9.0),
    ({"sum_visits": 3.0},                            "sum_visits",         3.0),
    ({},                                             None,                 None),
    ({"sum_admits": -4.0, "sum_visits": 3.0},        "sum_visits",         3.0),
    ({"sum_admits": 0.0,  "sum_visits": 3.0},        "sum_visits",         3.0),
])
def test_first_positive_unit_column_wins(spark, row, expected_col, expected_value):
    df = spark.createDataFrame([_fill_unit_columns(row)])
    got = (
        df.withColumn("util_source_col", util_priority_expr())
          .withColumn("picked", util_pick_expr())
          .collect()[0]
    )
    assert got["util_source_col"] == expected_col
    assert got["picked"] == expected_value
```

### G2 — Metric assignment is stable across valuation dates · **Nice-to-have**

**Target:** `S01A_Utilization_Metric.py:234–248` — the drift check

- **Validates:** A claim key whose assigned metric flips between vintages
  produces a level shift in every series it covers. The notebook displays
  these for review; the test turns the review into an assertion with an
  explicit allowlist for known, accepted flips.
- **Edge cases:** A genuinely new claim key with no prior vintage; a key that
  drops out; a flip driven by one month of new data crossing the `> 0`
  threshold.
- **Fixtures:** Two vintages of the assignment table differing in one key.

---

## Group H — Writes, determinism and explanations (3 tests)

### H1 — Idempotent writes replace only their own slice · **Critical**

**Target:** `S00:266–281` — `write_to_catalog`; `S04:463–475` —
`write_scenario_table`

- **Validates:** When the table exists, `replaceWhere` is set with the exact
  predicate; on first write it is omitted so the table can be created.
  Getting this wrong replaces the entire table — every prior vintage — on a
  routine rerun. It is fully testable with a mock `spark` and a fake writer;
  no Spark session needed.
- **Edge cases:**
  - Table does not exist: no `replaceWhere`, mode still `overwrite`
  - A scenario predicate combining `VAL_DATE` and `TRAIN_END_MONTH`
    (`S04:471-473`)
  - Quoting: S01A/S01B/S02 emit `DATE('2026-07-01')`, S04/S05 emit a bare
    quoted string — these are different column types, see H2
  - `mergeSchema` staying on, which is what lets a new feature column appear
    without a manual migration
  - Decimal casting running before the write, so no `decimal` column ever
    lands in a published table
- **Fixtures:** `unittest.mock.Mock` for `spark` and the writer chain.

```python
from unittest.mock import MagicMock

def test_existing_table_is_written_with_replace_where():
    spark = MagicMock()
    spark.catalog.tableExists.return_value = True
    df = _fake_df(decimal_columns=[])

    write_to_catalog(spark, df, "cat.sch.tbl", "VAL_DATE = DATE('2026-07-01')")

    writer = df.write.format.return_value.option.return_value
    writer.option.assert_called_once_with(
        "replaceWhere", "VAL_DATE = DATE('2026-07-01')"
    )
    writer.option.return_value.mode.assert_called_once_with("overwrite")


def test_first_write_omits_replace_where():
    spark = MagicMock()
    spark.catalog.tableExists.return_value = False
    df = _fake_df(decimal_columns=[])

    write_to_catalog(spark, df, "cat.sch.tbl", "VAL_DATE = DATE('2026-07-01')")

    writer = df.write.format.return_value.option.return_value
    assert "replaceWhere" not in [c.args[0] for c in writer.option.call_args_list]
```

### H2 — VAL_DATE has one type across the pipeline · **Recommended**

**Target:** `S01A:95`, `S01B:1053`, `S02:194`, `S03:292` (`cast("date")`) vs
`S04:416` and `S05:229` (string)

- **Suspected defect:** The upstream tables write `VAL_DATE` as a `date`;
  S04's `add_run_metadata` stamps `F.lit(config["val_date"])`, a string, and
  S05 declares `StructField("VAL_DATE", StringType())` outright. The
  forecast, SHAP and backtest tables therefore carry a string partition
  column while everything upstream carries a date. Each stage is internally
  consistent, so nothing fails — until someone joins across the boundary or
  filters with the wrong literal form.
- **Validates:** Every published table declares `VAL_DATE` with the same
  type, and the `replaceWhere` predicate matches that type.
- **Edge cases:** A `replaceWhere` of `VAL_DATE = '2026-07-01'` against a date
  column; `TRAIN_END_MONTH` as int versus string in the same predicate.
- **Fixtures:** The schema each stage builds, asserted without writing
  anything.

### H3 — Adjusted SHAP values sum to the prediction · **Recommended**

**Target:** `S04:505–538` — `_adjusted_shap_for_segment`

- **Validates:** The rescale exists precisely so the explanation ties out:
  per row, the adjusted SHAP values must sum to
  `predicted − exp(expected_value)`. If that stops holding, the SHAP table is
  decorative and anyone reading it is misled about what drove a forecast.
- **Edge cases:**
  - `total_feature_impact == 0`, where `.replace(0, np.nan)` deliberately
    yields null SHAP rather than dividing by zero — pin that it is null, not
    zero or infinite
  - `expected_value` arriving as a list or ndarray from `TreeExplainer`,
    which the code already flattens
  - The `exp()` undoing the Tweedie log link — the additivity only holds on
    the natural scale
  - The `round(4)` applied to `*_PREDICTED` after the rescale, so additivity
    holds against the unrounded value; set the tolerance accordingly
- **Fixtures:** A stub explainer returning fixed SHAP values and a known
  `expected_value` — no LightGBM training, no `shap` dependency in the test.

```python
def test_adjusted_shap_sums_to_prediction_minus_expected(monkeypatch):
    monkeypatch.setattr(shap, "TreeExplainer", lambda _m: StubExplainer(
        values=np.array([[0.4, 0.1, -0.2]]), expected=np.log(3.0),
    ))
    frame = _projected_frame(target=5.0, n_features=3)

    explained = _adjusted_shap_for_segment(frame, StubModel(), "PMPM", CONFIG)

    shap_cols = [f"{f}_SHAP" for f in CONFIG["features"]["PMPM"]]
    total = explained[shap_cols].sum(axis=1)
    assert total.iloc[0] == pytest.approx(5.0 - 3.0)          # predicted - exp(E[f])
    assert explained["EXPECTED_VALUE"].iloc[0] == pytest.approx(3.0)


def test_zero_total_impact_yields_null_shap_not_infinity(monkeypatch):
    """SHAP values summing to zero would divide by zero; the guard is
    total_feature_impact.replace(0, np.nan)."""
    monkeypatch.setattr(shap, "TreeExplainer", lambda _m: StubExplainer(
        values=np.array([[0.3, -0.3, 0.0]]), expected=np.log(3.0),
    ))
    explained = _adjusted_shap_for_segment(
        _projected_frame(target=5.0, n_features=3), StubModel(), "PMPM", CONFIG
    )
    shap_cols = [f"{f}_SHAP" for f in CONFIG["features"]["PMPM"]]
    assert explained[shap_cols].isna().all(axis=None)
```

### H4 — Training is reproducible, or the docstring stops claiming it is · **Nice-to-have**

**Target:** `S04:199–220` — `build_lightgbm_params`

- **Validates:** The docstring says "the seed + deterministic + single-thread
  settings make training reproducible so the SHAP pass explains the same
  model the forecast pass used" — but `deterministic` and `num_threads` are
  both commented out (`S04:218-219`), while `feature_fraction` and
  `bagging_fraction` randomize. Since the single-pass refactor trains once
  per group, the forecast/SHAP consistency the docstring worries about is no
  longer at risk; run-to-run reproducibility is. Decide which you want and
  make code and comment agree.
- **Edge cases:** Two trainings on identical input producing identical
  predictions; the same on multiple threads; whether `best_iteration` is
  stable, since early stopping drives it.
- **Fixtures:** A small deterministic training frame. This is the one test
  here that genuinely needs LightGBM — keep it in a `@pytest.mark.slow` tier.

---

## What has to change to make this testable

Ordered by how much testing each one unblocks. R1–R3 are required before a
single test in groups A–C can run; R6 removes an entire defect class rather
than testing around it.

| # | Change | Why it matters | Unblocks |
|---|---|---|---|
| R1 | Extract pure logic into an importable `mnr_forecast/` package | Month math, scoring helpers, SHAP rescaling, the slope routine and chain-ladder arithmetic have no Spark dependency and no reason to live in a notebook. | All |
| R2 | Replace `%run "./S00_Config"` with a real import | The magic comment is the single reason config names are unresolvable under pytest. | A–H |
| R3 | Wrap S01A, S01B and S02 top-level code in functions taking `(spark, config)` | S01B has ~67 module-level statements and 3 functions; S02 has none. Importing either runs the pipeline. | E, F, G |
| R4 | Delete the S01B category filter (line 36) | Live defect. Suppresses completion factors for every category but `PH`. | E6 |
| R5 | Parameterize the hardcoded valuation dates | `"2026-07-01"` is a literal in S03:372, S04:636 and S05:40. Tests cannot vary the vintage, and neither can a scheduled job. | A3, F, E |
| R6 | Unify the S03 and S04 feature implementations | One spec, two implementations, four known disagreements. A shared implementation makes group D's whole failure mode impossible rather than merely detected. | D1–D4 |
| R7 | Derive the S04 output schemas from `SERIES_GROUP` | Three functions retype the same eleven `StructField`s by hand, and they already disagree with S00 on the claim-key name. | C2 |
| R8 | Make `check()` return results instead of printing | Duplicated verbatim in S01A:111 and S01B:820. As a shared helper returning a result object, the existing validations become assertable. | E, F, G |
| R9 | Split `add_metric_features` into one function per feature family | Encodings, lags, rolling variance and zero counts are four independent behaviours in one 74-line function, testable only through a full Spark run. | D3, D4 |

---

## Roadmap

Four phases, ordered so each one ships working tests before the next begins.
The first needs no Spark, no cluster and no LightGBM — it runs on a laptop in
under a second and covers eleven cases, four of them over code that is
currently wrong.

### Phase 1 — First, half a day: pure Python, zero infrastructure

Create a virtualenv and install `pytest` alone. Do R1 and R2 for the smallest
possible surface: move the month-math functions, the S05 scoring helpers and
`S00_Config`'s constants into `mnr_forecast/`. Write groups A1, B, C.

- Fix the S01B category filter (R4) the same morning — it is one line and it
  is affecting live output
- Resolve the `hcc` / `cos_hccc_cd` question before writing C2, since the
  test encodes the answer

**Ships:** 11 tests · A1, B1–B4, C1–C4 · runs in < 1s · catches 2 live defects

### Phase 2 — Week 1: local Spark session

Add `pyspark` and a session-scoped `conftest.py` fixture on `local[1]` with
`spark.sql.shuffle.partitions = 1`. Use `pyspark.testing.assertDataFrameEqual`
— it ships with Spark 3.5, so no `chispa` dependency. Build the
`make_series()` and `make_claims()` fixtures here; groups D and F both depend
on them.

- A2 and A3 first — they exercise the fixture itself
- Then F1 and F2, the division and fan-out guards
- G1 last; it is the cheapest but the least urgent

**Ships:** 7 tests · A2, A3, F1–F3, G1, G2 · ~30s with session reuse

### Phase 3 — Week 2, the payoff: completion factors and train/serve skew

Do R3 and R6 first: S01B's chain-ladder math and the shared feature
implementation. This is the largest refactor in the plan and the one that
pays for itself, because group D's four tests stop being a maintenance
surface and become regression guards over a single implementation.

- E1 and E2 on hand-built triangles — small enough to verify with a
  calculator
- Add `hypothesis` for E2's interpolation invariant
- D1–D4 against the unified implementation, not the two current ones

**Ships:** 10 tests · D1–D4, E1–E6 · resolves 4 suspected defects

### Phase 4 — Ongoing: contracts, determinism, CI

The remaining write-path and explanation tests, plus the pieces that only pay
off once the suite runs automatically. Wire it into the linting workflow
already drafted in `Misc_Files/Linting and Formatting.yaml`.

- H1–H3; mark H4 `slow` and exclude it from the default run
- A schema-contract test per published table, so a column rename fails CI
  rather than a downstream read
- One golden-data integration test: a ~50-row synthetic extract through
  S01A → S02, asserting stable output. This is the only test that needs the
  full stack, and it is the last one worth writing, not the first

**Ships:** 4+ tests · H1–H4 · plus CI gating on every push

---

Total across all four phases: **32 tests**, of which **18 need no Spark
session at all**. The ordering is deliberate — phase 1 alone covers the
backtest scoring that tells you whether the model works, and the config
contract that keeps S03 and S04 from drifting further apart than they already
have.

## Assumptions / notes

- Based solely on reading the notebook sources in this folder at commit
  `b32e484`; no Databricks run was performed.
- The external source tables under `prod_tadm.mr_cos_prod_event` were not
  inspected — behaviors attributed to real data are inferred from the code
  that reads it.
- The six items marked **suspected defect** should be confirmed against a
  live run before being treated as fixed.

<sub>Prepared with Claude Code.</sub>
