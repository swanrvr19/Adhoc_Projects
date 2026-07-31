# ── Scenario parameters ─────────────────────────────────────────────────────
# Set defaults here; overridden by dbutils.notebook.run() when called from
# RUN_FORECAST_SCENARIOS.ipynb.
dbutils.widgets.text("train_end", "2026-03-01")   # must match LIGHTGBM_TRAIN run (YYYY-MM-DD)
dbutils.widgets.text("hcc",       "PHYSICIAN")     # must match LIGHTGBM_TRAIN run (e.g. PHYSICIAN, OUTPATIENT)
dbutils.widgets.text("val_date",  "2026-03-01")    # vintage marker from data prep (YYYY-MM-DD)

train_end = dbutils.widgets.get("train_end")
hcc       = dbutils.widgets.get("hcc")
val_date  = dbutils.widgets.get("val_date")

     

from delta.tables import DeltaTable
from pyspark.sql import functions as F
from pyspark.sql.window import Window

table_name  = 'ra_analytic_dev.ohc_forecast.ohc_final_output'
GROUP_KEYS  = ['MARKET', 'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_2_TADM',
               'PRODUCT_LEVEL_3_TADM', 'SEGMENT', 'HCC', 'SERVICE_CATEGORY']

# Actuals: collapse SERVICE_TYPE to match LightGBM grain
actuals = (
    spark.table('ra_analytic_dev.ohc_forecast.ohc_completed_combined')
    .filter(F.col('HCC') == hcc)
    .groupBy(*GROUP_KEYS, 'DATE_REPORT_MONTH')
    .agg(F.first('MM').alias('MM'), F.sum('UTIL').alias('UTIL'), F.sum('PD').alias('PD'))
)

# Most recent non-null MM per product group for carry-forward into projection months
w = Window.partitionBy(*GROUP_KEYS).orderBy(F.desc('DATE_REPORT_MONTH'))
last_mm = (
    actuals.filter(F.col('MM').isNotNull())
    .withColumn('rn', F.row_number().over(w))
    .filter('rn = 1')
    .select(*GROUP_KEYS, F.col('MM').alias('LAST_MM'))
)

nz  = lambda c: F.when(c != 0, c)                          # NULLIF(c, 0)
mm  = F.coalesce(F.col('MM'), F.col('LAST_MM'))            # effective MM (actual or carried-forward)

df_final = (
    spark.table('ra_analytic_dev.ohc_forecast.LIGHTGBM_PMPM_UTIL_OUTPUT_ENCODED')
    .filter(F.col('val_date') == val_date)
    .filter(F.col('train_end') == train_end)
    .filter(F.col('HCC') == hcc)
    .join(actuals, GROUP_KEYS + ['DATE_REPORT_MONTH'], 'left')
    .join(last_mm,  GROUP_KEYS, 'left')
    .select(
        F.col('MARKET').alias('ENTY'),
        F.col('PRODUCT_LEVEL_1_TADM').alias('LOB'),
        F.col('PRODUCT_LEVEL_2_TADM').alias('PLAN_TYPE'),
        F.col('PRODUCT_LEVEL_3_TADM').alias('RISK_TYPE'),
        F.col('HCC').alias('MAJ_SRV_CAT'),
        'SEGMENT',
        F.col('SERVICE_CATEGORY').alias('HCE_SRVC_CAT'),
        F.col('DATE_REPORT_MONTH').alias('YR_MO'),
        mm.alias('MM'),
        # Actuals metrics — NULL for projection months
        F.col('UTIL').alias('OH_ACTUALS_UTIL'),
        (F.col('UTIL') * 12000 / nz(F.col('MM'))).alias('OH_ACTUALS_UTIL_K'),
        (F.col('PD')   / nz(F.col('UTIL'))).alias('OH_ACTUALS_UNIT_COST'),
        (F.col('PD')   / nz(F.col('MM'))).alias('OH_ACTUALS_ALLOWED_PMPM'),
        # Forecast metrics — OH_FCST_UTIL uses carried-forward MM for projection months
        F.round(F.col('TARGET_UTIL_PREDICTED') / 12000 * mm, 4).alias('OH_FCST_UTIL'),
        F.round('TARGET_UTIL_PREDICTED', 4).alias('OH_FCST_UTIL_K'),
        F.round(F.col('TARGET_PMPM_PREDICTED') * 12000 / nz(F.col('TARGET_UTIL_PREDICTED')), 4).alias('OH_FCST_UNIT_COST'),
        F.round('TARGET_PMPM_PREDICTED', 4).alias('OH_FCST_ALLOWED_PMPM'),
        # Run metadata
        'VAL_DATE', 'N_TRAIN_MONTHS', 'TRAIN_END', 'TRAIN_START_LEAD',
        'PROJECTION_START', 'PROJECTION_END', 'RUN_TIMESTAMP',
    )
)

# Append to existing table; replace rows for this (val_date, train_end, MAJ_SRV_CAT) combo if already exists
if spark.catalog.tableExists(table_name):
    existing_cols_upper = {f.name.upper() for f in spark.table(table_name).schema.fields}
    if 'VAL_DATE' in existing_cols_upper:
        delta_table = DeltaTable.forName(spark, table_name)
        delta_table.delete(f"val_date = '{val_date}' AND train_end = '{train_end}' AND MAJ_SRV_CAT = '{hcc}'")
        df_final.write.mode("append").option("mergeSchema", "true").saveAsTable(table_name)
        print(f"Replaced rows for val_date={val_date}, train_end={train_end}, MAJ_SRV_CAT={hcc} in {table_name}")
    elif 'TRAIN_END' in existing_cols_upper:
        delta_table = DeltaTable.forName(spark, table_name)
        delta_table.delete(f"train_end = '{train_end}' AND MAJ_SRV_CAT = '{hcc}'")
        df_final.write.mode("append").option("mergeSchema", "true").saveAsTable(table_name)
        print(f"Replaced rows for train_end={train_end}, MAJ_SRV_CAT={hcc} in {table_name} (legacy — no val_date col yet)")
    else:
        df_final.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table_name)
        print(f"Schema migration: overwrote {table_name}")
else:
    df_final.write.saveAsTable(table_name)
    print(f"Created new table: {table_name}")

     

display(spark.sql(f"""
    SELECT
        COUNT(*)                                                AS total_rows,
        SUM(CASE WHEN MM IS NOT NULL THEN 1 ELSE 0 END)        AS rows_with_actuals,
        SUM(CASE WHEN MM IS NULL     THEN 1 ELSE 0 END)        AS rows_forecast_only,
        SUM(CASE WHEN OH_FCST_UTIL_K IS NULL THEN 1 ELSE 0 END) AS rows_missing_forecast
    FROM ra_analytic_dev.ohc_forecast.ohc_final_output
    WHERE val_date = '{val_date}'
      AND train_end = '{train_end}'
      AND MAJ_SRV_CAT = '{hcc}'
"""))
