# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "4"
# ///
# MAGIC %md
# MAGIC # CIRRUS Duplicate Denials

# COMMAND ----------

# DBTITLE 1,Inputs
from datetime import date

from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType

from dups.util.connection import extract_udw
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

product = "CIRRUS"

reason_codes = (
    spark
    .table(get_source_table("dups_usp_reason_code_dimension"))
    .select("Reason_Code")
    .distinct()
    .collect()
)
reason_codes2 = [row["Reason_Code"].strip() for row in reason_codes]
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
# Adding RDUC_RSN_*_CD to the criteria adds nothing
# Adding CLM_DENY_RSN_TYP_*_CD and ACCT_PAY_RMRK_RSN_TYP_*_CD to the criteria adds an addition 0.02%
# So am sticking with just DERIV_RDUC_RSN_CD for simplicity

claim_query = f"""
SELECT
  S.CLM_PD_DT,
  TO_CHAR(S.CLM_PD_DT, 'yyyy-mm') AS CLM_PD_MONTH,
  YEAR(S.SRVC_DT) AS SRVC_YEAR,
  H.CLM_INST_OR_PROF_TYP_CD,
  H.BIL_PROV_TIN AS TIN,
  SPROV.BIL_PROV_MPIN AS MPIN,
  FND.FUND_ARNG_TYP_NRML_CD,
  pln.CUST_ID,
  CASE WHEN pln.BRND_ENTY_CD LIKE 'UNITEDHEALTHCARE_SUREST%' THEN 'Y' ELSE 'N' END AS SUREST_IND,
  S.PROC_CD,
  S.BIL_RVNU_CD,
  H.SBMT_DRGS_CD,
  DERIV_RDUC_RSN_CD,
  S.BHV_CLM_LN_IND,
  S.PROV_PAR_STS_CD AS PAR_STATUS,
  S.SRC_CHRG_AMT AS CHRG_AMT
FROM UAHDMSECUREVIEW1.ADJD_CLM_EVNT_SRVC_CS AS S
JOIN UAHDMSECUREVIEW1.ADJD_CLM_EVNT_CS AS H
  ON H.UDW_ADJD_CLM_ID = S.UDW_ADJD_CLM_ID
  AND H.UDW_ADJD_CLM_EVNT_ID = S.UDW_ADJD_CLM_EVNT_ID
INNER JOIN UAHDMSECUREVIEW1.CUST_CS AS cust
  ON H.UDW_CUST_PTY_SEG_ID = cust.UDW_CUST_PTY_SEG_ID
  AND S.SRVC_STRT_DT BETWEEN cust.BUS_EFF_DT AND cust.BUS_EXPIR_DT
  AND S.POL_ORIG_SRC_SYS_CD = cust.POL_ORIG_SRC_SYS_CD
  AND S.POL_ORIG_SRC_SYS_CD IN ('CRR')
  AND cust.POL_ORIG_SRC_SYS_CD IN ('CRR')
  AND cust.SRC_ROW_STS_CD = 'A'
INNER JOIN UAHDMSECUREVIEW1.CUST_CONTR_CS AS cont
  ON H.UDW_CUST_PTY_ID = cont.UDW_CUST_PTY_ID
  AND H.UDW_CUST_PTY_SEG_ID = cont.UDW_CUST_PTY_SEG_ID
  AND H.UDW_CUST_CONTR_SEG_ID = cont.UDW_CUST_CONTR_SEG_ID
  AND cont.BUS_EFF_DT BETWEEN cust.BUS_EFF_DT AND cust.BUS_EXPIR_DT
  AND S.POL_ORIG_SRC_SYS_CD = cont.POL_ORIG_SRC_SYS_CD
  AND cont.POL_ORIG_SRC_SYS_CD IN ('CRR')
  AND cust.POL_ORIG_SRC_SYS_CD IN ('CRR')
  AND cont.SRC_ROW_STS_CD = 'A'
INNER JOIN UAHDMSECUREVIEW1.CUST_PLN_CS AS pln
  ON pln.UDW_CUST_PLN_SEG_ID = H.UDW_CUST_PLN_SEG_ID
  AND S.POL_ORIG_SRC_SYS_CD = pln.POL_ORIG_SRC_SYS_CD
  AND S.POL_ORIG_SRC_SYS_CD IN ('CRR')
  AND pln.POL_ORIG_SRC_SYS_CD IN ('CRR')
  AND pln.SRC_ROW_STS_CD = 'A'
INNER JOIN UAHDMSECUREVIEW1.MKT_SEG_TYP AS mkt
  ON cont.MKT_SEG_TYP_CD = mkt.MKT_SEG_TYP_CD
  AND cont.POL_ORIG_SRC_SYS_CD = mkt.POL_ORIG_SRC_SYS_CD
  AND cont.POL_ORIG_SRC_SYS_CD IN ('CRR')
  AND mkt.POL_ORIG_SRC_SYS_CD IN ('CRR')
INNER JOIN UAHDMSECUREVIEW1.LGL_ENTY_CS AS lgl
  ON lgl.UDW_LGL_ENTY_ID = pln.UDW_LGL_ENTY_ID
  AND pln.POL_ORIG_SRC_SYS_CD = lgl.POL_ORIG_SRC_SYS_CD
LEFT JOIN UAHDMSECUREVIEW1.PRDCT_CS AS prdct
  ON pln.UDW_PRDCT_ID = prdct.UDW_PRDCT_ID
  AND prdct.POL_ORIG_SRC_SYS_CD = pln.POL_ORIG_SRC_SYS_CD
  AND prdct.POL_ORIG_SRC_SYS_CD IN ('CRR')
INNER JOIN UAHDMSECUREVIEW1.FUND_ARNG_TYP AS FND
  ON FND.FUND_ARNG_TYP_CD = pln.FUND_ARNG_TYP_CD
  AND FND.POL_ORIG_SRC_SYS_CD IN ('CRR')
  AND pln.POL_ORIG_SRC_SYS_CD = FND.POL_ORIG_SRC_SYS_CD
INNER JOIN UAHDMSECUREVIEW1.MBR_CS AS m
  ON H.UDW_MBR_PTY_ID = m.UDW_MBR_PTY_ID
  AND S.POL_ORIG_SRC_SYS_CD = m.POL_ORIG_SRC_SYS_CD
LEFT JOIN UAHDMSECUREVIEW1.ADJD_CLM_EVNT_SRVC_PROV_CS AS SPROV
  ON SPROV.UDW_ADJD_CLM_ID = S.UDW_ADJD_CLM_ID
  AND SPROV.UDW_ADJD_CLM_EVNT_ID = S.UDW_ADJD_CLM_EVNT_ID
  AND SPROV.ADJD_CLM_SRVC_LN_NUM = S.ADJD_CLM_SRVC_LN_NUM
WHERE
  S.DERIV_RDUC_RSN_CD IN ({reason_list}) AND S.CLM_PD_DT >= '{min_proc_dt}'
"""

rawclaims = extract_udw(claim_query).cache()

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
claims_with_client = rawclaims.withColumn(
    "FINANCIAL_CLIENT",
    F
    .when(F.col("FUND_ARNG_TYP_NRML_CD") == "ASO", F.lit("EI_ASO"))
    .when(F.col("FUND_ARNG_TYP_NRML_CD") == "LF", F.lit("EI_LF"))
    .when(F.col("BHV_CLM_LN_IND") == "Y", F.lit("OBH"))
    .when(F.col("FUND_ARNG_TYP_NRML_CD").isin(["MMP", "MP", "FI"]), F.lit("EI_FI"))
    .otherwise(F.lit("")),
)

# COMMAND ----------

# DBTITLE 1,Claim Processing
claims = claims_with_client

claims = claims.withColumn(
    "FUND_ARNG_TYP_NRML_CD_DERIV",
    F.when(F.col("FUND_ARNG_TYP_NRML_CD").isin("LF", "MMP"), F.lit("FI")).otherwise(
        F.col("FUND_ARNG_TYP_NRML_CD")
    ),
)

claims = claims.withColumn(
    "DERIV_PROC_DRG_RVNU_CD",
    F
    .when(F.col("CLM_INST_OR_PROF_TYP_CD") == "2", F.col("PROC_CD"))
    .when(
        (F.col("SBMT_DRGS_CD").isNotNull())
        & (F.col("SBMT_DRGS_CD") != "")
        & (F.col("SBMT_DRGS_CD") != "00000"),
        F.col("SBMT_DRGS_CD"),
    )
    .otherwise(F.col("BIL_RVNU_CD")),
)

claims = claims.withColumn(
    "DERIV_PROC_DRG_RVNU_TYPE",
    F
    .when(F.col("CLM_INST_OR_PROF_TYP_CD") == "2", F.lit("PROC CODE"))
    .when(
        (F.col("SBMT_DRGS_CD").isNotNull())
        & (F.col("SBMT_DRGS_CD") != "")
        & (F.col("SBMT_DRGS_CD") != "00000"),
        F.lit("DRG CODE"),
    )
    .otherwise(F.lit("REV CODE")),
)

claims = claims.withColumn(
    "CHRG_AMT_RANGE_MIN",
    F
    .when(F.col("CLM_INST_OR_PROF_TYP_CD") == "P", F.lit(0))
    .when(F.col("CHRG_AMT") >= 100000, F.lit(100000))
    .when(F.col("CHRG_AMT") >= 50000, F.lit(50000))
    .when(F.col("CHRG_AMT") >= 20000, F.lit(20000))
    .when(F.col("CHRG_AMT") >= 10000, F.lit(10000))
    .when(F.col("CHRG_AMT") >= 5000, F.lit(5000))
    .otherwise(F.lit(0)),
)

claims = claims.withColumn(
    "CHRG_AMT_RANGE_MAX",
    F
    .when(F.col("CLM_INST_OR_PROF_TYP_CD") == "P", F.lit(99999999))
    .when(F.col("CHRG_AMT") >= 100000, F.lit(99999999))
    .when(F.col("CHRG_AMT") >= 50000, F.lit(100000))
    .when(F.col("CHRG_AMT") >= 20000, F.lit(50000))
    .when(F.col("CHRG_AMT") >= 10000, F.lit(20000))
    .when(F.col("CHRG_AMT") >= 5000, F.lit(10000))
    .otherwise(F.lit(5000)),
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
    (F.col("CHRG_AMT") * F.col("Bill_to_Primary_Allow")).cast("decimal(18,2)"),
)

final = final.withColumnRenamed("DERIV_RDUC_RSN_CD", "REASON_CODE")
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
    group_fields = [
        "CLM_PD_MONTH",
        "FINANCIAL_CLIENT",
        "TIN",
        "CUST_ID",
        "SUREST_IND",
        "REASON_CODE",
    ]
    order_fields = [
        F.desc("CLM_PD_MONTH"),
        "FINANCIAL_CLIENT",
        "TIN",
        "CUST_ID",
        "SUREST_IND",
        "REASON_CODE",
    ]
else:
    group_fields = ["CLM_PD_DT", "CLM_PD_MONTH", "FINANCIAL_CLIENT", "REASON_CODE"]
    order_fields = [F.desc("CLM_PD_DT"), "CLM_PD_MONTH", "FINANCIAL_CLIENT", "REASON_CODE"]

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
    .groupBy("CLM_PD_MONTH")
    .agg(
        F.count("*").alias("Claim_Line_Count"),
        F.sum("Savings_Adjustment").alias("Savings_Adjustment"),
        F.sum("CHRG_AMT").cast(DecimalType(18, 2)).alias("CHRG_AMT"),
    )
    .orderBy(F.desc("CLM_PD_MONTH"))
)

display(
    by_month_display
    .withColumn("Claim_Line_Count", F.format_number("Claim_Line_Count", 2))
    .withColumn("Savings_Adjustment", F.format_number("Savings_Adjustment", 2))
    .withColumn("CHRG_AMT", F.format_number("CHRG_AMT", 2)),
)

by_day_display = (
    final
    .groupBy("CLM_PD_DT")
    .agg(
        F.count("*").alias("Claim_Line_Count"),
        F.sum("Savings_Adjustment").alias("Savings_Adjustment"),
        F.sum("CHRG_AMT").cast(DecimalType(18, 2)).alias("CHRG_AMT"),
    )
    .orderBy(F.desc("CLM_PD_DT"))
    .limit(35)
)

display(
    by_day_display
    .withColumn("Claim_Line_Count", F.format_number("Claim_Line_Count", 2))
    .withColumn("Savings_Adjustment", F.format_number("Savings_Adjustment", 2))
    .withColumn("CHRG_AMT", F.format_number("CHRG_AMT", 2)),
)

