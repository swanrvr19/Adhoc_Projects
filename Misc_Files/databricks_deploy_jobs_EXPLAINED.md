# `databricks_deploy_jobs.yaml` — Explained

This is a **GitHub Actions workflow** that deploys the Databricks Asset Bundle to the `prod` workspace. Where the *validate* workflow only checks config on open PRs, this one pushes the bundle live **after a PR is merged** into `main`.

---

## Trigger (lines 1–12)

```yaml
name: Deploy Databricks Jobs
on:
  workflow_dispatch:
  pull_request:
    types:
      - closed
    branches:
      - main
env:
  PIP_NO_INPUT: "1"
```

Two ways to trigger:

- **`workflow_dispatch`** — manual run from the GitHub UI.
- **`pull_request: closed` on `main`** — fires whenever a PR to `main` is closed. Note "closed" includes both *merged* and *closed-without-merging*, so the job itself filters for the merged case (see below).

`PIP_NO_INPUT: "1"` stops pip from waiting on interactive prompts.

---

## The `deploy-job` — guard and auth (lines 14–25)

```yaml
jobs:
  deploy-job:
    if: (github.event_name == 'workflow_dispatch') || (github.event.pull_request.merged == true)
    runs-on: uhg-runner
    permissions:
      contents: read
    env:
      DATABRICKS_AUTH_TYPE: azure-client-secret
      DATABRICKS_HOST: https://adb-3239959380256842.2.azuredatabricks.net/
      ARM_CLIENT_ID: ${{ secrets.DATABRICKS_CLIENT_ID }}
      ARM_CLIENT_SECRET: ${{ secrets.DATABRICKS_CLIENT_SECRET }}
      ARM_TENANT_ID: ${{ secrets.DATABRICKS_TENANT_ID }}
```

- **`if:`** — the critical guard. The job runs only if it was triggered manually **or** the PR was actually **merged** (`merged == true`). This is what prevents a deploy when someone simply closes a PR without merging.
- **`env:`** — same Azure service-principal authentication as the validate workflow: host plus the `ARM_*` client ID / secret / tenant ID from secrets.

---

## Steps (lines 26–53)

```yaml
    steps:
      - name: Checkout repository
        uses: actions/checkout@v6
        with:
          ref: main
```

**Checkout** — explicitly checks out the `main` branch (`ref: main`), so the deploy always uses the final merged state of `main`, not the PR's head commit.

```yaml
      - name: Set up Python
        uses: actions/setup-python@v6
        with:
          python-version: '3.12'
```

**Set up Python 3.12**, with pip pointed at Optum's internal JFrog Artifactory mirrors via the `PIP_INDEX_URL` / `PIP_EXTRA_INDEX_URL` env vars (using the `JFROG_*` secrets).

```yaml
      - name: Install build dependencies
        run: pip install hatchling
```

**Install hatchling** — the build backend needed to build the project's Python wheel (the `pi_slg_package` artifact defined in `databricks.yml`).

```yaml
      - name: Set up Databricks CLI
        uses: databricks/setup-cli@v1.5.0
```

**Install the Databricks CLI** (v1.5.0).

```yaml
      - name: Validate Databricks bundle
        run: databricks bundle validate -t prod

      - name: Deploy Databricks bundle
        run: databricks bundle deploy -t prod
```

- **Validate** — re-checks the bundle for the `prod` target as a final safety net before deploying.
- **Deploy** — `databricks bundle deploy -t prod` builds the wheel, uploads all bundle files, and creates/updates the jobs (like `Dup Denials - Full`) in the production Databricks workspace.

---

## The big picture

This is the "ship it" workflow. On a merge to `main` (or a manual trigger), it authenticates as an Azure service principal, builds the project wheel, validates the bundle one more time, and deploys everything to production. The merged-only `if` guard and the explicit `ref: main` checkout make sure only reviewed, merged code ever reaches prod.
