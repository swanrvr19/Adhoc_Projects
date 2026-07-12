# Linting and Formatting Workflow — Explained

This document explains the `Linting and Formatting.yaml` GitHub Actions workflow chunk by chunk.
It's a CI pipeline that runs automated code-quality checks on a Databricks-oriented Python project.

---

## Top-level configuration (lines 1–9)

```yaml
name: Linting and Formatting
on:
  workflow_dispatch:
  pull_request:
    types: [opened, synchronize, reopened]
env:
  PIP_NO_INPUT: "1"
```

- **`name`** — what shows up in the GitHub Actions tab.
- **`on:`** — the triggers:
  - `workflow_dispatch` lets you run it manually from the GitHub UI.
  - `pull_request` runs it automatically when a PR is opened, updated with new commits (`synchronize`), or reopened.
- **`PIP_NO_INPUT: "1"`** — a global env var telling pip never to pause for interactive prompts (important on a CI runner where nobody is there to type).

---

## The jobs

There are **six jobs** that all run in parallel: `embedded-sql-check`, `ruff-check`, `ruff-format-check`, `pylint`, `ty`, and `pytest`. Each is an independent quality gate — if any fails, the PR check fails.

### Shared setup pattern (repeated in every job)

```yaml
if: ${{ github.event.pull_request.head.repo.full_name == github.repository && github.actor != 'github-actions[bot]' }}
runs-on: uhg-runner
permissions:
  contents: read
```

- **`if` condition** (present on the first three jobs) — the job only runs when the PR comes from a branch **within the same repo** (not an outside fork) and the actor isn't the bot itself. This is a security guard: fork PRs can't run with access to secrets, and it prevents the bot's own commits from re-triggering an infinite loop.
- **`runs-on: uhg-runner`** — targets a self-hosted runner (UHG = UnitedHealth Group / Optum).
- **`permissions: contents: read`** — read-only repo access (least-privilege).

Each job's first three steps are identical:

```yaml
- Checkout repository        # actions/checkout@v6 — pulls your code onto the runner
- Set up Python              # installs Python 3.12
- Install uv                 # installs uv, a fast Python package manager
```

The `PIP_INDEX_URL` / `PIP_EXTRA_INDEX_URL` (and `UV_*` equivalents) env vars point pip and uv at Optum's **internal JFrog Artifactory** mirrors instead of public PyPI, authenticating with the `JFROG_User` / `JFROG_Token` secrets. This is standard for a corporate environment that doesn't allow direct public-internet package downloads.

---

### Job 1 — `embedded-sql-check` (lines 12–55)

Runs `uv sync --dev` to install the project plus dev dependencies, then checks that **SQL written inside Python/notebook files is properly formatted**:

```bash
mapfile -t py_files < <(git ls-files '*.py')
if [ ${#py_files[@]} -gt 0 ]; then
  uv run embedded-sql --check --diff "${py_files[@]}"
fi
```

- `git ls-files '*.py'` collects all tracked Python files into an array; the `if` guard skips the step if there are none (avoids errors on an empty list).
- `embedded-sql --check --diff` verifies formatting without changing anything and prints a diff of what would change.
- A second step does the same for Jupyter notebooks (`.ipynb`) using **nbqa**, a tool that runs any Python linter/formatter against notebook cells.

---

### Job 2 — `ruff-check` (lines 57–81)

```yaml
- name: Ruff check
  run: uvx ruff check
```

Runs **Ruff**, a very fast linter, to catch code issues (unused imports, undefined names, style violations, etc.). `uvx` runs the tool in a throwaway environment without installing it into the project.

---

### Job 3 — `ruff-format-check` (lines 83–125)

Has an extra pre-processing step before the format check:

```bash
# Strip trailing blank lines, then ensure exactly one newline at EOF
sed -i -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$f"
```

The inline comment explains why: Ruff running inside Databricks doesn't reliably add a missing end-of-file newline to notebook source, which would cause this format check to fail. So the workflow strips trailing blank lines and guarantees each `.py`/`.pyi` file ends with exactly one newline first. Then:

```yaml
- name: Ruff format check
  run: uvx ruff format --check --diff
```

`ruff format --check` verifies the code matches Ruff's formatting style (like Black) without modifying files, showing a diff if anything's off.

---

### Job 4 — `pylint` (lines 127–167)

> Note: this job (and the last two) **drop the `if` guard**, so they run on all PRs including forks.

Runs **Pylint** with the **databricks-labs-pylint** plugin, which adds Databricks-specific lint rules:

```bash
uv run --with databricks-labs-pylint pylint \
  --load-plugins=databricks.labs.pylint.all \
  --ignore=.venv --recursive=y .
```

- `--recursive=y .` lints the whole tree, skipping the `.venv` folder.
- The notebook step disables two checks — `C0103` (naming conventions) and `E0602` (undefined variable) — because notebooks legitimately use non-standard names and rely on globals injected by the Databricks runtime (like `spark`, `dbutils`) that would otherwise trip false positives.

---

### Job 5 — `ty` (lines 169–198)

```yaml
- name: Run ty
  run: uv run ty check .
```

**ty** is Astral's (the Ruff makers') type checker — it verifies type annotations across the codebase, similar to mypy.

---

### Job 6 — `pytest` (lines 200–229)

```yaml
- name: Run pytest
  run: uv run pytest
```

Runs the project's **test suite** with pytest.

---

## The big picture

On every PR, six checks run in parallel:

1. **embedded-sql-check** — SQL embedded in Python/notebooks is formatted
2. **ruff-check** — linting
3. **ruff-format-check** — code formatting
4. **pylint** — linting with Databricks-specific rules
5. **ty** — type checking
6. **pytest** — unit tests

All must pass for the PR to be green. The whole thing is built around **uv** for fast, reproducible installs, pulls packages from Optum's internal Artifactory, and has fork-safety guards on the checks that matter most. The SQL-in-Python checks, the Databricks pylint plugin, and the EOF-newline workaround all indicate a **Databricks-oriented Python project**.

### Possible improvement

There's a lot of repeated setup boilerplate (checkout → Python → uv → install) across all six jobs. This could be factored into a **reusable composite action** or a matrix strategy to reduce duplication and make future changes (e.g., bumping Python versions or Artifactory URLs) a single-place edit.
