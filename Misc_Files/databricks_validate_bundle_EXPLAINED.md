# `databricks_validate_bundle.yaml` — Explained

This is a **GitHub Actions workflow** that validates the Databricks Asset Bundle on pull requests — a lightweight safety check that the bundle config is well-formed before it can be merged and deployed.

---

## Trigger (lines 1–15)

```yaml
name: Validate Databricks Bundle
on:
  pull_request:
    types:
      - opened
      - synchronize
      - reopened
    branches:
      - main
    paths:
      - .github/workflows/deploy-jobs.yml
      - .github/workflows/validate-bundle.yml
      - databricks.yml
      - '**/jobs/*.yml'
```

Runs on pull requests targeting `main`, when the PR is opened, updated (`synchronize`), or reopened. The **`paths:` filter** is the key detail — the workflow only runs when one of these files changes:

- either of the two workflow files themselves,
- the root `databricks.yml`,
- or any job definition under a `jobs/` folder.

This avoids wasting CI runs on PRs that don't touch bundle config (e.g., a docs-only change).

---

## The `validate-bundle` job (lines 17–27)

```yaml
jobs:
  validate-bundle:
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

- **`runs-on: uhg-runner`** — the self-hosted Optum runner.
- **`permissions: contents: read`** — read-only, least-privilege.
- **`env:`** — authentication for the Databricks CLI. It uses an **Azure service principal** (client-secret auth): `DATABRICKS_HOST` is the target workspace, and the `ARM_*` values are the service principal's client ID, secret, and tenant ID, pulled from repo secrets.

---

## Steps (lines 28–36)

```yaml
    steps:
      - name: Checkout repository
        uses: actions/checkout@v6

      - name: Set up Databricks CLI
        uses: databricks/setup-cli@f01853f8d6b12678ab0fab76ffad726c460be1a5 #v1.5.0

      - name: Validate Databricks bundle
        run: databricks bundle validate -t prod
```

1. **Checkout** — pulls the PR's code onto the runner.
2. **Set up Databricks CLI** — installs the CLI. Note it pins the action to a **full commit SHA** (with the `#v1.5.0` version as a comment) rather than a tag — a security best practice, since a tag can be re-pointed but a SHA can't.
3. **Validate** — runs `databricks bundle validate -t prod`, which parses `databricks.yml`, merges all included job files, resolves variables, and checks the whole bundle is valid against the `prod` target — **without deploying anything**.

---

## The big picture

This is the "check before you merge" gate. It confirms the bundle config compiles cleanly for `prod` on every relevant PR, so broken configuration is caught at review time rather than at deploy time. Its heavier sibling, `databricks_deploy_jobs.yaml`, does the actual deploy after merge.
