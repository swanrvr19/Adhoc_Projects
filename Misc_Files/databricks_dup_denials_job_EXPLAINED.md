# `databricks_dup_denials_job.yaml` — Explained

This is a **Databricks job definition** — one of the files pulled into the bundle by the `include: "**/jobs/*.yml"` rule in `databricks.yml`. It describes a scheduled, multi-task workflow called **"Dup Denials - Full"** that runs on a Databricks cluster.

---

## Job resource and permissions (lines 1–7)

```yaml
resources:
  jobs:
    Dup_Denials_Full:
      name: Dup Denials - Full
      permissions:
        - level: CAN_MANAGE_RUN
          group_name: AZU_UDLP_ota_payment_int_DataEngineer
```

Under `resources.jobs`, this defines a job keyed `Dup_Denials_Full` with the display name **"Dup Denials - Full"**. The `permissions` block grants the `AZU_UDLP_ota_payment_int_DataEngineer` group **`CAN_MANAGE_RUN`** — they can trigger and manage runs, but not edit the job definition itself.

---

## Schedule (lines 8–11)

```yaml
      schedule:
        quartz_cron_expression: "44 0 22 4 * ?"
        timezone_id: America/Chicago
        pause_status: UNPAUSED
```

A **Quartz cron** schedule. Reading the fields `seconds minutes hours day-of-month month day-of-week`:

- `44 0 22 4 * ?` → **at 22:00:44 (10:00:44 PM) on the 4th day of every month**.
- **`timezone_id: America/Chicago`** — Central time.
- **`pause_status: UNPAUSED`** — the schedule is active.

---

## Notifications (lines 12–17)

```yaml
      email_notifications:
        on_failure:
          - dan.colestock@optum.com
        no_alert_for_skipped_runs: true
      notification_settings:
        no_alert_for_skipped_runs: true
```

Emails `dan.colestock@optum.com` **only on failure**, and suppresses alerts for skipped runs so nobody gets pinged when a run is skipped (e.g., due to the queue/concurrency rules below).

---

## Compute — the job cluster (lines 18–32)

```yaml
      job_clusters:
        - job_cluster_key: dup_denials_cluster
          new_cluster:
            spark_version: 17.3.x-scala2.13
            node_type_id: Standard_E16d_v4
            driver_node_type_id: Standard_E16d_v4
            data_security_mode: SINGLE_USER
            runtime_engine: PHOTON
            azure_attributes:
              first_on_demand: 1
              availability: ON_DEMAND_AZURE
              spot_bid_max_price: -1
            autoscale:
              min_workers: 2
              max_workers: 16
```

Defines a **job cluster** (spun up for this job, torn down after) named `dup_denials_cluster`:

- **`spark_version: 17.3.x-scala2.13`** — the Databricks Runtime version.
- **`node_type_id` / `driver_node_type_id: Standard_E16d_v4`** — memory-optimized Azure VMs for both workers and driver.
- **`data_security_mode: SINGLE_USER`** — the cluster runs as a single identity (required for certain workloads/Unity Catalog access patterns).
- **`runtime_engine: PHOTON`** — uses Photon, Databricks' faster native query engine.
- **`azure_attributes`** — `availability: ON_DEMAND_AZURE` with `first_on_demand: 1` means use on-demand VMs (not spot/preemptible), avoiding interruptions.
- **`autoscale: 2–16 workers`** — the cluster scales between 2 and 16 workers based on load.

---

## Tasks (lines 33–77)

The job runs five tasks, all on the shared `dup_denials_cluster` and all attaching the project wheel (`../../dist/*.whl`, the artifact built from `databricks.yml`).

```yaml
      tasks:
        - task_key: CIRRUS
          notebook_task:
            notebook_path: "../product/cirrus_dup_denials.py"
            source: WORKSPACE
          job_cluster_key: dup_denials_cluster
          min_retry_interval_millis: 900000
          libraries:
            - whl: ../../dist/*.whl
```

- **`CIRRUS`, `COSMOS`, `CSP`, `UNET`** — four parallel tasks, each running a product-specific notebook (`cirrus_dup_denials.py`, `cosmos_dup_denials.py`, etc.). These have no dependencies, so they run **concurrently**.
- **`min_retry_interval_millis: 900000`** — if a task retries, wait at least 15 minutes (900,000 ms) between attempts. (The `CSP` task omits this.)
- **`libraries: whl: ../../dist/*.whl`** — installs the built project wheel so the notebooks can import the shared package code.

```yaml
        - task_key: Generate_CSVs
          depends_on:
            - task_key: CIRRUS
            - task_key: COSMOS
            - task_key: CSP
            - task_key: UNET
          notebook_task:
            notebook_path: "../export/generate_csvs.py"
            ...
```

- **`Generate_CSVs`** — the final fan-in task. Its `depends_on` lists all four product tasks, so it runs **only after CIRRUS, COSMOS, CSP, and UNET all succeed**, then exports the results via `generate_csvs.py`.

The task graph:

```
CIRRUS ─┐
COSMOS ─┤
CSP    ─┼──► Generate_CSVs
UNET   ─┘
```

---

## Tags, queue, and parameters (lines 78–94)

```yaml
      tags:
        stream: dups
        managed_by: databricks-bundle
      queue:
        enabled: true
      parameters:
        - name: min_proc_dt
          default: ""
        - name: note
          default: ""
        - name: run_type
          default: full
        - name: test_name
          default: ""
        - name: managed_by
          default: databricks-bundle
```

- **`tags`** — metadata for organization/cost tracking; `managed_by: databricks-bundle` flags that this job is owned by the bundle (don't hand-edit it in the UI).
- **`queue: enabled: true`** — if a run is already going when the next is triggered, the new run queues instead of being dropped.
- **`parameters`** — job-level parameters passed to the notebooks at runtime, with defaults. `run_type` defaults to `full` (matching the job name), while `min_proc_dt`, `note`, and `test_name` default to empty and can be overridden per run.

---

## The big picture

This file defines the production "Dup Denials - Full" pipeline: on the 4th of each month at ~10 PM Central, it spins up a Photon-enabled autoscaling cluster, runs four product-specific duplicate-denial notebooks in parallel, then fans into a CSV export step. It's deployed to the workspace by the `deploy-jobs` workflow and is one of the job definitions the root `databricks.yml` bundles together.
