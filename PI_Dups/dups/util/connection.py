from pyspark.sql import DataFrame

from shared.databricks_env import get_secret, get_spark

pk = get_secret("snowflaketoken")


def extract_udw(query: str) -> DataFrame:
    sf_options = {
        "sfURL": "uhgdwaas.east-us-2.azure.snowflakecomputing.com",
        "sfUser": "dan.colestock@optum.com",
        "sfDatabase": "ZJX_PRD_UHCCD_DB",
        "sfSchema": "UDWBASESECUREVIEW1",
        "sfWarehouse": "ZSUVG_PRD_OPTUM_OGADV_DW01_WH",
        "sfRole": "HCDP_OPTUM_OGADV_ADV_SVCS_PROVIDER_02_DATA_VIEWER_PRD_DAG_ROLE",
        "pem_private_key": pk,
    }
    return (
        get_spark()
        .read.format("snowflake")
        .options(**sf_options)
        .option("query", query)
        .load()
        .cache()
    )


def extract_galaxy(query: str) -> DataFrame:
    sf_options = {
        "sfURL": "uhgdwaas.east-us-2.azure.snowflakecomputing.com",
        "sfUser": "dan.colestock@optum.com",
        "sfDatabase": "ZJX_PRD_UHCCD_DB",
        "sfSchema": "Galaxy",
        "sfWarehouse": "ZSUVG_PRD_OPTUM_OGADV_DW01_WH",
        "sfRole": "HCDP_OPTUM_OGADV_ADV_SVCS_PROVIDER_02_DATA_VIEWER_PRD_DAG_ROLE",
        "pem_private_key": pk,
    }
    return (
        get_spark()
        .read.format("snowflake")
        .options(**sf_options)
        .option("query", query)
        .load()
        .cache()
    )


def extract_smart(query: str) -> DataFrame:
    sf_options = {
        "sfURL": "uhgdwaas.east-us-2.azure.snowflakecomputing.com",
        "sfUser": "dan.colestock@optum.com",
        "sfDatabase": "SMR_PRD_RPT_DB",
        "sfSchema": "DW",
        "sfWarehouse": "SMR_PRD_RPT_XL_WH",
        "sfRole": "AR_PRD_DAN_COLESTOCK_OPTUM_ROLE",
        "pem_private_key": pk,
    }
    return (
        get_spark()
        .read.format("snowflake")
        .options(**sf_options)
        .option("query", query)
        .load()
        .cache()
    )


def extract_smart_small(query: str) -> DataFrame:
    sf_options = {
        "sfURL": "uhgdwaas.east-us-2.azure.snowflakecomputing.com",
        "sfUser": "dan.colestock@optum.com",
        "sfDatabase": "SMR_PRD_RPT_DB",
        "sfSchema": "DW",
        "sfWarehouse": "SMR_PRD_RPT_XS_WH",
        "sfRole": "AR_PRD_DAN_COLESTOCK_OPTUM_ROLE",
        "pem_private_key": pk,
    }
    return (
        get_spark()
        .read.format("snowflake")
        .options(**sf_options)
        .option("query", query)
        .load()
        .cache()
    )
