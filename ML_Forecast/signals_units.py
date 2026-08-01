import pandas as pd
import numpy as np
from .numpy_time_series_utils import (
    build_group_position_arrays,
    rolling_mean_shift1,
    rolling_slope_shift1,
    rolling_var_shift1,
    rolling_zero_count_shift1,
    shift_array,
)
from .databricks_io import (
    assert_val_date_rows,
)
from .databricks_utils import finalize_val_date_table, to_date_columns


ROLLING_FEATURE_WINDOW = 12
ROLLING_FEATURE_MIN_PERIODS = 3
ZERO_FLOOR_EPSILON = 1e-9


def _floor_near_zero(values, epsilon):
    floored = values.copy()
    finite_mask = np.isfinite(floored)
    near_zero_mask = finite_mask & (np.abs(floored) < epsilon)
    floored[near_zero_mask] = 0.0
    return floored


def _build_config(
    run_val_date,
    source_table,
    seasonality_factors_table,
    calendar_table,
    population_table,
    risk_table,
    target_table,
    write_catalog,
    write_schema,
):
    val_date_ts = pd.to_datetime(run_val_date)
    val_date_str = val_date_ts.strftime("%Y-%m-%d")
    return {
        'val_date_str': val_date_str,
        'val_date': val_date_ts,
        'source': source_table,
        'seasonality_factors_table': seasonality_factors_table,
        'calendar_table': calendar_table,
        'population_table': population_table,
        'risk_table': risk_table,
        'catalog': write_catalog,
        'schema': write_schema,
        'output_table': target_table,
        'runout': 3,
        'cf_product_level': ['MARKET', 'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_2_TADM', 'PRODUCT_LEVEL_3_TADM', 'IS_DUAL'],
        'cf_claim_level': ['HCC', 'SERVICE_TYPE', 'SERVICE_CATEGORY'],
        'cf_dates': ['DATE_REPORT_QTR', 'DATE_REPORT_MONTH', 'DURATION'],
        'features': [
            'MARKET_ENCODED_UTIL_PRE', 'MARKET_ENCODED_UTIL', 'CATEGORY_ENCODED_UTIL_PRE', 'CATEGORY_ENCODED_UTIL',
            'PRODUCT_ENCODED_UTIL_PRE', 'PRODUCT_ENCODED_UTIL', 'TARGET_UTIL_1', 'TARGET_UTIL_2',
            'TARGET_UTIL_3', 'TARGET_UTIL_12', 'COUNT_ZEROS_UTIL', 'VARIANCE_12_MO_UTIL',
            'SLOPE_12_UTIL',
            'MARKET_ENCODED_PMPM_PRE', 'MARKET_ENCODED_PMPM', 'CATEGORY_ENCODED_PMPM_PRE', 'CATEGORY_ENCODED_PMPM',
            'PRODUCT_ENCODED_PMPM_PRE', 'PRODUCT_ENCODED_PMPM', 'TARGET_PMPM_1', 'TARGET_PMPM_2',
            'TARGET_PMPM_3', 'TARGET_PMPM_12', 'COUNT_ZEROS_PMPM', 'VARIANCE_12_MO_PMPM',
            'SLOPE_12_PMPM',
            'MM', 'WORKDAY', 'MONTH', 'PEDIATRIC_PERCENTAGE', 'ADULT_PERCENTAGE', 'SENIOR_PERCENTAGE',
            'FEMALE_PERCENTAGE', 'RACE_GROUP1_PERCENTAGE', 'RACE_GROUP2_PERCENTAGE', 'RACE_GROUP3_PERCENTAGE', 'RACE_GROUP4_PERCENTAGE',
            'DUAL_ALIGNED_PERCENTAGE', 'RURAL_PERCENTAGE', 'ACO_PERCENTAGE', 'PROSP_RISK',
            'SEASONAL_FACTOR_UTIL', 'SEASONAL_FACTOR_PMPM',
        ],
    }


def _load_source(spark, config):
    assert_val_date_rows(spark, config['source'], config['val_date_str'], stage_name='SIGNALS_UNITS')
    source = spark.table(config['source']).filter(f"VAL_DATE = TO_DATE('{config['val_date_str']}')").toPandas()
    source['BF_ESTIMATE_UTIL'] = source['BF_ESTIMATE_UTIL_K'] * (source['MM'] / 12000)
    source['BF_ESTIMATE_PD'] = source['BF_ESTIMATE_PMPM'] * source['MM']
    source['DURATION'] = source['DURATION'].astype(int)
    return source


def _aggregate_and_normalize_claims(source, config):
    group = config['cf_product_level'] + config['cf_claim_level'] + config['cf_dates']
    sumcols = [col for col in source.columns if col not in group and pd.api.types.is_numeric_dtype(source[col])]
    df = source.groupby(group)[sumcols].sum().reset_index()

    df['UTIL_K'] = df['UTIL'] * (12000 / df['MM'])
    df['PMPM'] = df['PD'] / df['MM']
    df['BF_ESTIMATE_UTIL_K'] = df['BF_ESTIMATE_UTIL'] * (12000 / df['MM'])
    df['BF_ESTIMATE_PMPM'] = df['BF_ESTIMATE_PD'] / df['MM']

    group = config['cf_product_level'] + config['cf_claim_level']
    df = df.sort_values(by=group + ['DATE_REPORT_QTR', 'DATE_REPORT_MONTH']).reset_index(drop=True)
    df['TARGET_UTIL'] = df['BF_ESTIMATE_UTIL_K'].copy()
    df['TARGET_PMPM'] = df['BF_ESTIMATE_PMPM'].copy()
    return df


def _fetch_seasonality_factors(spark, config):
    factors = spark.table(config['seasonality_factors_table']).select(
        'MARKET',
        'PRODUCT_LEVEL_1_TADM',
        'PRODUCT_LEVEL_3_TADM',
        'HCC',
        'SERVICE_CATEGORY',
        'METRIC',
        'MONTH',
        'FINAL_NORM_FACTOR',
    ).toPandas()

    factors = factors.copy()
    factors['METRIC'] = factors['METRIC'].astype(str).str.upper()
    factors = factors[factors['METRIC'].isin(['UTIL', 'PMPM'])].reset_index(drop=True)
    factors['MONTH'] = factors['MONTH'].astype(int)
    factors['FINAL_NORM_FACTOR'] = pd.to_numeric(factors['FINAL_NORM_FACTOR'], errors='coerce')

    dup_keys = ['MARKET', 'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_3_TADM',
                'HCC', 'SERVICE_CATEGORY', 'METRIC', 'MONTH']
    if factors.duplicated(subset=dup_keys, keep=False).any():
        raise ValueError(
            f"SIGNALS_UNITS: duplicate seasonality factor keys in {config['seasonality_factors_table']}"
        )

    join_keys = [
        'MARKET',
        'PRODUCT_LEVEL_1_TADM',
        'PRODUCT_LEVEL_3_TADM',
        'HCC',
        'SERVICE_CATEGORY',
        'MONTH',
    ]

    util_factors = factors[factors['METRIC'] == 'UTIL'][
        join_keys + ['FINAL_NORM_FACTOR']
    ].rename(columns={'FINAL_NORM_FACTOR': 'SEASONAL_FACTOR_UTIL'})
    pmpm_factors = factors[factors['METRIC'] == 'PMPM'][
        join_keys + ['FINAL_NORM_FACTOR']
    ].rename(columns={'FINAL_NORM_FACTOR': 'SEASONAL_FACTOR_PMPM'})

    return util_factors.merge(pmpm_factors, on=join_keys, how='outer')


def _fetch_calendar(spark, df, config):
    mindate = df['DATE_REPORT_MONTH'].min().strftime('%Y-%m-%d')
    maxdate = df['DATE_REPORT_MONTH'].max().strftime('%Y-%m-%d')
    cal_sql = f"""
            Select
                FIRST_DAY_MONTH as DATE_REPORT_MONTH,
                LINEAR_MONTH,
                MONTH_NBR as MONTH,
                sum(WORKDAY) as WORKDAY
            FROM {config['calendar_table']}
            WHERE FIRST_DAY_MONTH between '{mindate}' and '{maxdate}'
            GROUP BY ALL
            """
    return spark.sql(cal_sql).toPandas()


def _fetch_population(spark, config):
    pop_sql = f"""Select
        DATE_REPORT_QTR,
        DATE_REPORT_MONTH,
        MARKET,
        PRODUCT_LEVEL_1_TADM,
        PRODUCT_LEVEL_2_TADM,
        PRODUCT_LEVEL_3_TADM,
        sum(CASE WHEN AGE_GROUP = 'Pediatric' then MED_MM else 0 end) as PEDIATRIC_COUNT,
        sum(CASE WHEN AGE_GROUP = 'Adult' then MED_MM else 0 end) as ADULT_COUNT,
        sum(CASE WHEN AGE_GROUP = 'Senior' then MED_MM else 0 end) as SENIOR_COUNT,
        sum(FEMALE_IND * MED_MM) as FEMALE_COUNT,
        sum(CASE WHEN RACE = 'group1' then MED_MM else 0 end) as RACE_GROUP1_COUNT,
        sum(CASE WHEN RACE = 'group2' then MED_MM else 0 end) as RACE_GROUP2_COUNT,
        sum(CASE WHEN RACE = 'group3' then MED_MM else 0 end) as RACE_GROUP3_COUNT,
        sum(CASE WHEN RACE = 'group4' then MED_MM else 0 end) as RACE_GROUP4_COUNT,
        sum(DUAL_ALIGNED * MED_MM) as DUAL_ALIGNED_COUNT,
        sum(RURAL * MED_MM) as RURAL_COUNT,
        sum(ACO_IND * MED_MM) as ACO_COUNT,
        sum(MED_MM) as MM
    From {config['population_table']}
    group by all
    ;
    """
    pop_df = spark.sql(pop_sql).toPandas()

    # Population data is not stratified by IS_DUAL; exclude it from groupby keys
    group = [c for c in config['cf_product_level'] if c != 'IS_DUAL'] + ['DATE_REPORT_QTR', 'DATE_REPORT_MONTH']
    sumcols = [col for col in pop_df.columns if col not in group]
    pop_df = pop_df.groupby(group)[sumcols].sum().reset_index()

    for col in sumcols:
        if col != 'MM':
            col_name = col.replace('COUNT', 'PERCENTAGE')
            pop_df[col_name] = pop_df[col] / pop_df['MM']
            pop_df.drop(col, axis=1, inplace=True)
    pop_df.drop('MM', axis=1, inplace=True)
    return pop_df


def _fetch_risk(spark, config):
    risk_df = spark.table(config['risk_table']).toPandas()
    # Risk data is not stratified by IS_DUAL; exclude it from groupby keys
    group = [c for c in config['cf_product_level'] if c != 'IS_DUAL'] + ['DATE_REPORT_MONTH']
    sumcols = [col for col in risk_df.columns if col not in group]
    risk_df = risk_df.groupby(group)[sumcols].sum().reset_index()
    risk_df['PROSP_RISK'] = risk_df['PROSP_RISK_AGG'] / risk_df['MM']
    risk_df.drop(['PROSP_RISK_AGG', 'MM'], axis=1, inplace=True)
    return risk_df


def _resolve_product_and_category(config):
    if 'PRODUCT_LEVEL_3_TADM' in config['cf_product_level']:
        product = 'PRODUCT_LEVEL_3_TADM'
    elif 'PRODUCT_LEVEL_2_TADM' in config['cf_product_level']:
        product = 'PRODUCT_LEVEL_2_TADM'
    else:
        product = 'PRODUCT_LEVEL_1_TADM'
    category = 'SERVICE_CATEGORY' if 'SERVICE_CATEGORY' in config['cf_claim_level'] else 'HCC'
    return product, category


def _add_rolling_quarter_fields(df, group):
    df['UTIL_ROLLING_QTR'] = df.groupby(group)['BF_ESTIMATE_UTIL'].transform(lambda x: x.rolling(window=3).sum())
    df['MEM_ROLLING_QTR'] = df.groupby(group)['MM'].transform(lambda x: x.rolling(window=3).sum())
    df['PD_ROLLING_QTR'] = df.groupby(group)['BF_ESTIMATE_PD'].transform(lambda x: x.rolling(window=3).sum())

    df['UTILK_ROLLING_QTR'] = df['UTIL_ROLLING_QTR'] / df['MEM_ROLLING_QTR'] * 12000
    df['PMPM_ROLLING_QTR'] = df['PD_ROLLING_QTR'] / df['MEM_ROLLING_QTR']

    df['UTILK_ROLLING_QTR_SHIFTED'] = df.groupby(group)['UTILK_ROLLING_QTR'].shift(1)
    df['PMPM_ROLLING_QTR_SHIFTED'] = df.groupby(group)['PMPM_ROLLING_QTR'].shift(1)
    return df


def _add_metric_features(df, group, metric, product, category):
    if metric == 'UTIL':
        metric_source_suffix = 'UTIL_K'
    else:
        metric_source_suffix = metric

    out = df.copy()

    out[f'MARKET_ENCODED_{metric}_PRE'] = (
        out.groupby(['MARKET', 'PRODUCT_LEVEL_1_TADM', 'HCC', 'DATE_REPORT_MONTH'])[f'TARGET_{metric}'].transform('mean')
    )
    out[f'PRODUCT_ENCODED_{metric}_PRE'] = (
        out.groupby([product, 'PRODUCT_LEVEL_1_TADM', 'HCC', 'DATE_REPORT_MONTH'])[f'TARGET_{metric}'].transform('mean')
    )
    out[f'CATEGORY_ENCODED_{metric}_PRE'] = (
        out.groupby([category, 'PRODUCT_LEVEL_1_TADM', 'HCC', 'DATE_REPORT_MONTH'])[f'TARGET_{metric}'].transform('mean')
    )

    row_count = len(out)
    group_positions = build_group_position_arrays(out, group)

    target_values = out[f'TARGET_{metric}'].to_numpy(dtype=np.float64)
    bf_values = out[f'BF_ESTIMATE_{metric_source_suffix}'].to_numpy(dtype=np.float64)
    bf_values = _floor_near_zero(bf_values, ZERO_FLOOR_EPSILON)
    market_pre_values = out[f'MARKET_ENCODED_{metric}_PRE'].to_numpy(dtype=np.float64)
    product_pre_values = out[f'PRODUCT_ENCODED_{metric}_PRE'].to_numpy(dtype=np.float64)
    category_pre_values = out[f'CATEGORY_ENCODED_{metric}_PRE'].to_numpy(dtype=np.float64)

    market_encoded = np.full(row_count, np.nan, dtype=np.float64)
    product_encoded = np.full(row_count, np.nan, dtype=np.float64)
    category_encoded = np.full(row_count, np.nan, dtype=np.float64)
    target_1 = np.full(row_count, np.nan, dtype=np.float64)
    target_2 = np.full(row_count, np.nan, dtype=np.float64)
    target_3 = np.full(row_count, np.nan, dtype=np.float64)
    target_12 = np.full(row_count, np.nan, dtype=np.float64)
    count_zeros = np.full(row_count, np.nan, dtype=np.float64)
    variance_12_mo = np.full(row_count, np.nan, dtype=np.float64)
    slope_12 = np.full(row_count, np.nan, dtype=np.float64)

    for pos in group_positions:
        group_target = target_values[pos]
        group_bf = bf_values[pos]

        target_1_group = shift_array(group_target, 1)
        target_2_group = shift_array(group_target, 2)
        target_3_group = shift_array(group_target, 3)
        target_12_group = shift_array(group_target, 12)

        market_encoded[pos] = rolling_mean_shift1(
            market_pre_values[pos],
            window=ROLLING_FEATURE_WINDOW,
            min_periods=ROLLING_FEATURE_MIN_PERIODS,
        )
        product_encoded[pos] = rolling_mean_shift1(
            product_pre_values[pos],
            window=ROLLING_FEATURE_WINDOW,
            min_periods=ROLLING_FEATURE_MIN_PERIODS,
        )
        category_encoded[pos] = rolling_mean_shift1(
            category_pre_values[pos],
            window=ROLLING_FEATURE_WINDOW,
            min_periods=ROLLING_FEATURE_MIN_PERIODS,
        )

        target_1[pos] = target_1_group
        target_2[pos] = target_2_group
        target_3[pos] = target_3_group
        target_12[pos] = target_12_group

        count_zeros[pos] = rolling_zero_count_shift1(
            group_bf,
            window=ROLLING_FEATURE_WINDOW,
            min_periods=ROLLING_FEATURE_MIN_PERIODS,
        )
        variance_12_mo[pos] = rolling_var_shift1(
            group_target,
            window=ROLLING_FEATURE_WINDOW,
            min_periods=ROLLING_FEATURE_MIN_PERIODS,
        )
        slope_12[pos] = rolling_slope_shift1(
            group_bf,
            window=ROLLING_FEATURE_WINDOW,
            min_periods=ROLLING_FEATURE_MIN_PERIODS,
        )

    out[f'MARKET_ENCODED_{metric}'] = market_encoded
    out[f'PRODUCT_ENCODED_{metric}'] = product_encoded
    out[f'CATEGORY_ENCODED_{metric}'] = category_encoded
    out[f'TARGET_{metric}_1'] = target_1
    out[f'TARGET_{metric}_2'] = target_2
    out[f'TARGET_{metric}_3'] = target_3
    out[f'TARGET_{metric}_12'] = target_12
    out[f'COUNT_ZEROS_{metric}'] = count_zeros
    out[f'VARIANCE_12_MO_{metric}'] = variance_12_mo
    out[f'SLOPE_12_{metric}'] = slope_12
    return out


def _merge_auxiliary_features(df, calendar, pop_df, risk_df, seasonality_df, config):
    df = df.merge(calendar, on='DATE_REPORT_MONTH', how='left').reset_index(drop=True)

    # Population and risk data are not stratified by IS_DUAL; exclude it from
    # merge keys. Auxiliary values are shared across IS_DUAL within the same product/month.
    _product_level_no_dual = [c for c in config['cf_product_level'] if c != 'IS_DUAL']
    pop_group = _product_level_no_dual + ['DATE_REPORT_QTR', 'DATE_REPORT_MONTH']
    df = df.merge(pop_df, on=pop_group, how='left').reset_index(drop=True)

    risk_group = _product_level_no_dual + ['DATE_REPORT_MONTH']
    df = df.merge(risk_df, on=risk_group, how='left').reset_index(drop=True)

    seasonality_keys = [
        'MARKET', 'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_3_TADM',
        'HCC', 'SERVICE_CATEGORY', 'MONTH',
    ]
    df = df.merge(seasonality_df, on=seasonality_keys, how='left').reset_index(drop=True)
    return df


def _build_final_output(df, config):
    df['VAL_DATE'] = config['val_date_str']
    signals_level_cols = config['cf_product_level'] + config['cf_claim_level'] + config['cf_dates'] + ['VAL_DATE']
    signals_calc_cols = ['TARGET_UTIL', 'TARGET_PMPM'] + config['features']
    signals_table_final = df[signals_level_cols + signals_calc_cols].reset_index(drop=True)
    return to_date_columns(signals_table_final, ['DATE_REPORT_MONTH', 'VAL_DATE'])

def run(
    spark,
    run_val_date,
    source_table,
    seasonality_factors_table,
    calendar_table,
    population_table,
    risk_table,
    target_table,
    write_catalog,
    write_schema,
):
    config = _build_config(
        run_val_date,
        source_table,
        seasonality_factors_table,
        calendar_table,
        population_table,
        risk_table,
        target_table,
        write_catalog,
        write_schema,
    )
    source = _load_source(spark, config)
    df = _aggregate_and_normalize_claims(source, config)
    calendar = _fetch_calendar(spark, df, config)
    pop_df = _fetch_population(spark, config)
    risk_df = _fetch_risk(spark, config)
    seasonality_df = _fetch_seasonality_factors(spark, config)

    group = config['cf_product_level'] + config['cf_claim_level']
    df = _add_rolling_quarter_fields(df, group)

    product, category = _resolve_product_and_category(config)
    for metric in ['UTIL', 'PMPM']:
        df = _add_metric_features(df, group, metric, product, category)

    df = _merge_auxiliary_features(df, calendar, pop_df, risk_df, seasonality_df, config)
    signals_table_final = _build_final_output(df, config)

    finalize_val_date_table(
        spark,
        signals_table_final,
        config['output_table'],
        config['catalog'],
        config['schema'],
        config['val_date_str'],
        ['DATE_REPORT_MONTH', 'VAL_DATE'],
    )

    return {
        'status': 'SUCCESS',
        'target_table': f"{config['catalog']}.{config['schema']}.{config['output_table']}",
        'rows_written': int(len(signals_table_final)),
    }
