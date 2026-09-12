# Databricks notebook source
# MAGIC %md
# MAGIC # UNET Duplicate Denials

# COMMAND ----------

# DBTITLE 1,Inputs
from datetime import date

from pyspark.sql import functions as F

from dups.util.connection import extract_galaxy
from dups.util.table_config import define_common_widgets, get_source_table
from shared.databricks_env import get_dbutils, get_spark

spark = get_spark()
dbutils = get_dbutils()

define_common_widgets()

run_type = dbutils.widgets.get("run_type")
min_proc_dt = dbutils.widgets.get("min_proc_dt")

if not min_proc_dt:
    if run_type == "full":
        min_proc_dt = "2026-01-01"
    elif run_type == "intramonth":
        today = date.today()
        m = today.month - 3
        y = today.year
        if m <= 0:
            m += 12
            y -= 1
        min_proc_dt = date(y, m, 1).strftime("%Y-%m-%d")
    else:
        raise ValueError("Invalid run type")

print(f"Run type: {run_type}, min_proc_dt: {min_proc_dt}")

product = "UNET"

reason_codes = (
    spark
    .table(get_source_table("dups_unet_reason_code_dimension"))
    .select("Reason_Code")
    .distinct()
    .collect()
)
reason_codes2 = [row["Reason_Code"] for row in reason_codes]
reason_list = ",".join(f"'{x}'" for x in reason_codes2)
print(reason_codes2)

# COMMAND ----------

# DBTITLE 1,Load Ratios
base_join_keys = [
    "SRVC_YEAR",
    "FUND_ARNG_TYP_NRML_CD_DERIV",
    "CLM_INST_OR_PROF_TYP_CD",
    "CHRG_AMT_RANGE_MIN",
    "CHRG_AMT_RANGE_MAX",
]

ratio_join_keys = [
    [
        *base_join_keys,
        "MPIN",
        "TIN",
        "DERIV_PROC_DRG_RVNU_CD",
        "DERIV_PROC_DRG_RVNU_TYPE",
    ],
    [
        *base_join_keys,
        "TIN",
        "DERIV_PROC_DRG_RVNU_CD",
        "DERIV_PROC_DRG_RVNU_TYPE",
    ],
    [
        *base_join_keys,
        "DERIV_PROC_DRG_RVNU_CD",
        "DERIV_PROC_DRG_RVNU_TYPE",
        "PAR_STATUS",
    ],
    [
        *base_join_keys,
        "PAR_STATUS",
    ],
]

ratios = [
    spark.table(get_source_table(f"{product.lower()}_b_to_a_ratios_lvl{rank}"))
    for rank in range(1, 5)
]

for ratio_rank, ratio_df in enumerate(ratios):
    join_keys = ratio_join_keys[ratio_rank]

    dup_check = ratio_df.groupBy(*join_keys).count().filter(F.col("count") > 1)
    dup_count = dup_check.count()

    if dup_count > 0:
        print(f"WARNING: Ratio level {ratio_rank + 1} has {dup_count} duplicate key combinations")
        print("Sample duplicates:")
        dup_check.orderBy(F.desc("count")).show(5, truncate=False)
        message = f"Duplicate keys found in ratio DataFrame {ratio_rank + 1}. This will cause row multiplication."
        raise ValueError(message)

# COMMAND ----------

# DBTITLE 1,Claim Extract
claim_query = f"""
SELECT
  CLAIMS.ADJD_DT,
  TO_CHAR(CLAIMS.ADJD_DT, 'yyyy-mm') AS ADJD_MONTH,
  PROVIDER.MPIN,
  PROVIDER.TIN,
  HEADER.ERLY_SRVC_DT,
  YEAR(HEADER.ERLY_SRVC_DT) AS SRVC_YEAR,
  HEADER.FM_TYP_CD AS CLM_INST_OR_PROF_TYP_CD,
  CASE
    WHEN NOT UB.BIL_PROC_CD IS NULL
    THEN UB.BIL_PROC_CD
    WHEN NOT CLAIMS.BIL_PROC_CD IS NULL
    THEN CLAIMS.BIL_PROC_CD
    ELSE CLAIMS.PROC_CD
  END AS BIL_PROC_CD,
  CASE WHEN NOT UB.BIL_RVNU_CD IS NULL THEN UB.BIL_RVNU_CD ELSE CLAIMS.RVNU_CD END AS BIL_RVNU_CD,
  CASE
    WHEN NOT HEADER.BIL_DRG_CD IS NULL
    THEN HEADER.BIL_DRG_CD
    ELSE HEADER.ENT_DRG_CD
  END AS BIL_DRG_CD,
  CLM_RSN_CD.RSN_CD AS CLM_LVL_RSN_CD,
  FNL_RSN_CD.RSN_CD AS FNL_RSN_CD,
  ORIG_RSN_CD.RSN_CD AS ORIG_SRVC_LVL_RSN_CD,
  SRVC_RSN_CD.RSN_CD AS SRVC_LVL_RSN_CD,
  CLAIMS.PROV_PRTCP_STS_CD,
  CASE
    WHEN CLAIMS.PROV_PRTCP_STS_CD = 'P'
    THEN 'PAR'
    WHEN CLAIMS.PROV_PRTCP_STS_CD = 'T'
    THEN 'PAR'
    WHEN CLAIMS.PROV_PRTCP_STS_CD = 'N'
    THEN 'NON-PAR'
    WHEN CLAIMS.PROV_PRTCP_STS_CD = ' '
    THEN 'NON-PAR'
    ELSE 'PAR'
  END AS PAR_STATUS,
  CASE WHEN CLAIMS.CPTATN_FUND_CD IN ('X', 'Y', 'W') THEN 'Y' ELSE 'N' END AS BEHAVIORAL_HEALTH_FLAG,
  CASE
    WHEN RIGHT(CLAIMS.CUST_SEG_NBR, 5) = '30500'
    THEN 'ASO'
    WHEN HEADER.MKT_SEG_CD IN ('AA1', 'AA7', 'AA8')
    THEN 'ASO' /* From Geralyn Plautz */
    WHEN HEADER.MKT_SEG_CD = 'AA2'
    THEN 'MMP' /* From Geralyn Plautz */
    WHEN (
      HEADER.MKT_SEG_CD IN ('C', 'D', 'F') AND HEADER.ERLY_SRVC_DT >= '2024-09-01'
    )
    THEN 'MMP' /* From Geralyn Plautz */
    WHEN COMPANY_CODE.FINC_ARNG_CD = 'A'
    THEN 'ASO'
    WHEN COMPANY_CODE.FINC_ARNG_CD = 'F'
    THEN 'FI'
    WHEN COMPANY_CODE.FINC_ARNG_CD = 'M'
    THEN 'MMP'
    ELSE 'FI'
  END AS FINC_ARNG_CD_DERIV,
  CASE
    WHEN NOT UB.ALLOC_SRC_CHRG_AMT IS NULL
    THEN UB.ALLOC_SRC_CHRG_AMT
    ELSE CLAIMS.SRC_CHRG_AMT
  END AS SRC_CHRG_AMT,
  CASE
    WHEN NOT UB.ALLOC_ALLW_AMT IS NULL
    THEN UB.ALLOC_ALLW_AMT
    ELSE CLAIMS.ALLW_AMT
  END AS ALLW_AMT
FROM GALAXY.UNET_CLAIM_STATISTICAL_SERVICE AS CLAIMS
INNER JOIN GALAXY.UNET_CLAIM_HEADER AS HEADER
  ON CLAIMS.UNET_CLM_HEAD_SYS_ID = HEADER.UNET_CLM_HEAD_SYS_ID
  AND CLAIMS.MBR_SYS_ID = HEADER.MBR_SYS_ID
LEFT JOIN GALAXY.UNET_FACILITY_UB92 AS UBF
  ON UBF.MBR_SYS_ID = HEADER.MBR_SYS_ID
  AND UBF.UNET_CLM_HEAD_SYS_ID = HEADER.UNET_CLM_HEAD_SYS_ID
LEFT JOIN GALAXY.UNET_UB92_REVENUE_CODE_STATISTICAL_SERVICE AS UB
  ON UB.MBR_SYS_ID = CLAIMS.MBR_SYS_ID
  AND UB.UNET_CLM_SRVC_SYS_ID = CLAIMS.UNET_CLM_SRVC_SYS_ID
INNER JOIN GALAXY.REASON_CODE AS FNL_RSN_CD
  ON CLAIMS.FNL_RSN_CD_SYS_ID = FNL_RSN_CD.RSN_CD_SYS_ID
INNER JOIN GALAXY.REASON_CODE AS SRVC_RSN_CD
  ON CLAIMS.SRVC_LVL_RSN_CD_SYS_ID = SRVC_RSN_CD.RSN_CD_SYS_ID
INNER JOIN GALAXY.REASON_CODE AS ORIG_RSN_CD
  ON CLAIMS.ORIG_SRVC_LVL_RSN_CD_SYS_ID = ORIG_RSN_CD.RSN_CD_SYS_ID
INNER JOIN GALAXY.REASON_CODE AS CLM_RSN_CD
  ON CLAIMS.CLM_LVL_RSN_CD_SYS_ID = CLM_RSN_CD.RSN_CD_SYS_ID
INNER JOIN GALAXY.PROVIDER AS PROVIDER
  ON PROVIDER.PROV_SYS_ID = CLAIMS.SRVC_PROV_SYS_ID
  AND PROVIDER.PROV_ROW_EFF_DT = CLAIMS.SRVC_PROV_ROW_EFF_DT
INNER JOIN GALAXY.COMPANY_CODE AS COMPANY_CODE
  ON HEADER.CO_CD = COMPANY_CODE.CO_CD
WHERE
  CLAIMS.ADJD_DT >= '{min_proc_dt}'
  AND CLAIMS.TRANS_CD = '00'
  AND CLAIMS.CHRG_STS_CD = 'D'
  AND (
    CLM_RSN_CD.RSN_CD IN ({reason_list})
    OR FNL_RSN_CD.RSN_CD IN ({reason_list})
    OR ORIG_RSN_CD.RSN_CD IN ({reason_list})
    OR SRVC_RSN_CD.RSN_CD IN ({reason_list})
  )
  AND /* Filtering out claims with garbage episode identifiers */ CLAIMS.MBR_SYS_ID <> 0
  AND PROVIDER.MPIN <> 0
  AND PROVIDER.TIN <> ''
  AND HEADER.ERLY_SRVC_DT <> '1900-01-01'
  AND COALESCE(UB.ALLOC_SRC_CHRG_AMT, CLAIMS.SRC_CHRG_AMT) > 1
  AND COALESCE(UB.ALLOC_ALLW_AMT, CLAIMS.ALLW_AMT) = 0
"""

rawclaims = extract_galaxy(claim_query).cache()

# COMMAND ----------

# DBTITLE 1,Missing Reason Codes

reason_code_suffix = "_RSN_CD"
reason_code_cols = sorted(c for c in rawclaims.columns if c.endswith(reason_code_suffix))

observed_row = rawclaims.agg(
    *[F.collect_set(F.trim(F.col(c))).alias(c) for c in reason_code_cols],
).first()

observed_reason_codes = {code for c in reason_code_cols for code in observed_row[c]}
missing_reason_codes = sorted(set(reason_codes2) - observed_reason_codes)
print(
    "Reason codes in selection criteria not found in extracted data "
    f"({len(missing_reason_codes)}): {missing_reason_codes}",
)

# COMMAND ----------

# DBTITLE 1,Financial Tagging
claims_with_financial_client = rawclaims.withColumn(
    "FINANCIAL_CLIENT",
    F
    .when(F.col("FINC_ARNG_CD_DERIV") == "ASO", "EI_ASO")
    .when(F.col("BEHAVIORAL_HEALTH_FLAG") == "Y", "OBH")
    .when(F.col("FINC_ARNG_CD_DERIV").isin(["MMP", "FI"]), "EI_FI")
    .otherwise(""),
)

# COMMAND ----------

# DBTITLE 1,Claim Processing
claims = claims_with_financial_client.withColumn(
    "DERIV_PROC_DRG_RVNU_CD",
    F
    .when(F.col("CLM_INST_OR_PROF_TYP_CD") == "P", F.col("BIL_PROC_CD"))
    .when(
        (F.col("BIL_DRG_CD").isNotNull()) & (F.col("BIL_DRG_CD") != ""),
        F.col("BIL_DRG_CD"),
    )
    .otherwise(F.col("BIL_RVNU_CD")),
)

claims = claims.withColumn(
    "DERIV_PROC_DRG_RVNU_TYPE",
    F
    .when(F.col("CLM_INST_OR_PROF_TYP_CD") == "P", F.lit("PROC"))
    .when((F.col("BIL_DRG_CD").isNotNull()) & (F.col("BIL_DRG_CD") != ""), F.lit("DRG"))
    .otherwise(F.lit("RVNU_CD")),
)

claims = claims.withColumn(
    "CHRG_AMT_RANGE_MIN",
    F
    .when(F.col("CLM_INST_OR_PROF_TYP_CD") == "P", F.lit(0))
    .when(F.col("SRC_CHRG_AMT") >= 100000, F.lit(100000))
    .when(F.col("SRC_CHRG_AMT") >= 50000, F.lit(50000))
    .when(F.col("SRC_CHRG_AMT") >= 20000, F.lit(20000))
    .when(F.col("SRC_CHRG_AMT") >= 10000, F.lit(10000))
    .when(F.col("SRC_CHRG_AMT") >= 5000, F.lit(5000))
    .otherwise(F.lit(0)),
)

claims = claims.withColumn(
    "CHRG_AMT_RANGE_MAX",
    F
    .when(F.col("CLM_INST_OR_PROF_TYP_CD") == "P", F.lit(99999999))
    .when(F.col("SRC_CHRG_AMT") >= 100000, F.lit(99999999))
    .when(F.col("SRC_CHRG_AMT") >= 50000, F.lit(100000))
    .when(F.col("SRC_CHRG_AMT") >= 20000, F.lit(50000))
    .when(F.col("SRC_CHRG_AMT") >= 10000, F.lit(20000))
    .when(F.col("SRC_CHRG_AMT") >= 5000, F.lit(10000))
    .otherwise(F.lit(5000)),
)

claims = claims.withColumn(
    "FUND_ARNG_TYP_NRML_CD_DERIV",
    F.when(F.col("FINC_ARNG_CD_DERIV") == "ASO", "ASO").otherwise("FI"),
)

joined = claims
for ratio_rank, ratio_df in enumerate(ratios):
    join_keys = ratio_join_keys[ratio_rank]
    joined = joined.join(
        ratio_df.select(
            *join_keys,
            F.col("bill_to_allow").alias(f"bill_to_allow_{ratio_rank + 1}"),
        ),
        on=join_keys,
        how="left",
    )

joined = joined.withColumn(
    "Bill_to_Primary_Allow",
    F.coalesce(
        "bill_to_allow_1",
        "bill_to_allow_2",
        "bill_to_allow_3",
        "bill_to_allow_4",
        F.lit(0.3),
    ),
)

final = joined.withColumn(
    "Savings_Adjustment",
    (F.col("SRC_CHRG_AMT") * F.col("Bill_to_Primary_Allow")).cast("decimal(18,2)"),
)

reason_code_priority = F.coalesce(
    F.when(F.col("CLM_LVL_RSN_CD").isin(reason_codes2), F.col("CLM_LVL_RSN_CD")),
    F.when(F.col("FNL_RSN_CD").isin(reason_codes2), F.col("FNL_RSN_CD")),
    F.when(F.col("ORIG_SRVC_LVL_RSN_CD").isin(reason_codes2), F.col("ORIG_SRVC_LVL_RSN_CD")),
    F.when(F.col("SRVC_LVL_RSN_CD").isin(reason_codes2), F.col("SRVC_LVL_RSN_CD")),
    F.col("CLM_LVL_RSN_CD"),
    F.col("FNL_RSN_CD"),
    F.col("ORIG_SRVC_LVL_RSN_CD"),
    F.col("SRVC_LVL_RSN_CD"),
)

final = final.withColumn("REASON_CODE", reason_code_priority)
final = final.cache()
rawclaims.unpersist()

# COMMAND ----------

summary_by_claim_type = (
    final
    .groupBy("CLM_INST_OR_PROF_TYP_CD")
    .agg(
        F.count("*").alias("row_count"),
    )
    .orderBy("CLM_INST_OR_PROF_TYP_CD")
)
display(
    summary_by_claim_type.withColumn("row_count", F.format_number("row_count", 2)),
)

# COMMAND ----------

row_count = final.select(F.count_if(F.col("CLM_INST_OR_PROF_TYP_CD") == "P"))
display(row_count)

# COMMAND ----------

from pyspark.databricks.sql.functions import approx_top_k
from pyspark.sql.functions import col, explode

top_k_df = (
    final
    .groupBy("DERIV_PROC_DRG_RVNU_TYPE")
    .agg(approx_top_k("DERIV_PROC_DRG_RVNU_CD", 5).alias("top_codes"))
    .withColumn("top_code", explode("top_codes"))
    .select(
        "DERIV_PROC_DRG_RVNU_TYPE",
        col("top_code.item").alias("DERIV_PROC_DRG_RVNU_CD"),
        col("top_code.count").alias("frequency"),
    )
    .orderBy("DERIV_PROC_DRG_RVNU_TYPE", col("frequency").desc())
)

display(top_k_df)

# COMMAND ----------

summary_non_null = (
    final
    .groupBy("DERIV_PROC_DRG_RVNU_TYPE")
    .agg(
        F.count(F.col("bill_to_allow_1")).alias("non_null_bill_to_allow_1"),
        F.count(F.col("bill_to_allow_2")).alias("non_null_bill_to_allow_2"),
        F.count(F.col("bill_to_allow_3")).alias("non_null_bill_to_allow_3"),
        F.count(F.col("bill_to_allow_4")).alias("non_null_bill_to_allow_4"),
    )
    .orderBy("DERIV_PROC_DRG_RVNU_TYPE")
)
display(summary_non_null)

# COMMAND ----------

# DBTITLE 1,Export Summary
from dups.util.table_config import get_output_table

catalog_table = get_output_table(product)

if run_type == "full":
    group_fields = ["ADJD_MONTH", "FINANCIAL_CLIENT", "TIN", "REASON_CODE"]
    order_fields = [F.desc("ADJD_MONTH"), "FINANCIAL_CLIENT", "TIN", "REASON_CODE"]
else:
    group_fields = ["ADJD_DT", "ADJD_MONTH", "FINANCIAL_CLIENT", "REASON_CODE"]
    order_fields = [F.desc("ADJD_DT"), "ADJD_MONTH", "FINANCIAL_CLIENT", "REASON_CODE"]

by_month = (
    final
    .groupBy(*group_fields)
    .agg(
        F.count("*").alias("Claim_Line_Count"),
        F.sum("Savings_Adjustment").alias("Savings_Adjustment"),
    )
    .orderBy(*order_fields)
)

by_month.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(catalog_table)

# COMMAND ----------

# DBTITLE 1,Display Totals
by_month_display = (
    final
    .groupBy("ADJD_MONTH")
    .agg(
        F.count("*").alias("Claim_Line_Count"),
        F.sum("Savings_Adjustment").alias("Savings_Adjustment"),
        F.sum("SRC_CHRG_AMT").cast("decimal(18,2)").alias("SRC_CHRG_AMT"),
    )
    .orderBy(F.desc("ADJD_MONTH"))
)

display(
    by_month_display
    .withColumn("Claim_Line_Count", F.format_number("Claim_Line_Count", 2))
    .withColumn("Savings_Adjustment", F.format_number("Savings_Adjustment", 2))
    .withColumn("SRC_CHRG_AMT", F.format_number("SRC_CHRG_AMT", 2)),
)

by_day_display = (
    final
    .groupBy("ADJD_DT")
    .agg(
        F.count("*").alias("Claim_Line_Count"),
        F.sum("Savings_Adjustment").alias("Savings_Adjustment"),
        F.sum("SRC_CHRG_AMT").cast("decimal(18,2)").alias("SRC_CHRG_AMT"),
    )
    .orderBy(F.desc("ADJD_DT"))
    .limit(35)
)

display(
    by_day_display
    .withColumn("Claim_Line_Count", F.format_number("Claim_Line_Count", 2))
    .withColumn("Savings_Adjustment", F.format_number("Savings_Adjustment", 2))
    .withColumn("SRC_CHRG_AMT", F.format_number("SRC_CHRG_AMT", 2)),
)

