# ── Scenario parameters ─────────────────────────────────────────────────────
# Set defaults here; overridden by dbutils.notebook.run() when called from
# RUN_FORECAST_SCENARIOS.ipynb.
dbutils.widgets.text("train_end", "2026-03-01")   # last experience month included in training (YYYY-MM-DD)
dbutils.widgets.text("hcc",       "PHYSICIAN")     # HCC / MAJ_SRV_CAT to train (e.g. PHYSICIAN, OUTPATIENT)
dbutils.widgets.text("val_date",  "2026-03-01")    # vintage marker from data prep (YYYY-MM-DD)

     

# Import python packages
import pandas as pd  
import numpy as np
import lightgbm as lgb 
import warnings
warnings.filterwarnings('ignore')
from scipy.stats import linregress
from sklearn.model_selection import train_test_split  
from sklearn.metrics import mean_squared_error  
     

config = {}

# --- Metrics & dates ---
config['metrics']           = ['PMPM', 'UTIL']
config['HCC']               = dbutils.widgets.get("hcc")
config['val_date']          = dbutils.widgets.get("val_date")
config['train_end']         = pd.to_datetime(dbutils.widgets.get("train_end"))  # last experience month included in training
config['train_start_lead']  = 12                              # burn-in months per group after first observation (set below in training params too)
config['projection_months'] = 21
config['projection_start']  = config['train_end'] + pd.DateOffset(months=1)
config['projection_end']    = config['projection_start'] + pd.DateOffset(months=config['projection_months'] - 1)
config['run_timestamp']     = pd.Timestamp.now()

# --- Source tables ---
config['source']      = 'ra_analytic_dev.ohc_forecast.cs_forecast_signals_encoded'
config['seasonality'] = 'ra_analytic_dev.ohc_forecast.cs_cf_seasonality_factors'

# --- Output tables ---
config['DB']          = 'ra_analytic_dev'
config['schema']      = 'ohc_forecast'
config['model_stage'] = 'ra_analytic_dev.ohc_forecast.model'
config['output_table_name'] = 'LIGHTGBM_PMPM_UTIL_OUTPUT_ENCODED'
config['shap_table_name']   = 'LIGHTGBM_PMPM_UTIL_SHAP_ENCODED'

# --- Training parameters (not likely to change) ---
config['model_name']        = {m: f"CS_FINAL_{m}_{config['HCC']}_{config['train_end'].strftime('%Y%m')}.txt" for m in config['metrics']}
config['test_offset']       = 1
config['one_hot_columns']   = [
    'MONTH', 'MARKET',
    'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_2_TADM', 'PRODUCT_LEVEL_3_TADM',
    'HCC', 'SERVICE_CATEGORY',
]

# --- Features ---
def get_metric_features(metric):
    return [
        f'MARKET_ENCODED_{metric}', f'CATEGORY_ENCODED_{metric}', f'PRODUCT_ENCODED_{metric}',
        f'TARGET_{metric}_1', f'TARGET_{metric}_2', f'TARGET_{metric}_3', f'TARGET_{metric}_12',
        f'COUNT_ZEROS_{metric}', f'VARIANCE_12_MO_{metric}', f'SLOPE_12_{metric}',
        'MM', 'WORKDAY',
        'PEDIATRIC_PERCENTAGE', 'ADULT_PERCENTAGE', 'SENIOR_PERCENTAGE', 'FEMALE_PERCENTAGE',
        'RACE_GROUP1_PERCENTAGE', 'RACE_GROUP2_PERCENTAGE', 'RACE_GROUP3_PERCENTAGE', 'RACE_GROUP4_PERCENTAGE',
        'DUAL_ALIGNED_PERCENTAGE', 'RURAL_PERCENTAGE', 'ACO_PERCENTAGE', 'PROSP_RISK',
    ]

config['features'] = {m: get_metric_features(m) for m in config['metrics']}

# --- Column rename map ---
config['col_map'] = {
    'PRODUCT_LEVEL_3_TADM': 'PRODUCT',
    'SERVICE_CATEGORY': 'CATEGORY',
    'MARKET': 'MARKET',
}

# --- Calendar lookup ---
def quarter_map():
    qtr = spark.table('ra_analytic_dev.cs_reference.calendar').toPandas()
    qtr_grp = ['FIRST_DAY_MONTH', 'MONTH_NBR', 'QUARTER_NBR', 'YEAR_NBR', 'LINEAR_MONTH']
    qtr = qtr.groupby(qtr_grp)['WORKDAY'].sum().reset_index()
    qtr['FIRST_DAY_MONTH'] = pd.to_datetime(qtr['FIRST_DAY_MONTH']).dt.strftime('%Y-%m-%d')
    qtr['QUARTER'] = qtr['YEAR_NBR'].astype(str) + 'Q' + qtr['QUARTER_NBR'].astype(str)
    qtr = qtr[['FIRST_DAY_MONTH', 'QUARTER', 'MONTH_NBR', 'LINEAR_MONTH', 'WORKDAY']]
    qtr.set_index('FIRST_DAY_MONTH', inplace=True)
    return qtr.to_dict('index')

config['calendar'] = quarter_map()

     

join_keys = [
    'MARKET', 'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_2_TADM', 'PRODUCT_LEVEL_3_TADM',
    'HCC', 'SERVICE_TYPE', 'SERVICE_CATEGORY', 'IS_DUAL', 'DATE_REPORT_MONTH',
]

segment_lookup = (
    spark.table('ra_analytic_dev.ohc_forecast.ohc_completed_combined')
    .filter(f"HCC = '{config['HCC']}'")
    .select(*join_keys, 'SEGMENT')
)

src_sdf = (
    spark.table(config['source'])
    .filter(f"HCC = '{config['HCC']}'")
    .drop('seasonal_factor_pmpm', 'seasonal_factor_util')
)

pre_count = src_sdf.count()
source = src_sdf.join(segment_lookup, on=join_keys, how='left').toPandas()
assert len(source) == pre_count, f"Join fan-out detected: {pre_count} rows before, {len(source)} after"

source['DATE_REPORT_MONTH'] = pd.to_datetime(source['DATE_REPORT_MONTH'])

# Start training data N months after each product/market started
group = ['MARKET', 'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_2_TADM', 'PRODUCT_LEVEL_3_TADM']
source['MINDATE'] = source.groupby(group)['DATE_REPORT_MONTH'].transform('min')
source['TRAIN_START'] = source['MINDATE'] + pd.DateOffset(months=config['train_start_lead'])
source = source[
    (source['DATE_REPORT_MONTH'] >= source['TRAIN_START']) &
    (source['DATE_REPORT_MONTH'] <= config['train_end'])
].sort_values(by=group).reset_index(drop=True)

# Per-group training data quality indicator (months available after burn-in)
source['N_TRAIN_MONTHS'] = (
    (config['train_end'].year * 12 + config['train_end'].month) -
    (source['TRAIN_START'].dt.year * 12 + source['TRAIN_START'].dt.month)
)
     

# Load full seasonality table once
seasonality_factors = spark.table(config['seasonality']).toPandas()

seasonality_merge_keys = ['MARKET', 'HCC', 'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_3_TADM', 'SERVICE_CATEGORY', 'MONTH']

# For each metric, join its own FINAL_NORM_FACTOR as a metric-specific column
for m in config['metrics']:
    sf = (seasonality_factors[seasonality_factors['METRIC'] == m][seasonality_merge_keys + ['FINAL_NORM_FACTOR']]
          .copy()
          .rename(columns={'FINAL_NORM_FACTOR': f'FINAL_NORM_FACTOR_{m}'}))
    source = source.merge(sf, on=seasonality_merge_keys, how='left')
    # Force float64 regardless of whether all rows matched — prevents int64 infer
    # when every row finds a match and all factor values are whole numbers (e.g. 1).
    source[f'FINAL_NORM_FACTOR_{m}'] = source[f'FINAL_NORM_FACTOR_{m}'].astype('float64')
    config['features'][m].append(f'FINAL_NORM_FACTOR_{m}')
     

source.loc[source['TARGET_PMPM']<0,'TARGET_PMPM'] = 0
     

# Split into the four subsets  
splits = {  
    "OHC_DUAL": source[(source['SEGMENT'] == 'OHC') & (source['IS_DUAL'] == 1)],  
    "OHC_NONDUAL": source[(source['SEGMENT'] == 'OHC') & (source['IS_DUAL'] == 0)],  
    "OC_DUAL": source[(source['SEGMENT'] == 'OC') & (source['IS_DUAL'] == 1)],  
    "OC_NONDUAL": source[(source['SEGMENT'] == 'OC') & (source['IS_DUAL'] == 0)]  
}  
     

def get_train_data(df, metric, config=config):
    # change datatype for categorical columns to category so LightGBM can process correctly
    model_data_dict = {}
    for col in config['one_hot_columns']:
        df[col] = df[col].astype(('category'))

    end_date = config['train_end'] - pd.DateOffset(months=config['test_offset'])

    train = df[df['DATE_REPORT_MONTH'] <= end_date]
    test = df[df['DATE_REPORT_MONTH'] > end_date]

    #Split into X and y training datasets
    model_data_dict['y_train'] = train[[f"TARGET_{metric}"]]
    model_data_dict['X_train'] = train[config['features'][metric]]

    #Split into X and y testing datasets
    model_data_dict['y_test'] = test[[f"TARGET_{metric}"]]
    model_data_dict['X_test'] = test[config['features'][metric]]
    
    return model_data_dict

def train_model(model_data_dict): 
    params = {  
        'objective': 'tweedie',  
        'metric': 'rmse',          # Root mean squared error  
        'boosting_type': 'gbdt',  
        'learning_rate': 0.01,  
        'num_leaves': 31, 
        'max_depth': 6,
        'feature_fraction': 0.8,  
        'bagging_fraction': 0.8,  
        'bagging_freq': 5,  
        'verbose': -1
        ,'early_stopping_rounds': 100
    }  
    
    categoricals = []
    for col in config['one_hot_columns']:
        if col in model_data_dict['X_train'].columns.to_list():
            categoricals += [col]
            
    # Convert datasets into LightGBM format  
    train_data = lgb.Dataset(model_data_dict['X_train'], label=model_data_dict['y_train'], categorical_feature=categoricals)
    test_data = lgb.Dataset(model_data_dict['X_test'], label=model_data_dict['y_test'], categorical_feature=categoricals)

    

    
    # Train the LightGBM model  
    model = lgb.train(params, train_data, num_boost_round=10000,   
                      valid_sets=[test_data]) 

    return model

def loop_train_models(df, metric, column=None, config=config):
    model_dict = {}
    y_predicted = pd.DataFrame()
    model_dict['final'] = {}
    data_dict = get_train_data(df, metric) 
    model_dict['final']['model'] = train_model(data_dict) 
    model = model_dict['final']['model']
    y_pred = model.predict(data_dict['X_train'], num_iteration=model.best_iteration)
    y_pred = pd.DataFrame({f"TARGET_{metric}_PREDICTED":y_pred}, index=data_dict['y_train'].index)
    y_pred_test = model.predict(data_dict['X_test'], num_iteration=model.best_iteration)
    y_pred_test = pd.DataFrame({f"TARGET_{metric}_PREDICTED":y_pred_test}, index=data_dict['y_test'].index)
    model_dict['final']['y_predicted'] = pd.concat([y_pred,y_pred_test])
    return model_dict, data_dict
     

splits.items()
     

trained_models = {}   # {metric: {split_name: model}}
skipped_splits = {}   # {metric: [split_name, ...]}

for metric in config['metrics']:
    print(f"\n{'='*60}")
    print(f"Training models for metric: {metric}")
    print(f"{'='*60}")

    trained_models[metric] = {}
    skipped_splits[metric] = []

    features = config['features'][metric]

    for split_name, split_df in splits.items():
        print(f"  Training {split_name}...")

        if split_df[features].dropna(how='all').empty:
            print(f"  WARNING: {split_name} has no usable training data — skipping.")
            skipped_splits[metric].append(split_name)
            continue

        model_dict, data_dict = loop_train_models(split_df, metric, config=config)
        trained_models[metric][split_name] = model_dict['final']['model']

print(f"\nTraining complete. Skipped splits: {skipped_splits}")

     

def calendar_lookup(row,item,config=config):  
    date = row['DATE_REPORT_MONTH'].strftime('%Y-%m-%d') 
    return config.get('calendar', {}).get(date, {}).get(item, 'Not Found')
    
def rolling_slope(x):  
    try:
        time = range(len(x))  
        slope, intercept, _, _, _ = linregress(time, x)  
    except:
        return None
    return slope 
    
def new_month(df, metric, config=config):
    last_date = df['DATE_REPORT_MONTH'].max()
    new_df = df[df['DATE_REPORT_MONTH'] == last_date].copy()
    new_df['DATE_REPORT_MONTH'] = new_df['DATE_REPORT_MONTH'] + pd.DateOffset(months=1)
    new_df['DATE_REPORT_QTR'] = new_df.apply(lambda row: calendar_lookup(row,'QUARTER'), axis=1)
    new_df['MONTH'] = new_df.apply(lambda row: calendar_lookup(row,'MONTH_NBR'), axis=1)
    new_df['WORKDAY'] = new_df.apply(lambda row: calendar_lookup(row,'WORKDAY'), axis=1)
    # new_df['LINEAR_MONTH'] = new_df.apply(lambda row: calendar_lookup(row,'LINEAR_MONTH'), axis=1) RLS 2026-05-11 commented out
    new_df['DURATION'] = new_df['DURATION'] - 1
    new_df[f"MARKET_ENCODED_{metric}_PRE"] = (new_df.groupby(['MARKET','DATE_REPORT_MONTH'])[f'TARGET_{metric}']
                                    .transform('mean'))
    new_df[f"CATEGORY_ENCODED_{metric}_PRE"] = (new_df.groupby(['SERVICE_CATEGORY','DATE_REPORT_MONTH'])[f'TARGET_{metric}']
                                    .transform('mean'))
    new_df[f"PRODUCT_ENCODED_{metric}_PRE"] = (new_df.groupby(['PRODUCT_LEVEL_3_TADM','DATE_REPORT_MONTH'])[f'TARGET_{metric}']
                                    .transform('mean'))
    null_cols = [f"MARKET_ENCODED_{metric}",f"CATEGORY_ENCODED_{metric}",f"PRODUCT_ENCODED_{metric}",
                 f'TARGET_{metric}',f'TARGET_{metric}_1',f'TARGET_{metric}_2',f'TARGET_{metric}_3',f'TARGET_{metric}_12',
                f'COUNT_ZEROS_{metric}',f'VARIANCE_12_MO_{metric}',f'SLOPE_12_{metric}'] # RLS 2026-05-11 commented out,f'TREND_12_QTR_{metric}']
    for col in null_cols:
        new_df[col] =np.nan

    fnf_col = f'FINAL_NORM_FACTOR_{metric}'
    if fnf_col in new_df.columns:
        new_df = new_df.drop(columns=[fnf_col])
    # Join metric-specific seasonality factor
    sf = (seasonality_factors[seasonality_factors['METRIC'] == metric][seasonality_merge_keys + ['FINAL_NORM_FACTOR']]
          .copy()
          .rename(columns={'FINAL_NORM_FACTOR': fnf_col}))
    new_df = new_df.merge(sf, on=seasonality_merge_keys, how='left')

    new_source = pd.concat([df,new_df])
    group = ['MARKET','PRODUCT_LEVEL_1_TADM','PRODUCT_LEVEL_2_TADM','PRODUCT_LEVEL_3_TADM','HCC',
             'SERVICE_CATEGORY','DATE_REPORT_MONTH']
    new_source = new_source.sort_values(by=group).reset_index(drop=True)
    return new_source

def new_features(df, metric, config=config):
    
    last_date = df['DATE_REPORT_MONTH'].max()
    group = ['MARKET','PRODUCT_LEVEL_1_TADM','PRODUCT_LEVEL_2_TADM','PRODUCT_LEVEL_3_TADM','HCC',
             'SERVICE_CATEGORY']
    df.loc[df['DATE_REPORT_MONTH'] == last_date,f'MARKET_ENCODED_{metric}'] = (df.groupby(group)[f'MARKET_ENCODED_{metric}_PRE']
                                                                                .transform(lambda x: x.shift(1).rolling(window=12,min_periods=3).mean()))
    df.loc[df['DATE_REPORT_MONTH'] == last_date,f'PRODUCT_ENCODED_{metric}'] = (df.groupby(group)[f'PRODUCT_ENCODED_{metric}_PRE']
                                                                                .transform(lambda x: x.shift(1).rolling(window=12,min_periods=3).mean()))
    df.loc[df['DATE_REPORT_MONTH'] == last_date,f'CATEGORY_ENCODED_{metric}'] = (df.groupby(group)[f'CATEGORY_ENCODED_{metric}_PRE']
                                                                                .transform(lambda x: x.shift(1).rolling(window=12,min_periods=3).mean()))
    df.loc[df['DATE_REPORT_MONTH'] == last_date,f'TARGET_{metric}_1'] = df.groupby(group)[f'TARGET_{metric}'].shift(1)
    df.loc[df['DATE_REPORT_MONTH'] == last_date,f'TARGET_{metric}_2'] = df.groupby(group)[f'TARGET_{metric}'].shift(2)
    df.loc[df['DATE_REPORT_MONTH'] == last_date,f'TARGET_{metric}_3'] = df.groupby(group)[f'TARGET_{metric}'].shift(3)
    df.loc[df['DATE_REPORT_MONTH'] == last_date,f'TARGET_{metric}_12'] = df.groupby(group)[f'TARGET_{metric}'].shift(12).fillna(df.groupby(group)[f'TARGET_{metric}'].transform('mean'))
    df.loc[df['DATE_REPORT_MONTH'] == last_date,f'COUNT_ZEROS_{metric}'] = (df.groupby(group)[f'TARGET_{metric}']
                                                    .transform(lambda x: (x.shift(1)==0).rolling(window=12,min_periods=3).sum()))
    df.loc[df['DATE_REPORT_MONTH'] == last_date,f'VARIANCE_12_MO_{metric}'] = (df.groupby(group)[f'TARGET_{metric}']
                                                    .transform(lambda x: x.shift(1).rolling(window=12,min_periods=3).var()))
    df.loc[df['DATE_REPORT_MONTH'] == last_date,f'SLOPE_12_{metric}'] = (df.groupby(group)[f'TARGET_{metric}']
                                            .transform(lambda x: x.shift(1).rolling(window=12,min_periods=2).apply(rolling_slope, raw=False)))
    
    df.loc[df['DATE_REPORT_MONTH'] == last_date,f'SLOPE_12_{metric}'] = df.groupby(group)[f'SLOPE_12_{metric}'].ffill()  
    # df.loc[(df['DATE_REPORT_MONTH'] == last_date)
    #        & (df.groupby(group)[f'TARGET_{metric}_1'].shift(12) != 0),f'TREND_12_QTR_{metric}'] = (df[f'TARGET_{metric}_1'] 
    #                                                                                     / df.groupby(group)[f'TARGET_{metric}_1'].shift(12) 
    #                                                                                     - 1) RLS 2026-05-11 commented out

    df = df[df['DATE_REPORT_MONTH'] == last_date]
    return df

def get_prediction_data(df, metric, config=config):
    # change datatype for categorical columns to category so LightGBM can process correctly
    for col in config['one_hot_columns']:
        df[col] = df[col].astype(('category'))

    #Get only X columns
    X = df[config['features'][metric]]
    
    return X

def loop_run_models(df, model, metric, config=config):
    X = get_prediction_data(df, metric)
    y_pred = model.predict(X, num_iteration=model.best_iteration)
    return pd.DataFrame({f"TARGET_{metric}": y_pred}, index=X.index)

     

appended_sources_all = {}  # {metric: {split_name: DataFrame}}
predict_dfs = {}           # {metric: DataFrame}
appended_source_all = {}   # {metric: DataFrame} - combined across splits

for metric in config['metrics']:
    print(f"\n{'='*60}")
    print(f"Running predictions for metric: {metric}")
    print(f"{'='*60}")

    appended_sources = {}
    predict_df = pd.DataFrame()

    for split_name, split_df in splits.items():
        if split_name in skipped_splits.get(metric, []):
            print(f"  Skipping {split_name} — no model trained.")
            continue

        print(f"  Running predictions for {split_name}...")

        # Initialize appended_source for the current split
        appended_source = split_df[split_df['DATE_REPORT_MONTH'] < config['projection_start']].copy()
        model = trained_models[metric][split_name]

        for i in range(config['projection_months']):
            # add a month to the dataset produces all dates
            new_source = new_month(df=appended_source, metric=metric, config=config)

            # calculate features for the new month and limit to only the new month for prediction
            calc_features = new_features(df=new_source, metric=metric, config=config)

            # Run the final predictions
            y_predicted = loop_run_models(calc_features, model, metric)
            calc_features = calc_features.drop(f"TARGET_{metric}", axis=1)
            predict_set = y_predicted.join(calc_features)

            # Append to the source to build up each month
            group = ['MARKET','PRODUCT_LEVEL_1_TADM','PRODUCT_LEVEL_2_TADM','PRODUCT_LEVEL_3_TADM','HCC',
             'SERVICE_CATEGORY','DATE_REPORT_MONTH']
            appended_source = pd.concat([appended_source, predict_set])
            appended_source = appended_source.sort_values(by=group).reset_index(drop=True)

            # Save just the prediction set for writing to table
            predict_df = pd.concat([predict_df, predict_set])
            predict_df = predict_df.sort_values(by=group).reset_index(drop=True)

        # Store the final appended_source for this split
        appended_sources[split_name] = appended_source

    # Store results for this metric
    appended_sources_all[metric] = appended_sources
    predict_dfs[metric] = predict_df
    appended_source_all[metric] = pd.concat(appended_sources.values(), ignore_index=True) if appended_sources else pd.DataFrame()

print(f"\nPredictions complete for all metrics: {config['metrics']}")

     

import shap

# Calculate SHAP values for each metric, using the correct model per split
shap_dfs = {}  # {metric: DataFrame}

for metric in config['metrics']:
    print(f"\nCalculating SHAP values for metric: {metric}")
    
    metric_shap_parts = []  # collect per-split SHAP DataFrames
    
    for split_name in splits.keys():
        if split_name in skipped_splits.get(metric, []):
            print(f"  Skipping SHAP for {split_name} — no model trained.")
            continue

        print(f"  Calculating SHAP for split: {split_name}")
        
        # Use the model trained on this specific split
        model = trained_models[metric][split_name]
        appended_source = appended_sources_all[metric][split_name]
        
        shap_df = appended_source[appended_source['DATE_REPORT_MONTH'] >= config['projection_start']].reset_index(drop=True)
        X = get_prediction_data(shap_df.copy(), metric)
        column_names = [f"{feature_col}_SHAP" for feature_col in X.columns]
        explainer = shap.TreeExplainer(model)
        
        # Ensure the categorical columns are correctly set as 'category'  
        for col in config['one_hot_columns']:  
            if col in shap_df.columns:  
                shap_df[col] = shap_df[col].astype('category')  

        shap_values = explainer.shap_values(X)  
        shap_values = pd.DataFrame(
                data=shap_values, columns=column_names
            )
        shap_values['EV_RAW'] = explainer.expected_value

        # Use TARGET from appended_source (already contains predictions from this split's model)
        shap_values_adjusted = shap_values.copy()
        shap_values_adjusted[f'TARGET_{metric}'] = shap_df[f'TARGET_{metric}'].values
        shap_values_adjusted['EXPECTED_VALUE'] = np.exp(shap_values_adjusted['EV_RAW'])
        shap_values_adjusted['TOTAL_FEATURE_IMPACT'] = shap_values_adjusted[column_names].sum(axis=1)
        for col in column_names:
           shap_values_adjusted[col] = (
                                        (shap_values_adjusted[col]/shap_values_adjusted['TOTAL_FEATURE_IMPACT'])
                                        *(shap_values_adjusted[f'TARGET_{metric}'] - shap_values_adjusted['EXPECTED_VALUE'])
                                       )
        shap_values_adjusted = shap_values_adjusted.drop(['TOTAL_FEATURE_IMPACT','EV_RAW',f'TARGET_{metric}'],axis=1)
        shap_df = shap_df.join(shap_values_adjusted)
        for col in config['one_hot_columns']:
            if col in shap_df.columns:
                shap_df[col] = shap_df[col].astype('object')
        
        # Drop columns if they exist
        drop_cols = ['MINDATE', 'TRAIN_START']
        shap_df = shap_df.drop(columns=[c for c in drop_cols if c in shap_df.columns])
        
        metric_shap_parts.append(shap_df)
    
    # Combine all splits for this metric
    shap_dfs[metric] = pd.concat(metric_shap_parts, ignore_index=True) if metric_shap_parts else pd.DataFrame()

print(f"\nSHAP calculations complete for all metrics: {config['metrics']}")

     

# Build forecast output for each metric
dfs = {}  # {metric: DataFrame}

for metric in config['metrics']:
    print(f"\nBuilding forecast output for metric: {metric}")
    appended_source = appended_source_all[metric]
    forecast_cols = ['MARKET','PRODUCT_LEVEL_1_TADM','PRODUCT_LEVEL_2_TADM','PRODUCT_LEVEL_3_TADM',
                'HCC','SERVICE_TYPE','SERVICE_CATEGORY','SEGMENT','DATE_REPORT_MONTH','MM',f"TARGET_{metric}",'N_TRAIN_MONTHS']
    forecast_df = appended_source[forecast_cols].copy()
    forecast_df[f"TARGET_{metric}"] = round(forecast_df[f"TARGET_{metric}"],4)
    df = forecast_df
    #df['UNIT_COST'] = PMPM / TARGET_UTIL * 12000

    df = df.rename(columns={
        f"TARGET_{metric}": f"TARGET_{metric}_PREDICTED"
        #,f"BF_ESTIMATE_{target_name}": f"TARGET_{metric}"
    })
    df_cols = ['MARKET','PRODUCT_LEVEL_1_TADM','PRODUCT_LEVEL_2_TADM','PRODUCT_LEVEL_3_TADM','HCC',
               'SERVICE_TYPE','SERVICE_CATEGORY','SEGMENT','DATE_REPORT_MONTH',f"TARGET_{metric}_PREDICTED",'N_TRAIN_MONTHS']

    df = df[df_cols]  
    dfs[metric] = df

print(f"\nForecast outputs built for all metrics: {config['metrics']}")
     

# --- Combine PMPM and UTIL into a single output table ---
key_cols = ['MARKET','PRODUCT_LEVEL_1_TADM','PRODUCT_LEVEL_2_TADM','PRODUCT_LEVEL_3_TADM',
            'HCC','SERVICE_TYPE','SERVICE_CATEGORY','SEGMENT','DATE_REPORT_MONTH']

# Start with PMPM df as the base (includes shared reference columns)
pmpm_base = dfs['PMPM'].copy()

# From UTIL df, bring in UTIL-specific prediction columns.
# Rename overlapping computed columns (derived differently by each model) with a _UTIL_MODEL suffix.
util_cols_to_add = key_cols + ['TARGET_UTIL_PREDICTED']
util_join = dfs['UTIL'][util_cols_to_add].copy()
df_combined = pmpm_base.merge(util_join, on=key_cols, how='left')
print(f"Combined table: {df_combined.shape[0]:,} rows x {df_combined.shape[1]} columns")
print(f"Columns: {df_combined.columns.tolist()}")
     

df_combined['VAL_DATE']         = config['val_date']
df_combined['TRAIN_END']        = config['train_end'].strftime('%Y-%m-%d')
df_combined['TRAIN_START_LEAD'] = config['train_start_lead']
df_combined['PROJECTION_START'] = config['projection_start'].strftime('%Y-%m-%d')
df_combined['PROJECTION_END']   = config['projection_end'].strftime('%Y-%m-%d')
df_combined['RUN_TIMESTAMP']    = config['run_timestamp'].strftime('%Y-%m-%d %H:%M:%S')
     

def get_column_types(df):  
    df_cols = df.columns.to_list()  
    df_types = []  
  
    for col in df.columns:  
        # Handle datetime columns  
        if pd.api.types.is_datetime64_any_dtype(df[col]):  
            df[col] = df[col].dt.strftime('%Y-%m-%d')  # Convert datetime to string format  
            df_types.append('DATE')  
  
        # Handle numeric columns  
        elif pd.api.types.is_numeric_dtype(df[col]):  
            df_types.append('FLOAT')  
  
        # Handle categorical columns  
        elif pd.api.types.is_categorical_dtype(df[col]):  
            df[col] = df[col].astype(str)  # Convert categorical to string  
            df_types.append('VARCHAR')  
  
        # Handle object (string) columns  
        elif pd.api.types.is_string_dtype(df[col]):  
            df_types.append('VARCHAR')  
  
        # Default handling for unsupported types  
        else:  
            df[col] = df[col].astype(str)  # Convert unknown types to string  
            df_types.append('VARCHAR')  
  
    return df, df_cols, df_types  

def create_snowflake_table(tblnm, db, schema, cols, types, session=None):
    table_name = f"{db}.{schema}.{tblnm}"
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS {db}.{schema}")
    print(f"Target Databricks table: {table_name}")
    print("Table will be created or replaced during write.")

def load_to_snowflake(df,session,tblnm, db, schema):
    table_name = f"{db}.{schema}.{tblnm}"
    write_df = df.copy()

    for col in write_df.columns:
        if pd.api.types.is_datetime64_any_dtype(write_df[col]):
            write_df[col] = write_df[col].dt.date
        elif pd.api.types.is_categorical_dtype(write_df[col]):
            write_df[col] = write_df[col].astype(str)

    spark_df = spark.createDataFrame(write_df)
    (spark_df.write
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable(table_name))
    print(f"Data loaded to Databricks table successfully: {table_name}")


     

# Write the single combined output table (PMPM + UTIL predictions as columns)
# Append to existing table; replace rows for this (train_end, HCC) combo if already exists
from delta.tables import DeltaTable

table_name = f"{config['DB']}.{config['schema']}.{config['output_table_name']}"
print(f"Writing combined prediction table: {table_name}")

final_table = df_combined.copy()
for col in final_table.columns:
    if pd.api.types.is_datetime64_any_dtype(final_table[col]):
        final_table[col] = final_table[col].dt.strftime('%Y-%m-%d')
    elif pd.api.types.is_categorical_dtype(final_table[col]):
        final_table[col] = final_table[col].astype(str)

spark_df = spark.createDataFrame(final_table)

train_end_str = config['train_end'].strftime('%Y-%m-%d')
hcc_str       = config['HCC']
val_date_str  = config['val_date']

if spark.catalog.tableExists(table_name):
    existing_cols_upper = {f.name.upper() for f in spark.table(table_name).schema.fields}
    if 'VAL_DATE' in existing_cols_upper:
        delta_table = DeltaTable.forName(spark, table_name)
        delta_table.delete(f"val_date = '{val_date_str}' AND train_end = '{train_end_str}' AND HCC = '{hcc_str}'")
        spark_df.write.mode("append").option("mergeSchema", "true").saveAsTable(table_name)
        print(f"Replaced rows for val_date={val_date_str}, train_end={train_end_str}, HCC={hcc_str} in {table_name}")
    elif 'TRAIN_END' in existing_cols_upper:
        delta_table = DeltaTable.forName(spark, table_name)
        delta_table.delete(f"train_end = '{train_end_str}' AND HCC = '{hcc_str}'")
        spark_df.write.mode("append").option("mergeSchema", "true").saveAsTable(table_name)
        print(f"Replaced rows for train_end={train_end_str}, HCC={hcc_str} in {table_name} (legacy — no val_date col yet)")
    else:
        spark_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(table_name)
        print(f"Schema migration: overwrote {table_name}")
else:
    spark_df.write.saveAsTable(table_name)
    print(f"Created new table: {table_name}")

     

# Combine SHAP tables for all metrics into a single output table with a METRIC column
from delta.tables import DeltaTable

shap_combined_parts = []
for metric in config['metrics']:
    part = shap_dfs[metric].copy()
    part['METRIC'] = metric
    shap_combined_parts.append(part)

shap_combined = pd.concat(shap_combined_parts, ignore_index=True)

# Add run metadata (uppercase — matches CS-ML convention and all other columns)
shap_combined['VAL_DATE']         = config['val_date']
shap_combined['TRAIN_END']        = config['train_end'].strftime('%Y-%m-%d')
shap_combined['TRAIN_START_LEAD'] = config['train_start_lead']
shap_combined['PROJECTION_START'] = config['projection_start'].strftime('%Y-%m-%d')
shap_combined['PROJECTION_END']   = config['projection_end'].strftime('%Y-%m-%d')
shap_combined['RUN_TIMESTAMP']    = config['run_timestamp'].strftime('%Y-%m-%d %H:%M:%S')

# Prepare for write
shap_final = shap_combined.copy()
for col in shap_final.columns:
    if pd.api.types.is_datetime64_any_dtype(shap_final[col]):
        shap_final[col] = shap_final[col].dt.strftime('%Y-%m-%d')
    elif isinstance(shap_final[col].dtype, pd.CategoricalDtype):
        shap_final[col] = shap_final[col].astype(str)

shap_table_name = f"{config['DB']}.{config['schema']}.{config['shap_table_name']}"
print(f"Writing combined SHAP table: {shap_table_name}")
print(f"Shape: {shap_final.shape[0]:,} rows x {shap_final.shape[1]} columns")

spark_shap_df = spark.createDataFrame(shap_final)

train_end_str = config['train_end'].strftime('%Y-%m-%d')
hcc_str       = config['HCC']
val_date_str  = config['val_date']

# Append to existing table; replace rows for this (val_date, train_end, HCC) combo if already exists
if spark.catalog.tableExists(shap_table_name):
    existing_fields = {f.name: f.dataType for f in spark.table(shap_table_name).schema.fields}
    existing_fields_upper = {k.upper() for k in existing_fields}
    if 'VAL_DATE' in existing_fields_upper:
        for field in spark_shap_df.schema.fields:
            if field.name in existing_fields and field.dataType != existing_fields[field.name]:
                spark_shap_df = spark_shap_df.withColumn(field.name, spark_shap_df[field.name].cast(existing_fields[field.name]))
        delta_table = DeltaTable.forName(spark, shap_table_name)
        delta_table.delete(f"val_date = '{val_date_str}' AND train_end = '{train_end_str}' AND HCC = '{hcc_str}'")
        spark_shap_df.write.mode("append").option("mergeSchema", "true").saveAsTable(shap_table_name)
        print(f"Replaced rows for val_date={val_date_str}, train_end={train_end_str}, HCC={hcc_str} in {shap_table_name}")
    elif 'TRAIN_END' in existing_fields_upper:
        for field in spark_shap_df.schema.fields:
            if field.name in existing_fields and field.dataType != existing_fields[field.name]:
                spark_shap_df = spark_shap_df.withColumn(field.name, spark_shap_df[field.name].cast(existing_fields[field.name]))
        delta_table = DeltaTable.forName(spark, shap_table_name)
        delta_table.delete(f"train_end = '{train_end_str}' AND HCC = '{hcc_str}'")
        spark_shap_df.write.mode("append").option("mergeSchema", "true").saveAsTable(shap_table_name)
        print(f"Replaced rows for train_end={train_end_str}, HCC={hcc_str} in {shap_table_name} (legacy — no val_date col yet)")
    else:
        spark_shap_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(shap_table_name)
        print(f"Schema migration: overwrote {shap_table_name}")
else:
    spark_shap_df.write.saveAsTable(shap_table_name)
    print(f"Created new table: {shap_table_name}")
