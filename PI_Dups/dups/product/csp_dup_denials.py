# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # CSP Duplicate Denials

# COMMAND ----------

# DBTITLE 1,Inputs
from datetime import date

from pyspark.sql import Window
from pyspark.sql import functions as F

from dups.util.connection import extract_smart
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

product = "CSP"

reason_codes = (
    spark
    .table(get_source_table("dups_csp_rsn_code_dimension"))
    .select("Reason_Code")
    .distinct()
    .collect()
)
reason_codes2 = [row["Reason_Code"] for row in reason_codes]
reason_list = ",".join(f"'{x}'" for x in reason_codes2)
print(reason_codes2)

tre_membership = (
    spark
    .table(get_source_table("csp_tre_optum_membership"))
    .select("FIN_INC_MONTH", "FIN_MBI_HICN_FNL", "OPTUM_DELEGATION")
    .withColumnsRenamed(
        {"FIN_INC_MONTH": "ERLY_SRVC_MONTH", "FIN_MBI_HICN_FNL": "MEDICARE_NO"},
    )
)

# COMMAND ----------

# DBTITLE 1,Load Ratios
base_ratio_index_fields = [
    "SRVC_YEAR",
    "CLAIM_TYPE_DIM_ID_DERIV",
    "PROD_LVL_1_CODE",
    "CHRG_AMT_RANGE_MIN",
    "CHRG_AMT_RANGE_MAX",
]

ratio_join_keys = [
    [
        *base_ratio_index_fields,
        "COMPANY_DIM_ID",
        "MPIN",
        "TIN",
        "PROC_COS_CODE",
    ],
    [
        *base_ratio_index_fields,
        "COMPANY_DIM_ID",
        "TIN",
        "PROC_COS_CODE",
    ],
    [
        *base_ratio_index_fields,
        "COMPANY_DIM_ID",
        "PROC_COS_CODE",
        "PAR_STATUS",
    ],
    [
        *base_ratio_index_fields,
        "PROC_COS_CODE",
        "PAR_STATUS",
    ],
    [
        *base_ratio_index_fields,
        "COMPANY_DIM_ID",
        "PAR_STATUS",
    ],
]

ratios = [
    spark.table(get_source_table(f"{product.lower()}_b_to_a_ratios_lvl{rank}"))
    for rank in range(1, 6)
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

# DBTITLE 1,Additional Inputs
company = spark.table(get_source_table("dim_company"))
geography = spark.table(get_source_table("dim_geography_state"))
patch = spark.table(get_source_table("tblu_bh_patch_map"))
region = spark.table(get_source_table("tblu_ses_region_map"))

code_market = (
    company
    .join(
        geography,
        company["GEOGRAPHY_STATE_DIM_ID"] == geography["GEOGRAPHY_STATE_DIM_ID"],
        how="left",
    )
    .join(region, geography["STATE"] == region["State_Abbr"], how="left")
    .select(company["COMPANY_CODE"], region["Market"])
)

patch = patch.withColumn("CAL_YEAR_MONTH", F.date_format(F.col("month"), "yyyyMM"))

window_spec = Window.partitionBy("Market", "PROD_LVL_3_CODE").orderBy(
    F.col("CAL_YEAR_MONTH").desc(),
)
patch_with_rank = patch.withColumn("rn", F.row_number().over(window_spec))
bh_overrides_recent = patch_with_rank.filter(F.col("rn") == 1).drop(
    "month",
    "rn",
    "CAL_YEAR_MONTH",
)


def add_bh_overrides(df):
    df = df.withColumn(
        "CAL_YEAR_MONTH",
        F.date_format(F.col("DETAIL_SVC_DATE"), "yyyyMM"),
    )

    df = df.join(code_market, on="COMPANY_CODE", how="left")

    df = df.join(
        patch.select("Market", "PROD_LVL_3_CODE", "CAL_YEAR_MONTH", "patch_ind_final"),
        on=["Market", "PROD_LVL_3_CODE", "CAL_YEAR_MONTH"],
        how="left",
    )
    df = df.join(
        bh_overrides_recent.withColumnRenamed(
            "patch_ind_final",
            "patch_ind_final_recent",
        ),
        on=["Market", "PROD_LVL_3_CODE"],
        how="left",
    )
    df = df.withColumn(
        "patch_ind_final",
        F.coalesce(F.col("patch_ind_final"), F.col("patch_ind_final_recent")),
    )
    df = df.withColumn(
        "OBH_RISK",
        F
        .when(
            (F.col("patch_ind_final") == "Y") & (F.col("CLAIM_TYPE_DIM_ID").isin([6, 7])),
            "N",
        )
        .when(
            (F.col("PROD_LVL_1_CODE").isin(["HMO", "EPO"]))
            & (F.col("CLAIM_TYPE_DIM_ID").isin([6, 7])),
            "N",
        )
        .when(F.col("CLAIM_TYPE_DIM_ID").isin([6, 7]), "Y")
        .otherwise("N"),
    )
    return df.withColumn(
        "CLAIM_STATUS_TYPE_DESC_BH_MOD",
        F.when(
            (F.col("CLAIM_TYPE_DIM_ID").isin([6, 7]))
            & (F.col("CLAIM_STATUS_TYPE_DESC") == "Capitated"),
            "Fee for Service",
        ).otherwise(F.col("CLAIM_STATUS_TYPE_DESC")),
    )


# COMMAND ----------

# DBTITLE 1,Claim Extract
claim_query = f"""
WITH AVOIDED_REASONS AS (
  SELECT
    REASON_DIM_ID
  FROM DW.DIM_REASON_CODE
  WHERE
    REASON_CODE IN ({reason_list})
)
SELECT
  FC.ADJUD_DATE AS ADJD_DT,
  TO_CHAR(FC.ADJUD_DATE, 'yyyy-mm') AS ADJD_MONTH,
  FC.COMPANY_DIM_ID,
  COMPANY.COMPANY_CODE,
  CLAIM.CSCS_ID,
  CLAIM.CSPI_ID,
  GRGR_GROUP.GRGR_ID,
  PRODLVL.PROD_LVL_1_CODE,
  PRODLVL.PROD_LVL_3_CODE,
  DM.MEDICARE_NO,
  PROV.MPIN,
  PROV.IRS_TAX_ID AS TIN,
  FC.DETAIL_SVC_DATE,
  REV.PROCEDURE_CODE AS REVENUE_CODE,
  PROC.PROCEDURE_CODE,
  CASE
    WHEN FC.CLAIM_TYPE_DIM_ID = 1
    THEN PROC.PROCEDURE_CODE
    ELSE COS.COS_STL_3_DESC
  END AS PROC_COS_CODE,
  FC.BILLED_AMT,
  RC1.REASON_CODE AS ALLOWED_REASON_CODE,
  RC2.REASON_CODE AS NOT_COVERED_REASON_CODE,
  RC3.REASON_CODE AS ADJUSTMENT_REASON_CODE,
  RC4.REASON_CODE AS OC_PAID_REASON_CODE,
  RCEXTN.REASON_CODE AS EXTN_REASON_CODE,
  FC.CLAIM_TYPE_DIM_ID,
  CS.CLAIM_STATUS_TYPE_DESC,
  CASE WHEN FC.PROVIDER_PAR_DIM_ID = 1 THEN 'PAR' ELSE 'NON-PAR' END AS PAR_STATUS
FROM DW.FACT_CLAIM AS FC
LEFT JOIN SMR_PRD_RPT_DB.SRC_CSP.CMC_CLCL_CLAIM AS CLAIM
  ON FC.CLAIM_NUMBER = CLAIM.CLCL_ID
LEFT JOIN SMR_PRD_RPT_DB.SRC_CSP.CMC_GRGR_GROUP AS GRGR_GROUP
  ON CLAIM.GRGR_CK = GRGR_GROUP.GRGR_CK
JOIN DW.DIM_PROD_LVL_3 AS PRODLVL
  ON FC.PROD_LVL_3_DIM_ID = PRODLVL.PROD_LVL_3_DIM_ID
JOIN DW.DIM_COMPANY AS COMPANY
  ON FC.COMPANY_DIM_ID = COMPANY.COMPANY_DIM_ID
JOIN DW.DIM_COS_STL_4 AS COS
  ON FC.COS_STL_4_DIM_ID = COS.COS_STL_4_DIM_ID
JOIN DW.DIM_REASON_CODE AS RC1
  ON FC.ALLOWED_REASON_DIM_ID = RC1.REASON_DIM_ID
JOIN DW.DIM_REASON_CODE AS RC2
  ON FC.NOT_COVERED_REASON_DIM_ID = RC2.REASON_DIM_ID
JOIN DW.DIM_REASON_CODE AS RC3
  ON FC.ADJUSTMENT_REASON_DIM_ID = RC3.REASON_DIM_ID
JOIN DW.DIM_REASON_CODE AS RC4
  ON FC.OC_PAID_REASON_DIM_ID = RC4.REASON_DIM_ID
JOIN DW.DIM_PROCEDURE_CODE AS REV
  ON FC.REVENUE_CODE_DIM_ID = REV.PROCEDURE_DIM_ID
JOIN DW.DIM_PROCEDURE_CODE AS PROC
  ON FC.CPT_CODE_DIM_ID = PROC.PROCEDURE_DIM_ID
JOIN DW.DIM_CLAIM_STATUS AS CS
  ON FC.CLAIM_STATUS_DIM_ID = CS.CLAIM_STATUS_DIM_ID
JOIN DW.DIM_PROVIDER AS PROV
  ON FC.PROV_DIM_ID = PROV.PROV_DIM_ID
JOIN DW.DIM_MEMBER AS DM
  ON FC.MEMB_DIM_ID = DM.MEMB_DIM_ID AND FC.COMPANY_DIM_ID = DM.COMPANY_DIM_ID
LEFT JOIN (
  SELECT
    extn.COMPANY_DIM_ID,
    extn.SEQ_CLAIM_ID,
    extn.LINE_NUMBER,
    MIN(extn.reason_dim_id) AS reason_dim_id
  FROM DW.FACT_CLAIM_EXTN_REASON_CODE AS extn
  WHERE
    extn.reason_dim_id IN (
      SELECT
        REASON_DIM_ID
      FROM AVOIDED_REASONS
    )
  GROUP BY
    extn.COMPANY_DIM_ID,
    extn.SEQ_CLAIM_ID,
    extn.LINE_NUMBER
) AS EXTNReason
  ON EXTNReason.COMPANY_DIM_ID = FC.COMPANY_DIM_ID
  AND EXTNReason.SEQ_CLAIM_ID = FC.SEQ_CLAIM_ID
  AND EXTNReason.LINE_NUMBER = FC.LINE_NUMBER
LEFT JOIN DW.DIM_REASON_CODE AS RCEXTN
  ON EXTNReason.REASON_DIM_ID = RCEXTN.REASON_DIM_ID
WHERE
  FC.ADJUD_DATE >= '{min_proc_dt}'
  AND YEAR(FC.ADJUD_DATE) < 9000
  AND (
    FC.ALLOWED_REASON_DIM_ID IN (
      SELECT
        REASON_DIM_ID
      FROM AVOIDED_REASONS
    )
    OR FC.NOT_COVERED_REASON_DIM_ID IN (
      SELECT
        REASON_DIM_ID
      FROM AVOIDED_REASONS
    )
    OR FC.ADJUSTMENT_REASON_DIM_ID IN (
      SELECT
        REASON_DIM_ID
      FROM AVOIDED_REASONS
    )
    OR FC.OC_PAID_REASON_DIM_ID IN (
      SELECT
        REASON_DIM_ID
      FROM AVOIDED_REASONS
    )
    OR EXTNReason.reason_dim_id IN (
      SELECT
        REASON_DIM_ID
      FROM AVOIDED_REASONS
    )
  )
"""

rawclaims = extract_smart(claim_query).cache()

# COMMAND ----------

# DBTITLE 1,Missing Reason Codes

reason_code_suffix = "_REASON_CODE"
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
min_tre_date = tre_membership.agg(F.min("ERLY_SRVC_MONTH")).first()[0]
max_tre_date = tre_membership.agg(F.max("ERLY_SRVC_MONTH")).first()[0]

claims_with_tre = add_bh_overrides(rawclaims)
claims_with_tre = claims_with_tre.withColumn(
    "ERLY_SRVC_MONTH",
    F.date_format("DETAIL_SVC_DATE", "yyyyMM").cast("int"),
)

claims_with_tre = claims_with_tre.withColumn(
    "ERLY_SRVC_MONTH",
    F
    .when(F.col("ERLY_SRVC_MONTH") < min_tre_date, min_tre_date)
    .when(F.col("ERLY_SRVC_MONTH") > max_tre_date, max_tre_date)
    .otherwise(F.col("ERLY_SRVC_MONTH")),
)

claims_with_tre = claims_with_tre.join(
    tre_membership,
    on=["ERLY_SRVC_MONTH", "MEDICARE_NO"],
    how="left",
)

ohc_companies = ["UHGDC", "UHGDE", "UHGIA", "UHGMD", "UHGMO", "UHGPA", "UHGWA", "UHGWI"]

claims_with_tre = claims_with_tre.withColumn(
    "OPTUM_DELEGATION",
    F
    .when(F.col("PROD_LVL_1_CODE") != "DSNP", F.lit(None))
    .when(F.col("COMPANY_CODE").isin(ohc_companies), F.lit("OHC"))
    .otherwise(F.col("OPTUM_DELEGATION")),
)

claims_with_tre = claims_with_tre.withColumn(
    "FINANCIAL_CLIENT",
    F
    .when(F.col("OBH_RISK") == "Y", F.lit("OHBS"))
    .when(F.col("OPTUM_DELEGATION") == "OptumCare", F.lit("OptumCare"))
    .when(F.col("OPTUM_DELEGATION") == "OHC", F.lit("Optum Home and Community"))
    .when(F.col("PROD_LVL_1_CODE") == "Medicaid", F.lit("CnS Medicaid"))
    .when(F.col("PROD_LVL_1_CODE").isin("LTSS", "MMP", "LTSS_MAP"), F.lit("CnS LTSS"))
    .when(F.col("PROD_LVL_1_CODE") == "DSNP", F.lit("CnS DNSP"))
    .when(F.col("PROD_LVL_1_CODE").isin("HMO", "EPO"), F.lit("EnI IFP"))
    .otherwise(F.lit("Not Reported")),
)

# COMMAND ----------

# DBTITLE 1,Claim Processing
claims = claims_with_tre.withColumn("SRVC_YEAR", F.year("DETAIL_SVC_DATE"))

claims = claims.withColumn(
    "CLAIM_TYPE_DIM_ID_DERIV",
    F.when(F.col("CLAIM_TYPE_DIM_ID").isin([1, 6]), F.lit(1)).otherwise(F.lit(2)),
)

claims = claims.withColumn(
    "DERIV_PROC_REV_CD",
    F
    .when(
        ~F.col("REVENUE_CODE").isin("UNK", "N/A") & F.col("REVENUE_CODE").isNotNull(),
        F.col("REVENUE_CODE"),
    )
    .when(
        ~F.col("PROCEDURE_CODE").isin("UNK", "N/A", "9999") & F.col("PROCEDURE_CODE").isNotNull(),
        F.col("PROCEDURE_CODE"),
    )
    .otherwise("N/A"),
)
claims = claims.withColumn(
    "DERIV_PROC_REV_TYPE",
    F
    .when(
        ~F.col("REVENUE_CODE").isin("UNK", "N/A") & F.col("REVENUE_CODE").isNotNull(),
        F.lit("REVENUE_CODE"),
    )
    .when(
        ~F.col("PROCEDURE_CODE").isin("UNK", "N/A", "9999") & F.col("PROCEDURE_CODE").isNotNull(),
        F.lit("PROCEDURE_CODE"),
    )
    .otherwise("N/A"),
)

claims = claims.withColumn(
    "CHRG_AMT_RANGE_MIN",
    F
    .when(F.col("CLAIM_TYPE_DIM_ID_DERIV") == 2, F.lit(0))
    .when(F.col("BILLED_AMT") >= 100000, F.lit(100000))
    .when(F.col("BILLED_AMT") >= 50000, F.lit(50000))
    .when(F.col("BILLED_AMT") >= 20000, F.lit(20000))
    .when(F.col("BILLED_AMT") >= 10000, F.lit(10000))
    .when(F.col("BILLED_AMT") >= 5000, F.lit(5000))
    .otherwise(F.lit(0)),
)

claims = claims.withColumn(
    "CHRG_AMT_RANGE_MAX",
    F
    .when(F.col("CLAIM_TYPE_DIM_ID_DERIV") == 2, F.lit(99999999))
    .when(F.col("BILLED_AMT") >= 100000, F.lit(99999999))
    .when(F.col("BILLED_AMT") >= 50000, F.lit(100000))
    .when(F.col("BILLED_AMT") >= 20000, F.lit(50000))
    .when(F.col("BILLED_AMT") >= 10000, F.lit(20000))
    .when(F.col("BILLED_AMT") >= 5000, F.lit(10000))
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
        "bill_to_allow_5",
        F.lit(0.3),
    ),
)

final = joined.withColumn(
    "Savings_Adjustment",
    (F.col("BILLED_AMT") * F.col("Bill_to_Primary_Allow")).cast("decimal(18,2)"),
)

reason_code_priority = F.coalesce(
    F.when(F.col("ALLOWED_REASON_CODE").isin(reason_codes2), F.col("ALLOWED_REASON_CODE")),
    F.when(
        F.col("NOT_COVERED_REASON_CODE").isin(reason_codes2),
        F.col("NOT_COVERED_REASON_CODE"),
    ),
    F.when(
        F.col("ADJUSTMENT_REASON_CODE").isin(reason_codes2),
        F.col("ADJUSTMENT_REASON_CODE"),
    ),
    F.when(F.col("OC_PAID_REASON_CODE").isin(reason_codes2), F.col("OC_PAID_REASON_CODE")),
    F.when(F.col("EXTN_REASON_CODE").isin(reason_codes2), F.col("EXTN_REASON_CODE")),
    F.col("ALLOWED_REASON_CODE"),
    F.col("NOT_COVERED_REASON_CODE"),
    F.col("ADJUSTMENT_REASON_CODE"),
    F.col("OC_PAID_REASON_CODE"),
    F.col("EXTN_REASON_CODE"),
)

final = final.withColumn("REASON_CODE", reason_code_priority)
final = final.cache()
rawclaims.unpersist()

# COMMAND ----------

summary_by_claim_type = (
    final
    .groupBy("CLAIM_TYPE_DIM_ID_DERIV")
    .agg(
        F.count("*").alias("row_count"),
    )
    .orderBy("CLAIM_TYPE_DIM_ID_DERIV")
)
display(
    summary_by_claim_type.withColumn("row_count", F.format_number("row_count", 2)),
)

# COMMAND ----------

row_count = final.select(F.count_if(F.col("CLAIM_TYPE_DIM_ID_DERIV") == 2))
display(row_count)

# COMMAND ----------

from pyspark.databricks.sql.functions import approx_top_k
from pyspark.sql.functions import col, explode

top_k_df = (
    final
    .groupBy("DERIV_PROC_REV_TYPE")
    .agg(approx_top_k("DERIV_PROC_REV_CD", 5).alias("top_codes"))
    .withColumn("top_code", explode("top_codes"))
    .select(
        "DERIV_PROC_REV_TYPE",
        col("top_code.item").alias("DERIV_PROC_REV_CD"),
        col("top_code.count").alias("frequency"),
    )
    .orderBy("DERIV_PROC_REV_TYPE", col("frequency").desc())
)

display(top_k_df)

# COMMAND ----------

summary_non_null = (
    final
    .groupBy("DERIV_PROC_REV_TYPE")
    .agg(
        F.count(F.col("bill_to_allow_1")).alias("non_null_bill_to_allow_1"),
        F.count(F.col("bill_to_allow_2")).alias("non_null_bill_to_allow_2"),
        F.count(F.col("bill_to_allow_3")).alias("non_null_bill_to_allow_3"),
        F.count(F.col("bill_to_allow_4")).alias("non_null_bill_to_allow_4"),
        F.count(F.col("bill_to_allow_4")).alias("non_null_bill_to_allow_5"),
    )
    .orderBy("DERIV_PROC_REV_TYPE")
)
display(summary_non_null)

# COMMAND ----------

# DBTITLE 1,Export Summary
from dups.util.table_config import get_output_table

catalog_table = get_output_table(product)

if run_type == "full":
    group_fields = [
        "ADJD_MONTH",
        "FINANCIAL_CLIENT",
        "OPTUM_DELEGATION",
        "TIN",
        "CSCS_ID",
        "CSPI_ID",
        "GRGR_ID",
        "COMPANY_CODE",
        "REASON_CODE",
    ]
    order_fields = [
        F.desc("ADJD_MONTH"),
        "FINANCIAL_CLIENT",
        "OPTUM_DELEGATION",
        "TIN",
        "CSCS_ID",
        "CSPI_ID",
        "GRGR_ID",
        "COMPANY_CODE",
        "REASON_CODE",
    ]
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
        F.sum("BILLED_AMT").cast("decimal(18,2)").alias("BILLED_AMT"),
    )
    .orderBy(F.desc("ADJD_MONTH"))
)

display(
    by_month_display
    .withColumn("Claim_Line_Count", F.format_number("Claim_Line_Count", 2))
    .withColumn("Savings_Adjustment", F.format_number("Savings_Adjustment", 2))
    .withColumn("BILLED_AMT", F.format_number("BILLED_AMT", 2)),
)

by_day_display = (
    final
    .groupBy("ADJD_DT")
    .agg(
        F.count("*").alias("Claim_Line_Count"),
        F.sum("Savings_Adjustment").alias("Savings_Adjustment"),
        F.sum("BILLED_AMT").cast("decimal(18,2)").alias("BILLED_AMT"),
    )
    .orderBy(F.desc("ADJD_DT"))
    .limit(35)
)

display(
    by_day_display
    .withColumn("Claim_Line_Count", F.format_number("Claim_Line_Count", 2))
    .withColumn("Savings_Adjustment", F.format_number("Savings_Adjustment", 2))
    .withColumn("BILLED_AMT", F.format_number("BILLED_AMT", 2)),
)

