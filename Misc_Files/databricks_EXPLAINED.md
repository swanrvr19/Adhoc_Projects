# `databricks.yaml` — Explained

This is the **root configuration file for a Databricks Asset Bundle (DAB)**. A bundle packages your code, jobs, and deployment settings so the Databricks CLI can validate and deploy everything as one unit. This file is the entry point that ties the other pieces together.

---

## Bundle name (lines 1–2)

```yaml
bundle:
  name: pi-slg-jobs
```

Names the bundle `pi-slg-jobs`. This name is used in paths and to identify the deployed bundle in the workspace.

---

## Include (lines 4–5)

```yaml
include:
  - "**/jobs/*.yml"
```

Tells the bundle to pull in every `*.yml` file inside any `jobs/` folder in the repo. This is how job definitions (like `databricks_dup_denials_job.yaml`) get merged into the bundle without listing each one by hand.

---

## Artifacts (lines 7–11)

```yaml
artifacts:
  pi_slg_package:
    type: whl
    path: .
    build: pip wheel . --no-deps --no-build-isolation -w dist
```

Defines a build artifact named `pi_slg_package`:

- **`type: whl`** — the output is a Python wheel (a packaged, installable library).
- **`path: .`** — build from the repo root.
- **`build:`** — the command that produces the wheel. `pip wheel .` builds the current project; `--no-deps` skips dependencies, `--no-build-isolation` uses the existing environment, and `-w dist` writes the `.whl` into the `dist/` folder.

This `dist/*.whl` is exactly what the job tasks attach as a library (see `databricks_dup_denials_job.yaml`).

---

## Targets (lines 13–20)

```yaml
targets:
  prod:
    mode: production
    default: true
    workspace:
      host: https://adb-3239959380256842.2.azuredatabricks.net/
      root_path: /Workspace/Users/${workspace.current_user.userName}/.bundle/${bundle.name}/${bundle.target}
```

Defines deployment targets (environments). Here there's one, `prod`:

- **`mode: production`** — enforces production safety rules (e.g., no dev-style prefixing of resources).
- **`default: true`** — used when no target is specified. Note the CI workflows explicitly pass `-t prod`.
- **`workspace.host`** — the Azure Databricks workspace URL to deploy into.
- **`root_path`** — where the bundle files land in the workspace. It uses variables (`${...}`) that expand to the deploying user's name, the bundle name, and the target — keeping each deployment neatly namespaced.

---

## How it fits together

`databricks.yaml` is the hub: it names the bundle, builds the wheel, pulls in all job definitions, and defines the `prod` target. The two GitHub Actions workflows (`validate-bundle` and `deploy-jobs`) run `databricks bundle validate/deploy -t prod` against this file, and the job YAMLs it includes describe the actual scheduled work.
