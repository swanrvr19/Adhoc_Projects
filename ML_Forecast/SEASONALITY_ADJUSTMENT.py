# Import python packages
import calendar
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px  
from scipy.stats import linregress
from scipy.stats import friedmanchisquare
from sklearn.cluster import KMeans  
from sklearn.metrics import silhouette_score 

# Ignore Warnings
import warnings
warnings.filterwarnings("ignore")

     

# Prefer val_date from upstream task value; fall back to MAX from table for interactive use
try:
    val_date = dbutils.jobs.taskValues.get(taskKey="ohc_completed_combined", key="val_date")
    print(f"VAL_DATE from task value: {val_date}")
except AttributeError:
    val_date = (
        spark.sql("SELECT MAX(CAST(VAL_DATE AS STRING)) FROM ra_analytic_dev.ohc_forecast.ohc_completed_combined")
        .collect()[0][0]
    )
    print(f"VAL_DATE from table MAX: {val_date}")

     
Extract data

# Query main data from ohc_completed_combined with 24-month completeness filter
data = spark.sql(f"""
    WITH included AS (
        SELECT
            HCC,
            MARKET,
            PRODUCT_LEVEL_3_TADM,
            COUNT(DISTINCT DATE_REPORT_MONTH) AS counts
        FROM ra_analytic_dev.ohc_forecast.ohc_completed_combined
        WHERE VAL_DATE = '{val_date}'
            AND DATE_REPORT_MONTH BETWEEN '2024-04-01' AND '2026-03-01'
        GROUP BY HCC, MARKET, PRODUCT_LEVEL_3_TADM
        HAVING COUNT(DISTINCT DATE_REPORT_MONTH) = 24
    )
    SELECT 
        a.HCC,
        a.MARKET,
        a.PRODUCT_LEVEL_1_TADM,
        a.PRODUCT_LEVEL_2_TADM,
        a.PRODUCT_LEVEL_3_TADM,
        a.SERVICE_TYPE,
        a.SERVICE_CATEGORY,
        a.SEGMENT,
        a.DATE_REPORT_MONTH,
        CASE WHEN a.IS_DUAL = 1 THEN 'Dual' ELSE 'Non-Dual' END AS DUAL_IND,
        CASE WHEN a.DATE_REPORT_MONTH <= '2025-03-01' THEN 'Y1' ELSE 'Y2' END AS MEASURE_YEAR,
        SUM(a.MM) AS MM,
        SUM(a.UTIL_K * a.MM / 1000) AS UTIL_COMPLETE,
        SUM(a.PD) AS PAID_COMPLETE
    FROM ra_analytic_dev.ohc_forecast.ohc_completed_combined AS a
    JOIN included AS b
        ON a.HCC = b.HCC
        AND a.MARKET = b.MARKET
        AND a.PRODUCT_LEVEL_3_TADM = b.PRODUCT_LEVEL_3_TADM
    WHERE a.VAL_DATE = '{val_date}'
        AND a.DATE_REPORT_MONTH BETWEEN '2024-04-01' AND '2026-03-01'
    GROUP BY a.HCC, a.MARKET, a.PRODUCT_LEVEL_1_TADM, a.PRODUCT_LEVEL_2_TADM,
             a.PRODUCT_LEVEL_3_TADM, a.SERVICE_TYPE, a.SERVICE_CATEGORY,
             a.SEGMENT, a.DATE_REPORT_MONTH, a.IS_DUAL
""")
print(f"Rows: {data.count():,}")

     

# Query all distinct dimensional splits (used to scaffold final factor table)
data_all = spark.sql(f"""
    SELECT DISTINCT
        a.HCC,
        a.MARKET,
        a.PRODUCT_LEVEL_1_TADM,
        a.PRODUCT_LEVEL_2_TADM,
        a.PRODUCT_LEVEL_3_TADM,
        a.SERVICE_TYPE,
        a.SERVICE_CATEGORY,
        a.SEGMENT,
        a.DATE_REPORT_MONTH,
        CASE WHEN a.IS_DUAL = 1 THEN 'Dual' ELSE 'Non-Dual' END AS DUAL_IND
    FROM ra_analytic_dev.ohc_forecast.ohc_completed_combined AS a
    WHERE a.VAL_DATE = '{val_date}'
""")
print(f"Rows: {data_all.count():,}")

     

def get_month_name(month_num):  
    if 1 <= month_num <= 12:  
        return calendar.month_name[month_num]  
    return 'Invalid Month'

def calc_factor(df1, group_list):
    df1 = df1.groupby(group_list + ['MONTH'])[['MM','UTIL_COMPLETE','PAID_COMPLETE']].sum().reset_index()
    df1['MM_YEAR'] = df1.groupby(group_list)['MM'].transform("sum")
    df1['UTIL_YEAR'] = df1.groupby(group_list)['UTIL_COMPLETE'].transform("sum")
    df1['PAID_YEAR'] = df1.groupby(group_list)['PAID_COMPLETE'].transform("sum")
    df1['UTIL_MEM'] = df1['UTIL_COMPLETE'] / df1['MM']
    df1['PMPM'] = df1['PAID_COMPLETE'] / df1['MM']
    df1['UTIL_MEM_YEAR'] = df1['UTIL_YEAR'] / df1['MM_YEAR']
    df1['PMPM_YEAR'] = df1['PAID_YEAR'] / df1['MM_YEAR']
    df1['NORM_FACTOR_UTIL'] = round(df1['UTIL_MEM'] / df1['UTIL_MEM_YEAR'],4)
    df1['NORM_FACTOR_PMPM'] = round(df1['PMPM'] / df1['PMPM_YEAR'],4)

    return df1

all_group_list = ['SEGMENT','MARKET','PRODUCT_LEVEL_1_TADM','PRODUCT_LEVEL_2_TADM','PRODUCT_LEVEL_3_TADM','DUAL_IND','HCC','SERVICE_TYPE','SERVICE_CATEGORY']
agg_group_list = ['SEGMENT','PRODUCT_LEVEL_1_TADM','DUAL_IND','HCC','SERVICE_CATEGORY','MEASURE_YEAR'] 

df = data.toPandas()
df['DATE_REPORT_MONTH'] = pd.to_datetime(df['DATE_REPORT_MONTH'])
df['MONTH'] = df['DATE_REPORT_MONTH'].dt.month.apply(get_month_name)
# DUAL_IND already computed in SQL
df = df[df['HCC'].isin(['PHYSICIAN'])]  # PHYSICIAN has 406 groups; PHARMACY only has 6

df_all = calc_factor(df, all_group_list + ['MEASURE_YEAR'])
df_agg = calc_factor(df, agg_group_list)

# add average of two years
# avg_group = [i for i in agg_group_list if i != 'MEASURE_YEAR'] + ['MONTH']
# df_avg = df_agg.groupby(avg_group).mean(['NORM_FACTOR_UTIL','NORM_FACTOR_PMPM']).reset_index()
# df_avg['MEASURE_YEAR'] = 'AVG'
# df_agg = pd.concat([df_agg,df_avg]).sort_values(by=avg_group).reset_index(drop=True)

     

loop_list = [i for i in agg_group_list if i != 'MEASURE_YEAR']
grouped_agg = df_agg.groupby(loop_list)

results = []
for group_name, group_data in grouped_agg:
    monthly_data = [group_data[group_data['MONTH'] == month]['PMPM'].values for month in group_data['MONTH'].unique()]

    if len(monthly_data) >= 3:  
        stat, p = friedmanchisquare(*monthly_data)  
        results.append({'group': group_name, 'test_statistic': stat, 'p_value': p})
        
results_df = pd.DataFrame(results)
results_df[loop_list] = pd.DataFrame(results_df['group'].tolist(), index=results_df.index)  
results_df.drop(columns=['group'], inplace=True) 
results_df.display()
     



# Compute average normalization factors across both years
avg_group = [i for i in agg_group_list if i != 'MEASURE_YEAR'] + ['MONTH']
pivot_df = df_agg.groupby(avg_group)[['NORM_FACTOR_UTIL','NORM_FACTOR_PMPM']].mean().reset_index()
pivot_df['MEASURE_YEAR'] = 'AVG'

pivot_df = pivot_df.pivot_table(index=agg_group_list,
                              columns= 'MONTH',
                              values='NORM_FACTOR_UTIL')
pivot_df = pivot_df.fillna(1.0)

pivot_df_reindex = pivot_df.reset_index(drop=True)


def check_cluster_size(kmeans,min_cluster_size):
    # Check cluster sizes  
    cluster_sizes = np.bincount(kmeans.labels_) 
    # Identify valid clusters (clusters meeting the minimum size requirement)  
    valid_clusters = {cluster_idx for cluster_idx, size in enumerate(cluster_sizes) if size >= min_cluster_size} 
    
    if not valid_clusters:
        return kmeans, kmeans.inertia_

    # Reassign small clusters (example heuristic)  
    for cluster_idx, size in enumerate(cluster_sizes):  
        if size < min_cluster_size:  
            # Find samples in the small cluster  
            small_cluster_samples = np.where(kmeans.labels_ == cluster_idx)[0]  
            for sample_idx in small_cluster_samples:  
                # Reassign sample to the closest cluster center (excluding the current cluster)  
                distances = np.linalg.norm(  
                                    np.array(kmeans.cluster_centers_)[list(valid_clusters)] -   
                                    np.array(pivot_df_reindex.loc[sample_idx]), axis=1  
                                )
                closest_valid_cluster = list(valid_clusters)[np.argmin(distances)]  
                kmeans.labels_[sample_idx] = closest_valid_cluster
                
    # Recalculate inertia  
    new_inertia = 0.0  
    for i, label in enumerate(kmeans.labels_):  
        # Add squared distance of each sample to its assigned cluster center  
        new_inertia += np.linalg.norm(pivot_df_reindex.loc[i] - kmeans.cluster_centers_[label]) ** 2 
        
    return kmeans, new_inertia

wcss = []  # Within-cluster sum of squares 
silhouette_scores = [] 
k_values = range(2, 21)  
labeled_data = pd.DataFrame()

# cluster and collect 
for k in k_values:
    if k >= len(pivot_df):
        continue
    cluster_data = pivot_df.copy()
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)  # Initialize KMeans  
    kmeans.fit_predict(pivot_df)  # Get cluster labels
    kmeans, inertia = check_cluster_size(kmeans,3)
    n_unique_labels = len(np.unique(kmeans.labels_))
    if n_unique_labels <= 1 or n_unique_labels >= len(pivot_df):
        continue
    wcss.append(inertia)  # Append WCSS (inertia) for each k  
    silhouette_avg = silhouette_score(pivot_df, kmeans.labels_)  # Compute Silhouette Score  
    silhouette_scores.append(silhouette_avg)
    cluster_data['num_clusters'] = k
    cluster_data['cluster_label'] = kmeans.labels_
    labeled_data = pd.concat([labeled_data,cluster_data])
labeled_data
     

# Plot the Elbow Method  
num_clusters = labeled_data['num_clusters'].unique().tolist()
plt.figure(figsize=(8, 5))  
plt.plot(num_clusters, wcss, marker='o', linestyle='--')  
plt.title("Elbow Method: Optimal Number of Clusters")  
plt.xlabel("Number of Clusters (k)")  
plt.ylabel("WCSS (Inertia)")  
plt.xticks(num_clusters)  
plt.grid()  
plt.show() 
     

# Plot the Silhouette Scores  
plt.figure(figsize=(8, 5))  
plt.plot(num_clusters, silhouette_scores, marker='o', linestyle='--', color='green')  
plt.title("Silhouette Score: Optimal Number of Clusters")  
plt.xlabel("Number of Clusters (k)")  
plt.ylabel("Silhouette Score")  
plt.xticks(num_clusters)  
plt.grid()  
plt.show()  
     

chart_df = labeled_data.copy().reset_index()
chart_df = chart_df[chart_df['MEASURE_YEAR'] == 'AVG']

# Select number of clusters to visualize (adjust as needed)
available_k = sorted(chart_df['num_clusters'].unique())
cluster_numbers = available_k[-1] if available_k else 2  # Use max available k
print(f"Available k values: {available_k}, using k={cluster_numbers}")
chart_df = chart_df[(chart_df['num_clusters'] == cluster_numbers)]

count_df = chart_df.groupby(['num_clusters','cluster_label'])['MEASURE_YEAR'].count()
# Set cluster = 'All' to see all clusters, or an int to filter
cluster = 'All'

if cluster != 'All':
    chart_df = chart_df[(chart_df['cluster_label'] == cluster)]

chart_melt = chart_df.melt(id_vars=agg_group_list + ['num_clusters','cluster_label'],
                          var_name='MONTH',
                          value_name='NORM_FACTOR')
chart_melt['cluster_label'] = chart_melt['cluster_label'].astype(int)
month_order = ['January', 'February', 'March', 'April', 'May', 'June',   
               'July', 'August', 'September', 'October', 'November', 'December']
chart_melt['MONTH'] = pd.Categorical(chart_melt['MONTH'], categories=month_order, ordered=True) 
# Ensure cluster_label is ordered numerically  
cluster_order = sorted(chart_melt['cluster_label'].unique(), key=int)  # Sort clusters numerically  
chart_melt['cluster_label'] = pd.Categorical(chart_melt['cluster_label'], categories=cluster_order, ordered=True)  

# Create the interactive violin plot  
fig = px.violin(  
    chart_melt,  
    x="MONTH",                # Grouped by month on the x-axis  
    y="NORM_FACTOR",     # Value on the y-axis  
    color="cluster_label",    # Separate violins by cluster  
    # box=True,                 # Add a mini boxplot inside the violin for more detail  
    # points="all",             # Show all individual data points  
    # hover_data=["additional_info"],  # Add tooltips with additional data  
    title="Interactive Violin Plot by Month and Cluster",  
    color_discrete_sequence=px.colors.qualitative.Set2,  # Custom color palette  
    category_orders={"MONTH": month_order,  
                    "cluster_label": cluster_order}
)  
  
# Customize the layout  
fig.update_layout(  
    xaxis_title="Month",  
    yaxis_title="NORM_FACTOR",  
    legend_title="Cluster",  
    template="plotly_white"  
) 

display(count_df)
fig.show()
     

def calculate_slope_and_rvalue(group):  
    slope, intercept, r_value, p_value, std_err = linregress(group['MONTH_NUM'], group['NORM_PMPM'])  
    group['NORM_SLOPE'] = slope  # Add slope to each row in the group  
    group['NORM_R_VALUE'] = r_value**2  # Add r_value to each row in the group  
    return group 

def calculate_slope_and_rvalue_final(group):
    try:
        slope, intercept, r_value, p_value, std_err = linregress(group['MONTH_NUM'], group['FINAL_NORM_PMPM'])  
        group['FINAL_NORM_SLOPE'] = slope  # Add slope to each row in the group  
        group['FINAL_NORM_R_VALUE'] = r_value**2  # Add r_value to each row in the group  
    except:
        group['FINAL_NORM_SLOPE'] = None  
        group['FINAL_NORM_R_VALUE'] = None
    
    return group 


test_df = df_agg[agg_group_list + ['MONTH','PMPM']]
month_order = ['January', 'February', 'March', 'April', 'May', 'June',   
               'July', 'August', 'September', 'October', 'November', 'December']
test_df['MONTH'] = pd.Categorical(test_df['MONTH'], categories=month_order, ordered=True) 
test_df.sort_values(by=agg_group_list + ['MONTH'],inplace=True)

# df_agg['MONTH'] = pd.Categorical(df_agg['MONTH'], categories=month_order, ordered=True) 
# pivot_df
final_clusters_df = labeled_data[labeled_data['num_clusters'] == 7].reset_index()

# final_clusters_df = final_clusters_df[agg_group_list + month_order + ['num_clusters','cluster_label']]
# for month in month_order:
#     final_clusters_df[month] = final_clusters_df.groupby('cluster_label')[month].transform('median')
final_clusters_df.drop(columns=['MEASURE_YEAR'],inplace=True)
avg_group_list = [i for i in agg_group_list if i != 'MEASURE_YEAR']
final_clusters_df = final_clusters_df.melt(id_vars=avg_group_list + ['num_clusters','cluster_label'],
                          var_name='MONTH',
                          value_name='NORM_FACTOR_PMPM')
final_clusters_df['FINAL_NORM_FACTOR_PMPM'] = final_clusters_df.groupby(['MONTH','cluster_label'])['NORM_FACTOR_PMPM'].transform('median')
final_clusters_df['MONTH'] = pd.Categorical(final_clusters_df['MONTH'], categories=month_order, ordered=True) 
final_clusters_df.sort_values(by=avg_group_list + ['MONTH'],inplace=True)

join_list = [i for i in agg_group_list if i != 'MEASURE_YEAR'] + ['MONTH']
new_test_df = test_df.merge(final_clusters_df,on=join_list,how='inner').reset_index(drop=True)
new_test_df['NORM_PMPM'] = new_test_df['PMPM'] / new_test_df['NORM_FACTOR_PMPM']
new_test_df['FINAL_NORM_PMPM'] = new_test_df['PMPM'] / new_test_df['FINAL_NORM_FACTOR_PMPM']
new_test_df['MONTH_NUM'] = pd.to_datetime(new_test_df['MONTH'], format='%B').dt.month
new_test_df = new_test_df.groupby(agg_group_list, group_keys=False).apply(calculate_slope_and_rvalue)
new_test_df = new_test_df.groupby(agg_group_list, group_keys=False).apply(calculate_slope_and_rvalue_final)
new_test_df
# final_clusters_df['cluster_label'] = final_clusters_df['cluster_label'].astype(int)
# final_clusters_df
# final_clusters_df = final_clusters_df[avg_group+['FINAL_NORM_FACTOR_PMPM']]

# df_final = df_all.merge(final_clusters_df,on=avg_group,how='left')
# df_final['FINAL_NORM_FACTOR_PMPM'] = df_final['FINAL_NORM_FACTOR_PMPM'].fillna(1)
# final_cols = ['MARKET','PRODUCT_LEVEL_1_TADM','PRODUCT_LEVEL_3_TADM','HCC','SERVICE_CATEGORY','MONTH','FINAL_NORM_FACTOR_PMPM']
# df_final = df_final[final_cols]
# df_final['MONTH'] = pd.to_datetime(df_final['MONTH'], format='%B').dt.month
     

def get_month_name(month_num):  
    if 1 <= month_num <= 12:  
        return calendar.month_name[month_num]  
    return 'Invalid Month'

def calc_factor(df1,group_list,hcc):
    df1 = df1.groupby(group_list + ['MONTH'])[['MM','UTIL_COMPLETE','PAID_COMPLETE']].sum().reset_index()
    df1['MM_YEAR'] = df1.groupby(group_list)['MM'].transform("sum")
    df1['UTIL_YEAR'] = df1.groupby(group_list)['UTIL_COMPLETE'].transform("sum")
    df1['PAID_YEAR'] = df1.groupby(group_list)['PAID_COMPLETE'].transform("sum")
    df1['UTIL_MEM'] = df1['UTIL_COMPLETE'] / df1['MM']
    df1['PMPM'] = df1['PAID_COMPLETE'] / df1['MM']
    df1['UTIL_MEM_YEAR'] = df1['UTIL_YEAR'] / df1['MM_YEAR']
    df1['PMPM_YEAR'] = df1['PAID_YEAR'] / df1['MM_YEAR']
    df1['NORM_FACTOR_UTIL'] = round(df1['UTIL_MEM'] / df1['UTIL_MEM_YEAR'],4)
    df1['NORM_FACTOR_PMPM'] = round(df1['PMPM'] / df1['PMPM_YEAR'],4)
    df1 = df1[group_list+['MONTH','NORM_FACTOR_UTIL','NORM_FACTOR_PMPM']]
    return df1
    
def check_cluster_size(kmeans,min_cluster_size,pivot_df):
    pivot_df_reindex = pivot_df.reset_index(drop=True)
    # Check cluster sizes  
    cluster_sizes = np.bincount(kmeans.labels_) 
    # Identify valid clusters (clusters meeting the minimum size requirement)  
    valid_clusters = {cluster_idx for cluster_idx, size in enumerate(cluster_sizes) if size >= min_cluster_size} 
    
    if not valid_clusters:
        return kmeans

    # Reassign small clusters (example heuristic)  
    for cluster_idx, size in enumerate(cluster_sizes):  
        if size < min_cluster_size:  
            # Find samples in the small cluster  
            small_cluster_samples = np.where(kmeans.labels_ == cluster_idx)[0]  
            for sample_idx in small_cluster_samples:  
                # Reassign sample to the closest cluster center (excluding the current cluster)  
                distances = np.linalg.norm(  
                                    np.array(kmeans.cluster_centers_)[list(valid_clusters)] -   
                                    np.array(pivot_df_reindex.loc[sample_idx]), axis=1  
                                )
                closest_valid_cluster = list(valid_clusters)[np.argmin(distances)]  
                kmeans.labels_[sample_idx] = closest_valid_cluster
                
    return kmeans

def run_cluster(df,k,agg_group_list,metric):
    #shape data for kmeans clustering
    norm_factor_metric = f"NORM_FACTOR_{metric}"
    pivot_group = [i for i in agg_group_list if i != 'MEASURE_YEAR']
    month_order = ['January', 'February', 'March', 'April', 'May', 'June',   
               'July', 'August', 'September', 'October', 'November', 'December'] 
    df['MONTH'] = pd.Categorical(df['MONTH'], categories=month_order, ordered=True)
    pivot_df = df.sort_values(by=pivot_group+['MONTH'])
    pivot_df = pivot_df.pivot_table(index=pivot_group,
                                  columns= 'MONTH',
                                  values=norm_factor_metric)
    # Fill NaN with 1.0 (no seasonality effect) for groups missing some months
    pivot_df = pivot_df.fillna(1.0)
    
    # Separate groups with no real variation (all 1.0) — don't cluster those
    has_variation = ~(pivot_df == 1.0).all(axis=1)
    flat_df = pivot_df[~has_variation].copy()  # will get default cluster
    pivot_df = pivot_df[has_variation]
    
    if len(pivot_df) == 0:
        # All groups are flat — return single cluster
        flat_df['cluster_label'] = flat_df.index.get_level_values('HCC') + "_0"
        flat_df = flat_df.reset_index()
        return flat_df
    
    # Cap k at available samples
    effective_k = min(k, len(pivot_df) - 1) if len(pivot_df) > 1 else 1
    if effective_k < k:
        print(f"  Warning: {metric} - reduced k from {k} to {effective_k} (only {len(pivot_df)} groups available)")
    if effective_k < 2:
        # Can't cluster with fewer than 2 groups - return single cluster
        pivot_df['cluster_label'] = pivot_df.index.get_level_values('HCC') + "_0"
        pivot_df = pivot_df.reset_index()
        return pivot_df

    # run clustering
    kmeans = KMeans(n_clusters=effective_k, random_state=42, n_init=10)  # Initialize KMeans  
    pivot_df['cluster_label'] = kmeans.fit_predict(pivot_df)
    pivot_df = pivot_df.reset_index()
    pivot_df['cluster_label'] = pivot_df['HCC'] + "_" + pivot_df['cluster_label'].astype(str)
    
    # Add back the flat groups as their own cluster
    if len(flat_df) > 0:
        flat_df['cluster_label'] = flat_df.index.get_level_values('HCC') + "_flat"
        flat_df = flat_df.reset_index()
        pivot_df = pd.concat([pivot_df, flat_df], ignore_index=True)
    
    return pivot_df

def get_final_data(cluster_df,full_df,agg_group_list,all_group_list,metric):
    # Calc the median of Norm Factors over each cluster and shape data for final form
    final_norm_factor_metric = f"FINAL_NORM_FACTOR"
    melt_group = [i for i in agg_group_list if i != 'MEASURE_YEAR']
    median_col_list = [col for col in cluster_df.columns if col not in melt_group  + ['cluster_label']]
    for month in median_col_list:
        cluster_df[month] = cluster_df.groupby('cluster_label')[month].transform('median')
    cluster_df = cluster_df.melt(id_vars=melt_group  + ['cluster_label'],
                              var_name='MONTH',
                              value_name=final_norm_factor_metric)
    
    # get all splits from main data and merge seasonality factors
    full_df = full_df[all_group_list + ['MONTH']].drop_duplicates()
    df_final = full_df.merge(cluster_df,on=melt_group + ['MONTH'],how='left').reset_index(drop=True)
    df_final[final_norm_factor_metric] = df_final[final_norm_factor_metric].fillna(1)
    df_final[final_norm_factor_metric] = df_final[final_norm_factor_metric].clip(lower=0.5, upper=2.0)
    df_final['cluster_label'] = df_final['cluster_label'].fillna(df_final['HCC'] + '_unmatched')
    df_final['MONTH'] = pd.to_datetime(df_final['MONTH'], format='%B').dt.month
    df_final['METRIC'] = metric
    
    return df_final

def final_data_no_factors(full_df,all_group_list,hcc,metric):
    # Fill factors with 1 as a placeholder
    final_norm_factor_metric = f"FINAL_NORM_FACTOR"
    full_df = full_df[all_group_list + ['MONTH']].drop_duplicates()
    full_df['MONTH'] = pd.to_datetime(full_df['MONTH'], format='%B').dt.month
    full_df['cluster_label'] = f"{hcc}_0" 
    full_df[final_norm_factor_metric] = 1
    full_df['METRIC'] = metric
    
    return full_df
     

avg_group = [i for i in agg_group_list if i != 'MEASURE_YEAR'] + ['MONTH']

df = data.toPandas()
df['DATE_REPORT_MONTH'] = pd.to_datetime(df['DATE_REPORT_MONTH'])
df['MONTH'] = df['DATE_REPORT_MONTH'].dt.month.apply(get_month_name)
# DUAL_IND already computed in SQL

df_all = data_all.toPandas()
df_all['DATE_REPORT_MONTH'] = pd.to_datetime(df_all['DATE_REPORT_MONTH'])
df_all['MONTH'] = df_all['DATE_REPORT_MONTH'].dt.month.apply(get_month_name) 
df_all.drop(columns=['DATE_REPORT_MONTH'],inplace=True)
df_all.drop_duplicates(inplace=True)
# DUAL_IND already computed in SQL

# k values selected via silhouette + elbow analysis on the full agg_group_list
hcc_list_pmpm = [['PHYSICIAN',0], ['OUTPATIENT',0], ['INPATIENT',0], ['PHARMACY',0]]
hcc_list_util = [['PHYSICIAN',0], ['OUTPATIENT',0], ['INPATIENT',0], ['PHARMACY',0]]
hcc_list_all = [['UTIL',hcc_list_util],['PMPM',hcc_list_pmpm]]

final_df = pd.DataFrame()
for metric, hcc_list in hcc_list_all:
    for hcc,k in hcc_list:
        df_hcc = df[df['HCC'] == hcc]  # Limit data to the HCC
        df_hcc_all = df_all[df_all['HCC'] == hcc]  # Limit data to the HCC
        if k == 0:
            final_hcc_df = final_data_no_factors(df_hcc_all,all_group_list,hcc,metric) # Create placeholder factors = 1
        else:
            df_agg = calc_factor(df_hcc,agg_group_list,hcc)  # Calculate the normalization factors
            df_avg = df_agg.groupby(avg_group)[['NORM_FACTOR_UTIL','NORM_FACTOR_PMPM']].mean().reset_index()  # average of two years
            cluster_df = run_cluster(df_avg,k,agg_group_list,metric)  # run clusters
            final_hcc_df = get_final_data(cluster_df,df_hcc_all,agg_group_list,all_group_list,metric) # prepare uploadable table
        final_df = pd.concat([final_df,final_hcc_df])  # append to master dataframe
    
final_df.display()

     

# Plot seasonality factors by month, grouped by cluster, faceted by HCC
cols = final_df.columns.tolist()
metric_col = 'METRIC' if 'METRIC' in cols else 'metric'
cluster_col = 'CLUSTER_LABEL' if 'CLUSTER_LABEL' in cols else 'cluster_label'
month_col = 'MONTH' if 'MONTH' in cols else 'month'
factor_col = 'FINAL_NORM_FACTOR' if 'FINAL_NORM_FACTOR' in cols else 'final_norm_factor'
hcc_col = 'HCC' if 'HCC' in cols else 'hcc'

# Diagnostic: show cluster counts per HCC per metric
plot_df = final_df[~final_df[cluster_col].str.contains('unmatched')].copy()
print("Distinct clusters per HCC per metric (excluding unmatched):")
for metric in sorted(plot_df[metric_col].unique()):
    mdf = plot_df[plot_df[metric_col] == metric]
    for hcc in sorted(mdf[hcc_col].unique()):
        labels = sorted(mdf[mdf[hcc_col] == hcc][cluster_col].unique())
        print(f"  {metric} / {hcc}: {labels}")

# Aggregate to one value per (metric, cluster, month)
month_order = list(range(1, 13))
plot_df = plot_df.groupby([metric_col, hcc_col, cluster_col, month_col])[factor_col].first().reset_index()
plot_df[month_col] = plot_df[month_col].astype(int)
plot_df = plot_df.sort_values([metric_col, hcc_col, cluster_col, month_col])

fig = px.line(
    plot_df,
    x=month_col,
    y=factor_col,
    color=cluster_col,
    facet_row=metric_col,
    facet_col=hcc_col,
    markers=True,
    title='Seasonality Factors by Month and Cluster',
    category_orders={month_col: month_order},
    labels={factor_col: 'Norm Factor', month_col: 'Month', cluster_col: 'Cluster'}
)
fig.update_xaxes(tickvals=month_order, ticktext=['J','F','M','A','M','J','J','A','S','O','N','D'])
fig.update_layout(height=700, template='plotly_white')
fig.add_hline(y=1.0, line_dash='dash', line_color='gray', opacity=0.5)
fig.show()
     

# Compare new factors with reference table (ra_analytic_dev.cs_reference.cs_cf_seasonality_factors)
ref_df = spark.table("ra_analytic_dev.cs_reference.cs_cf_seasonality_factors").toPandas()

print(f"Reference table: {ref_df.shape[0]:,} rows")
print(f"Reference factor range: {ref_df['FINAL_NORM_FACTOR'].min():.4f} to {ref_df['FINAL_NORM_FACTOR'].max():.4f}")
print(f"New factor range:       {final_df['FINAL_NORM_FACTOR'].min():.4f} to {final_df['FINAL_NORM_FACTOR'].max():.4f}")

# Plot reference factors same way
month_order = list(range(1, 13))
plot_ref = ref_df[~ref_df['CLUSTER_LABEL'].str.contains('unmatched', na=False)].copy()
plot_ref = plot_ref.groupby(['METRIC', 'HCC', 'CLUSTER_LABEL', 'MONTH'])['FINAL_NORM_FACTOR'].first().reset_index()
plot_ref['MONTH'] = plot_ref['MONTH'].astype(int)
plot_ref = plot_ref.sort_values(['METRIC', 'HCC', 'CLUSTER_LABEL', 'MONTH'])

fig = px.line(
    plot_ref,
    x='MONTH',
    y='FINAL_NORM_FACTOR',
    color='CLUSTER_LABEL',
    facet_row='METRIC',
    facet_col='HCC',
    markers=True,
    title='REFERENCE TABLE: Seasonality Factors (cs_reference.cs_cf_seasonality_factors)',
    category_orders={'MONTH': month_order},
    labels={'FINAL_NORM_FACTOR': 'Norm Factor', 'MONTH': 'Month', 'CLUSTER_LABEL': 'Cluster'}
)
fig.update_xaxes(tickvals=month_order, ticktext=['J','F','M','A','M','J','J','A','S','O','N','D'])
fig.update_layout(height=700, template='plotly_white')
fig.add_hline(y=1.0, line_dash='dash', line_color='gray', opacity=0.5)
fig.show()

print(f"\nReference clusters per HCC:")
for metric in sorted(plot_ref['METRIC'].unique()):
    mdf = plot_ref[plot_ref['METRIC'] == metric]
    for hcc in sorted(mdf['HCC'].unique()):
        labels = sorted(mdf[mdf['HCC'] == hcc]['CLUSTER_LABEL'].unique())
        print(f"  {metric} / {hcc}: {labels}")
     

# Write seasonality factors to Unity Catalog
# Target: ra_analytic_dev.ohc_forecast.cs_cf_seasonality_factors

catalog = 'ra_analytic_dev'
schema = 'ohc_forecast'
table_name = 'cs_cf_seasonality_factors'
full_table_name = f"{catalog}.{schema}.{table_name}"

final_df.columns = final_df.columns.str.upper()

# Drop extra-granularity columns not used by the pipeline join/duplicate check.
# Keeping SEGMENT, DUAL_IND, SERVICE_TYPE, PRODUCT_LEVEL_2_TADM causes multiple
# rows per pipeline key combination, triggering the duplicate ValueError.
extra_cols = [c for c in ['SEGMENT', 'DUAL_IND', 'SERVICE_TYPE', 'PRODUCT_LEVEL_2_TADM'] if c in final_df.columns]
final_df = final_df.drop(columns=extra_cols)

# Deduplicate to the key columns the pipeline expects
key_cols = ['MARKET', 'PRODUCT_LEVEL_1_TADM', 'PRODUCT_LEVEL_3_TADM', 'HCC', 'SERVICE_CATEGORY', 'METRIC', 'MONTH']
final_df = final_df.drop_duplicates(subset=key_cols)

dup_count = final_df.duplicated(subset=key_cols, keep=False).sum()
print(f"Duplicate rows on key columns after dedup: {dup_count}")
assert dup_count == 0, f"Duplicate rows remain — do not write!"

# Convert pandas DataFrame to Spark and write
spark_df = spark.createDataFrame(final_df)
spark_df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(full_table_name)

print(f"Table written: {full_table_name}")
print(f"Rows written: {spark.table(full_table_name).count():,}")
