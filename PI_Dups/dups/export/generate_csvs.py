# Databricks notebook source
# DBTITLE 1,Generate CSVs
from dups.util.table_config import PRODUCTS, define_common_widgets, get_output_table
from shared.databricks_env import get_dbutils, get_spark
from shared.export import ExportContext, export_dataset, write_trig

spark = get_spark()
dbutils = get_dbutils()

define_common_widgets()

ctx = ExportContext.from_widgets(stream="dups", product="all")

trig_rows: list[tuple[str, str, str, str]] = []
for product in PRODUCTS:
    catalog_table = get_output_table(product)
    output_df = spark.table(catalog_table)
    base_name = f"{product}_DUP_DENIALS_Savings_Extract{ctx.intramonth_suffix}"
    export_dataset(ctx, output_df, base_name)
    trig_rows.append((product, ctx.nas_path(f"{base_name}.txt.gz"), "DBVEP41939", "OPI_PayPol"))

write_trig(ctx, trig_rows, f"trig_Dup_Denials{ctx.intramonth_suffix}.trig")

