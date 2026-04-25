# Claims PMPM Dashboard — Process Documentation

*NonSentience Health — Medicare Advantage | Monthly Close Deliverable*

---

## 1. Purpose

The Claims PMPM Dashboard presents calendar-year 2024 vs. 2025 ultimate incurred PMPM by incurred month, with quarterly, year-to-date, and full-year rollups, plus YoY trend. It is produced once per close month using (a) that month's paid claims and member month extracts, and (b) the current completion factor table. The workbook is self-contained — all aggregations, completions, and display formulas live inside the file.

## 2. Input Files

Two CSVs land in the close-month folder (`YYYYMM/`):

- **`clms_YYYYMM.csv`** — Paid claims through the close date.
  - Columns: `incurred_year_month` (EOM date, M/D/YYYY), `plan_type` (HMO/PPO), `claim_type` (IP/Non-IP), `plan_paid` (USD).
  - Grain: one row per incurred month × plan_type × claim_type. Four rows per incurred month.
  - History: starts January 2024; newest row = the close month (will be heavily undeveloped at lag 0–1).
- **`mbr_YYYYMM.csv`** — Member months through the close month.
  - Columns: `year_month` (EOM date), `plan_type`, `member_months`.
  - Grain: two rows per month (HMO + PPO).

Approximate volume: HMO ~63k / PPO ~37k member months per month (~100k total MA lives).

## 3. Workbook Architecture

The workbook is the same structure each month. Eight tabs:

| Tab | Role | Notes |
|---|---|---|
| `controls` | Driver | Single hardcoded input: **Close Date** (`B5`). Drives everything downstream via named ranges. Blue/teal text denotes an input cell per the workbook's convention (`A2`: *"inputs are in teal text throughout file"*). |
| `cf` | Completion factor table | Plan × claim × lag (0–23). Header note `A1`: *"see 'Completion Factors' folder and use most recent"*. |
| `claims` | CSV paste area for `clms` | Header note `A1`: *"data pasted in from clms_yyyymm CSV file and formatted"*. Formula columns add year/month/lag/CF/ultimate. |
| `mbr` | CSV paste area for `mbr` | Header note `A1`: *"data pasted in from mbr_yyyymm CSV file and formatted"*. Formula columns add year/month. |
| `pivot` | Pivot tables | One for member months, one for ultimate_incurred; both cross-tabbed calendar year × calendar month. |
| `combined data` | Long-format dataset | Year, month, plan_type, claim_type, member_months, ultimate_incurred. Handoff point for any downstream analysis. |
| `calcs` | Engine | Month-in-YTD flags, member months by year (GETPIVOTDATA), ultimate incurred by year (GETPIVOTDATA), PMPMs, trend, graph series. |
| `Dashboard` | Display | Presentation layer. All cells reference `calcs`. |

## 4. Named Ranges (defined in `controls`)

| Name | Formula | Meaning |
|---|---|---|
| `close_date` | `controls!B5` (hardcoded EOM date) | Paid-thru date for this close cycle. |
| `close_year` | `=YEAR(close_date)` | |
| `close_month` | `=MONTH(close_date)` | |
| `incurred_date` | `=DATE(YEAR(close_date), MONTH(close_date)-1, 0)` | End of month **two months before** close. This is the most recent incurred month shown on the dashboard (i.e., lag 2 convention). For a Nov close, this resolves to Sep 30. For a Dec close, Oct 31. |
| `incurred_year` | `=YEAR(incurred_date)` | |
| `incurred_month` | `=MONTH(incurred_date)` | Drives the "is this month in YTD?" flags in `calcs`. |

## 5. Core Transformations

### 5.1 Lag and Completion (on `claims`)

For each row (incurred_year_month, plan_type, claim_type, plan_paid):

1. `incurred_year = YEAR(incurred_year_month)`
2. `incurred_month = MONTH(incurred_year_month)`
3. `lag = (YEAR(close_date) - YEAR(A)) * 12 + MONTH(close_date) - MONTH(A)`
4. `completion_factor = VLOOKUP(plan_type & claim_type & lag, cf!D:E, 2, FALSE)`
5. `ultimate_incurred = plan_paid / completion_factor`

The CF lookup key is concatenated in `cf` column D (e.g., `HMOIP5`) so the VLOOKUP is a single-column match. Factors tail to 1.000 by around lag 10 (HMO IP fastest; Non-IP slightly later).

### 5.2 Pivots

- `pivot!C2:P6` — Sum of `member_months` by year × month (HMO + PPO combined).
- `pivot!C20:P24` — Sum of `ultimate_incurred` by year × month (HMO + PPO and IP + Non-IP combined).

These are the sources for every figure on the Dashboard.

### 5.3 `calcs` — Engine Layout

Columns E:P represent calendar months Jan–Dec. Rows encode the metric blocks:

| Block | Rows | Purpose |
|---|---|---|
| Month-in-YTD flag | row 2 | `=IF(month > incurred_month, 0, 1)` — 1 if the month is at or before incurred_date, else 0. |
| Quarter index | row 1 | Hard-coded 1,1,1,2,2,2,…,4,4,4. Drives quarter rollups. |
| Quarter YTD flag | row 3 | `=IF(row2=1, row1, 0)` — only counts the quarter if the month is within YTD. |
| Member months 2024 | row 7 | `GETPIVOTDATA` from the `pivot!C2` member pivot for all 12 months. |
| Member months 2025 | row 8 | Same, but gated by `row2` flag so CY2025 stops at incurred_month. |
| Ultimate claims 2024 | row 12 | `GETPIVOTDATA` from the `pivot!C20` claims pivot. |
| Ultimate claims 2025 | row 13 | Same, gated by `row2`. |
| PMPM 2024 | row 17 | `= claims_2024 / mbr_2024` (cell-level). |
| PMPM 2025 | row 18 | Same, gated by `row2` (returns `""` for months beyond incurred_month). |
| Trend '25/'24 | row 21 | `= PMPM_2025 / PMPM_2024 - 1`, gated by `row2`. |
| CY graph series | row 24+ | Uses `NA()` for months beyond incurred_month so charts break cleanly. |

Quarter columns (T:W) and YTD column (R) use `AVERAGEIFS` keyed on row 2 (in-YTD flag) or row 1 (quarter index). FY column (Y) uses a plain `AVERAGE` over all 12 months (2024 only, since 2025 FY only exists once December is in YTD).

### 5.4 Dashboard Display

The `Dashboard` tab is a pure display layer. Every numeric cell is a direct reference to `calcs`:

- Rows 24 and 25: PMPM for 2024 and 2025 across Jan–Dec, YTD, Q1–Q4, FY.
- Row 27: YoY trend.
- Title subtitle (`B5`): `="Data incurred thru "&TEXT(incurred_date,"mmmyy")&"; paid thru "&TEXT(close_date,"mmmyy")` — updates automatically with the close date.
- Column headers (`D22:O22`): hardcoded Jan–Dec. `Q22` dynamically reads `TEXT(incurred_date,"mmm")&" YTD"`.

## 6. Monthly Update Procedure

To refresh the dashboard for a new close month:

1. **Start from the prior month's workbook** to preserve formatting, named ranges, formulas, pivots, and charts.
2. **Update the close date** in `controls!B5` to the new EOM date.
3. **Replace `claims` data** — paste the new `clms_YYYYMM.csv` into the `claims` tab starting at row 7 (preserving header row 6). Extend the formula columns (E–I) down to cover all new rows.
4. **Replace `mbr` data** — paste the new `mbr_YYYYMM.csv` into the `mbr` tab starting at row 7. Extend columns D–E.
5. **Confirm CF table is current** — check `cf!A1` note and refresh from the Completion folder if factors have been re-estimated.
6. **Refresh the two pivots** on the `pivot` tab (Data → Refresh All). Pivot source range should cover the new row count.
7. **Recalculate** the workbook.
8. **Sanity-check** the Dashboard:
   - Title subtitle reads correctly ("Data incurred thru {incurred_month}; paid thru {close_month}").
   - 2025 row stops populating after incurred_month.
   - New incurred month (at lag 2) looks reasonable relative to prior months.
   - Trend % row populates only for months inside YTD.

## 7. Formatting Conventions

- **Font**: consistent workbook-wide (default Calibri body).
- **Number formats**:
  - PMPMs: `_("$"* #,##0.00_);_("$"* \(#,##0.00\);_("$"* "-"??_);_(@_)` (accounting dollars, 2 decimals).
  - Trend: `0.0%`.
- **Input cells**: teal font (per `controls!A2`).
- **Dashboard title block**: merged across `B4:X4` (title) and `B5:X5` (subtitle).
- **Column layout on Dashboard**: monthly block D:O, gap in P, YTD in Q, gap in R, Q1:Q4 in S:V, gap in W, FY in X.
- **Notes**: header-row comments in `cf`, `claims`, `mbr`, and `controls` describe source and input convention.

## 8. What Varies vs. What Stays Constant

**Varies each close:**
- `controls!B5` close date.
- Contents of `claims` rows 7+ and `mbr` rows 7+.
- Pivot source ranges (one additional incurred month of rows).
- Dashboard row 25 populates one month further out as incurred_date advances.

**Stays constant:**
- Workbook structure (8 tabs, named ranges, formulas).
- Completion factor table, unless the model is refreshed (see `cf!A1`).
- `calcs` layout, pivot structure, Dashboard template.
- Formatting, headers, dynamic subtitle formula.

## 9. Known Quirks / Things to Watch

- **Lag 2 convention**: the incurred month shown is always two months before close because paid data at lag 0–1 is too thin for completion to be reliable. The `incurred_date` formula enforces this.
- **Most recent incurred months in the raw data look tiny.** That's the lag 0 / lag 1 trail in the CSV. It's filtered out of the dashboard by the `incurred_month` gate, but it's visible if you pivot the raw tabs directly.
- **FY 2025** only populates once December is inside YTD (i.e., after the Jan26 close, when `incurred_date` = Dec 31, 2025).
- **Completion factors go to 1.000 by lag ~10.** If incurred_year_month is beyond 23 months old, the VLOOKUP key won't exist — but that's never an issue in practice because the CF table carries lags out far enough to cover the oldest incurred months in the dataset (Jan 2024).
- **Trend volatility at the newest incurred month**: the most recent incurred month on the dashboard is at lag 2, where the completion factor still leans heavily on the model. Expect meaningful restatement as that month ages into lag 3 and lag 4.

---

*Reverse-engineered from the Nov25 and Dec25 close workbooks. No external documentation was available from the prior owner.*
