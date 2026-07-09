# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "5"
# ///
# MAGIC %md
# MAGIC # Trigger Data Launchpad Extracts
# MAGIC Extracts data from on-prem sources tadm-gimli and C&S-Tre and places them into the catalog schema `ota_payment_int.pi_sources`

# COMMAND ----------

# DBTITLE 1,Install Libraries
# pylint: disable=C0412,W0404
# Suppresses import groupings, and reimports
import importlib

from shared.databricks_env import install_packages

try:
    ClientSecretCredential = importlib.import_module("azure.identity").ClientSecretCredential
    DataFactoryManagementClient = importlib.import_module(
        "azure.mgmt.datafactory"
    ).DataFactoryManagementClient
except ImportError:
    install_packages(
        ["azure-identity", "azure-mgmt-datafactory"],
        restart=True,
    )

# COMMAND ----------

# DBTITLE 1,Input Variables
import importlib
import time
from collections import deque
from typing import Any

from shared.databricks_env import get_secret

# Re-import after potential restartPython() call
ClientSecretCredential = importlib.import_module("azure.identity").ClientSecretCredential
DataFactoryManagementClient = importlib.import_module(
    "azure.mgmt.datafactory"
).DataFactoryManagementClient
clear_output = importlib.import_module("IPython.display").clear_output

# Connecting via ServicePrincipal
TENANT_ID = "db05faca-c82a-4b9d-b9c5-0f64b6755421"
CLIENT_ID = "fe4ac0ad-5db0-4ce9-8752-8d983e1641e2"
CLIENT_SECRET = get_secret("sp-exec-client-secret")

# ADF details
SUBSCRIPTION_ID = "e28165d8-cc3a-4cd3-9dbd-22793afee35a"
RESOURCE_GROUP = "udlp-dlp-nonprod-rg"
FACTORY_NAME = "udlp-dlp-nonprod-adf"
PIPELINE_NAME = "PL_DataSupplyChainBus"

# Authentication
credential = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
df_client = DataFactoryManagementClient(credential, SUBSCRIPTION_ID)

# How many pipelines to run concurrently
MAX_CONCURRENT = 2

# COMMAND ----------

# DBTITLE 1,Run Triggers
terminal_states = {"Succeeded", "Failed", "Cancelled"}


def display_errors(all_completed: dict[str, str], all_runs: dict[str, str]) -> None:
    """Print detailed error messages for any failed runs."""
    failures = {t: s for t, s in all_completed.items() if s == "Failed"}
    if failures:
        print(f"Error details for {len(failures)} failed run(s):")
        print(f"{'=' * 60}")
        for trigger in failures:
            pipeline_run = df_client.pipeline_runs.get(
                resource_group_name=RESOURCE_GROUP,
                factory_name=FACTORY_NAME,
                run_id=all_runs[trigger],
            )
            print(f"\n❌ {trigger} (Run ID: {all_runs[trigger]})")
            print(f"  {getattr(pipeline_run, 'message', 'No error message available')}")


def run_triggers(trigger_names: list[str]) -> dict[str, str]:
    """Fire and monitor ADF pipeline runs for each trigger name,
    keeping up to MAX_CONCURRENT runs active at a time.
    Returns a mapping of trigger_name -> final status.
    """
    log_lines: list[str] = []
    line_index: dict[str, int] = {}
    all_runs: dict[str, str] = {}
    all_completed: dict[str, str] = {}

    def trigger_run(name: str) -> str | None:
        parameters: dict[str, Any] = {"FactoryName": "OTAPAYMENT_TST", "TriggerName": name}
        try:
            result = df_client.pipelines.create_run(
                resource_group_name=RESOURCE_GROUP,
                factory_name=FACTORY_NAME,
                pipeline_name=PIPELINE_NAME,
                parameters=parameters,
            )
            line_index[name] = len(log_lines)
            log_lines.append(f"▶️ {name} -> Run ID: {result.run_id}")
            return result.run_id
        except Exception as e:
            line_index[name] = len(log_lines)
            log_lines.append(f"❌ {name} -> Error: {e}")
            return None

    def check_run(name: str, rid: str) -> str | None:
        run = df_client.pipeline_runs.get(
            resource_group_name=RESOURCE_GROUP,
            factory_name=FACTORY_NAME,
            run_id=rid,
        )
        if run.status in terminal_states:
            icon = "✅" if run.status == "Succeeded" else "❌"
            log_lines[line_index[name]] = f"{icon} {name}: {run.status} -> Run ID: {rid}"
            return run.status
        return None

    def render(current_active: dict[str, str], current_queue: deque[str]) -> None:
        clear_output(wait=True)
        for line in log_lines:
            print(line)
        if current_active:
            names = ", ".join(current_active.keys())
            print(
                f"\n⏳ {len(current_active)} active ({names})"
                f" | {len(current_queue)} queued | {len(all_completed)} done"
            )

    # --- Worker pool ---
    queue: deque[str] = deque(trigger_names)
    active: dict[str, str] = {}

    while queue and len(active) < MAX_CONCURRENT:
        trigger = queue.popleft()
        run_id = trigger_run(trigger)
        if run_id:
            active[trigger] = run_id
            all_runs[trigger] = run_id
        else:
            all_completed[trigger] = "Error"
    render(active, queue)

    while active:
        for trigger in list(active):
            status = check_run(trigger, active[trigger])
            if status:
                all_completed[trigger] = status
                del active[trigger]
                if queue:
                    next_trigger = queue.popleft()
                    run_id = trigger_run(next_trigger)
                    if run_id:
                        active[next_trigger] = run_id
                        all_runs[next_trigger] = run_id
                    else:
                        all_completed[next_trigger] = "Error"
        render(active, queue)
        if active:
            time.sleep(30)

    succeeded = sum(1 for s in all_completed.values() if s == "Succeeded")
    failed = sum(1 for s in all_completed.values() if s != "Succeeded")
    print(f"\n{'=' * 60}")
    print(f"All done: {succeeded} succeeded, {failed} failed/cancelled/errored")
    print(f"{'=' * 60}")

    display_errors(all_completed, all_runs)
    return all_completed


# COMMAND ----------

# DBTITLE 1,Gimli and C&S TRE triggers
# MAGIC %skip
# MAGIC run_triggers([
# MAGIC     "tr-ota-payment-int-cirrus-ratios",
# MAGIC     "tr-ota-payment-int-cosmos-combos",
# MAGIC     "tr-ota-payment-int-cosmos-membership",
# MAGIC     "tr-ota-payment-int-cosmos-ratios",
# MAGIC     "tr-ota-payment-int-csp-ratios",
# MAGIC     "tr-ota-payment-int-csp-tre-membership",
# MAGIC     "tr-ota-payment-int-gimli-reason-codes",
# MAGIC     "tr-ota-payment-int-tre-bh-patch-map",
# MAGIC     "tr-ota-payment-int-tre-dim-company",
# MAGIC     "tr-ota-payment-int-tre-dim-geography-state",
# MAGIC     "tr-ota-payment-int-tre-ses-region-map",
# MAGIC     "tr-ota-payment-int-unet-ratios",
# MAGIC ])

# COMMAND ----------

# DBTITLE 1,CCM Triggers
# MAGIC %skip
# MAGIC run_triggers([
# MAGIC     "tr-ota-payment-int-ccm-cire",
# MAGIC     "tr-ota-payment-int-ccm-contract-audit",
# MAGIC     "tr-ota-payment-int-ccm-cosmos-hd-aru",
# MAGIC     "tr-ota-payment-int-ccm-sam-feeds",
# MAGIC     "tr-ota-payment-int-ccm-sam-sav",
# MAGIC     "tr-ota-payment-int-ccm-unet-aru",
# MAGIC     "tr-ota-payment-int-ccm-usp",
# MAGIC     "tr-ota-payment-int-ccm-usp-aru",
# MAGIC ])
