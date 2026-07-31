"""Single-stage runner for the cs-ml-trend-forecast pipeline.

Designed to be called as a spark_python_task in a multi-task Databricks job.
Each task invokes this script with --stage <name> --val-date <date>.

For lightgbm_train: sets a task value 'model_id' so downstream tasks can
retrieve it via {{tasks.lightgbm_train.values.model_id}}.

For lightgbm_predict: accepts --model-id to receive the trained model ID
from the upstream task.
"""

import argparse
import inspect
from copy import deepcopy
from pathlib import Path

import yaml
from pyspark.sql import SparkSession
from pyspark.dbutils import DBUtils

_PIPELINE_DIR = Path(inspect.getfile(inspect.currentframe())).resolve().parent
DEFAULT_CONFIG_PATH = _PIPELINE_DIR / 'config' / 'pipeline_config.yaml'

VALID_STAGES = ['completion', 'valuation', 'signals_units', 'lightgbm_train', 'lightgbm_predict']


def load_pipeline_config(config_path=DEFAULT_CONFIG_PATH):
    with open(config_path, 'r', encoding='utf-8') as stream:
        return yaml.safe_load(stream)


def run_completion(spark, run_config):
    from src.pipeline import completion
    return completion.run(
        spark,
        run_val_date=run_config['run_val_date'],
        source_table=run_config['completion']['source_table'],
        target_table=run_config['completion']['target_table'],
        write_catalog=run_config['completion']['write_catalog'],
        write_schema=run_config['completion']['write_schema'],
        val_cf_enabled=run_config['completion']['val_cf_enabled'],
        val_cf_source_table=run_config['completion'].get('val_cf_source_table'),
        val_cf_target_table=run_config['completion'].get('val_cf_target_table'),
    )


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


def run_signals_units(spark, run_config):
    from src.pipeline import signals_units
    return signals_units.run(
        spark,
        run_val_date=run_config['run_val_date'],
        source_table=run_config['signals_units']['source_table'],
        seasonality_factors_table=run_config['signals_units']['seasonality_factors_table'],
        calendar_table=run_config['signals_units']['calendar_table'],
        population_table=run_config['signals_units']['population_table'],
        risk_table=run_config['signals_units']['risk_table'],
        target_table=run_config['signals_units']['target_table'],
        write_catalog=run_config['signals_units']['write_catalog'],
        write_schema=run_config['signals_units']['write_schema'],
    )


def run_lightgbm_train(spark, run_config):
    from src.pipeline import lightgbm_train
    cfg = run_config['lightgbm_train']
    return lightgbm_train.run(
        spark,
        run_val_date=run_config['run_val_date'],
        source_table=cfg['source_table'],
        metric=cfg['metric'],
        hcc=cfg['hcc'],
        train_end=cfg['train_end'],
        model_store_path=run_config['model_store_path'],
    )


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
    return lightgbm_predict.run(
        spark,
        run_val_date=run_config['run_val_date'],
        source_table=cfg['source_table'],
        seasonality_factors_table=cfg['seasonality_factors_table'],
        calendar_table=cfg['calendar_table'],
        hectar_table=cfg['hectar_table'],
        target_table=cfg['target_table'],
        shap_table=cfg['shap_table'],
        write_catalog=cfg['write_catalog'],
        write_schema=cfg['write_schema'],
        metric=cfg['metric'],
        hcc=cfg['hcc'],
        projection_months=cfg['projection_months'],
        model_id=model_id,
        model_store_path=run_config['model_store_path'],
    )


STAGE_RUNNERS = {
    'completion': run_completion,
    'valuation': run_valuation,
    'signals_units': run_signals_units,
    'lightgbm_train': run_lightgbm_train,
    'lightgbm_predict': run_lightgbm_predict,
}


def main():
    parser = argparse.ArgumentParser(description='Run a single pipeline stage.')
    parser.add_argument('--stage', required=True, choices=VALID_STAGES, help='Stage to run')
    parser.add_argument('--val-date', required=True, help='Valuation date (YYYY-MM-DD)')
    parser.add_argument('--model-id', default=None, help='Model ID for lightgbm_predict (passed from lightgbm_train task)')
    args = parser.parse_args()

    cfg = load_pipeline_config()
    cfg['run_val_date'] = args.val_date

    spark = SparkSession.builder.getOrCreate()
    dbutils = DBUtils(spark)

    stage = args.stage
    runner = STAGE_RUNNERS[stage]

    if stage == 'lightgbm_predict':
        result = runner(spark, cfg, args.model_id)
    else:
        result = runner(spark, cfg)

    print(f"{stage.upper()} Result: {result}")

    # Publish model_id for downstream tasks
    if stage == 'lightgbm_train' and result.get('status') == 'SUCCESS':
        model_id = result.get('model_id')
        if model_id:
            # Write to Volume so predict task can read it as fallback
            model_id_path = f"{cfg.get('model_store_path', '/tmp')}/.last_model_id"
            dbutils.fs.put(model_id_path, str(model_id), overwrite=True)
            print(f"Model ID written to {model_id_path}: {model_id}")
            # Also set task value for job UI visibility
            dbutils.jobs.taskValues.set(key='model_id', value=str(model_id))
            print(f"Task value set: model_id={model_id}")


if __name__ == '__main__':
    main()
