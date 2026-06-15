# PI-SLG

Payment Integrity Savings Logic processing tools.

## Contents

- [Project Structure](#project-structure)
- [Branching Strategy (Gitflow)](#branching-strategy-gitflow)
- [Getting Started (Databricks)](#getting-started-databricks)
  - [Databricks Access Roles](#databricks-access-roles)
  - [Git Setup](#git-setup)
- [Local Development (Optional)](#local-development-optional)
- [Code Quality & CI](#code-quality--ci)
- [Infrastructure](#infrastructure)
  - [Repository Access](#repository-access)
  - [HCP / UDLP](#hcp--udlp)
  - [Data Launchpad](#data-launchpad)
- [SAS Connection](#sas-connection)

## Project Structure

```
pi-slg/
├── tools/              # Standalone programs and notebooks (not imported by other code)
├── domain/             # Shared business logic (billed-to-allowed ratios, financial tagging)
├── shared/             # Shared non-business logic (logging, exporting, connections)
├── tests/
│   ├── domain/         # Tests for domain/
│   └── shared/         # Tests for shared/
├── docs/               # Documentation
├── dups/               # Value stream: Duplicate denials
│   ├── product/        # Product-specific notebooks (UNET, CIRRUS, COSMOS, CSP)
│   ├── export/         # Output generation
│   ├── util/           # Stream-specific utilities
│   ├── tests/          # Stream-specific tests
│   └── docs/           # Stream-specific documentation
├── cob/                # Value stream: Coordination of Benefits
│   ├── product/        # Product-specific logic
│   ├── connections/    # Stream-specific connections
│   ├── notebooks/      # Diagnostic and validation notebooks
│   ├── util/           # Stream-specific utilities
│   ├── tests/          # Stream-specific tests
│   └── docs/           # Stream-specific documentation
├── .github/workflows/  # CI pipeline definitions
├── pyproject.toml      # Project metadata and dependencies
└── .pre-commit-config.yaml
```

### Conventions

- Each value stream gets its own **top-level folder** with short, lowercase, abbreviated names
- Value streams should **not import from each other** — shared code belongs in `domain/` or `shared/`
- `tools/` contains standalone programs and notebooks — nothing here should be imported by other code
- Each value stream should have its own `tests/` and `docs/` subfolders

## Branching Strategy (Gitflow)

This repository uses the Gitflow branching model:
<https://www.atlassian.com/git/tutorials/comparing-workflows/gitflow-workflow>

Use one of these branch name formats:

- `main`
- `develop`
- `feature/<short-description>`
- `bugfix/<short-description>`
- `release/<major>.<minor>.<patch>`
- `hotfix/<major>.<minor>.<patch>-<short-description>`

Rules for `<short-description>`:

- Use lowercase letters, numbers, dots, and hyphens only
- Do not use spaces or underscores

Examples:

- `feature/unet-ratio-refresh`
- `bugfix/dlp-timeout-fix`
- `release/1.4.0`
- `hotfix/1.4.1-prod-patch`

Regex reference (for branch policy checks):

```regex
^(main|develop|feature\/[a-z0-9.-]+|bugfix\/[a-z0-9.-]+|release\/[0-9]+\.[0-9]+\.[0-9]+|hotfix\/[0-9]+\.[0-9]+\.[0-9]+-[a-z0-9.-]+)$
```

---

## Getting Started (Databricks)

Most team members develop directly in Databricks.

**Workspace URL**: <https://adb-3239959380256842.2.azuredatabricks.net/>

### Databricks Access Roles

Request these groups in Secure to get access to the `ota_payment_int` Databricks environment:

| Secure group | Purpose |
|--------------|----------|
| `AZU_UDLP_ota_payment_int_DataEngineer` | Full development access (create tables, schemas, volumes, etc.) |
| `AZU_UDLP_ota_payment_int_DataScientist` | Development access (create models, volumes, functions) |
| `AZU_UDLP_ota_payment_int_DataAnalyst` | Read/execute access (select, browse, execute) |
| `AZU_UDLP_ota_payment_int_reporting` | Read-only access to the `ota_payment_int.pi_results` schema (custom role — required for PAT token exception used by SAS connections) |

<details>
<summary>Detailed permissions by role</summary>

| | Data Engineer | Data Scientist | Data Analyst |
|--|--------------|----------------|---------------|
| **Workspace level** | User | User | User |
| **Catalog level** | Use Schema, Use Catalog, Browse metadata, Execute, Select, Modify, Create Function, Create Materialized View, Create Schema, Create Table, Create Volume | Use Schema, Use Catalog, Browse metadata, Execute, Select, Modify, Create Function, Create Materialized View, Create Model, Create Volume | Use Schema, Use Catalog, Browse metadata, Execute, Select |
| **External Locations** | CREATE_EXTERNAL_TABLE, CREATE_MANAGED_STORAGE, READ_FILES, WRITE_FILES, READ_VOLUME | CREATE_EXTERNAL_TABLE, READ_FILES, WRITE_FILES, READ_VOLUME | CREATE_EXTERNAL_TABLE, READ_FILES, WRITE_FILES, READ_VOLUME |

</details>

### Git Setup

See the full guide: **[Databricks Git Setup](docs/databricks-git-setup.md)**

Key steps:
1. Get GitHub access (Secure → AZU_GHEC_USERS)
2. Generate a GitHub Personal Access Token (classic)
3. Create a Git folder in your Databricks home directory
4. Authenticate with your PAT
5. **Enable source notebooks** as your default format (Settings → Developer → File format → Source)

---

## Local Development (Optional)

For developers who want to edit and test locally (e.g., using VS Code). This is not required — all development can be done in Databricks.

### Install Prerequisites

| Software | Install link |
|----------|-------------|
| Python | <https://optum.service-now.com/euts_intake?id=appstore&q=python> |
| Git | <https://optum.service-now.com/euts_intake?id=euts_appstore_app_details&appKeyId=44014> |
| Visual Studio Code | <https://optum.service-now.com/euts_intake?id=appstore&q=Microsoft%20Visual%20Studio%20Code> |

You'll also need to configure pip to use Artifactory for package installation. See: **[Artifactory Setup](docs/artifactory-setup.md)**

### Clone and Install

```bash
git clone <repo-url>
cd pi-slg
python -m pip install -e . --group dev
```

### Pre-commit Hooks (Optional)

Pre-commit runs the **SQL formatter**, **pylint**, and **pytest** automatically before each commit. It does not run ruff or ty (see [Code Quality & CI](#code-quality--ci) for what runs where).

```bash
# Install the git hook (one-time setup)
python -m pre_commit install

# Run manually against all files
python -m pre_commit run --all-files
```

The hooks are defined in `.pre-commit-config.yaml`:
- **SQL formatter** — formats SQL embedded in Python files
- **pylint** — with `databricks-labs-pylint` plugin for Databricks-specific checks
- **pytest** — runs the `tests/` suite

---

## Code Quality & CI

Code quality is enforced at three levels:

| Level | Tools | Runs where |
|-------|-------|------------|
| Local (on commit) | SQL formatter, pylint, pytest | Developer machine (pre-commit hook) |
| CI (on pull request) | ruff, ty, SQL formatter, pylint, pytest | GitHub runner |
| Databricks | ruff, ty, SQL formatter, pylint, pytest | Databricks workspace |

### GitHub Actions

The CI workflow (`.github/workflows/`) runs the full suite on every pull request:
- **ruff** — fast formatting and lint checks
- **ty** — type checking
- **SQL formatter** — formats SQL embedded in Python notebooks
- **pylint** — with Databricks plugin
- **pytest** — test suite

It uses `uv` for fast dependency resolution in the CI environment.

### Linting Notebook

The linting notebook in `tools/` can be run directly from Databricks and performs the same checks as CI (ruff, ty, SQL formatter, pylint, pytest) against the workspace copy of the code.

---

## Infrastructure

### Repository Access

| Resource | Link |
|----------|------|
| Repository (Immerse) | <https://immerse.uhg.com/repositories/AIDE_0088396/pi-slg> |
| Contributor team | <https://immerse.uhg.com/teams/pi-slg> |
| Admin team | <https://immerse.uhg.com/teams/pi-slg-admin> |
| All Immerse repos | <https://immerse.uhg.com/repositories> |

### HCP / UDLP

UDLP Databricks resources are managed through HCP. Delegates of the [HCP account](https://console.hcp.uhg.com/account-manager/account/AIDE_0088396) have access to make changes.

| Resource | Link |
|----------|------|
| Databricks workspace | <https://adb-3239959380256842.2.azuredatabricks.net/> |
| UDLP documentation | <https://docs.hcp.uhg.com/unified-data-lakehouse-platform-(udlp)> |
| UDLP Databricks support | <https://optum.service-now.com/itss2?id=itss2_sc_cat_item&sys_id=b56a90a41b4aa5906b5c7798624bcbb0> |
| Tenant management (clusters, warehouses, pools, secrets, custom roles, service principals) | <https://console.hcp.uhg.com/dashboard/data-management/udlp/tenant> |

#### Secrets

| Secret name | Purpose | Rotation |
|-------------|---------|----------|
| `snowflaketoken` | Token for accessing Snowflake | — |
| `artifactory-full-url` | Used for pip installing from serverless compute using Artifactory | — |

### Data Launchpad

Data Launchpad (DLP) extracts data from on-prem SQL servers (**tadm-gimli** and **C&S Tre**) and lands it in the `ota_payment_int.pi_sources` schema in the Databricks catalog. The `tools/trigger_dlp` notebook triggers these extractions.

| Resource | Link |
|----------|------|
| DLP documentation | <https://docs.hcp.uhg.com/data-launchpad> |
| Configuration repo | <https://github.com/optum-eeps/hcpdlp-tenant-configs> |
| Our tenant config | <https://github.com/optum-eeps/hcpdlp-tenant-configs/tree/main/tenants/OTAPAYMENT_TST/PI_COB_Inputs> |
| Grafana monitoring | <https://grafana-enterprise.optum.com/d/eeteu9wp3tq0we/dlp-datapipeline-dashboard-nonprod?orgId=1&from=now-24h&to=now&timezone=browser&var-DLPAzureMonitorDatasourceProd=ae60xamnyu4g0a&var-Instance=33ebd6bf-5eef-4650-9263-ffcc7b3d437c&var-Tenant=OTAPAYMENT_TST&var-Source=src-ota-payment-int-gimli&var-TriggerName=tr-ota-payment-int-cirrus-ratios> |

#### DLP Secrets

| Secret name | Purpose | Rotation |
|-------------|---------|----------|
| `pi-dlp-password` | Password for the `pi_dlp` service account | Yearly |
| `dlp-token` | Access token for the exec service principal. Generated per [these instructions](https://github.com/optum-eeps/udlp-docs/blob/main/docs/UDLP/SOPs/Runbooks/Databricks/Databricks_Access_Token.md) | Yearly |
| `sp-exec-client-secret` | Exec service principal client secret (used by DLP config and the Trigger DLP notebook) | Every 90 days |

#### Updating DLP Configuration

1. Submit a PR to the [tenant config](https://github.com/optum-eeps/hcpdlp-tenant-configs/tree/main/tenants/OTAPAYMENT_TST/PI_COB_Inputs) — must be approved by someone on our team other than the submitter
2. After merge, deploy the config by [opening an issue](https://github.com/optum-eeps/hcpdlp-tenant-configs/issues/new/choose) using the **[Tenant] configurations deployment** template and fill in the following values:
   - **Tenant_name**: `OTAPAYMENT_TST`
   - **Source_name**: `PI_COB_Inputs`

#### New Configuration Fields

When you first create a new DLP configuration, leave `FwkTargetId`, `FwkSourceId`, and `FwkConfigId` as null. After the initial deployment runs, look up the actual values from the [Grafana monitoring dashboard](https://grafana-enterprise.optum.com/d/eeteu9wp3tq0we/dlp-datapipeline-dashboard-nonprod?orgId=1&from=now-24h&to=now&timezone=browser&var-DLPAzureMonitorDatasourceProd=ae60xamnyu4g0a&var-Instance=33ebd6bf-5eef-4650-9263-ffcc7b3d437c&var-Tenant=OTAPAYMENT_TST&var-Source=src-ota-payment-int-gimli&var-TriggerName=tr-ota-payment-int-cirrus-ratios) and fill them in on subsequent PRs.

---

## SAS Connection

See: **[SAS Connection to UDLP Databricks](docs/sas-connection.md)**
