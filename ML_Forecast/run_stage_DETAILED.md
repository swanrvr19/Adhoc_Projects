# run_stage.py — Detailed Walkthrough

A section-by-section reading of the pipeline stage runner.

---

## 1. Module docstring

```python
"""Single-stage runner for the cs-ml-trend-forecast pipeline.

Designed to be called as a spark_python_task in a multi-task Databricks job.
Each task invokes this script with --stage <name> --val-date <date>.

For lightgbm_train: sets a task value 'model_id' so downstream tasks can
retrieve it via {{tasks.lightgbm_train.values.model_id}}.

For lightgbm_predict: accepts --model-id to receive the trained model ID
from the upstream task.
"""
```

A good docstring — it states the deployment context, the invocation pattern, and
the one non-obvious mechanism (the model_id handoff) including the exact
Databricks template syntax a job author would need. Anyone wiring up the job can
work from this alone.

---

## 2. Imports and path resolution

```python
import argparse
import inspect
from copy import deepcopy
from pathlib import Path

import yaml
from pyspark.sql import SparkSession
from pyspark.dbutils import DBUtils

_PIPELINE_DIR = Path(inspect.getfile(inspect.currentframe())).resolve().parent
DEFAULT_CONFIG_PATH = _PIPELINE_DIR / 'config' / 'pipeline_config.yaml'
```

The path resolution line is doing real work. Broken down:

- `inspect.currentframe()` — the currently executing frame
- `inspect.getfile(...)` — the file that frame belongs to
- `.resolve()` — absolute, symlinks followed
- `.parent` — the containing directory

The simpler `Path(__file__).resolve().parent` would normally do this. The
`inspect` route is more robust in environments where `__file__` is unreliable or
absent — which includes some Databricks execution contexts, where the script may
be loaded in a way that doesn't set it conventionally. Given this file is
explicitly built for `spark_python_task`, that's a deliberate choice, not
over-engineering.

The effect: config is found relative to the script's own location, so the job
works regardless of the working directory it's launched from.

`deepcopy` is imported and never used. Likely a remnant of an earlier version that
copied the config per stage.

```python
VALID_STAGES = ['completion', 'valuation', 'signals_units', 'lightgbm_train', 'lightgbm_predict']
```

Declared at module level and used as `argparse`'s `choices`, so an invalid stage
name fails at parse time with a helpful message rather than raising a `KeyError`
after Spark has already spun up. The list order also documents the intended
execution sequence.

---

## 3. Config loading

```python
def load_pipeline_config(config_path=DEFAULT_CONFIG_PATH):
    with open(config_path, 'r', encoding='utf-8') as stream:
        return yaml.safe_load(stream)
```

Four lines, three decisions worth noting:

- `safe_load` rather than `load` — will not instantiate arbitrary Python objects
  from YAML. Correct default even for a trusted internal file.
- Explicit `encoding='utf-8'` — avoids depending on the platform's locale.
- `config_path` is a parameter with a default, which makes the function testable
  with a fixture config.

---

## 4. Stage runner functions

Five functions with a shared shape. The simplest illustrates it:

```python
def run_valuation(spark, run_config):
    from src.pipeline import valuation
    return valuation.run(
        spark,
        run_val_date=run_config['run_val_date'],
        source_table=run_config['valuation']['source_table'],
        seasonality_factors_table=run_config['valuation']['seasonality_factors_table'],
        target_table=run_config['valuation']['target_table'],
        write_catalog=run_config['valuation']['write_catalog'],
        write_schema=run_config['valuation']['write_schema'],
    )
```

### The lazy import

`from src.pipeline import valuation` sits inside the function, not at module top.
This is intentional. A task running `completion` never imports the LightGBM or
SHAP modules, so it doesn't pay their import cost and doesn't fail if their
dependencies are missing from that cluster's environment. On a Spark cluster where
heavy ML libraries take real seconds to load, this is a measurable win — and it
means a broken import in one stage's module can't take down the other four.

### Explicit keyword unpacking

Each runner pulls individual keys out of the config and passes them as named
arguments rather than handing the whole dict to the pipeline module. More verbose,
but:

- The pipeline module's interface is visible at the call site
- Pipeline modules don't need to know the config's shape
- A missing key raises `KeyError` naming the exact key
- The functions are callable from a test without constructing a full config

### Config access patterns

Two forms appear:

```python
val_cf_enabled=run_config['completion']['val_cf_enabled'],                 # required
val_cf_source_table=run_config['completion'].get('val_cf_source_table'),   # optional → None
```

Bracket access means "this key must exist"; `.get()` means "optional, `None` is
fine." In `run_completion`, the `val_cf_*` table names are optional because
`val_cf_enabled` may be false, in which case they're never used.

Consistent and readable — but note that required-key errors surface when the
runner is called, after Spark has initialized. There's no upfront schema
validation of the YAML.

### Stage-specific notes

| Runner | Distinguishing detail |
|---|---|
| `run_completion` | Handles the optional `val_cf_*` (completion factor) path |
| `run_valuation` | Straightforward; reads seasonality factors |
| `run_signals_units` | Widest signature — five source tables (seasonality, calendar, population, risk) |
| `run_lightgbm_train` | Binds `cfg = run_config['lightgbm_train']` first to reduce repetition; passes `model_store_path` from the *top level* of config, not the stage block |
| `run_lightgbm_predict` | Takes a third parameter and contains fallback logic — see below |

The `model_store_path` being top-level rather than per-stage is deliberate: train
writes there and predict reads from there, so it has to be shared.

---

## 5. `run_lightgbm_predict` — the fallback path

```python
def run_lightgbm_predict(spark, run_config, model_id):
    from src.pipeline import lightgbm_predict
    from pyspark.dbutils import DBUtils
    cfg = run_config['lightgbm_predict']
    if not model_id:
        # Fallback: read model_id from Volume file written by lightgbm_train
        _dbutils = DBUtils(spark)
        model_id_path = f"{run_config.get('model_store_path', '/tmp')}/.last_model_id"
        try:
            model_id = _dbutils.fs.head(model_id_path).strip()
            print(f"Read model_id from {model_id_path}: {model_id}")
        except Exception:
            pass
    if not model_id:
        raise ValueError(
            "lightgbm_predict requires --model-id. Either pass it as a job parameter, "
            "or ensure lightgbm_train wrote it to the model store path."
        )
    return lightgbm_predict.run(spark, ..., model_id=model_id, ...)
```

The only runner with real logic. Three-level resolution:

1. **`--model-id` argument** — the normal path, populated by the Databricks task
   parameter `{{tasks.lightgbm_train.values.model_id}}`.
2. **Volume file** — `{model_store_path}/.last_model_id`, written by the train
   stage.
3. **Fail loudly** — a `ValueError` naming both remedies.

Why two mechanisms for the same value? They fail in different situations. Task
values only exist within a single job run, so re-running just the predict task, or
invoking the script manually for a debugging pass, loses them. The file persists.
Conversely, the task value is visible in the job UI and unambiguous about which
run produced it, while the file is last-writer-wins and could be stale.

The bare `except Exception: pass` is defensible here specifically — a missing file
is the expected case on a first run, and the code proceeds to a clear error two
lines later. It would still be better as `except Exception as e:` with a printed
warning, since a permissions problem and a missing file are currently
indistinguishable in the logs.

The `'/tmp'` default in `.get('model_store_path', '/tmp')` is a soft fallback that
will almost certainly not contain the file. It prevents a `KeyError` but doesn't
buy much.

The redundant `from pyspark.dbutils import DBUtils` inside the function duplicates
the module-level import. Harmless.

The error message is worth calling out as well-written: it names the flag, names
both ways to satisfy it, and doesn't require reading the source to act on.

---

## 6. Dispatch table

```python
STAGE_RUNNERS = {
    'completion': run_completion,
    'valuation': run_valuation,
    'signals_units': run_signals_units,
    'lightgbm_train': run_lightgbm_train,
    'lightgbm_predict': run_lightgbm_predict,
}
```

Name → function. Replaces an if/elif chain, and keeps the set of valid stages
declarative. Adding a stage is three edits: write the runner, add it to
`VALID_STAGES`, add it here.

The mild wart: `VALID_STAGES` and `STAGE_RUNNERS.keys()` must stay in sync
manually. `VALID_STAGES = list(STAGE_RUNNERS)` would enforce it, at the cost of
having to move the list below the function definitions.

---

## 7. `main()`

```python
parser = argparse.ArgumentParser(description='Run a single pipeline stage.')
parser.add_argument('--stage', required=True, choices=VALID_STAGES, help='Stage to run')
parser.add_argument('--val-date', required=True, help='Valuation date (YYYY-MM-DD)')
parser.add_argument('--model-id', default=None, help='Model ID for lightgbm_predict ...')
args = parser.parse_args()
```

Two required arguments, one optional. `choices=VALID_STAGES` gives free validation
and a usage message listing every valid stage. `--val-date` becomes `args.val_date`
under argparse's standard dash-to-underscore conversion.

```python
cfg = load_pipeline_config()
cfg['run_val_date'] = args.val_date
```

The valuation date is injected into the config rather than threaded through as a
separate parameter, so every runner reads it uniformly via
`run_config['run_val_date']`. This is why the runner signatures stay narrow.

Note this mutates the loaded dict in place — fine here, since the config is loaded
fresh per process invocation. (Possibly what `deepcopy` was once for.)

```python
spark = SparkSession.builder.getOrCreate()
dbutils = DBUtils(spark)
```

`getOrCreate()` attaches to the existing cluster session rather than building a new
one.

```python
if stage == 'lightgbm_predict':
    result = runner(spark, cfg, args.model_id)
else:
    result = runner(spark, cfg)
```

The one place the uniform interface breaks. It works, and with five stages the
special case is easy to see. If more stages grow extra parameters, the cleaner
refactor is to give every runner `(spark, config, args)` and let each pick what it
needs — the branch here would disappear.

```python
print(f"{stage.upper()} Result: {result}")
```

Stage results land in the Databricks driver log. The uppercase prefix makes them
greppable.

---

## 8. Publishing the model_id

```python
if stage == 'lightgbm_train' and result.get('status') == 'SUCCESS':
    model_id = result.get('model_id')
    if model_id:
        model_id_path = f"{cfg.get('model_store_path', '/tmp')}/.last_model_id"
        dbutils.fs.put(model_id_path, str(model_id), overwrite=True)
        print(f"Model ID written to {model_id_path}: {model_id}")

        dbutils.jobs.taskValues.set(key='model_id', value=str(model_id))
        print(f"Task value set: model_id={model_id}")
```

The guard is three conditions deep, and each is load-bearing:

1. `stage == 'lightgbm_train'` — only training produces a model
2. `result.get('status') == 'SUCCESS'` — **never publish a model ID from a failed
   run.** Without this, a partially-failed training job could hand a broken model
   to the predict stage, which would run happily and produce garbage.
3. `if model_id` — the runner returned success but no ID; skip rather than write
   `"None"` to the file

Then both publication paths, in order. The file first (durable), the task value
second (visible in the UI, consumable by the job's dependency wiring).

`str(model_id)` at both call sites — `dbutils.fs.put` and `taskValues.set` both
want strings, and the runner might return an int or a UUID object.

The `.last_model_id` leading dot follows the Unix hidden-file convention, marking
it as machine state rather than a user-facing artifact.

Both writes print. Between those two lines and the result print above, the driver
log tells you exactly what any given run produced.

---

## 9. Entry point

```python
if __name__ == '__main__':
    main()
```

Standard guard. Keeps the module importable — so `load_pipeline_config` or an
individual runner can be exercised from a test without triggering argument
parsing.

---

## How this fits the job

A Databricks multi-task job with five tasks, all pointing at this file:

```
completion → valuation → signals_units → lightgbm_train → lightgbm_predict
```

Each task supplies `--stage <name> --val-date {{job.parameters.val_date}}`, and
the predict task adds
`--model-id {{tasks.lightgbm_train.values.model_id}}`.

Dependencies are declared in the job definition, not in this script. That's the
right split — it means a failed stage retries independently, each stage gets its
own cluster sizing and logs, and the DAG is visible in the Databricks UI rather
than buried in Python control flow.

---

## Summary of observations

| Area | Note |
|---|---|
| Lazy imports | Good — per-stage dependency isolation and faster startup |
| Dispatch table | Clean; `VALID_STAGES` duplication is the only sync risk |
| Predict special case | Non-uniform signature handled by an `if` in `main()` |
| Success guard | Correctly prevents publishing a model_id from a failed train |
| Dual handoff | File + task value cover different failure modes; sensible redundancy |
| `except Exception: pass` | Justified in context, but hides permissions errors — a printed warning would cost nothing |
| `'/tmp'` default | Prevents a `KeyError` without providing a useful fallback |
| Config validation | No upfront schema check; missing keys surface at runner call time |
| Dead code | Unused `deepcopy` import; duplicate `DBUtils` import inside `run_lightgbm_predict` |
| Logging | `print` to the driver log throughout — adequate for Databricks, not structured |
