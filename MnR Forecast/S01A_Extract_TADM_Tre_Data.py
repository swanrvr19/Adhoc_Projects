# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # S01 — Claim Extract

# COMMAND ----------

# DBTITLE 1,Imports
from pyspark.sql import functions as F

# COMMAND ----------

# DBTITLE 1,Define S0 Config
# MAGIC %run "./S00_Config"

# COMMAND ----------

MIN_SRVC_YEAR = 2022

# COMMAND ----------

# MAGIC %md
# MAGIC # Physician Claims

# COMMAND ----------

# DBTITLE 1,PH Extract: Append then Dedup
# Two-step extract:
#   Step 1 – Straight append for yearly tables (no overlap possible).
#   Step 2 – Incremental append + dedup for remaining tables against the
#            consolidated Step 1 result AND each other.

STEP1_APPEND_TABLES = [
    #"prod_tadm.mr_cos_prod_event.glxy_pr_f_2021",
    "prod_tadm.mr_cos_prod_event.glxy_pr_f_2022",
]  

STEP2_APPEND_AND_DEDUP_TABLES = [
    "prod_tadm.mr_cos_prod_event.glxy_pr_f_202607",
]  

DIMENSIONS = {
    "fin_inc_month": "CAST(DATE_FORMAT({fst_srvc_dt}, 'yyyyMM') AS INT)",
    "service_code": "{service_code}",
    "catgy_rol_up_2_desc": "{catgy_rol_up_2_desc}",
    "fst_srvc_dt": "{fst_srvc_dt}",
    "cos_hccc_cd": "{cos_hccc_cd}",
    "site_cd": "{site_cd}",
    "global_cap": "{global_cap}",
    "market_fnl": "{market_fnl}",
    "tadmprodrollup_fnl": "{tadmprodrollup_fnl}",
    "tfm_product_fnl": "{tfm_product_fnl}",
    "segment_name_fnl": "{segment_name_fnl}",
    "drug_cov_type_fnl": "{drug_cov_type_fnl}",
    "tfm_product_new_fnl": "{tfm_product_new_fnl}",
    "migration_source": "{migration_source}",
    "region_fnl": "{region_fnl}",
    "region1_fnl": "{region1_fnl}",
    "product_level_1_fnl": "{product_level_1_fnl}",
    "product_level_2_fnl": "{product_level_2_fnl}",
    "product_level_3_fnl": "{product_level_3_fnl}",
    "plan_level_1_fnl": "{plan_level_1_fnl}",
    "plan_level_2_fnl": "{plan_level_2_fnl}",
    "group_ind_fnl": "{group_ind_fnl}",
    "fin_submarket": "{fin_submarket}",
    "fin_scc": "{fin_scc}",
    "contractpbp_fnl": "{contractpbp_fnl}",
    "ccreconadjmkt_fnl": "{ccreconadjmkt_fnl}",
    "special_network": "{special_network}",
    "delegated_entity": "{delegated_entity}",
    "erickson_desc_fnl": "{erickson_desc_fnl}",
    "tfm_include_flag": "{tfm_include_flag}",
    "adjd_dt": "{adjd_dt}",
}
MEASURES = {
    "row_cnt": "COUNT(*)",
    "distinct_clm_cnt": "COUNT(DISTINCT {site_clm_aud_nbr})",
    "sum_tadm_units": "SUM({tadm_units})",
    "sum_visits": "SUM({visits})",
    "sum_srvc_unit_cnt": "SUM({srvc_unit_cnt})",
    "sum_adj_srvc_unit_cnt": "SUM({adj_srvc_unit_cnt})",
    "sum_src_chrg_amt": "SUM({src_chrg_amt})",
    "sum_allw_amt": "SUM({allw_amt_fnl})",
    "sum_net_pd_amt": "SUM({net_pd_amt_fnl})",
    "sum_case_cnt": "CAST(0 AS DOUBLE)",
    "sum_fst_visits": "CAST(0 AS DOUBLE)",
    "sum_calc_tadm_procedures": "CAST(0 AS DOUBLE)",
    "sum_tadm_hcta_util": "CAST(0 AS DOUBLE)",
    "sum_admits": "CAST(0 AS DOUBLE)",
    "sum_qtydays": "CAST(0 AS DOUBLE)",
}
FILTER_TEMPLATE = f"{{service_code}} not in ('PR_CLM_DNL', 'PR_DWNADJ_DNL') AND {{denial_f}} = 'N' AND YEAR({{fst_srvc_dt}}) >= {MIN_SRVC_YEAR}"
DEDUP_KEYS = ["site_clm_aud_nbr", "fst_srvc_dt"]


def resolve(template, alias):
    """Substitute {col} placeholders with alias-qualified column names."""
    class _Resolver(dict):
        def __missing__(self, key):
            return f"{alias}.{key}"
    return template.format_map(_Resolver())


# --- Step 1: Append-only (no dedup) ---
step1_branches = []
for i, table in enumerate(STEP1_APPEND_TABLES):
    alias = f"s1_{i}"
    select_list = [f"{resolve(expr, alias)} AS {name}"
                   for name, expr in {**DIMENSIONS, **MEASURES}.items()]
    where_clause = resolve(FILTER_TEMPLATE, alias)
    step1_branches.append(
        f"SELECT {', '.join(select_list)}\n"
        f"        FROM {table} {alias}\n"
        f"        WHERE {where_clause}\n"
        f"        GROUP BY ALL"
    )

step1_query = "\n\nUNION ALL\n\n".join(step1_branches)

# --- Step 2: Append + dedup vs. Step 1 tables and earlier Step 2 tables ---
step2_branches = []
for i, table in enumerate(STEP2_APPEND_AND_DEDUP_TABLES):
    alias = f"s2_{i}"
    select_list = [f"{resolve(expr, alias)} AS {name}"
                   for name, expr in {**DIMENSIONS, **MEASURES}.items()]
    where_clause = resolve(FILTER_TEMPLATE, alias)
    key_exprs = [resolve("{" + k + "}", alias) for k in DEDUP_KEYS]

    # Exclude claims already present in any Step 1 table
    dedup_clauses = ""
    for j, prior_table in enumerate(STEP1_APPEND_TABLES):
        prior_alias = f"p1_{j}"
        prior_key_exprs = [resolve("{" + k + "}", prior_alias) for k in DEDUP_KEYS]
        conds = " AND ".join(f"{pk} = {ck}" for pk, ck in zip(prior_key_exprs, key_exprs))
        dedup_clauses += f"\n  AND NOT EXISTS (SELECT 1 FROM {prior_table} {prior_alias} WHERE {conds})"

    # Exclude claims already present in earlier Step 2 tables
    for j, prior_table in enumerate(STEP2_APPEND_AND_DEDUP_TABLES[:i]):
        prior_alias = f"p2_{j}"
        prior_key_exprs = [resolve("{" + k + "}", prior_alias) for k in DEDUP_KEYS]
        conds = " AND ".join(f"{pk} = {ck}" for pk, ck in zip(prior_key_exprs, key_exprs))
        dedup_clauses += f"\n  AND NOT EXISTS (SELECT 1 FROM {prior_table} {prior_alias} WHERE {conds})"

    step2_branches.append(
        f"SELECT {', '.join(select_list)}\n"
        f"        FROM {table} {alias}\n"
        f"        WHERE {where_clause}{dedup_clauses}\n"
        f"        GROUP BY ALL"
    )

# --- Combine Step 1 + Step 2 ---
full_query = step1_query + "\n\nUNION ALL\n\n" + "\n\nUNION ALL\n\n".join(step2_branches)

df = spark.sql(full_query)
print(f"Total row count: {df.count():,}")

display(df)

# COMMAND ----------

# DBTITLE 1,Cell 6
# MAGIC %md
# MAGIC # Outpatient Claims

# COMMAND ----------

# DBTITLE 1,OP Extract: Append then Dedup
# Outpatient extract — mirrors PR Cell 5 structure.
# Differences:
#   - Tables: glxy_op_f_* instead of glxy_pr_f_*
#   - service_code → hce_service_code  (aligns with CF OP table's HCEBKCAT;
#     service_code includes svc_cat_override which inflates FACMISC and deflates OBS)
#   - Filter: OP_CLM_DNL / OP_DWNADJ_DNL still on service_code (denial codes live there)
#   - op_f_2022 lacks erickson_desc_fnl → use NULL (CFs don't apply that far back)

OP_STEP1_TABLES = [
    "prod_tadm.mr_cos_prod_event.glxy_op_f_2022",
]
OP_STEP2_TABLES = [
    "prod_tadm.mr_cos_prod_event.glxy_op_f_202607",
]

# Same dimensions as PR, but remap service_code → hce_service_code to match CF HCEBKCAT
OP_DIMENSIONS = {**DIMENSIONS}
OP_DIMENSIONS["service_code"] = "{hce_service_code}"

OP_DIM_OVERRIDES = {
    "prod_tadm.mr_cos_prod_event.glxy_op_f_2022": {
        "erickson_desc_fnl": "CAST(NULL AS STRING)",
    }
}

OP_MEASURES = {**MEASURES}
OP_MEASURES["sum_case_cnt"] = "SUM({case_cnt})"
OP_MEASURES["sum_fst_visits"] = "SUM({fst_visits})"
OP_MEASURES["sum_calc_tadm_procedures"] = "SUM({calc_tadm_procedures})"
OP_MEASURES["sum_tadm_hcta_util"] = "SUM({tadm_hcta_util})"

OP_FILTER_TEMPLATE = f"{{service_code}} NOT IN ('OP_CLM_DNL', 'OP_DWNADJ_DNL') AND {{denial_f}} = 'N' AND YEAR({{fst_srvc_dt}}) >= {MIN_SRVC_YEAR}"
OP_DEDUP_KEYS = DEDUP_KEYS


def get_dims(base_dims, table, overrides):
    """Return dimensions with per-table overrides applied."""
    dims = {**base_dims}
    if table in overrides:
        dims.update(overrides[table])
    return dims


# --- Step 1: Append-only ---
op_step1_branches = []
for i, table in enumerate(OP_STEP1_TABLES):
    alias = f"op1_{i}"
    dims = get_dims(OP_DIMENSIONS, table, OP_DIM_OVERRIDES)
    select_list = [f"{resolve(expr, alias)} AS {name}"
                   for name, expr in {**dims, **OP_MEASURES}.items()]
    where_clause = resolve(OP_FILTER_TEMPLATE, alias)
    op_step1_branches.append(
        f"SELECT {', '.join(select_list)}\n"
        f"        FROM {table} {alias}\n"
        f"        WHERE {where_clause}\n"
        f"        GROUP BY ALL"
    )

op_step1_query = "\n\nUNION ALL\n\n".join(op_step1_branches)

# --- Step 2: Append + dedup ---
op_step2_branches = []
for i, table in enumerate(OP_STEP2_TABLES):
    alias = f"op2_{i}"
    dims = get_dims(OP_DIMENSIONS, table, OP_DIM_OVERRIDES)
    select_list = [f"{resolve(expr, alias)} AS {name}"
                   for name, expr in {**dims, **OP_MEASURES}.items()]
    where_clause = resolve(OP_FILTER_TEMPLATE, alias)
    key_exprs = [resolve("{" + k + "}", alias) for k in OP_DEDUP_KEYS]

    dedup_clauses = ""
    for j, prior_table in enumerate(OP_STEP1_TABLES):
        prior_alias = f"opp1_{j}"
        prior_key_exprs = [resolve("{" + k + "}", prior_alias) for k in OP_DEDUP_KEYS]
        conds = " AND ".join(f"{pk} = {ck}" for pk, ck in zip(prior_key_exprs, key_exprs))
        dedup_clauses += f"\n  AND NOT EXISTS (SELECT 1 FROM {prior_table} {prior_alias} WHERE {conds})"

    for j, prior_table in enumerate(OP_STEP2_TABLES[:i]):
        prior_alias = f"opp2_{j}"
        prior_key_exprs = [resolve("{" + k + "}", prior_alias) for k in OP_DEDUP_KEYS]
        conds = " AND ".join(f"{pk} = {ck}" for pk, ck in zip(prior_key_exprs, key_exprs))
        dedup_clauses += f"\n  AND NOT EXISTS (SELECT 1 FROM {prior_table} {prior_alias} WHERE {conds})"

    op_step2_branches.append(
        f"SELECT {', '.join(select_list)}\n"
        f"        FROM {table} {alias}\n"
        f"        WHERE {where_clause}{dedup_clauses}\n"
        f"        GROUP BY ALL"
    )

# --- Combine ---
if op_step2_branches:
    op_full_query = op_step1_query + "\n\nUNION ALL\n\n" + "\n\nUNION ALL\n\n".join(op_step2_branches)
else:
    op_full_query = op_step1_query

df_op = spark.sql(op_full_query)
print(f"OP total row count: {df_op.count():,}")

display(df_op)

# COMMAND ----------

# DBTITLE 1,Cell 8
# MAGIC %md
# MAGIC # Inpatient Claims

# COMMAND ----------

# DBTITLE 1,IP Extract: Append then Dedup
# Inpatient extract — mirrors PR Cell 5 structure.
# Differences:
#   - Tables: glxy_ip_admit_f_* instead of glxy_pr_f_*
#   - service_code → tadm_admit_type  (maps to IP CF's HCEPRCAT)
#   - sum_tadm_units → SUM(tadm_qtydays)  (days instead of units)
#   - sum_visits → SUM(tadm_admits)  (admits instead of visits)
#   - No service-code denial filter (IP has no CLM_DNL/DWNADJ_DNL categories)

IP_STEP1_TABLES = [
    "prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_2022",
]
IP_STEP2_TABLES = [
    "prod_tadm.mr_cos_prod_event.glxy_ip_admit_f_202607",
]

# IP dimensions: remap service_code to tadm_admit_type
IP_DIMENSIONS = {**DIMENSIONS}
IP_DIMENSIONS["service_code"] = "{tadm_admit_type}"

IP_DIM_OVERRIDES = {}

# IP measures: remap units and visits to IP equivalents
IP_MEASURES = {**MEASURES}
IP_MEASURES["sum_tadm_units"] = "SUM({tadm_qtydays})"
IP_MEASURES["sum_visits"] = "SUM({tadm_admits})"
IP_MEASURES["sum_admits"] = "SUM({admits})"
IP_MEASURES["sum_qtydays"] = "SUM({qtydays})"

# Exclude OTH (not in CF table) + standard denial/year filter
IP_FILTER_TEMPLATE = f"{{tadm_admit_type}} NOT IN ('OTH') AND {{denial_f}} = 'N' AND YEAR({{fst_srvc_dt}}) >= {MIN_SRVC_YEAR}"
IP_DEDUP_KEYS = DEDUP_KEYS


# --- Step 1: Append-only ---
ip_step1_branches = []
for i, table in enumerate(IP_STEP1_TABLES):
    alias = f"ip1_{i}"
    dims = get_dims(IP_DIMENSIONS, table, IP_DIM_OVERRIDES)
    select_list = [f"{resolve(expr, alias)} AS {name}"
                   for name, expr in {**dims, **IP_MEASURES}.items()]
    where_clause = resolve(IP_FILTER_TEMPLATE, alias)
    ip_step1_branches.append(
        f"SELECT {', '.join(select_list)}\n"
        f"        FROM {table} {alias}\n"
        f"        WHERE {where_clause}\n"
        f"        GROUP BY ALL"
    )

ip_step1_query = "\n\nUNION ALL\n\n".join(ip_step1_branches)

# --- Step 2: Append + dedup ---
ip_step2_branches = []
for i, table in enumerate(IP_STEP2_TABLES):
    alias = f"ip2_{i}"
    dims = get_dims(IP_DIMENSIONS, table, IP_DIM_OVERRIDES)
    select_list = [f"{resolve(expr, alias)} AS {name}"
                   for name, expr in {**dims, **IP_MEASURES}.items()]
    where_clause = resolve(IP_FILTER_TEMPLATE, alias)
    key_exprs = [resolve("{" + k + "}", alias) for k in IP_DEDUP_KEYS]

    dedup_clauses = ""
    for j, prior_table in enumerate(IP_STEP1_TABLES):
        prior_alias = f"ipp1_{j}"
        prior_key_exprs = [resolve("{" + k + "}", prior_alias) for k in IP_DEDUP_KEYS]
        conds = " AND ".join(f"{pk} = {ck}" for pk, ck in zip(prior_key_exprs, key_exprs))
        dedup_clauses += f"\n  AND NOT EXISTS (SELECT 1 FROM {prior_table} {prior_alias} WHERE {conds})"

    for j, prior_table in enumerate(IP_STEP2_TABLES[:i]):
        prior_alias = f"ipp2_{j}"
        prior_key_exprs = [resolve("{" + k + "}", prior_alias) for k in IP_DEDUP_KEYS]
        conds = " AND ".join(f"{pk} = {ck}" for pk, ck in zip(prior_key_exprs, key_exprs))
        dedup_clauses += f"\n  AND NOT EXISTS (SELECT 1 FROM {prior_table} {prior_alias} WHERE {conds})"

    ip_step2_branches.append(
        f"SELECT {', '.join(select_list)}\n"
        f"        FROM {table} {alias}\n"
        f"        WHERE {where_clause}{dedup_clauses}\n"
        f"        GROUP BY ALL"
    )

# --- Combine ---
if ip_step2_branches:
    ip_full_query = ip_step1_query + "\n\nUNION ALL\n\n" + "\n\nUNION ALL\n\n".join(ip_step2_branches)
else:
    ip_full_query = ip_step1_query

df_ip = spark.sql(ip_full_query)
print(f"IP total row count: {df_ip.count():,}")

display(df_ip)

# COMMAND ----------

# DBTITLE 1,Cell 10
# MAGIC %md
# MAGIC # Stack Claims (PH + OP + IP)

# COMMAND ----------

# DBTITLE 1,Stack PH + OP + IP with HCC field
# Add HCC identifier and stack all three claim types.
# Reassigns `df` so the downstream Write cell picks up the combined result.

df = (
    df.withColumn("hcc", F.lit("PH"))
    .unionByName(df_op.withColumn("hcc", F.lit("OP")))
    .unionByName(df_ip.withColumn("hcc", F.lit("IP")))
)

print(f"Combined total rows: {df.count():,}")
display(df.groupBy("hcc").agg(F.count("*").alias("rows"), F.sum("sum_allw_amt").alias("total_allw")).orderBy("hcc"))

# COMMAND ----------

# DBTITLE 1,Derive val_date
# Derive val_date from max claim YR_MO (exclude MBR rows, which carry prospective enrollment)
_max_yrmo = df.selectExpr("MAX(fst_srvc_dt) AS m").collect()[0]["m"]
print(f"Max Year Month: {_max_yrmo}")
val_date = f"{_max_yrmo.strftime('%Y-%m')}-01"
print(f"Valuation Date: {val_date}")

# COMMAND ----------

# DBTITLE 1,Write Claims Table

df = df.withColumn("VAL_DATE", F.lit(val_date).cast("date"))

write_to_catalog(spark, df, table_fqn("clm"), f"VAL_DATE = DATE('{val_date}')")

# COMMAND ----------

# spark.sql("DROP TABLE IF EXISTS prod_tadm.mr_cos_prod_actuarial.DEV_TFM_HCTA_mnr_mbr_DATA")

# COMMAND ----------

# MAGIC %md
# MAGIC # Membership

# COMMAND ----------

# DBTITLE 1,Two-Step Membership Extract: Append then Dedup
# Membership two-step extract (mirrors claims Cell 3 structure):
#   Step 1 – Straight append for yearly tables (no overlap possible).
#   Step 2 – Incremental append + dedup for remaining tables against the
#            consolidated Step 1 result AND each other.

# --- Table Groups ---
MBR_STEP1_APPEND_TABLES = [
    # "prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_2021",
    "prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_2022",
]

MBR_STEP2_APPEND_AND_DEDUP_TABLES = [
    "prod_tadm.mr_cos_prod_event.gl_rstd_gpsgalnce_f_202607",
]

# --- Dimensions (GROUP BY columns) ---
MBR_DIMENSIONS = {
    "fin_inc_month": "CAST({fin_inc_month} AS INT)",
    "global_cap": "{global_cap}",
    "market_fnl": "{fin_market}",
    "tadmprodrollup_fnl": "{fin_tadmprodrollup}",
    "tfm_product_fnl": "{fin_tfm_product}",
    "segment_name_fnl": "{fin_segment_name}",
    "drug_cov_type_fnl": "{fin_ma_mapd}",
    "migration_source": "{migration_source}",
    "tfm_product_new_fnl": "{fin_tfm_product_new}",
    "region_fnl": "{fin_region}",
    "region1_fnl": "{fin_region1}",
    "product_level_1_fnl": "{fin_product_level_1}",
    "product_level_2_fnl": "{fin_product_level_2}",
    "product_level_3_fnl": "{fin_product_level_3}",
    "plan_level_1_fnl": "{fin_plan_level_1}",
    "plan_level_2_fnl": "{fin_plan_level_2}",
    "group_ind_fnl": "{fin_g_i}",
    "fin_submarket": "{fin_submarket}",
    "fin_scc": "{fin_scc}",
    "contractpbp_fnl": "{fin_contractpbp}",
    "ccreconadjmkt_fnl": "{fin_ccreconadjmkt}",
    "special_network": "{fin_special_network}",
    "delegated_entity": "{delegated_entity}",
    "erickson_desc_fnl": "{erickson_desc}",
    "tfm_include_flag": "{tfm_include_flag}",
    "fin_risk_type": "{fin_risk_type}",
}

# --- Measures (aggregated columns) ---
MBR_MEASURES = {
    "sum_member_cnt": "SUM({fin_member_cnt})"
}

# --- Filter & Dedup Keys ---
# No claims-style filter needed for membership; add FIN_MAX_ENROLL_IND = 1
# below if you want to restrict to the max-enrollment snapshot per member.
MBR_FILTER_TEMPLATE = f"{{global_cap}} = 'NA' AND {{fin_source_name}} = 'COSMOS' AND {{fin_tfm_product_new}} NOT IN ('PEOPLES HEALTH') AND {{sgr_source_name}} = 'COSMOS' AND CAST({{fin_inc_month}} AS INT) >= {MIN_SRVC_YEAR * 100}"
MBR_DEDUP_KEYS = ["fin_hicn", "fin_inc_month"]


def mbr_resolve(template, alias):
    """Substitute {col} placeholders with alias-qualified column names."""
    class _Resolver(dict):
        def __missing__(self, key):
            return f"{alias}.{key}"
    return template.format_map(_Resolver())


# --- Step 1: Append-only (no dedup) ---
mbr_step1_branches = []
for i, table in enumerate(MBR_STEP1_APPEND_TABLES):
    alias = f"m1_{i}"
    select_list = [f"{mbr_resolve(expr, alias)} AS {name}"
                   for name, expr in {**MBR_DIMENSIONS, **MBR_MEASURES}.items()]
    where_clause = mbr_resolve(MBR_FILTER_TEMPLATE, alias)
    mbr_step1_branches.append(
        f"SELECT {', '.join(select_list)}\n"
        f"        FROM {table} {alias}\n"
        f"        WHERE {where_clause}\n"
        f"        GROUP BY ALL"
    )

mbr_step1_query = "\n\nUNION ALL\n\n".join(mbr_step1_branches)

# --- Step 2: Append + dedup vs. Step 1 tables and earlier Step 2 tables ---
mbr_step2_branches = []
for i, table in enumerate(MBR_STEP2_APPEND_AND_DEDUP_TABLES):
    alias = f"m2_{i}"
    select_list = [f"{mbr_resolve(expr, alias)} AS {name}"
                   for name, expr in {**MBR_DIMENSIONS, **MBR_MEASURES}.items()]
    where_clause = mbr_resolve(MBR_FILTER_TEMPLATE, alias)
    key_exprs = [mbr_resolve("{" + k + "}", alias) for k in MBR_DEDUP_KEYS]

    # Exclude members already present in any Step 1 table
    dedup_clauses = ""
    for j, prior_table in enumerate(MBR_STEP1_APPEND_TABLES):
        prior_alias = f"mp1_{j}"
        prior_key_exprs = [mbr_resolve("{" + k + "}", prior_alias) for k in MBR_DEDUP_KEYS]
        conds = " AND ".join(f"{pk} = {ck}" for pk, ck in zip(prior_key_exprs, key_exprs))
        dedup_clauses += f"\n  AND NOT EXISTS (SELECT 1 FROM {prior_table} {prior_alias} WHERE {conds})"

    # Exclude members already present in earlier Step 2 tables
    for j, prior_table in enumerate(MBR_STEP2_APPEND_AND_DEDUP_TABLES[:i]):
        prior_alias = f"mp2_{j}"
        prior_key_exprs = [mbr_resolve("{" + k + "}", prior_alias) for k in MBR_DEDUP_KEYS]
        conds = " AND ".join(f"{pk} = {ck}" for pk, ck in zip(prior_key_exprs, key_exprs))
        dedup_clauses += f"\n  AND NOT EXISTS (SELECT 1 FROM {prior_table} {prior_alias} WHERE {conds})"

    mbr_step2_branches.append(
        f"SELECT {', '.join(select_list)}\n"
        f"        FROM {table} {alias}\n"
        f"        WHERE {where_clause}{dedup_clauses}\n"
        f"        GROUP BY ALL"
    )

# --- Combine Step 1 + Step 2 ---
if mbr_step2_branches:
    mbr_full_query = mbr_step1_query + "\n\nUNION ALL\n\n" + "\n\nUNION ALL\n\n".join(mbr_step2_branches)
else:
    mbr_full_query = mbr_step1_query

df_mbr = spark.sql(mbr_full_query)
print(f"Membership total row count: {df_mbr.count():,}")

_max_yrmo = df_mbr.selectExpr("MAX(FIN_INC_MONTH) AS m").collect()[0]["m"]
print(f"Max Year Month: {_max_yrmo}")

df_mbr = df_mbr.withColumn("VAL_DATE", F.lit(val_date).cast("date"))

display(df_mbr)

# COMMAND ----------

# DBTITLE 1,Write Membership Table
write_to_catalog(spark, df_mbr, table_fqn("mbr"), f"VAL_DATE = DATE('{val_date}')")

# COMMAND ----------

# DBTITLE 1,Check: PMPM by Month
# Calculate PMPM by month: total net paid / total members
clm_monthly = (
    spark.read.table(table_fqn("clm"))
    .groupBy("fin_inc_month")
    .agg(F.sum("sum_allw_amt").alias("total_allw_amt"),
         F.sum("sum_net_pd_amt").alias("total_net_paid"))
)

mbr_monthly = (
    spark.read.table(table_fqn("mbr"))
    .groupBy("fin_inc_month")
    .agg(F.sum("sum_member_cnt").alias("total_members"))
)

pmpm_by_month = (
    clm_monthly
    .join(mbr_monthly, on="fin_inc_month", how="inner")
    .withColumn("allw_pmpm", F.col("total_allw_amt") / F.col("total_members"))
    .withColumn("net_pmpm", F.col("total_net_paid") / F.col("total_members"))
    .orderBy("fin_inc_month")
)

display(pmpm_by_month)

