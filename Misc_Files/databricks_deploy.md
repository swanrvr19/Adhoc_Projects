# Databricks Job Deployment

This runbook documents how Databricks jobs are defined, validated, and deployed from this repository.

## Source of Truth

- Bundle root config: `databricks.yml`
- Deploy workflow: `.github/workflows/deploy-jobs.yml`
- PR validation workflow: `.github/workflows/validate-bundle.yml`
- Job resource files: `**/jobs/*.yml`

`databricks.yml` currently includes:

- `**/jobs/*.yml`

This means any stream can add jobs under a `jobs/` folder, for example:

- `dups/jobs/*.yml`
- `cob/jobs/*.yml`
- `<stream>/jobs/*.yml`

## Onboarding: Add a New Job

Use this flow when a developer needs to create or migrate a Databricks job into repo-managed deployment.

1. Create a test job in Databricks UI
   - In the workspace, open **Jobs & Pipelines** and create a job.
   - Configure it with the tasks, cluster settings, parameters, and schedule you want.
   - Run it once manually to verify behavior before exporting config.

2. Copy the job definition from Databricks
   - Open the created job in the UI.
   - On the job page, click the three dots next to **Run now**.
   - Click **View as code**.
   - Select **YAML**.
   - Click **Copy**.
   - Use it as the starting point for a bundle resource file.

3. Save the job definition in this repo under a `jobs/` folder
   - Example path: `dups/jobs/my_new_job.job.yml`
   - Keep one job resource per file when possible.


4. Use notebook tasks with wheel libraries
   - Keep `notebook_task` for stream jobs.
   - Add a wheel library reference (for example `../../dist/*.whl`) on each task.
   - Set `notebook_path` to the notebook/script deployed by the bundle.
   - Example:

       ```yaml
       libraries:
          - whl: ../../dist/*.whl
       notebook_task:
          notebook_path: "../product/your_job_notebook.py"
          source: WORKSPACE
       ```

5. Add stream tags to each job
    - Use key-value tags for discoverability and governance.
    - Required conventions:
    - `stream: <stream_name>`
    - `managed_by: databricks-bundle` (reserved for all jobs deployed through this bundle flow)
    - Example for dups jobs:

       ```yaml
       tags:
          stream: dups
          managed_by: databricks-bundle
       ```

6. Pull requests trigger validation
   - PR validation workflow runs `databricks bundle validate -t prod` for job config changes.
   - Fix any validation errors before merge.

7. Merging to main triggers deploy

## Recommended Job Template (For Other Streams)

Use this as the baseline template when creating new stream jobs.


```yaml
resources:
   jobs:
      <Stream_Job_Name>:
         name: <Stream Job Display Name>
         permissions:
            - level: CAN_MANAGE_RUN
               group_name: <AAD_Group_For_Stream>
         schedule:
            quartz_cron_expression: "<cron_expression>"
            timezone_id: America/Chicago
            pause_status: UNPAUSED
         email_notifications:
            on_failure:
               - <owner_email@optum.com>
            no_alert_for_skipped_runs: true
         notification_settings:
            no_alert_for_skipped_runs: true
         job_clusters:
            - job_cluster_key: <shared_cluster_key>
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
         tasks:
            - task_key: TASK_1
               notebook_task:
                  notebook_path: "../product/<task_notebook>.py"
                  source: WORKSPACE
               job_cluster_key: <shared_cluster_key>
               min_retry_interval_millis: 900000
               libraries:
                  - whl: ../../dist/*.whl
         tags:
            stream: <stream_name>
            managed_by: databricks-bundle
         queue:
            enabled: true
         parameters:
            - name: min_proc_dt
               default: ""
            - name: note
               default: ""
            - name: run_type
               default: <run_type>
            - name: test_name
               default: ""
            - name: managed_by
               default: databricks-bundle
```


## Authentication Used by Workflows

Current workflow authentication uses Azure service principal client secret auth:

- `DATABRICKS_AUTH_TYPE=azure-client-secret`
- `DATABRICKS_HOST`
- `ARM_CLIENT_ID` (from `DATABRICKS_CLIENT_ID` secret)
- `ARM_CLIENT_SECRET` (from `DATABRICKS_CLIENT_SECRET` secret)
- `ARM_TENANT_ID` (from `DATABRICKS_TENANT_ID` secret)

## Developer Checklist for New Job Files

- File is under `*/jobs/*.yml`
- Resource structure starts with `resources.jobs`
- Notebook paths are valid for WORKSPACE source
- Task libraries include the built wheel (`../../dist/*.whl` or stream equivalent)
- Job tags include `stream: <stream_name>`
- Job tags include `managed_by: databricks-bundle`
- Job notifications include failure recipients and skipped-run mute settings as required by the stream
- `databricks bundle validate -t prod` passes locally (or in PR checks)
- Job name and permissions are production-appropriate
