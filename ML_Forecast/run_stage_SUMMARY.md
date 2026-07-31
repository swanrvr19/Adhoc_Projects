# run_stage.py — Summary

## What it is

A thin command-line entry point that runs exactly one stage of the
`cs-ml-trend-forecast` pipeline. It is designed to be invoked as a
`spark_python_task` inside a multi-task Databricks job, once per stage.

## What it does

```
python run_stage.py --stage lightgbm_train --val-date 2026-03-01
```

1. Parses `--stage`, `--val-date`, and optionally `--model-id`.
2. Loads `config/pipeline_config.yaml` and injects the valuation date.
3. Looks the stage up in a dispatch table and calls its runner.
4. Prints the result.
5. If the stage was `lightgbm_train` and it succeeded, publishes the resulting
   `model_id` so the downstream predict task can find it.

## The five stages

| Stage | Purpose |
|---|---|
| `completion` | Complete partial claims data for recent months |
| `valuation` | Apply seasonality and valuation adjustments |
| `signals_units` | Build the feature/signal set for modeling |
| `lightgbm_train` | Train models, register a `model_id` |
| `lightgbm_predict` | Generate forecasts using a trained model |

Order matters — each stage reads what the previous one wrote. The script itself
enforces nothing about ordering; that lives in the Databricks job's task
dependency graph.

## Why one script instead of five

A single entry point means one deployment artifact, one config loading path, and
one place to add cross-cutting behavior. The Databricks job defines five tasks
that all point at this file with different `--stage` values, which keeps the job
definition readable and the retry semantics per-stage.

## The model_id handoff

The one piece of real state passing between tasks. When training succeeds,
`run_stage.py` publishes the model ID two ways:

1. **Task value** — `dbutils.jobs.taskValues.set()`, retrievable downstream as
   `{{tasks.lightgbm_train.values.model_id}}`. Visible in the job UI.
2. **Volume file** — written to `{model_store_path}/.last_model_id`.

The predict stage prefers `--model-id` if passed, falls back to reading the file,
and raises a clear error if neither is available. Belt and suspenders — the task
value is cleaner but only works within a single job run, while the file survives
across runs and manual invocations.

## Design notes

- **Lazy imports.** Each `run_*` function imports its pipeline module inside the
  function body, so a task only loads the dependencies it actually needs.
- **Dispatch dictionary.** `STAGE_RUNNERS` maps names to functions; `argparse`
  validates against `VALID_STAGES`. Adding a stage means adding a function and
  two list entries.
- **Config-driven.** Every table name and path comes from the YAML file. The
  only runtime input is the valuation date.
- **Explicit argument passing.** Runners unpack config keys into named
  parameters rather than passing the config dict through, so each pipeline
  module's interface is visible at the call site.

## Things to watch

- `lightgbm_predict` is the only stage with a special signature, handled by an
  `if` in `main()` rather than a uniform interface.
- Config access is a mix of `[...]` and `.get(...)`; the bracket form means a
  missing YAML key raises `KeyError` at call time, not at load time.
- `deepcopy` is imported but unused.
