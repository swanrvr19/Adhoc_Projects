# Running the AzCopy Transfer

Your config:

| Setting | Value |
|---|---|
| Source | `//nasv0701/PI_SLG/98 Data Files/01_Databricks/Test` |
| Destination | `https://udlplandingg9w6l6.dfs.core.windows.net/landingzone/MnR_Test` |

---

## Step 1 — Open PowerShell

Press `Win + X`, choose **Windows PowerShell** or **Terminal**. No admin rights needed.

## Step 2 — Go to the folder holding your .ps1 file

```powershell
cd "C:\Users\<you>\Documents"
```

Use whatever folder you saved it in. Confirm it's there:

```powershell
Get-ChildItem *.ps1
```

If nothing lists, you're in the wrong folder or the file saved as `.ps1.txt`.

## Step 3 — Allow scripts to run (only if blocked)

```powershell
Set-ExecutionPolicy -Scope Process -Bypass
```

Applies to this window only. Skip unless you hit "running scripts is disabled."

## Step 4 — Load the config

**Note the leading dot.** Dot, space, then the path:

```powershell
. .\azcopy-setup.ps1
```

You should see "Ready." plus your `$Source` and `$Dest` values. Verify they look right:

```powershell
$Source
$Dest
```

If either is blank, you ran it without the leading dot. Run it again with the dot.

## Step 5 — Dry run

```powershell
azcopy copy $Source $Dest --recursive --dry-run
```

Lists every file that would transfer. Nothing moves. Check the count and paths.

## Step 6 — Transfer

Same command, `--dry-run` removed:

```powershell
azcopy copy $Source $Dest --recursive
```

Leave the window open until it finishes. Progress updates as it goes.

## Step 7 — Verify

```powershell
azcopy list "https://udlplandingg9w6l6.dfs.core.windows.net/landingzone/MnR_Test" --recursive
```

Then from Databricks:

```sql
LIST 'abfss://landingzone@udlplandingg9w6l6.dfs.core.windows.net/MnR_Test';
```

## Step 8 — Clear the secret

```powershell
Remove-Item Env:\AZCOPY_SPA_CLIENT_SECRET
```

Or just close the PowerShell window.

---

## If something goes wrong

| Message | Cause | Fix |
|---|---|---|
| `azcopy is not recognized` | Not on PATH | `Set-Alias azcopy "C:\path\to\azcopy.exe"` then retry |
| `running scripts is disabled` | Execution policy | Step 3 |
| `$Source` / `$Dest` empty | Missing leading dot | `. .\azcopy-setup.ps1` |
| `AuthorizationPermissionMismatch` | SP lacks `Storage Blob Data Contributor` | Ask admin — Owner/Contributor are not enough |
| `Path not found` on source | Network drive unreachable | Open the UNC path in Explorer first |
| `403` / `AuthenticationFailed` | Secret expired or wrong | Request a fresh secret |
| Stalls at 0% | Firewall blocking 443 | Network team; check storage firewall rules |

**Interrupted transfer** — resume rather than restart:

```powershell
azcopy jobs list
azcopy jobs resume <job-id>
```

Already-copied files are skipped.

---

## Re-running later

Steps 4–6 only. The config file stays as is.

Once the load is done, set `$ClientSecret = ""` in the file so it prompts rather than storing the credential on disk.

---

## After the files land: reading them in Databricks

Check the storage is already registered:

```sql
SHOW EXTERNAL LOCATIONS;
```

Read into a dataframe:

```python
df = spark.read.option("header", "true").csv(
    "abfss://landingzone@udlplandingg9w6l6.dfs.core.windows.net/MnR_Test/*.csv"
)
display(df)
```

Or load into a table (idempotent — re-running won't duplicate rows):

```sql
CREATE TABLE main.default.mnr_test;

COPY INTO main.default.mnr_test
FROM 'abfss://landingzone@udlplandingg9w6l6.dfs.core.windows.net/MnR_Test'
FILEFORMAT = CSV
FORMAT_OPTIONS ('header' = 'true', 'inferSchema' = 'true')
COPY_OPTIONS ('mergeSchema' = 'true');
```

`inferSchema` guesses types from a sample — leading zeros in zip codes and account numbers get lost. Run `DESCRIBE main.default.mnr_test` afterward and declare types explicitly for anything you'll build on.
