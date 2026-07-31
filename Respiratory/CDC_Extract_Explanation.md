# CDC_Extract.py Explanation

Source file: `CDC_Extract.py`

## Overall Summary

This program is a Databricks notebook exported as a Python file. Its job is to download influenza surveillance data from the CDC FluView API, reshape the CDC's nested JSON response into flat tabular data, split that data into meaningful datasets, and register those datasets as Spark temporary views for downstream analysis in Databricks.

At a high level, the script does five things:

1. Imports libraries and defines API configuration.
2. Defines three older helper functions for downloading ILINet, clinical lab, and public health lab data from a CDC download endpoint.
3. Uses a different CDC endpoint, `PostPhase02WHOGetData`, because the script comments say the original download endpoint was returning empty responses.
4. Parses the nested FluView response into two pandas DataFrames:
   - `ilinet_all`: region/week-level ILI and percentage metrics.
   - `virus_all`: virus/week/region/lab-type-level positive count records.
5. Splits `virus_all` into clinical lab and public health lab records, converts the pandas DataFrames into Spark DataFrames, and registers Spark temp views.

The final Databricks temp views created are:

- `cdc_ilinet`
- `cdc_clinical_labs`
- `cdc_public_health_labs`

## Runtime Context

This file is written like a Databricks notebook. Several lines rely on Databricks-only objects:

- `spark`: the active Spark session provided by Databricks.
- `display(...)`: Databricks notebook display helper.
- `# COMMAND ----------`, `# DBTITLE`, and `# MAGIC`: Databricks notebook cell metadata/comments.

If this file is run as a plain local Python script, the CDC API calls may work, but the parts using `spark` and `display` will fail unless a Spark session and display function are available.

## Important Data Concepts

### CDC FluView API

The script uses CDC FluView endpoints under:

```text
https://gis.cdc.gov/grasp/flu2
```

Two endpoint styles appear in the code:

- `PostPhase02DataDownload`: used by the older helper functions.
- `PostPhase02WHOGetData`: used by the actual extraction workflow later in the script.

The comments say `PostPhase02WHOGetData` is the functional endpoint and returns both WHO/NREVSS virus counts and ILI surveillance data in one nested JSON response.

### Season IDs

CDC flu seasons are represented by numeric IDs. The script sets:

```python
CURRENT_SEASON_ID = 64
ALL_SEASONS = list(range(49, CURRENT_SEASON_ID + 1))
```

Based on the code comments, season ID `64` represents the 2024-2025 season, and ID `49` is treated as approximately the 2009-2010 season.

### Region Types

The script defines region type IDs:

- `1`: National
- `2`: HHS regions
- `3`: Census regions, according to the initial comment, though later the script uses `3` with a comment saying it returns all data
- `5`: States

## Step-by-Step Walkthrough

## Lines 1-12: Databricks Notebook Header

```python
# Databricks notebook source
# DBTITLE 1,CDC FluView Portal Extract
```

These comments tell Databricks that this file came from a notebook and give the first cell a title.

```python
# MAGIC %md
```

This indicates a Databricks markdown cell.

```python
# MAGIC ## CDC FluView Portal Data Extract
# MAGIC **Source:** https://gis.cdc.gov/grasp/fluview/fluportaldashboard.html
```

These are markdown lines describing the notebook's purpose and listing the CDC FluView dashboard source.

```python
# MAGIC This notebook downloads influenza surveillance data from the CDC FluView monitoring:
# MAGIC - **ILINet** ...
# MAGIC - **WHO/NREVSS Clinical Labs** ...
# MAGIC - **WHO/NREVSS Public Health Labs** ...
```

These comments explain that the notebook downloads three categories of influenza surveillance data:

- ILINet influenza-like illness data.
- WHO/NREVSS clinical lab testing data.
- WHO/NREVSS public health lab virological data.

```python
# COMMAND ----------
```

This marks the end of a Databricks notebook cell.

## Lines 14-44: Imports and Basic Configuration

```python
# DBTITLE 1,Imports and Configuration
```

This gives the next Databricks cell a title.

```python
import requests
```

Imports the `requests` library, which is used to make HTTP GET and POST calls to CDC APIs.

```python
import pandas as pd
```

Imports pandas as `pd`, used to create and combine DataFrames.

```python
import io
import json
```

Imports Python's `io` and `json` modules. In the current script, these imports are not used.

```python
from datetime import datetime
```

Imports `datetime`, used to print the current date.

```python
BASE_URL = "https://gis.cdc.gov/grasp/flu2"
```

Defines the common base URL for the CDC FluView API.

```python
ILINET_URL = f"{BASE_URL}/PostPhase02DataDownload"
CLINICAL_LABS_URL = f"{BASE_URL}/PostPhase02DataDownload"
PUBLIC_HEALTH_LABS_URL = f"{BASE_URL}/PostPhase02DataDownload"
```

Defines three endpoint variables. All three point to the same CDC endpoint, but each helper function later sends a different payload to request a different data source.

```python
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json"
}
```

Defines HTTP headers for API calls. The script tells the CDC API that it is sending JSON and expects JSON back.

```python
CURRENT_SEASON_ID = 64
```

Sets the highest season ID that the first set of helper functions should use. The comment says this is the 2024-2025 flu season.

```python
ALL_SEASONS = list(range(49, CURRENT_SEASON_ID + 1))
```

Creates a list of season IDs from `49` through `64`, inclusive.

```python
REGION_NATIONAL = 1
REGION_HHS = 2
REGION_STATES = 5
```

Defines named constants for region type IDs, making later function calls easier to read.

```python
print(f"Configuration loaded. Targeting seasons {len(ALL_SEASONS)} (IDs {ALL_SEASONS[0]}-{ALL_SEASONS[-1]})")
```

Prints a message showing how many season IDs are configured and the first and last IDs in that range.

```python
print(f"Current date: {datetime.now().strftime('%Y-%m-%d')}")
```

Prints the current date in `YYYY-MM-DD` format.

## Lines 48-89: `get_ilinet_data`

```python
def get_ilinet_data(region_type=REGION_NATIONAL, seasons=None, sub_regions=None):
```

Defines a helper function to download ILINet data. It defaults to national data.

```python
"""
Download ILINet data from CDC FluView API.
...
"""
```

Documents what the function does and explains its parameters.

```python
if seasons is None:
    seasons = ALL_SEASONS
```

If the caller does not provide specific seasons, the function uses the full `ALL_SEASONS` list.

```python
if sub_regions is None:
```

Checks whether the caller gave specific sub-regions.

```python
if region_type == REGION_NATIONAL:
    sub_regions = [0]
```

For national data, the CDC sub-region ID is `0`.

```python
elif region_type == REGION_HHS:
    sub_regions = list(range(1, 11))
```

For HHS regions, creates IDs `1` through `10`.

```python
elif region_type == REGION_STATES:
    sub_regions = list(range(1, 60))
```

For state/territory data, creates IDs `1` through `59`.

```python
payload = {
    "AppVersion": "Public",
    "DatasourceDT": [{"ID": 1, "Name": "ILINet"}],
    "RegionTypeId": region_type,
    "SubRegionsDT": [{"ID": sr} for sr in sub_regions],
    "SeasonsDT": [{"ID": s} for s in seasons]
}
```

Builds the JSON payload sent to the CDC API. The important part is `DatasourceDT`, where `ID: 1` and `Name: "ILINet"` identify the ILINet data source.

```python
response = requests.post(ILINET_URL, json=payload, headers=HEADERS, timeout=120)
```

Sends a POST request to the CDC endpoint with the JSON payload.

```python
response.raise_for_status()
```

Raises an error if the CDC response has an unsuccessful HTTP status, such as 404 or 500.

```python
data = response.json()
```

Parses the response body as JSON.

```python
if "datadownload" in data:
```

Checks whether the expected data key exists in the response.

```python
df = pd.DataFrame(data["datadownload"])
```

Converts the returned data records into a pandas DataFrame.

```python
print(f"ILINet (region_type={region_type}): {len(df)} rows downloaded")
return df
```

Prints the number of rows downloaded and returns the DataFrame.

```python
else:
    print(f"No ILINet data returned for region_type={region_type}")
    return pd.DataFrame()
```

If the response does not include data, prints a message and returns an empty DataFrame.

## Lines 91-124: `get_clinical_labs_data`

This function follows the same structure as `get_ilinet_data`, but requests WHO/NREVSS clinical lab data.

Key differences:

```python
def get_clinical_labs_data(region_type=REGION_NATIONAL, seasons=None, sub_regions=None):
```

Defines a function specifically for clinical lab data.

```python
"DatasourceDT": [{"ID": 0, "Name": "WHO_NREVSS"}],
```

Uses the WHO/NREVSS data source with `ID: 0`, which this script treats as clinical labs.

```python
response = requests.post(CLINICAL_LABS_URL, json=payload, headers=HEADERS, timeout=120)
```

Sends the API request using the clinical labs endpoint variable. The URL is the same as the ILINet URL, but the payload differs.

```python
df = pd.DataFrame(data["datadownload"])
```

Converts clinical lab records into a DataFrame.

If no data is returned, it returns an empty DataFrame.

## Lines 127-160: `get_public_health_labs_data`

This function also follows the same pattern, but requests WHO/NREVSS public health lab data.

Key difference:

```python
"DatasourceDT": [{"ID": 1, "Name": "WHO_NREVSS"}],
```

Uses the WHO/NREVSS data source with `ID: 1`, which this script treats as public health labs.

The function posts to the CDC endpoint, checks for `datadownload`, converts the data to pandas, and returns either the populated DataFrame or an empty one.

## Line 163: Helper Function Confirmation

```python
print("API helper functions defined.")
```

Prints a simple confirmation that the three helper functions have been defined.

Important note: these helper functions are not actually called later in the script. The later code uses `PostPhase02WHOGetData` instead.

## Lines 167-179: Switch to the Working API Endpoint

```python
import time
```

Imports `time`, used later to pause briefly between API requests.

```python
import json as json_mod
```

Imports the JSON module under the name `json_mod`. In the current script, this import is not used.

```python
# Working approach: PostPhase02WHOGetData is the ONLY functional CDC FluView API endpoint.
```

Explains why the script changes approach. The author found that the `PostPhase02WHOGetData` endpoint works and returns the needed data.

```python
WHO_URL = "https://gis.cdc.gov/grasp/flu2/PostPhase02WHOGetData"
```

Defines the endpoint used for the actual data extraction.

```python
INIT_URL = "https://gis.cdc.gov/grasp/flu2/GetPhase02InitApp?appVersion=Public"
```

Defines the initialization/configuration endpoint. This endpoint returns metadata such as available seasons, states, lab types, and virus labels.

## Lines 180-203: Fetch API Configuration and Build Lookups

```python
print("=== Step 1: Fetching API configuration ===")
```

Prints a progress message.

```python
init_resp = requests.get(INIT_URL, timeout=30)
```

Sends a GET request to the CDC initialization endpoint.

```python
init_resp.raise_for_status()
```

Raises an error if the config request fails.

```python
init_data = init_resp.json()
```

Parses the CDC configuration response as JSON.

```python
seasons = init_data['seasons']
states = init_data['states']
hhs_regions = init_data['hhsregion']
labtypes = init_data['labtypes']
viruslist = init_data.get('viruslist', [])
```

Extracts metadata lists from the response:

- `seasons`: available flu seasons.
- `states`: states and territories.
- `hhs_regions`: HHS region metadata.
- `labtypes`: lab type metadata.
- `viruslist`: virus metadata, defaulting to an empty list if missing.

```python
season_lookup = {s['seasonid']: s['label'] for s in seasons}
```

Creates a dictionary mapping each season ID to a readable season label.

```python
state_lookup = {s['stateid']: s['statename'] for s in states}
```

Creates a dictionary mapping each state ID to a state name. This lookup is created but not used later in the script.

```python
hhs_lookup = {r['hhsregionid']: r['hhsregionname'] for r in hhs_regions}
```

Creates a dictionary mapping each HHS region ID to a region name. This lookup is also created but not used later.

```python
virus_lookup = {v['virusid']: v['label'] for v in viruslist}
```

Creates a dictionary mapping each virus ID to a readable virus label.

```python
labtype_lookup = {lt['labtypeid']: lt['labname'] for lt in labtypes}
```

Creates a dictionary mapping each lab type ID to a readable lab type name.

```python
print(f"Seasons available: {len(seasons)} (latest: {seasons[0]['label']})")
print(f"States/territories: {len(states)}")
print(f"HHS Regions: {len(hhs_regions)}")
print(f"Lab types: {labtype_lookup}")
print(f"Virus types: {len(viruslist)}")
```

Prints summary information about the metadata received from CDC.

## Lines 206-297: `parse_who_response`

This is the most important function in the script. It converts a deeply nested CDC response into two flat pandas DataFrames.

```python
def parse_who_response(response_json, season_id, region_type_id, region_id):
```

Defines the parser function. It accepts the raw CDC response plus the season and region values used for the request.

Important note: `region_type_id` and `region_id` are passed in but not used inside the function. The function uses the region type and region IDs found inside the response itself.

```python
"""
Parse the nested CDC FluView WHO response into flat DataFrames.
...
"""
```

Documents the nested structure expected from the CDC API.

The response structure is roughly:

```text
week
  lab type
    region type
      region
        virus records
        region-level metrics
```

```python
mmwr_weeks = {w['mmwrid']: w for w in response_json.get('mmwr', [])}
```

Builds a lookup dictionary from MMWR week ID to week metadata. MMWR means Morbidity and Mortality Weekly Report, the CDC week numbering system.

```python
cumulative = response_json.get('WHO_Virus_Counts_Summary_Cumulative', {})
```

Gets the main nested virus count summary object from the response. If it is missing, uses an empty dictionary.

```python
data_items = cumulative.get('data', [])
```

Gets the nested list of actual data records. If missing, uses an empty list.

```python
ili_records = []
virus_records = []
```

Creates two empty Python lists that will be filled with flattened records.

```python
for week_item in data_items:
```

Starts looping over each week in the CDC data.

```python
mmwrid = week_item[0]
```

The first item in each week record is the MMWR week ID.

```python
week_info = mmwr_weeks.get(mmwrid, {})
```

Looks up metadata for that MMWR week, such as calendar year, week number, and week ending date.

```python
labtype_list = week_item[1]
```

Gets the list of lab types contained under that week.

```python
for labtype_item in labtype_list:
```

Loops through each lab type for that week.

```python
labtypeid = labtype_item[0]
```

Gets the lab type ID.

```python
regiontype_list = labtype_item[1]
```

Gets the list of region types under that lab type.

```python
for regiontype_item in regiontype_list:
```

Loops through each region type.

```python
regiontypeid = regiontype_item[0]
```

Gets the region type ID.

```python
region_list = regiontype_item[1]
```

Gets the list of regions under that region type.

```python
for region_item in region_list:
```

Loops through each region.

```python
regionid = region_item[0]
```

Gets the region ID.

```python
virus_data = region_item[1]
```

Gets the list of virus count records for that week/lab type/region.

```python
pct_positive = region_item[2] if len(region_item) > 2 else None
```

Gets the percent positive value if it exists; otherwise sets it to `None`.

```python
pct_a = region_item[3] if len(region_item) > 3 else None
pct_b = region_item[4] if len(region_item) > 4 else None
```

Gets the percent influenza A and percent influenza B values if present.

```python
pct_weighted_ili = region_item[5] if len(region_item) > 5 else None
baseline = region_item[6] if len(region_item) > 6 else None
elevated = region_item[7] if len(region_item) > 7 else None
```

Gets ILI-related metrics:

- Weighted percent ILI.
- Baseline.
- Elevated flag/indicator.

```python
pct_unweighted_ili = region_item[8] if len(region_item) > 8 else None
weekly_ili_data = region_item[9] if len(region_item) > 9 else None
insufficient = region_item[10] if len(region_item) > 10 else None
```

Gets additional ILI fields:

- Unweighted percent ILI.
- Weekly ILI data value.
- Insufficient data flag/indicator.

```python
ili_records.append({
    ...
})
```

Adds one flat ILI/surveillance record for the current season, week, lab type, region type, and region.

The record includes:

- Season fields: `season_id`, `season`.
- Week fields: `mmwrid`, `year`, `week`, `weekend`.
- Lab fields: `labtype_id`, `labtype`.
- Region fields: `region_type_id`, `region_id`.
- ILI and positivity metrics: `pct_positive`, `pct_a`, `pct_b`, `pct_weighted_ili`, `baseline`, `elevated`, `pct_unweighted_ili`, `weekly_ili_data`, `insufficient`.

```python
for virus_item in virus_data:
```

Loops through each virus count record for the current week/lab type/region.

```python
virus_records.append({
    ...
})
```

Adds one flat virus-count record per virus.

Each virus record includes:

- Season fields.
- Week fields.
- Lab type fields.
- Region fields.
- Virus fields: `virus_id`, `virus`.
- Count fields: `positive_count_cumulative`, `positive_count_three_weeks`, `positive_count`.

```python
return pd.DataFrame(ili_records), pd.DataFrame(virus_records)
```

Converts the two Python lists into pandas DataFrames and returns them as a pair:

1. ILI/surveillance DataFrame.
2. Virus-count DataFrame.

## Lines 300-339: Download Recent Seasons and Parse Data

```python
print("\n=== Step 2: Downloading FluView data ===")
```

Prints a progress message.

```python
seasons_to_fetch = [s['seasonid'] for s in seasons if s['enabled'] == 1][:5]
```

Builds a list of enabled CDC season IDs and keeps only the first five. The comment says these are the last five seasons. This assumes the CDC returns seasons ordered newest first.

```python
print(f"Fetching seasons: {[season_lookup[s] for s in seasons_to_fetch]}")
```

Prints readable labels for the seasons being fetched.

```python
all_ili_frames = []
all_virus_frames = []
```

Creates empty lists that will store one DataFrame per season.

```python
for season_id in seasons_to_fetch:
```

Loops through each selected season.

```python
payload = {
    "AppVersion": "Public",
    "SeasonID": season_id,
    "RegionTypeID": 3,
    "RegionID": 0
}
```

Builds the CDC request payload for one season. It asks the public FluView app for that season. The code comment says `RegionTypeID = 3` with `RegionID = 0` returns all data.

```python
try:
```

Starts an error-handling block so that if one season fails, the script can print the error and continue.

```python
resp = requests.post(WHO_URL, json=payload, headers={"Content-Type": "application/json"}, timeout=60)
```

Sends the POST request to `PostPhase02WHOGetData`.

```python
resp.raise_for_status()
```

Raises an exception for unsuccessful HTTP status codes.

```python
data = resp.json()
```

Parses the response JSON.

```python
ili_df, virus_df = parse_who_response(data, season_id, 3, 0)
```

Flattens the nested CDC response into two DataFrames.

```python
all_ili_frames.append(ili_df)
all_virus_frames.append(virus_df)
```

Stores the season's parsed DataFrames for later concatenation.

```python
print(f"  {season_lookup[season_id]}: {len(ili_df)} ILI records, {len(virus_df)} virus records")
```

Prints how many records were parsed for that season.

```python
except Exception as e:
    print(f"  {season_lookup[season_id]}: Error - {e}")
```

If the API request, JSON parsing, or parsing function fails, prints the error for that season.

```python
time.sleep(0.5)
```

Waits half a second between CDC requests. This is a light rate-limiting/politeness delay.

```python
ilinet_all = pd.concat(all_ili_frames, ignore_index=True) if all_ili_frames else pd.DataFrame()
```

Combines all season-level ILI DataFrames into one DataFrame. If nothing was downloaded, creates an empty DataFrame.

```python
virus_all = pd.concat(all_virus_frames, ignore_index=True) if all_virus_frames else pd.DataFrame()
```

Combines all season-level virus-count DataFrames into one DataFrame. If nothing was downloaded, creates an empty DataFrame.

```python
print(f"\n=== Results ===")
print(f"ILI/Surveillance records: {len(ilinet_all):,}")
print(f"Virus count records: {len(virus_all):,}")
```

Prints final row counts for the combined DataFrames.

```python
if not ilinet_all.empty:
```

Checks whether the ILI DataFrame has records.

```python
print(f"\nILI columns: {list(ilinet_all.columns)}")
```

Prints the column names in the ILI DataFrame.

```python
display(spark.createDataFrame(ilinet_all.head(20).astype(str)))
```

Converts the first 20 rows of `ilinet_all` to a Spark DataFrame and displays them in Databricks. The `.astype(str)` converts all values to strings first, which can avoid type inference issues when creating Spark DataFrames.

## Lines 343-357: Split Lab Surveillance Data

```python
# The PostPhase02DataDownload endpoint is broken on CDC's server (returns empty responses).
```

Explains why the earlier helper functions are not being used.

```python
# Cell 4 already downloaded all lab surveillance data via PostPhase02WHOGetData.
```

Clarifies that `virus_all` already contains the lab surveillance data.

```python
# virus_all contains virus counts with labtype_id: 2=Clinical Labs, 1=Public Health Labs
```

Documents the lab type IDs used for splitting the data.

```python
clinical_labs_all = virus_all[virus_all['labtype_id'] == 2].copy() if not virus_all.empty else pd.DataFrame()
```

Creates a clinical labs DataFrame by filtering `virus_all` where `labtype_id` equals `2`. If `virus_all` is empty, returns an empty DataFrame.

```python
public_health_labs_all = virus_all[virus_all['labtype_id'] == 1].copy() if not virus_all.empty else pd.DataFrame()
```

Creates a public health labs DataFrame by filtering `virus_all` where `labtype_id` equals `1`. If `virus_all` is empty, returns an empty DataFrame.

```python
print(f"Total Clinical Labs records: {len(clinical_labs_all):,}")
print(f"Total Public Health Labs records: {len(public_health_labs_all):,}")
```

Prints row counts for the two lab-specific DataFrames.

```python
print("\n--- Clinical Labs Columns ---")
print(list(clinical_labs_all.columns) if not clinical_labs_all.empty else "No data")
```

Prints clinical lab columns if data exists; otherwise prints `No data`.

```python
print("\n--- Public Health Labs Columns ---")
print(list(public_health_labs_all.columns) if not public_health_labs_all.empty else "No data")
```

Prints public health lab columns if data exists; otherwise prints `No data`.

## Lines 361-381: Convert to Spark and Register Temp Views

```python
# Convert pandas DataFrames to Spark DataFrames for downstream use
```

Explains the purpose of this section.

```python
if not ilinet_all.empty:
```

Checks whether ILI data exists.

```python
sdf_ilinet = spark.createDataFrame(ilinet_all.astype(str))
```

Converts the pandas ILI DataFrame to a Spark DataFrame, converting all values to strings first.

```python
print(f"sdf_ilinet: {sdf_ilinet.count():,} rows, {len(sdf_ilinet.columns)} columns")
```

Prints the Spark DataFrame row and column count.

```python
sdf_ilinet.createOrReplaceTempView("cdc_ilinet")
```

Registers the Spark DataFrame as a temporary SQL view named `cdc_ilinet`.

```python
if not clinical_labs_all.empty:
```

Checks whether clinical lab data exists.

```python
sdf_clinical_labs = spark.createDataFrame(clinical_labs_all.astype(str))
```

Converts the clinical lab pandas DataFrame to Spark.

```python
print(f"sdf_clinical_labs: {sdf_clinical_labs.count():,} rows, {len(sdf_clinical_labs.columns)} columns")
```

Prints row and column counts for the clinical labs Spark DataFrame.

```python
sdf_clinical_labs.createOrReplaceTempView("cdc_clinical_labs")
```

Registers the clinical lab Spark DataFrame as `cdc_clinical_labs`.

```python
if not public_health_labs_all.empty:
```

Checks whether public health lab data exists.

```python
sdf_public_health_labs = spark.createDataFrame(public_health_labs_all.astype(str))
```

Converts the public health lab pandas DataFrame to Spark.

```python
print(f"sdf_public_health_labs: {sdf_public_health_labs.count():,} rows, {len(sdf_public_health_labs.columns)} columns")
```

Prints row and column counts for the public health labs Spark DataFrame.

```python
sdf_public_health_labs.createOrReplaceTempView("cdc_public_health_labs")
```

Registers the public health lab Spark DataFrame as `cdc_public_health_labs`.

```python
print("\n✓ Spark DataFrames created and registered as temp views:")
print("  - cdc_ilinet")
print("  - cdc_clinical_labs")
print("  - cdc_public_health_labs")
```

Prints a final success message listing the temp views. Note that this message prints even if one or more source DataFrames were empty and therefore not actually registered.

## DataFrames Produced

### `ilinet_all`

This is the combined pandas DataFrame containing ILI and region-level surveillance metrics across the selected seasons.

Columns created by the parser:

- `season_id`
- `season`
- `mmwrid`
- `year`
- `week`
- `weekend`
- `labtype_id`
- `labtype`
- `region_type_id`
- `region_id`
- `pct_positive`
- `pct_a`
- `pct_b`
- `pct_weighted_ili`
- `baseline`
- `elevated`
- `pct_unweighted_ili`
- `weekly_ili_data`
- `insufficient`

### `virus_all`

This is the combined pandas DataFrame containing virus-specific positive counts across the selected seasons.

Columns created by the parser:

- `season_id`
- `season`
- `mmwrid`
- `year`
- `week`
- `weekend`
- `labtype_id`
- `labtype`
- `region_type_id`
- `region_id`
- `virus_id`
- `virus`
- `positive_count_cumulative`
- `positive_count_three_weeks`
- `positive_count`

### `clinical_labs_all`

This is a filtered copy of `virus_all` where:

```python
labtype_id == 2
```

It represents clinical lab virus count records.

### `public_health_labs_all`

This is a filtered copy of `virus_all` where:

```python
labtype_id == 1
```

It represents public health lab virus count records.

## Execution Flow in Plain English

1. The notebook starts and imports the libraries it needs.
2. It defines constants for CDC API URLs, request headers, season IDs, and region IDs.
3. It defines three helper functions for an older CDC download endpoint.
4. It then switches to a different endpoint, `PostPhase02WHOGetData`, because the comments say that endpoint is the reliable one.
5. It calls the CDC initialization endpoint to get metadata.
6. It builds lookup dictionaries so numeric IDs can be converted into readable labels.
7. It defines a parser to flatten CDC's nested response.
8. It chooses the first five enabled flu seasons from CDC's metadata.
9. For each selected season, it sends a POST request to CDC.
10. It parses each response into ILI records and virus-count records.
11. It concatenates all season-level DataFrames into two combined DataFrames.
12. It filters virus records into clinical labs and public health labs.
13. It converts each pandas DataFrame into a Spark DataFrame.
14. It registers the Spark DataFrames as temporary SQL views.

## Notes and Potential Issues

- The script assumes the CDC `seasons` list is ordered with the latest season first because it takes `[:5]` after filtering enabled seasons.
- `io`, `json`, and `json_mod` are imported but not used.
- The helper functions `get_ilinet_data`, `get_clinical_labs_data`, and `get_public_health_labs_data` are defined but not called.
- `state_lookup` and `hhs_lookup` are created but not used.
- `parse_who_response` accepts `region_type_id` and `region_id`, but does not use those parameters.
- The final success message always lists all three temp views, even if some DataFrames were empty and skipped.
- Because all pandas DataFrames are converted with `.astype(str)`, Spark receives every column as a string. This can simplify ingestion but may require later casting for numeric analysis.
- This script is designed for Databricks. Running it outside Databricks would require adding or replacing `spark` and `display`.

## Short Version

`CDC_Extract.py` downloads recent CDC FluView influenza surveillance data, flattens nested API responses into tabular pandas DataFrames, splits the virus records into clinical and public health lab datasets, converts everything to Spark DataFrames, and creates temporary Databricks SQL views for analysis.
