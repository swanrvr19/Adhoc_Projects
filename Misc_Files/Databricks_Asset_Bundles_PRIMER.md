# What Is a Databricks Asset Bundle? — A Primer

A Databricks Asset Bundle (DAB) is basically **infrastructure-as-code for Databricks**. Instead of clicking around the Databricks web UI to create jobs, set schedules, configure clusters, and upload notebooks, you describe all of it in YAML files that live in your Git repo. The Databricks CLI then reads those files and creates or updates everything in the workspace to match.

The core idea is that your workspace setup becomes **code** — version-controlled, reviewable in pull requests, and deployable through CI. If you've heard of Terraform, it's the same concept (in fact DABs are built on Terraform under the hood), but purpose-built for Databricks resources like jobs, pipelines, clusters, and notebooks.

---

## The key concepts, mapped to this repo

**Bundle** — the whole package, defined by the root `databricks.yml`. That file gives the bundle a name (`pi-slg-jobs`), says how to build your Python code into a wheel, pulls in all the job definitions, and defines a deployment target.

**Target** — a named environment. This repo defines one, `prod`, pointing at a specific Azure Databricks workspace. Many teams have `dev`, `staging`, and `prod` targets pointing at different workspaces, so the same code deploys to each with different settings.

**Resources** — the actual things you want to exist in Databricks. `databricks_dup_denials_job.yaml` defines one: a job with a schedule, a cluster spec, and five tasks. That job isn't created by hand in the UI — it exists because it's declared in the bundle.

---

## The workflow (two CLI verbs)

These are the commands the GitHub Actions workflows run:

- **`databricks bundle validate -t prod`** — parse and check the whole bundle for the `prod` target without changing anything. The *validate-bundle* workflow runs this on every PR.
- **`databricks bundle deploy -t prod`** — actually build the wheel, upload files, and create/update the jobs in the workspace. The *deploy-jobs* workflow runs this after a merge.

---

## Why teams use bundles instead of the UI

- **Reproducible** — you can recreate the exact setup in a new workspace straight from the repo.
- **Reviewable** — every change goes through code review as a pull request.
- **Automated & consistent** — deploys run through CI, not manual clicks.
- **Single source of truth** — the `managed_by: databricks-bundle` tag reminds people not to hand-edit the job in the UI, because the next deploy would overwrite their changes back to whatever the YAML says.

---

## How the deploy "knows" which files to use (discovery)

A common point of confusion: the deploy workflow just runs `databricks bundle deploy -t prod` — it never names `databricks.yml` or any job file. So how does it find them? The answer is **convention and discovery**, not explicit references. There are two hops.

**Hop 1 — CLI finds `databricks.yml` by filename convention.** Whenever you run any `bundle` command, the Databricks CLI automatically looks in the current working directory (and walks up parent directories) for a file named exactly `databricks.yml` (or `databricks.yaml`). That filename is the magic convention — the CLI treats it as the bundle root. Because the workflow checks out the repo and runs from the repo root, the CLI finds `databricks.yml` without being told where it is.

**Hop 2 — `databricks.yml` finds the job files by a glob pattern.** Inside `databricks.yml`:

```yaml
include:
  - "**/jobs/*.yml"
```

When the CLI loads `databricks.yml`, it expands that glob and pulls in **every `.yml` file inside any `jobs/` folder** anywhere in the repo, merging their contents into the bundle as if written directly in `databricks.yml`. The dup-denials job file gets swept up by that glob — which is why it defines `resources: jobs: Dup_Denials_Full`, contributing a `jobs` resource to the merged bundle.

The full chain:

```
deploy-jobs workflow
   │  runs `databricks bundle deploy -t prod` from the repo root
   ▼
CLI finds databricks.yml   ← by filename convention (no reference needed)
   │  reads its `include: "**/jobs/*.yml"`
   ▼
job YAMLs get merged in    ← by glob pattern, not by name
   │  now the bundle knows about the Dup_Denials_Full job
   ▼
deploy creates/updates that job in the prod workspace
```

**The mental shift:** nothing points to a specific file *by name*. The workflow relies on the CLI finding `databricks.yml` by its well-known filename, and `databricks.yml` finds the jobs by a wildcard pattern. Drop a new file into any `jobs/` folder and the next deploy picks it up automatically — no edits to the workflow or to `databricks.yml` needed. That's the whole appeal of the convention.

**Caveat:** this depends on the real repo layout — the job file sitting under a `jobs/` folder so the glob matches it, and `databricks.yml` at the repo root where the CLI's working directory can reach it. If the files are flattened into one directory with renamed copies (as in a scratch folder), the connection won't be obvious just from looking at them.

---

## In one sentence

A Databricks Asset Bundle lets you define your Databricks jobs, clusters, and code in Git-tracked YAML and deploy them reliably through the CLI, rather than configuring them by hand in the web console.
