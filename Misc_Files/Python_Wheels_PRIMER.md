# What Is a Python Wheel? (And When Is It Built?) — A Primer

## What a wheel is

A Python wheel is a **pre-built, zip-format package of Python code** — the standard way to bundle a Python library so it installs quickly. The file has a `.whl` extension and is really just a ZIP archive containing your `.py` files plus metadata (name, version, dependencies).

The name comes from "cheese wheel" (Python has a cheese theme — PyPI was originally the "Cheese Shop").

**Mental model:** a wheel is like a **flat-pack furniture box that's already assembled**. When you `pip install requests`, pip typically downloads a wheel — a ready-to-go package — and just unzips it into place. Fast, no assembly required.

## Wheel vs. source distribution

The contrast is a **source distribution** (`sdist`), which ships the raw source code and has to be *built* on your machine at install time (running `setup.py`, compiling any C extensions, etc.). That's slower and can fail if the build environment isn't right.

A wheel is the already-built result, so installing it is just "unzip and go."

In this project, the wheel packages the shared project code (the `pi_slg_package`) so the Databricks notebooks can simply `import` it.

---

## Where does the wheel actually get created?

A key distinction: **`databricks.yml` does NOT create the wheel.** It only *declares the recipe* for how to build it:

```yaml
artifacts:
  pi_slg_package:
    type: whl
    path: .
    build: pip wheel . --no-deps --no-build-isolation -w dist
```

That `build:` line is just a stored command — a definition sitting on the shelf. Nothing runs at the moment the CLI reads this file.

The wheel is actually **built later, at deploy time**, when the `deploy-jobs` workflow runs `databricks bundle deploy -t prod`. During that deploy, the CLI processes the `artifacts` section, executes the `pip wheel ...` command, produces the `.whl` in the `dist/` folder, uploads it to the workspace, and wires it into the jobs.

### Timeline

```
databricks.yml   →  declares HOW to build the wheel (recipe only, nothing runs)
        │
`databricks bundle deploy -t prod`  →  CLI runs the build command NOW
        │                               → produces dist/*.whl
        │                               → uploads it to the workspace
        ▼
job tasks reference `../../dist/*.whl`  →  install it on the cluster at run time
```

### Why the workflow installs hatchling first

Remember the `pip install hatchling` step before the deploy in the `deploy-jobs` workflow? That's there because the `pip wheel .` build command needs a **build backend** (hatchling) available to actually assemble the wheel. So the workflow installs the build tool first, *then* the deploy step triggers the build.

---

## In one sentence

A Python wheel is a pre-built, zip-format package that installs by simply unzipping; in this repo it's created **during `databricks bundle deploy`** using the recipe defined in `databricks.yml`'s `artifacts` block — not when the YAML is read, and not before the deploy step.
