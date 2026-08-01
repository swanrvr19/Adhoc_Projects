from pyspark.sql import functions as F
     

catalog    = 'ra_analytic_dev'
schema     = 'ohc_forecast'
table_name = 'DEV_TFM_HCTA_OH_DATA'
     

pat_sf_ohc = dbutils.secrets.get("optumcare_snowflake", "optumcare_snowflake_pat")

def get_ohc_sf_table(query: str):
    sf_options = {
        "sfURL":       "uhg_optumcare.east-us-2.azure.snowflakecomputing.com",
        "sfUser":      "ryan_shannon@optum.com",
        "sfDatabase":  "OCDP_PRD_OCUDL_CCM_HCE_JMJ_DB",
        "sfSchema":    "CCM",
        "sfWarehouse": "DWS_ENV_CUSTOMER_SERVICE_WH",
        "sfRole":      "AZU_DWS_OCDP_PRD_OCUDL_CCM_HCE_JMJ_HIST_SC_R_RL",
        "sfPassword":  pat_sf_ohc,
    }
    return spark.read.format("snowflake").options(**sf_options).option("query", query).load()

def write_table_stacked(df, table_name, val_date):
    """Write df to Delta, replacing only the current val_date slice (idempotent)."""
    full_name = f"{catalog}.{schema}.{table_name}"
    writer = df.write.format("delta").option("mergeSchema", "true")
    if spark.catalog.tableExists(full_name):
        writer = writer.option("replaceWhere", f"VAL_DATE = DATE('{val_date}')")
    writer.mode("overwrite").saveAsTable(full_name)
    print(f"Wrote {full_name} (val_date={val_date})")

     

ohc_hcta_sql = "select * from OCDP_PRD_OCUDL_HCE_DB.ACTUARIALANALYTICS.DEV_TFM_HCTA_OH_DATA"

ohc_hcta = get_ohc_sf_table(ohc_hcta_sql)

# Derive val_date from max claim YR_MO (exclude MBR rows, which carry prospective enrollment)
_max_yrmo = ohc_hcta.filter("MAJ_SRV_CAT != 'MBR'").selectExpr("MAX(YR_MO) AS m").collect()[0]["m"]
val_date = f"{_max_yrmo[:4]}-{_max_yrmo[4:6]}-01"
print(f"Derived val_date from claim-row MAX(YR_MO)={_max_yrmo}: {val_date}")

# Tag every row with the snapshot date before writing
ohc_hcta = ohc_hcta.withColumn("VAL_DATE", F.lit(val_date).cast("date"))

write_table_stacked(ohc_hcta, 'DEV_TFM_HCTA_OH_DATA', val_date)

# Emit val_date for downstream tasks in the Databricks Workflow
try:
    dbutils.jobs.taskValues.set(key="val_date", value=val_date)
    print(f"Task value set: val_date = {val_date}")
except AttributeError:
    pass  # not running in a Databricks Workflows job context

     

from pyspark.sql import functions as F

ohc_hcta = spark.table('ra_analytic_dev.ohc_forecast.DEV_TFM_HCTA_OH_DATA')

coverage = (
    ohc_hcta
    .groupBy('SEGMENT', 'MAJ_SRV_CAT')
    .agg(
        F.min('YR_MO').alias('min_mo'),
        F.max('YR_MO').alias('max_mo'),
        F.countDistinct('YR_MO').alias('n_months')
    )
    .orderBy('SEGMENT', 'min_mo')
)
display(coverage)
