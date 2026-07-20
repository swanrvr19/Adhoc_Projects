# Databricks notebook source
# DBTITLE 1,CDC FluView Portal Extract
# MAGIC %md
# MAGIC ## CDC FluView Portal Data Extract
# MAGIC **Source:** https://gis.cdc.gov/grasp/fluview/fluportaldashboard.html
# MAGIC
# MAGIC This notebook downloads influenza surveillance data from the CDC FluView monitoring:
# MAGIC - **ILINet** — Influenza-Like Illness (ILI) surveillance at national, regional, and state levels
# MAGIC - **WHO/NREVSS Clinical Labs** — Clinical laboratory testing data
# MAGIC - **WHO/NREVSS Public Health Labs** — Public health laboratory virological surveillance

# COMMAND ----------

# DBTITLE 1,Imports and Configuration
import requests
import pandas as pd
import io
import json
from datetime import datetime

# CDC FluView API base URLs
BASE_URL = "https://gis.cdc.gov/grasp/flu2"
ILINET_URL = f"{BASE_URL}/PostPhase02DataDownload"
CLINICAL_LABS_URL = f"{BASE_URL}/PostPhase02DataDownload"
PUBLIC_HEALTH_LABS_URL = f"{BASE_URL}/PostPhase02DataDownload"

# Configuration
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Current season ID (CDC seasons: e.g., 2024-25 season)
# Season IDs increment each year; adjust as needed
CURRENT_SEASON_ID = 64  # 2024-2025 season
ALL_SEASONS = list(range(49, CURRENT_SEASON_ID + 1))  # From 2009-10 onward

# Region types: 1=National, 2=HHS Regions, 3=Census, 5=States
REGION_NATIONAL = 1
REGION_HHS = 2
REGION_STATES = 5

print(f"Configuration loaded. Targeting seasons {len(ALL_SEASONS)} (IDs {ALL_SEASONS[0]}-{ALL_SEASONS[-1]})")
print(f"Current date: {datetime.now().strftime('%Y-%m-%d')}")

# COMMAND ----------

# DBTITLE 1,API Helper Functions
def get_ilinet_data(region_type=REGION_NATIONAL, seasons=None, sub_regions=None):
    """
    Download ILINet data from CDC FluView API.
    
    Parameters:
        region_type: 1=National, 2=HHS Regions, 5=States
        seasons: list of season IDs (defaults to all available)
        sub_regions: list of sub-region IDs (defaults to all for the region type)
    """
    if seasons is None:
        seasons = ALL_SEASONS
    
    # Build sub-regions based on region type
    if sub_regions is None:
        if region_type == REGION_NATIONAL:
            sub_regions = [0]  # National
        elif region_type == REGION_HHS:
            sub_regions = list(range(1, 11))  # HHS Regions 1-10
        elif region_type == REGION_STATES:
            sub_regions = list(range(1, 60))  # State/territory IDs
    
    payload = {
        "AppVersion": "Public",
        "DatasourceDT": [{"ID": 1, "Name": "ILINet"}],
        "RegionTypeId": region_type,
        "SubRegionsDT": [{"ID": sr} for sr in sub_regions],
        "SeasonsDT": [{"ID": s} for s in seasons]
    }
    
    response = requests.post(ILINET_URL, json=payload, headers=HEADERS, timeout=120)
    response.raise_for_status()
    
    data = response.json()
    if "datadownload" in data:
        df = pd.DataFrame(data["datadownload"])
        print(f"ILINet (region_type={region_type}): {len(df)} rows downloaded")
        return df
    else:
        print(f"No ILINet data returned for region_type={region_type}")
        return pd.DataFrame()


def get_clinical_labs_data(region_type=REGION_NATIONAL, seasons=None, sub_regions=None):
    """
    Download WHO/NREVSS Clinical Labs data from CDC FluView API.
    """
    if seasons is None:
        seasons = ALL_SEASONS
    
    if sub_regions is None:
        if region_type == REGION_NATIONAL:
            sub_regions = [0]
        elif region_type == REGION_HHS:
            sub_regions = list(range(1, 11))
        elif region_type == REGION_STATES:
            sub_regions = list(range(1, 60))
    
    payload = {
        "AppVersion": "Public",
        "DatasourceDT": [{"ID": 0, "Name": "WHO_NREVSS"}],
        "RegionTypeId": region_type,
        "SubRegionsDT": [{"ID": sr} for sr in sub_regions],
        "SeasonsDT": [{"ID": s} for s in seasons]
    }
    
    response = requests.post(CLINICAL_LABS_URL, json=payload, headers=HEADERS, timeout=120)
    response.raise_for_status()
    
    data = response.json()
    if "datadownload" in data:
        df = pd.DataFrame(data["datadownload"])
        print(f"Clinical Labs (region_type={region_type}): {len(df)} rows downloaded")
        return df
    else:
        print(f"No Clinical Labs data returned for region_type={region_type}")
        return pd.DataFrame()


def get_public_health_labs_data(region_type=REGION_NATIONAL, seasons=None, sub_regions=None):
    """
    Download WHO/NREVSS Public Health Labs data from CDC FluView API.
    """
    if seasons is None:
        seasons = ALL_SEASONS
    
    if sub_regions is None:
        if region_type == REGION_NATIONAL:
            sub_regions = [0]
        elif region_type == REGION_HHS:
            sub_regions = list(range(1, 11))
        elif region_type == REGION_STATES:
            sub_regions = list(range(1, 60))
    
    payload = {
        "AppVersion": "Public",
        "DatasourceDT": [{"ID": 1, "Name": "WHO_NREVSS"}],
        "RegionTypeId": region_type,
        "SubRegionsDT": [{"ID": sr} for sr in sub_regions],
        "SeasonsDT": [{"ID": s} for s in seasons]
    }
    
    response = requests.post(PUBLIC_HEALTH_LABS_URL, json=payload, headers=HEADERS, timeout=120)
    response.raise_for_status()
    
    data = response.json()
    if "datadownload" in data:
        df = pd.DataFrame(data["datadownload"])
        print(f"Public Health Labs (region_type={region_type}): {len(df)} rows downloaded")
        return df
    else:
        print(f"No Public Health Labs data returned for region_type={region_type}")
        return pd.DataFrame()


print("API helper functions defined.")

# COMMAND ----------

# DBTITLE 1,Download ILINet Data (National, Regional, State)
import time
import json as json_mod

# ============================================================================
# Working approach: PostPhase02WHOGetData is the ONLY functional CDC FluView API
# endpoint. It returns both WHO/NREVSS virus counts AND ILI surveillance data
# in a single nested response structure.
# ============================================================================

WHO_URL = "https://gis.cdc.gov/grasp/flu2/PostPhase02WHOGetData"
INIT_URL = "https://gis.cdc.gov/grasp/flu2/GetPhase02InitApp?appVersion=Public"

# Step 1: Get configuration (seasons, regions, virus reference data)
print("=== Step 1: Fetching API configuration ===")
init_resp = requests.get(INIT_URL, timeout=30)
init_resp.raise_for_status()
init_data = init_resp.json()

seasons = init_data['seasons']
states = init_data['states']
hhs_regions = init_data['hhsregion']
labtypes = init_data['labtypes']
viruslist = init_data.get('viruslist', [])

# Build reference lookups
season_lookup = {s['seasonid']: s['label'] for s in seasons}
state_lookup = {s['stateid']: s['statename'] for s in states}
hhs_lookup = {r['hhsregionid']: r['hhsregionname'] for r in hhs_regions}
virus_lookup = {v['virusid']: v['label'] for v in viruslist}
labtype_lookup = {lt['labtypeid']: lt['labname'] for lt in labtypes}

print(f"Seasons available: {len(seasons)} (latest: {seasons[0]['label']})")
print(f"States/territories: {len(states)}")
print(f"HHS Regions: {len(hhs_regions)}")
print(f"Lab types: {labtype_lookup}")
print(f"Virus types: {len(viruslist)}")


def parse_who_response(response_json, season_id, region_type_id, region_id):
    """
    Parse the nested CDC FluView WHO response into flat DataFrames.
    
    Response structure per the API's data_structure field:
    [mmwrid, [[Labtypeid, [[regiontypeid, [[regionid, [
        [virusid, positive_count_cumulative, positive_count_three_weeks, positive_count],
        ...more viruses...
      ],
      PercentPositive, PercentA, PercentB, PercentWeightedILI,
      Baseline, elevated, PercentUnWeightedILI, WeeklyILIData, Insufficient
    ]]]]]]]
    """
    mmwr_weeks = {w['mmwrid']: w for w in response_json.get('mmwr', [])}
    cumulative = response_json.get('WHO_Virus_Counts_Summary_Cumulative', {})
    data_items = cumulative.get('data', [])
    
    ili_records = []
    virus_records = []
    
    for week_item in data_items:
        mmwrid = week_item[0]
        week_info = mmwr_weeks.get(mmwrid, {})
        
        labtype_list = week_item[1]  # [[Labtypeid, [...]]]
        for labtype_item in labtype_list:
            labtypeid = labtype_item[0]
            regiontype_list = labtype_item[1]  # [[regiontypeid, [...]]]
            
            for regiontype_item in regiontype_list:
                regiontypeid = regiontype_item[0]
                region_list = regiontype_item[1]  # [[regionid, [...], metrics...]]
                
                for region_item in region_list:
                    regionid = region_item[0]
                    virus_data = region_item[1]  # [[virusid, cum, 3wk, count], ...]
                    
                    # Region-level metrics (after virus data)
                    pct_positive = region_item[2] if len(region_item) > 2 else None
                    pct_a = region_item[3] if len(region_item) > 3 else None
                    pct_b = region_item[4] if len(region_item) > 4 else None
                    pct_weighted_ili = region_item[5] if len(region_item) > 5 else None
                    baseline = region_item[6] if len(region_item) > 6 else None
                    elevated = region_item[7] if len(region_item) > 7 else None
                    pct_unweighted_ili = region_item[8] if len(region_item) > 8 else None
                    weekly_ili_data = region_item[9] if len(region_item) > 9 else None
                    insufficient = region_item[10] if len(region_item) > 10 else None
                    
                    # ILI record
                    ili_records.append({
                        'season_id': season_id,
                        'season': season_lookup.get(season_id, str(season_id)),
                        'mmwrid': mmwrid,
                        'year': week_info.get('year'),
                        'week': week_info.get('weeknumber'),
                        'weekend': week_info.get('weekend'),
                        'labtype_id': labtypeid,
                        'labtype': labtype_lookup.get(labtypeid, str(labtypeid)),
                        'region_type_id': regiontypeid,
                        'region_id': regionid,
                        'pct_positive': pct_positive,
                        'pct_a': pct_a,
                        'pct_b': pct_b,
                        'pct_weighted_ili': pct_weighted_ili,
                        'baseline': baseline,
                        'elevated': elevated,
                        'pct_unweighted_ili': pct_unweighted_ili,
                        'weekly_ili_data': weekly_ili_data,
                        'insufficient': insufficient,
                    })
                    
                    # Virus-level records
                    for virus_item in virus_data:
                        virus_records.append({
                            'season_id': season_id,
                            'season': season_lookup.get(season_id, str(season_id)),
                            'mmwrid': mmwrid,
                            'year': week_info.get('year'),
                            'week': week_info.get('weeknumber'),
                            'weekend': week_info.get('weekend'),
                            'labtype_id': labtypeid,
                            'labtype': labtype_lookup.get(labtypeid, str(labtypeid)),
                            'region_type_id': regiontypeid,
                            'region_id': regionid,
                            'virus_id': virus_item[0],
                            'virus': virus_lookup.get(virus_item[0], str(virus_item[0])),
                            'positive_count_cumulative': virus_item[1],
                            'positive_count_three_weeks': virus_item[2],
                            'positive_count': virus_item[3],
                        })
    
    return pd.DataFrame(ili_records), pd.DataFrame(virus_records)


# Step 2: Download data for recent seasons (National view = all regions)
print("\n=== Step 2: Downloading FluView data ===")

# Download recent seasons (National view with RegionTypeID=3 returns all data)
seasons_to_fetch = [s['seasonid'] for s in seasons if s['enabled'] == 1][:5]  # Last 5 seasons
print(f"Fetching seasons: {[season_lookup[s] for s in seasons_to_fetch]}")

all_ili_frames = []
all_virus_frames = []

for season_id in seasons_to_fetch:
    payload = {
        "AppVersion": "Public",
        "SeasonID": season_id,
        "RegionTypeID": 3,  # National (returns data for all regions)
        "RegionID": 0
    }
    try:
        resp = requests.post(WHO_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        ili_df, virus_df = parse_who_response(data, season_id, 3, 0)
        all_ili_frames.append(ili_df)
        all_virus_frames.append(virus_df)
        print(f"  {season_lookup[season_id]}: {len(ili_df)} ILI records, {len(virus_df)} virus records")
    except Exception as e:
        print(f"  {season_lookup[season_id]}: Error - {e}")
    time.sleep(0.5)

# Combine all seasons
ilinet_all = pd.concat(all_ili_frames, ignore_index=True) if all_ili_frames else pd.DataFrame()
virus_all = pd.concat(all_virus_frames, ignore_index=True) if all_virus_frames else pd.DataFrame()

print(f"\n=== Results ===")
print(f"ILI/Surveillance records: {len(ilinet_all):,}")
print(f"Virus count records: {len(virus_all):,}")

if not ilinet_all.empty:
    print(f"\nILI columns: {list(ilinet_all.columns)}")
    display(spark.createDataFrame(ilinet_all.head(20).astype(str)))

# COMMAND ----------

# DBTITLE 1,Download WHO/NREVSS Lab Surveillance Data
# The PostPhase02DataDownload endpoint is broken on CDC's server (returns empty responses).
# Cell 4 already downloaded all lab surveillance data via PostPhase02WHOGetData.
# virus_all contains virus counts with labtype_id: 2=Clinical Labs, 1=Public Health Labs

clinical_labs_all = virus_all[virus_all['labtype_id'] == 2].copy() if not virus_all.empty else pd.DataFrame()
public_health_labs_all = virus_all[virus_all['labtype_id'] == 1].copy() if not virus_all.empty else pd.DataFrame()

print(f"Total Clinical Labs records: {len(clinical_labs_all):,}")
print(f"Total Public Health Labs records: {len(public_health_labs_all):,}")

print("\n--- Clinical Labs Columns ---")
print(list(clinical_labs_all.columns) if not clinical_labs_all.empty else "No data")
print("\n--- Public Health Labs Columns ---")
print(list(public_health_labs_all.columns) if not public_health_labs_all.empty else "No data")

# COMMAND ----------

# DBTITLE 1,Convert to Spark DataFrames and Display Summary
# Convert pandas DataFrames to Spark DataFrames for downstream use
if not ilinet_all.empty:
    sdf_ilinet = spark.createDataFrame(ilinet_all.astype(str))
    print(f"sdf_ilinet: {sdf_ilinet.count():,} rows, {len(sdf_ilinet.columns)} columns")
    sdf_ilinet.createOrReplaceTempView("cdc_ilinet")

if not clinical_labs_all.empty:
    sdf_clinical_labs = spark.createDataFrame(clinical_labs_all.astype(str))
    print(f"sdf_clinical_labs: {sdf_clinical_labs.count():,} rows, {len(sdf_clinical_labs.columns)} columns")
    sdf_clinical_labs.createOrReplaceTempView("cdc_clinical_labs")

if not public_health_labs_all.empty:
    sdf_public_health_labs = spark.createDataFrame(public_health_labs_all.astype(str))
    print(f"sdf_public_health_labs: {sdf_public_health_labs.count():,} rows, {len(sdf_public_health_labs.columns)} columns")
    sdf_public_health_labs.createOrReplaceTempView("cdc_public_health_labs")

print("\n✓ Spark DataFrames created and registered as temp views:")
print("  - cdc_ilinet")
print("  - cdc_clinical_labs")
print("  - cdc_public_health_labs")
