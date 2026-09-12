# Databricks notebook source
# DBTITLE 1,Package installation (for serverless)
import pandas as pd

try:
    pd.ExcelWriter("/tmp/output.xlsx", engine="xlsxwriter")
except ImportError:
    from shared.databricks_env import install_packages

    install_packages(["xlsxwriter"])

# COMMAND ----------

# DBTITLE 1,Generate Excel
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
from pyspark.sql import functions as F

from dups.util.table_config import PRODUCTS, define_common_widgets, get_output_table
from shared.databricks_env import get_dbutils, get_spark

spark = get_spark()
dbutils = get_dbutils()

define_common_widgets()

today = datetime.now(ZoneInfo("America/Chicago")).strftime("%Y-%m-%d")

base_output = Path("/Workspace/Shared/Dup Denials/output")

keep_fields = [
    "CLM_PD_DT",
    "CLM_PD_MONTH",
    "ADJD_DT",
    "ADJD_MONTH",
    "FINANCIAL_CLIENT",
    "DELEGATED_ENTITY",
    "OPTUM_DELEGATION",
]

file_suffix = today

run_type = dbutils.widgets.get("run_type")
if run_type == "intramonth":
    file_suffix += "_IM"

test_name = dbutils.widgets.get("test_name")
if test_name:
    file_suffix += f"_{test_name}"

excel_path = base_output / f"Dup_Denials_{file_suffix}.xlsx"

with pd.ExcelWriter(str(excel_path), engine="xlsxwriter") as writer:
    fmt = writer.book.add_format({"num_format": "#,##0"})
    for product in PRODUCTS:
        catalog_table = get_output_table(product)
        df = spark.table(catalog_table)
        group_fields = [col for col in keep_fields if col in df.columns]
        by_month_summary = (
            df
            .groupBy(*group_fields)
            .agg(
                F.sum("Claim_Line_Count").alias("Claim_Line_Count"),
                F.sum("Savings_Adjustment").alias("Savings_Adjustment"),
            )
            .orderBy(*group_fields)
            .toPandas()
            .assign(
                Savings_Adjustment=lambda x: pd.to_numeric(
                    x["Savings_Adjustment"],
                    errors="coerce",
                ),
            )
        )
        by_month_summary.to_excel(writer, sheet_name=product, index=False)
        worksheet = writer.sheets[product]
        for idx, col in enumerate(by_month_summary.columns):
            if col in {"Claim_Line_Count", "Savings_Adjustment"}:
                worksheet.set_column(idx, idx, None, fmt)
        worksheet.autofit()

