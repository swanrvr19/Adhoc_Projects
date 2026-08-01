# SEASONALITY_ADJUSTMENT — Detailed Walkthrough

A section-by-section reading of the seasonality factor notebook.

**Read this first:** the file mixes exploratory analysis with the production build
path, and the two are interleaved rather than separated. Sections below are marked
**[PRODUCTION]** or **[EXPLORATORY]** so it's clear which code affects the
published table.

---

## 1. Imports **[PRODUCTION]**

```python
import calendar, pandas as pd, numpy as np
import matplotlib.pyplot as plt, seaborn as sns, plotly.express as px
from scipy.stats import linregress, friedmanchisquare
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import warnings; warnings.filterwarnings("ignore")
```

Three plotting libraries — matplotlib, seaborn, plotly — of which seaborn is
imported and never used. The plotting stack is a tell that this file's center of
gravity is analysis rather than a pipeline stage.

`warnings.filterwarnings("ignore")` is blanket-applied, the same pattern as
`LIGHTGM_TRAIN`. Given how much pandas chained-assignment happens below, this is
suppressing warnings that would be worth seeing.

---

## 2. Valuation date resolution **[PRODUCTION]**

```python
try:
    val_date = dbutils.jobs.taskValues.get(taskKey="ohc_completed_combined", key="val_date")
    print(f"VAL_DATE from task value: {val_date}")
except AttributeError:
    val_date = (
        spark.sql("SELECT MAX(CAST(VAL_DATE AS STRING)) FROM ra_analytic_dev.ohc_forecast.ohc_completed_combined")
        .collect()[0][0]
    )
    print(f"VAL_DATE from table MAX: {val_date}")
```

Two-tier resolution — the upstream task value when running as part of a job,
falling back to the table's maximum for interactive use. The same dual-mechanism
thinking as `run_stage.py`'s `model_id` handoff, and the print statements make the
resolved path visible in the log.

The catch is narrowed to `AttributeError`, which is the specific failure when
`dbutils.jobs` is unavailable outside a job context. Better than a bare `except`.

One consequence worth naming: the interactive fallback takes `MAX(VAL_DATE)`,
which is whatever happens to be newest at that moment. Two people running this
notebook on different days can silently produce factors from different vintages —
and since the output table has no `VAL_DATE` column, there's no way to tell after
the fact.

---

## 3. Line 31 — a syntax error **[BROKEN]**

```python
Extract data
```

A markdown cell that wasn't commented out during notebook export. As Python, two
juxtaposed names are a syntax error, so **this file cannot be imported or run with
`python`**. It executes only when pasted back into a notebook, where that line was
a heading.

This matters beyond tidiness: it means the file can't be linted, imported by a
test, or invoked from `run_stage.py`. Prefixing it with `#` is a one-character fix
and a prerequisite for any of that.

---

## 4. Data extraction **[PRODUCTION]**

```sql
WITH included AS (
    SELECT HCC, MARKET, PRODUCT_LEVEL_3_TADM, COUNT(DISTINCT DATE_REPORT_MONTH) AS counts
    FROM ra_analytic_dev.ohc_forecast.ohc_completed_combined
    WHERE VAL_DATE = '{val_date}'
      AND DATE_REPORT_MONTH BETWEEN '2024-04-01' AND '2026-03-01'
    GROUP BY HCC, MARKET, PRODUCT_LEVEL_3_TADM
    HAVING COUNT(DISTINCT DATE_REPORT_MONTH) = 24
)
SELECT ... FROM ohc_completed_combined AS a JOIN included AS b ON ...
```

The CTE is a completeness filter — only `(HCC, MARKET, PRODUCT_LEVEL_3_TADM)`
combinations with all 24 months present survive. This is the right instinct: a
seasonality factor computed from a partial year is comparing a month against an
average that doesn't include the same months, which biases the ratio.

`HAVING COUNT(DISTINCT ...) = 24` uses exact equality rather than `>= 24`, which
is correct given the window is exactly 24 months, but brittle if the window ever
changes without the constant changing with it.

**The date range is hardcoded.** `'2024-04-01' AND '2026-03-01'`, plus the literal
`24`, plus the `'2025-03-01'` Y1/Y2 boundary below. Three constants that must move
together each cycle, none derived from `val_date`. This is the item most likely to
cause a stale or silently-wrong run.

```sql
CASE WHEN a.IS_DUAL = 1 THEN 'Dual' ELSE 'Non-Dual' END AS DUAL_IND,
CASE WHEN a.DATE_REPORT_MONTH <= '2025-03-01' THEN 'Y1' ELSE 'Y2' END AS MEASURE_YEAR,
SUM(a.MM) AS MM,
SUM(a.UTIL_K * a.MM / 1000) AS UTIL_COMPLETE,
SUM(a.PD) AS PAID_COMPLETE
```

`MEASURE_YEAR` splits the window into two 12-month periods so factors can be
computed per year and then averaged — a cheap stability check that a pattern
repeats rather than reflecting one anomalous year.

`UTIL_K * MM / 1000` converts the per-1,000 rate back to a raw count before
summing. Same rates-aren't-additive reasoning as in `signals_units`.

### The scaffold query

```python
data_all = spark.sql(f"""SELECT DISTINCT ... WHERE a.VAL_DATE = '{val_date}'""")
```

Every dimensional combination, with **no date filter and no completeness filter**.
This is the scaffold the factors are joined onto at the end, so groups excluded
from the calculation still appear in the output — filled with 1.0. That's the right
design: the published table covers the full book, and groups without enough data
get a neutral factor rather than a missing row.

---

## 5. First `calc_factor` and the Friedman test **[EXPLORATORY]**

```python
def calc_factor(df1, group_list):
    df1 = df1.groupby(group_list + ['MONTH'])[['MM','UTIL_COMPLETE','PAID_COMPLETE']].sum().reset_index()
    df1['MM_YEAR'] = df1.groupby(group_list)['MM'].transform("sum")
    ...
    df1['NORM_FACTOR_UTIL'] = round(df1['UTIL_MEM'] / df1['UTIL_MEM_YEAR'], 4)
    df1['NORM_FACTOR_PMPM'] = round(df1['PMPM'] / df1['PMPM_YEAR'], 4)
    return df1
```

The core calculation, and it is the same in both definitions of this function:

```
NORM_FACTOR = (month's util per member) / (year's util per member)
```

Both numerator and denominator are member-month-weighted rates, so a month with
unusual enrollment doesn't distort the comparison. Factors center on 1.0 by
construction.

```python
df = df[df['HCC'].isin(['PHYSICIAN'])]  # PHYSICIAN has 406 groups; PHARMACY only has 6
```

The exploratory analysis is scoped to `PHYSICIAN`. The comment explains why — it's
the only HCC with enough groups to cluster meaningfully, which is useful context
for interpreting the k-selection work below and a caution against assuming the
chosen k generalizes to the other three HCCs.

### Friedman test

```python
for group_name, group_data in grouped_agg:
    monthly_data = [group_data[group_data['MONTH'] == month]['PMPM'].values for month in group_data['MONTH'].unique()]
    if len(monthly_data) >= 3:
        stat, p = friedmanchisquare(*monthly_data)
        results.append({'group': group_name, 'test_statistic': stat, 'p_value': p})
results_df.display()
```

A non-parametric repeated-measures test — does PMPM differ systematically across
months within a group? That is precisely the right question to ask before applying
seasonality factors, and the non-parametric choice is appropriate for skewed
healthcare cost data.

**The result is displayed and then discarded.** Nothing downstream reads
`results_df`. The most natural use — gate factor application on `p_value < 0.05`,
give non-significant groups a flat 1.0 — is exactly what the pipeline needs and
isn't wired up.

---

## 6. k selection **[EXPLORATORY]**

```python
pivot_df = df_agg.groupby(avg_group)[['NORM_FACTOR_UTIL','NORM_FACTOR_PMPM']].mean().reset_index()
pivot_df['MEASURE_YEAR'] = 'AVG'
pivot_df = pivot_df.pivot_table(index=agg_group_list, columns='MONTH', values='NORM_FACTOR_UTIL')
pivot_df = pivot_df.fillna(1.0)
```

Y1 and Y2 factors are averaged, then pivoted so each row is one group and each
column one month. Each row is now a 12-dimensional seasonality *shape*, which is
what k-means clusters on.

`fillna(1.0)` treats a missing month as "no seasonal effect" — reasonable, though
it does pull a sparse group's shape toward flat and makes it likelier to land in a
low-variation cluster.

Note `pivot_table` is built on `NORM_FACTOR_UTIL` only, but `MEASURE_YEAR` was set
to `'AVG'` on the line before and `agg_group_list` still contains `MEASURE_YEAR`,
so it is part of the pivot index. Harmless here since every row now has the same
value.

### `check_cluster_size` (first definition)

```python
def check_cluster_size(kmeans, min_cluster_size):
    cluster_sizes = np.bincount(kmeans.labels_)
    valid_clusters = {i for i, size in enumerate(cluster_sizes) if size >= min_cluster_size}
    if not valid_clusters:
        return kmeans, kmeans.inertia_
    for cluster_idx, size in enumerate(cluster_sizes):
        if size < min_cluster_size:
            for sample_idx in np.where(kmeans.labels_ == cluster_idx)[0]:
                distances = np.linalg.norm(
                    np.array(kmeans.cluster_centers_)[list(valid_clusters)] -
                    np.array(pivot_df_reindex.loc[sample_idx]), axis=1)
                kmeans.labels_[sample_idx] = list(valid_clusters)[np.argmin(distances)]
    ...
```

Post-processes k-means to eliminate clusters below a minimum size, reassigning
their members to the nearest valid centroid. The motivation is sound — a cluster of
two groups gives a median computed from two observations, which defeats the purpose
of clustering as a smoothing step.

Two problems:

- **`pivot_df_reindex` is read from module globals**, not passed in. The function
  is silently coupled to whatever that name refers to at call time. The second
  definition fixes this by taking `pivot_df` as a parameter.
- **Inertia is recomputed by hand** in a Python loop after reassignment, since
  `kmeans.inertia_` no longer reflects the modified labels. Correct, but it means
  the WCSS values plotted in the elbow chart are not sklearn's and aren't directly
  comparable to a standard elbow plot.

### Elbow and silhouette

```python
for k in k_values:                      # range(2, 21)
    if k >= len(pivot_df): continue
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
    kmeans.fit_predict(pivot_df)
    kmeans, inertia = check_cluster_size(kmeans, 3)
    n_unique_labels = len(np.unique(kmeans.labels_))
    if n_unique_labels <= 1 or n_unique_labels >= len(pivot_df): continue
    wcss.append(inertia)
    silhouette_scores.append(silhouette_score(pivot_df, kmeans.labels_))
```

Standard sweep, with `random_state=42` — so unlike `LIGHTGM_TRAIN`, the clustering
here is reproducible.

The guards are well chosen: skip k values that exceed the sample count, and skip
results that collapsed to one cluster or degenerated to one-per-sample. Both would
otherwise crash `silhouette_score`.

Then two plots, elbow and silhouette. **Neither result is captured into a variable
that the production section reads** — the k values are set by hand afterward.

```python
cluster_numbers = available_k[-1] if available_k else 2  # Use max available k
```

The violin plot section takes the *maximum* k rather than the one the elbow and
silhouette charts recommend, which undercuts the purpose of having computed them.

---

## 7. Slope comparison **[EXPLORATORY]**

```python
def calculate_slope_and_rvalue(group):
    slope, intercept, r_value, p_value, std_err = linregress(group['MONTH_NUM'], group['NORM_PMPM'])
    group['NORM_SLOPE'] = slope
    group['NORM_R_VALUE'] = r_value**2
    return group

def calculate_slope_and_rvalue_final(group):
    try:
        ...
    except:
        group['FINAL_NORM_SLOPE'] = None
        group['FINAL_NORM_R_VALUE'] = None
    return group
```

```python
new_test_df['NORM_PMPM'] = new_test_df['PMPM'] / new_test_df['NORM_FACTOR_PMPM']
new_test_df['FINAL_NORM_PMPM'] = new_test_df['PMPM'] / new_test_df['FINAL_NORM_FACTOR_PMPM']
```

A genuinely good validation idea: divide the observed series by each candidate
factor set and regress the result on month number. **A well-constructed seasonality
factor should leave a residual series with slope near zero and low R²** — meaning
the seasonal pattern has been removed rather than replaced with a trend.

Comparing group-specific factors (`NORM_`) against cluster-median factors
(`FINAL_NORM_`) quantifies what smoothing costs. That is exactly the check that
should gate a production release of new factors.

It ends at `new_test_df` displayed in a cell. No threshold, no pass/fail, no
persistence.

The first function has no `try`, so a degenerate group raises; the second catches
bare `Exception` and returns `None`. Inconsistent, and the bare `except` hides real
errors.

```python
final_clusters_df = labeled_data[labeled_data['num_clusters'] == 7].reset_index()
```

`k = 7` hardcoded, with no comment connecting it to the elbow or silhouette
results.

---

## 8. Production function definitions **[PRODUCTION]**

Lines 360–485 redefine `get_month_name`, `calc_factor`, and `check_cluster_size`,
shadowing the earlier versions.

| Function | Change from the first version |
|---|---|
| `get_month_name` | Identical — pure duplication |
| `calc_factor` | Adds an unused `hcc` parameter; trims output to key columns plus the two factors |
| `check_cluster_size` | Takes `pivot_df` as a parameter (fixing the global); returns only `kmeans`, not inertia |

**This is the single most confusing thing about the file.** Two functions with the
same name and different signatures, ~250 lines apart, with the later one silently
winning. Anyone who opens the file, finds `calc_factor` at line 102, and edits it
to change production behavior will have changed nothing.

The `hcc` parameter on the second `calc_factor` is accepted and never used.

### `run_cluster` — the intended production path

```python
def run_cluster(df, k, agg_group_list, metric):
    ...
    pivot_df = pivot_df.fillna(1.0)

    has_variation = ~(pivot_df == 1.0).all(axis=1)
    flat_df = pivot_df[~has_variation].copy()
    pivot_df = pivot_df[has_variation]

    if len(pivot_df) == 0:
        flat_df['cluster_label'] = flat_df.index.get_level_values('HCC') + "_0"
        return flat_df.reset_index()

    effective_k = min(k, len(pivot_df) - 1) if len(pivot_df) > 1 else 1
    if effective_k < k:
        print(f"  Warning: {metric} - reduced k from {k} to {effective_k} ...")
    if effective_k < 2:
        ...
    kmeans = KMeans(n_clusters=effective_k, random_state=42, n_init=10)
    pivot_df['cluster_label'] = kmeans.fit_predict(pivot_df)
    pivot_df['cluster_label'] = pivot_df['HCC'] + "_" + pivot_df['cluster_label'].astype(str)

    if len(flat_df) > 0:
        flat_df['cluster_label'] = flat_df.index.get_level_values('HCC') + "_flat"
        pivot_df = pd.concat([pivot_df, flat_df], ignore_index=True)
    return pivot_df
```

Notably more careful than the exploratory version:

- Groups with no variation are pulled out before clustering and labeled `_flat`.
  Without this, k-means spends centroids separating identical flat rows.
- `k` is capped at the sample count with an explicit warning.
- Degenerate cases return a single cluster instead of raising.
- Labels are namespaced by HCC (`PHYSICIAN_3`), so cluster 3 for one HCC can't be
  confused with cluster 3 for another.

Note `check_cluster_size` — the minimum-cluster-size enforcement that the
exploratory sweep used — is **not called here**. So production clustering, if it
ran, would permit clusters of size 1, and their "median" would be a single
observation. Given that smoothing is the entire justification for clustering, this
looks like an oversight rather than a decision.

### `get_final_data`

```python
for month in median_col_list:
    cluster_df[month] = cluster_df.groupby('cluster_label')[month].transform('median')
cluster_df = cluster_df.melt(id_vars=melt_group + ['cluster_label'], var_name='MONTH', value_name='FINAL_NORM_FACTOR')

full_df = full_df[all_group_list + ['MONTH']].drop_duplicates()
df_final = full_df.merge(cluster_df, on=melt_group + ['MONTH'], how='left').reset_index(drop=True)
df_final['FINAL_NORM_FACTOR'] = df_final['FINAL_NORM_FACTOR'].fillna(1)
df_final['FINAL_NORM_FACTOR'] = df_final['FINAL_NORM_FACTOR'].clip(lower=0.5, upper=2.0)
df_final['cluster_label'] = df_final['cluster_label'].fillna(df_final['HCC'] + '_unmatched')
df_final['MONTH'] = pd.to_datetime(df_final['MONTH'], format='%B').dt.month
df_final['METRIC'] = metric
```

**Median per cluster per month** — this is the smoothing step, and median rather
than mean is the right call for a noisy ratio with occasional extreme values.

Three good defensive touches:

- `fillna(1)` — a group absent from clustering gets a neutral factor
- `.clip(0.5, 2.0)` — bounds the damage from a bad estimate to ±100%
- `_unmatched` labeling — makes unjoined groups identifiable in the output, and
  the diagnostic plotting later filters on exactly this string

Month names are converted back to integers last, matching what `signals_units`
expects on the join.

### `final_data_no_factors` — the currently active path

```python
def final_data_no_factors(full_df, all_group_list, hcc, metric):
    full_df = full_df[all_group_list + ['MONTH']].drop_duplicates()
    full_df['MONTH'] = pd.to_datetime(full_df['MONTH'], format='%B').dt.month
    full_df['cluster_label'] = f"{hcc}_0"
    full_df['FINAL_NORM_FACTOR'] = 1
    full_df['METRIC'] = metric
    return full_df
```

Produces a schema-compatible table with every factor set to 1.0. A clean neutral
placeholder — and, as of the current configuration, the only path that executes.

---

## 9. The build loop **[PRODUCTION]**

```python
# k values selected via silhouette + elbow analysis on the full agg_group_list
hcc_list_pmpm = [['PHYSICIAN',0], ['OUTPATIENT',0], ['INPATIENT',0], ['PHARMACY',0]]
hcc_list_util = [['PHYSICIAN',0], ['OUTPATIENT',0], ['INPATIENT',0], ['PHARMACY',0]]
hcc_list_all  = [['UTIL',hcc_list_util],['PMPM',hcc_list_pmpm]]

for metric, hcc_list in hcc_list_all:
    for hcc, k in hcc_list:
        df_hcc = df[df['HCC'] == hcc]
        df_hcc_all = df_all[df_all['HCC'] == hcc]
        if k == 0:
            final_hcc_df = final_data_no_factors(df_hcc_all, all_group_list, hcc, metric)
        else:
            df_agg = calc_factor(df_hcc, agg_group_list, hcc)
            df_avg = df_agg.groupby(avg_group)[['NORM_FACTOR_UTIL','NORM_FACTOR_PMPM']].mean().reset_index()
            cluster_df = run_cluster(df_avg, k, agg_group_list, metric)
            final_hcc_df = get_final_data(cluster_df, df_hcc_all, agg_group_list, all_group_list, metric)
        final_df = pd.concat([final_df, final_hcc_df])
```

The structure is good — `k` doubles as both the cluster count and an on/off switch
per HCC per metric, so seasonality can be enabled selectively as each HCC is
validated.

**Every k is 0.** All eight combinations take the placeholder branch. `run_cluster`,
`get_final_data`, and the second `calc_factor` are dead at runtime; the published
table is uniformly 1.0.

The comment above the lists — *"k values selected via silhouette + elbow analysis
on the full agg_group_list"* — describes a state the code is not in. Whether the
values were deliberately reset (with the comment left stale) or the tuning was
never applied is not determinable from the file.

**Downstream consequences, if this is unintentional:**

- `signals_units` publishes `SEASONAL_FACTOR_UTIL` and `SEASONAL_FACTOR_PMPM` as
  constant 1.0 columns
- `LIGHTGM_TRAIN` appends `FINAL_NORM_FACTOR_{metric}` to its feature list, where
  a zero-variance column contributes nothing — LightGBM cannot split on it
- Every downstream fallback that fills a missing factor with 1.0 is indistinguishable
  from a real factor, so nothing anywhere will surface the situation

A single assertion before the write would make the state explicit either way:

```python
n_nonflat = (final_df['FINAL_NORM_FACTOR'] != 1.0).sum()
print(f"Non-neutral factors: {n_nonflat:,} of {len(final_df):,}")
if n_nonflat == 0:
    print("WARNING: all seasonality factors are 1.0 — seasonality is effectively disabled.")
```

---

## 10. Diagnostics and reference comparison **[EXPLORATORY]**

```python
metric_col = 'METRIC' if 'METRIC' in cols else 'metric'
cluster_col = 'CLUSTER_LABEL' if 'CLUSTER_LABEL' in cols else 'cluster_label'
...
```

Case-defensive column resolution repeated five times — a symptom of the uppercase
conversion happening later at line 613 rather than at construction. Normalizing case
once, early, would remove all of it.

```python
ref_df = spark.table("ra_analytic_dev.cs_reference.cs_cf_seasonality_factors").toPandas()
print(f"Reference factor range: {ref_df['FINAL_NORM_FACTOR'].min():.4f} to {ref_df['FINAL_NORM_FACTOR'].max():.4f}")
print(f"New factor range:       {final_df['FINAL_NORM_FACTOR'].min():.4f} to {final_df['FINAL_NORM_FACTOR'].max():.4f}")
```

Compares against a table in a **different catalog and schema** —
`cs_reference.cs_cf_seasonality_factors` versus the `ohc_forecast` target. Same
table name, different location.

Worth being clear about which is authoritative. The pipeline reads
`ohc_forecast.cs_cf_seasonality_factors` (this notebook's output). The
`cs_reference` copy appears to be a curated or prior-generation set used here as a
benchmark. With all factors currently at 1.0, the printed range comparison should
show `1.0000 to 1.0000` against whatever the reference contains — a fast way to
confirm the state described above.

The side-by-side plots are a reasonable eyeball check. Like the slope analysis,
they produce no pass/fail.

---

## 11. Write **[PRODUCTION]**

```python
final_df.columns = final_df.columns.str.upper()

extra_cols = [c for c in ['SEGMENT', 'DUAL_IND', 'SERVICE_TYPE', 'PRODUCT_LEVEL_2_TADM'] if c in final_df.columns]
final_df = final_df.drop(columns=extra_cols)

key_cols = ['MARKET', 'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_3_TADM', 'HCC', 'SERVICE_CATEGORY', 'METRIC', 'MONTH']
final_df = final_df.drop_duplicates(subset=key_cols)

dup_count = final_df.duplicated(subset=key_cols, keep=False).sum()
assert dup_count == 0, f"Duplicate rows remain — do not write!"

spark_df = spark.createDataFrame(final_df)
spark_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(full_table_name)
```

The comment above the drop is candid about why it exists:

> Keeping SEGMENT, DUAL_IND, SERVICE_TYPE, PRODUCT_LEVEL_2_TADM causes multiple
> rows per pipeline key combination, triggering the duplicate ValueError.

That `ValueError` is `_fetch_seasonality_factors`'s guard in `signals_units`. So the
grain mismatch between the two files is being resolved here, at the last possible
moment, by dropping columns and deduplicating.

**`drop_duplicates(subset=key_cols)` keeps an arbitrary survivor.** Factors are
computed at a nine-column grain (including `SEGMENT`, `DUAL_IND`, `SERVICE_TYPE`);
the pipeline joins on seven. Four columns are dropped and one row per remaining key
is kept — whichever happens to come first.

With `k = 0` this is harmless, since every row holds 1.0. **With clustering enabled
it would silently discard real variation** that was just computed at a finer grain.
If seasonality is ever turned on, this line needs to become an explicit aggregation:

```python
final_df = (final_df.groupby(key_cols, as_index=False)
                    .agg(FINAL_NORM_FACTOR=('FINAL_NORM_FACTOR', 'median'),
                         CLUSTER_LABEL=('CLUSTER_LABEL', 'first')))
```

That makes the collapse a stated decision — median across the dropped dimensions —
rather than an accident of row order.

The duplicate assertion is good practice, though `assert` is stripped under
`python -O`; an explicit `raise` would be safer. It also runs *after* the dedup that
guarantees it passes, so it can only fail if `drop_duplicates` itself
malfunctioned.

### The write itself

```python
spark_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(full_table_name)
```

Full overwrite. **No `VAL_DATE` column, no delete-then-append, no history.**

Every other table in this pipeline is keyed on `(val_date, train_end, ...)` and
written so that scenarios coexist and re-runs are idempotent. This one replaces its
entire contents on every execution.

The implication: **you cannot determine which seasonality factors any past forecast
was built on.** A forecast in `ohc_final_output` stamped `RUN_TIMESTAMP` from March
is joined to whatever factors happen to be in this table today. That breaks the
reproducibility story the rest of the pipeline is careful to maintain.

Adding a `VAL_DATE` column and switching to the same delete-then-append pattern
would close the gap, and `signals_units` could then filter to the matching vintage
rather than reading whatever is current.

---

## Summary of observations

| Area | Note |
|---|---|
| **All k = 0** | Every HCC/metric takes the placeholder path; published factors are uniformly 1.0. The comment above claims tuned values. Confirm intent before changing anything else. |
| Syntax error | Bare `Extract data` at line 31 — file cannot be imported or linted |
| Duplicate definitions | `get_month_name`, `calc_factor`, `check_cluster_size` each defined twice with different signatures; the second silently wins |
| No versioning | Full overwrite, no `VAL_DATE` — past forecasts cannot be traced to the factors they used |
| Dedup discards variation | `drop_duplicates` keeps an arbitrary row per key; harmless at 1.0, lossy once clustering is on |
| Hardcoded window | `'2024-04-01'`/`'2026-03-01'`/`24`/`'2025-03-01'` — four constants that must move together each cycle |
| Unused validation | Friedman test, slope/R² comparison, elbow and silhouette all computed and displayed, none gate anything |
| k not wired to analysis | Production k values are hand-set; the violin section takes max k rather than the recommended k |
| `check_cluster_size` unused in production | Minimum-cluster-size enforcement exists but `run_cluster` never calls it |
| Global dependency | First `check_cluster_size` reads `pivot_df_reindex` from module scope |
| Two similar tables | Writes `ohc_forecast.cs_cf_seasonality_factors`, compares against `cs_reference.cs_cf_seasonality_factors` |
| Bare `except` | `calculate_slope_and_rvalue_final` swallows all exceptions |
| Exploratory code in path | ~250 lines of analysis run on every execution and feed nothing |
| Interactive val_date | `MAX(VAL_DATE)` fallback means two runs on different days can differ, with no record in the output |
