# final_output — Detailed Walkthrough

A section-by-section reading of the reporting notebook.

---

## 1. Scenario parameters

```python
dbutils.widgets.text("train_end", "2026-03-01")   # must match LIGHTGBM_TRAIN run
dbutils.widgets.text("hcc",       "PHYSICIAN")     # must match LIGHTGBM_TRAIN run
dbutils.widgets.text("val_date",  "2026-03-01")    # vintage marker from data prep

train_end = dbutils.widgets.get("train_end")
hcc       = dbutils.widgets.get("hcc")
val_date  = dbutils.widgets.get("val_date")
```

Identical widget set to the training notebook, and the inline comments say why:
these values *must* match the training run. They are used as filter predicates
against the prediction table, so a mismatch doesn't error — it returns zero rows.

Unlike the training notebook, `train_end` stays a string here. It is only ever
used for string comparison in filters and delete predicates, never for date
arithmetic, so parsing it would be pointless.

---

## 2. Setup

```python
from delta.tables import DeltaTable
from pyspark.sql import functions as F
from pyspark.sql.window import Window

table_name  = 'ra_analytic_dev.ohc_forecast.ohc_final_output'
GROUP_KEYS  = ['MARKET', 'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_2_TADM',
               'PRODUCT_LEVEL_3_TADM', 'SEGMENT', 'HCC', 'SERVICE_CATEGORY']
```

Pure Spark — no pandas anywhere in this notebook, which is why it runs in a
fraction of the training notebook's time regardless of data volume.

`GROUP_KEYS` defines the join grain: market, three product levels, segment, HCC,
and service category. Seven columns. Note what is *absent*: `SERVICE_TYPE`,
present in the source claims table, is deliberately excluded.

---

## 3. Aggregating actuals

```python
actuals = (
    spark.table('ra_analytic_dev.ohc_forecast.ohc_completed_combined')
    .filter(F.col('HCC') == hcc)
    .groupBy(*GROUP_KEYS, 'DATE_REPORT_MONTH')
    .agg(F.first('MM').alias('MM'),
         F.sum('UTIL').alias('UTIL'),
         F.sum('PD').alias('PD'))
)
```

The completed-claims table is finer-grained than the model output — it carries
`SERVICE_TYPE`, which the model does not forecast at. This aggregation collapses
that dimension so the join grains match.

The aggregation choices encode a real assumption:

| Column | Aggregation | Reasoning |
|---|---|---|
| `MM` | `first` | Member months are a property of the *population*, not the service type. Every `SERVICE_TYPE` row for a given group-month repeats the same membership figure. Summing would multiply it by the number of service types. |
| `UTIL` | `sum` | Utilization counts are additive across service types |
| `PD` | `sum` | Paid dollars are additive |

`F.first('MM')` is the line to understand. It is correct *given* that `MM` is
constant within the group — which it should be by construction. If that ever
stops holding, `first` picks an arbitrary value with no warning. A defensive
version would use `F.max` and separately assert `min == max`.

---

## 4. Member-month carry-forward

```python
w = Window.partitionBy(*GROUP_KEYS).orderBy(F.desc('DATE_REPORT_MONTH'))
last_mm = (
    actuals.filter(F.col('MM').isNotNull())
    .withColumn('rn', F.row_number().over(w))
    .filter('rn = 1')
    .select(*GROUP_KEYS, F.col('MM').alias('LAST_MM'))
)
```

The problem this solves: projection months have no membership data, but the rate
metrics all divide by `MM`. Without a value, every forecast rate would be null.

The classic "latest non-null per group" pattern — filter out nulls, rank
descending by date, keep rank 1. The result is one row per group carrying that
group's most recent known membership as `LAST_MM`.

**The assumption embedded here is flat membership.** Enrollment is held constant
at its last observed level for up to 21 months forward. For a stable book that's
reasonable; for a market in active growth or runoff, forecast rate metrics will
drift from reality in a direction the model itself never sees. This is probably
the single most important thing to know when reading the output table.

---

## 5. Two small helpers

```python
nz = lambda c: F.when(c != 0, c)                  # NULLIF(c, 0)
mm = F.coalesce(F.col('MM'), F.col('LAST_MM'))    # effective MM
```

`nz` reimplements SQL's `NULLIF(c, 0)`. `F.when` without an `.otherwise()` returns
null for non-matching rows, so a zero becomes null. Wrapping every divisor in
`nz()` converts what would be a division error or infinity into a clean null. It
appears in four places below and is the reason the notebook never blows up on
empty denominators.

`mm` is the effective member-month expression: use the actual when present, fall
back to the carried-forward value. Because it is defined as a Column object once
and reused, actuals and forecast metrics are guaranteed to use the same
denominator — you can't accidentally update one and not the other.

---

## 6. The main select

```python
df_final = (
    spark.table('ra_analytic_dev.ohc_forecast.LIGHTGBM_PMPM_UTIL_OUTPUT_ENCODED')
    .filter(F.col('val_date')  == val_date)
    .filter(F.col('train_end') == train_end)
    .filter(F.col('HCC')       == hcc)
    .join(actuals, GROUP_KEYS + ['DATE_REPORT_MONTH'], 'left')
    .join(last_mm, GROUP_KEYS, 'left')
    .select(...)
)
```

Predictions are the base; actuals are joined on. That direction matters — the
output row set is defined by what the model produced. A historical month with
actuals but no prediction (a group that was filtered out by the burn-in) simply
won't appear.

Both joins are `left`. The first is on group keys *plus month*, so it populates
actuals only for months that have them — projection months get nulls, which is
the intended behavior. The second is on group keys only, so every row picks up
its group's `LAST_MM`.

The triple filter must exactly match a training run's metadata stamps. All three
are string comparisons.

### Column renaming

```python
F.col('MARKET').alias('ENTY'),
F.col('PRODUCT_LEVEL_1_TADM').alias('LOB'),
F.col('PRODUCT_LEVEL_2_TADM').alias('PLAN_TYPE'),
F.col('PRODUCT_LEVEL_3_TADM').alias('RISK_TYPE'),
F.col('HCC').alias('MAJ_SRV_CAT'),
F.col('SERVICE_CATEGORY').alias('HCE_SRVC_CAT'),
F.col('DATE_REPORT_MONTH').alias('YR_MO'),
```

Modeling names map to enterprise reporting names. `PRODUCT_LEVEL_1/2/3_TADM`
becomes the semantically meaningful `LOB` / `PLAN_TYPE` / `RISK_TYPE`.

Note the consequence for the delete predicate later: the output table's HCC
column is named `MAJ_SRV_CAT`, so the delete filters on `MAJ_SRV_CAT` here but on
`HCC` in the training notebook. Same concept, two names, depending on which side
of this notebook you're standing on.

`SEGMENT` passes through unrenamed.

### Actuals metrics

```python
F.col('UTIL').alias('OH_ACTUALS_UTIL'),
(F.col('UTIL') * 12000 / nz(F.col('MM'))).alias('OH_ACTUALS_UTIL_K'),
(F.col('PD')   / nz(F.col('UTIL'))).alias('OH_ACTUALS_UNIT_COST'),
(F.col('PD')   / nz(F.col('MM'))).alias('OH_ACTUALS_ALLOWED_PMPM'),
```

| Metric | Formula | Reading |
|---|---|---|
| `OH_ACTUALS_UTIL` | raw | Service count |
| `OH_ACTUALS_UTIL_K` | `UTIL × 12000 / MM` | Services per 1,000 members per year |
| `OH_ACTUALS_UNIT_COST` | `PD / UTIL` | Average cost per service |
| `OH_ACTUALS_ALLOWED_PMPM` | `PD / MM` | Allowed dollars per member per month |

The `12000` factor is the standard actuarial conversion: 1,000 members × 12
months. It turns a monthly per-member figure into an annualized per-thousand rate,
which is the unit health actuaries actually work in.

Note these use `F.col('MM')` directly, not the `mm` fallback expression — actuals
metrics should be null in projection months, and using real `MM` guarantees that.

### Forecast metrics

```python
F.round(F.col('TARGET_UTIL_PREDICTED') / 12000 * mm, 4).alias('OH_FCST_UTIL'),
F.round('TARGET_UTIL_PREDICTED', 4).alias('OH_FCST_UTIL_K'),
F.round(F.col('TARGET_PMPM_PREDICTED') * 12000 / nz(F.col('TARGET_UTIL_PREDICTED')), 4).alias('OH_FCST_UNIT_COST'),
F.round('TARGET_PMPM_PREDICTED', 4).alias('OH_FCST_ALLOWED_PMPM'),
```

The model predicts in normalized units; these convert back:

- `OH_FCST_UTIL_K` is the raw prediction — the model already outputs per-1,000.
- `OH_FCST_UTIL` reverses the conversion (`/ 12000 * mm`) to get a raw count.
  **This is where `mm` — the carry-forward expression — is used**, so projected
  utilization counts depend on the flat-membership assumption.
- `OH_FCST_UNIT_COST` derives cost per service from two separate model outputs.
  Worth flagging: this quantity is not modeled directly. It is a ratio of two
  independent predictions, so its error is the compounded error of both. Treat it
  as the softest number in the table.
- `OH_FCST_ALLOWED_PMPM` is the raw PMPM prediction.

The structural parallelism between the actuals and forecast blocks is deliberate —
`OH_ACTUALS_UTIL_K` and `OH_FCST_UTIL_K` are the same quantity computed two ways,
so plotting them on one axis is valid.

### Run metadata

```python
'VAL_DATE', 'N_TRAIN_MONTHS', 'TRAIN_END', 'TRAIN_START_LEAD',
'PROJECTION_START', 'PROJECTION_END', 'RUN_TIMESTAMP',
```

Passed through unchanged from the prediction table. `N_TRAIN_MONTHS` is the useful
one for consumers — it lets a dashboard flag or filter rows backed by thin history.

---

## 7. Writing to Delta

```python
if spark.catalog.tableExists(table_name):
    existing_cols_upper = {f.name.upper() for f in spark.table(table_name).schema.fields}
    if 'VAL_DATE' in existing_cols_upper:
        delta_table = DeltaTable.forName(spark, table_name)
        delta_table.delete(f"val_date = '{val_date}' AND train_end = '{train_end}' AND MAJ_SRV_CAT = '{hcc}'")
        df_final.write.mode("append").option("mergeSchema", "true").saveAsTable(table_name)
    elif 'TRAIN_END' in existing_cols_upper:
        delta_table.delete(f"train_end = '{train_end}' AND MAJ_SRV_CAT = '{hcc}'")
        df_final.write.mode("append")...
    else:
        df_final.write.mode("overwrite").option("overwriteSchema", "true")...
else:
    df_final.write.saveAsTable(table_name)
```

The same four-branch pattern as the training notebook, and for the same reason:
idempotent scenario-scoped writes.

| Condition | Behavior |
|---|---|
| Table has `VAL_DATE` | Delete this `(val_date, train_end, MAJ_SRV_CAT)` slice, append |
| Table has `TRAIN_END` only | Legacy path — delete on `(train_end, MAJ_SRV_CAT)`, append |
| Neither | Schema migration — overwrite with `overwriteSchema` |
| Table absent | Create |

The `.upper()` normalization guards against case inconsistency in the metastore.
The legacy branch exists because `val_date` was added to the schema after the
table was already in production; it lets old tables keep working while they
migrate.

`mergeSchema` on append allows new columns to be added without a manual DDL step.
Convenient, but it also means a typo in a column name silently creates a new
column rather than failing.

Every branch prints what it did, which is how you tell from the job log whether a
run replaced rows, migrated the schema, or created the table fresh.

---

## 8. Validation query

```python
display(spark.sql(f"""
    SELECT
        COUNT(*)                                                AS total_rows,
        SUM(CASE WHEN MM IS NOT NULL THEN 1 ELSE 0 END)        AS rows_with_actuals,
        SUM(CASE WHEN MM IS NULL     THEN 1 ELSE 0 END)        AS rows_forecast_only,
        SUM(CASE WHEN OH_FCST_UTIL_K IS NULL THEN 1 ELSE 0 END) AS rows_missing_forecast
    FROM ra_analytic_dev.ohc_forecast.ohc_final_output
    WHERE val_date = '{val_date}' AND train_end = '{train_end}' AND MAJ_SRV_CAT = '{hcc}'
"""))
```

Four numbers, and each answers a specific question:

| Metric | What it tells you | Bad value |
|---|---|---|
| `total_rows` | Did anything get written | `0` — parameters didn't match a training run |
| `rows_with_actuals` | Historical coverage | Much lower than expected — the actuals join under-matched |
| `rows_forecast_only` | Projection coverage | Should be ≈ groups × 21 |
| `rows_missing_forecast` | Prediction gaps | Anything above 0 warrants investigation |

Because `MM` is only null where the actuals join found nothing, it doubles as the
historical/projection discriminator. And because `mm` (the coalesced version) is
what feeds the metrics while raw `MM` is what lands in the output column, this
check works as intended.

`rows_missing_forecast > 0` most often traces back to a split that was skipped
during training — the group has actuals but no model produced a prediction for it.

---

## Summary of concerns

| Area | Note |
|---|---|
| Silent parameter mismatch | Wrong `train_end` or `val_date` yields an empty write, not an error. `total_rows = 0` is the only signal. |
| Flat membership | `LAST_MM` carry-forward assumes stable enrollment across the full projection horizon |
| `F.first('MM')` | Correct only while `MM` is constant within a group-month; no assertion enforces it |
| Derived unit cost | `OH_FCST_UNIT_COST` is a ratio of two independent predictions — compounded error, not a modeled quantity |
| Grain loss | `SERVICE_TYPE` is aggregated away and unrecoverable downstream |
| String-interpolated SQL | Parameters formatted directly into the delete predicate and validation query |
| Non-atomic write | Delete-then-append leaves the slice briefly missing; avoid reading during the job window |
| `mergeSchema` | A misnamed column silently becomes a new column instead of failing |
