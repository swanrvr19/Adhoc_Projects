"""Shared configuration for the pi-dup-denials project.

All product and export notebooks should use get_output_table() to compute
table names, ensuring consistency across the pipeline.
"""

from shared.databricks_env import get_dbutils

CATALOG = "ota_payment_int"
SCHEMA_SOURCES = "pi_sources"
SCHEMA_RESULTS = "pi_results"
SCHEMA_DEV = "pi_dev"
PRODUCTS = {"UNET", "CIRRUS", "CSP", "COSMOS"}


def define_common_widgets() -> None:
    """Create the standard DUPS notebook widgets in one place."""
    dbutils = get_dbutils()
    dbutils.widgets.text("note", "", "1. Note")
    dbutils.widgets.dropdown("run_type", "full", ["full", "intramonth"], "2. Run Type")
    dbutils.widgets.text("min_proc_dt", "", "3. Min Proc Date (override)")
    dbutils.widgets.text("test_name", "", "4. Test Name")
    dbutils.widgets.text("deployment_target", "", "5. Deployment Target")


def get_source_table(name: str) -> str:
    """Get fully qualified source table name in pi_sources.

    Args:
        name: Table name (e.g. "dups_usp_reason_code_dimension", "cirrus_b_to_a_ratios_lvl1")

    Returns:
        Fully qualified table name, e.g. ota_payment_int.pi_sources.cirrus_b_to_a_ratios_lvl1
    """
    return f"{CATALOG}.{SCHEMA_SOURCES}.{name}"


def get_output_table(product: str) -> str:
    """Compute the fully qualified output table name for a product.

    Reads 'run_type' and 'test_name' widgets to determine the correct
    catalog, schema, and table name.

    Args:
        product: One of PRODUCTS (e.g., "UNET", "CSP", "COSMOS", "CIRRUS")

    Returns:
        Fully qualified table name, e.g.
        ota_payment_int.pi_results.unet_dup_denials_savings_extract
    """

    dbutils = get_dbutils()
    run_type = dbutils.widgets.get("run_type")
    test_name = dbutils.widgets.get("test_name").strip()
    deployment_target = dbutils.widgets.get("deployment_target").strip()

    # Only allow production targets for prod deployment target with no test name.
    is_prod_run = deployment_target == "prod" and not test_name
    schema = SCHEMA_RESULTS if is_prod_run else SCHEMA_DEV
    table_name = f"{product}_dup_denials_savings_extract"

    if run_type == "intramonth":
        table_name += "_IM"

    if test_name:
        table_name += f"_{test_name}"

    full_name = f"{CATALOG}.{schema}.{table_name}".lower()
    print(f"Table name: {full_name}")
    return full_name
