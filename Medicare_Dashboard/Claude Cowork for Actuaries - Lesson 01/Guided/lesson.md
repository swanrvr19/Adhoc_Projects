# Guided Lesson

## Step 1: Read and Analyze the Data

I'm going to start by reading everything — the raw CSVs and the finished dashboards for both completed months. I want to understand the data structure, what the previous actuary built, and how the inputs map to the outputs.

ACTION: Read all files in `Guided/202511/` and `Guided/202512/`:
- `clms_202511.csv`, `mbr_202511.csv`, `Claude Cowork for Actuaries - Claims Dashboard - 202511.xlsx`
- `clms_202512.csv`, `mbr_202512.csv`, `Claude Cowork for Actuaries - Claims Dashboard - 202512.xlsx`

Cross-reference the CSVs against the dashboards. Identify the data structure, calculated fields, aggregations, tab layout, formatting, and any embedded notes or commentary.

Then present a summary of what you found. Hit the key structural points — what's in the raw data, what the dashboards contain, how inputs were transformed into outputs. Keep it concise.

That's the first thing — I can read and understand your existing work. Raw data, finished deliverables, all of it. I didn't need anyone to walk me through it.

Ready to move on to Step 2 — Document the Process?

WAIT: Wait for the user to respond. If they say something looks wrong, address it and then re-ask. Do not proceed to Step 2 until they confirm.

---

## Step 2: Document the Process

Now I'm going to take what I just learned and write it up — a full process document covering how the dashboards were built from the raw data.

ACTION: Create `Guided/Process-Documentation/dashboard-process.md` AND a PDF version `Guided/Process-Documentation/dashboard-process.pdf` documenting:
- Input files and their structure
- Each tab in the dashboard and what data feeds it
- Transformations applied (PMPM calculations, plan type splits, claim type breakouts, trend periods, etc.)
- Formatting conventions (number formats, headers, colors, column widths)
- Any embedded notes, footnotes, or commentary in the dashboards
- Anything that varies between the two months vs. what stays constant

Then present a summary of the documentation. Keep it concise — hit the key structural points.

Here's what just happened: you inherited someone else's work with no documentation, and I read their finished dashboards and reverse-engineered the process. That's the second capability — Cowork can learn standards from existing deliverables, even when the person who built them isn't around to explain.

Ready to move on to Step 3 — Build the January Dashboard?

WAIT: Wait for the user to respond. If they say something looks wrong, address it and then re-ask. Do not proceed to Step 3 until they confirm.

---

## Step 3: Build the January Dashboard

Now I'll use that documentation to produce the January 2026 dashboard. Same structure, same formatting, same logic — just new data.

ACTION: Copy `Guided/202512/Claude Cowork for Actuaries - Claims Dashboard - 202512.xlsx` into the `Guided/202601/` folder and rename it to `Claude Cowork for Actuaries - Claims Dashboard - 202601.xlsx`. This preserves all formatting, formulas, conditional logic, and layout from the December dashboard as a template.

ACTION: Read `Guided/202601/clms_202601.csv` and `Guided/202601/mbr_202601.csv`. Then open the copied January dashboard and update the data in place — replace December's numbers with January's, following the process documented in `Guided/Process-Documentation/dashboard-process.md`. Do not rebuild the workbook from scratch; only update the data and any date references.

Note: January is the most recent run date, so expect to see claims lag in the most recent incurred months — low paid amounts for late-2025 service dates. That's the data behaving normally, not an error.

You define the standard once — I execute it going forward. That's the third capability. If you get a February data drop next month, this same process documentation drives the next dashboard. You don't re-explain anything.

Ready to move on to Step 4 — Claims Restatement?

WAIT: Wait for the user to respond. If they want to discuss November trend, explain: November's trend is showing negative because at lag 2, paid claims are still thin and the completed estimate is sensitive to the factors applied. It'll likely restate upward in the February run when it reaches lag 3. This is exactly the kind of thing the restatement in Step 4 will help track. Then re-ask if they're ready to continue. Do not proceed to Step 4 until they confirm.

---

## Step 4: Claims Restatement

Steps 1 through 3 replicated what you already do. This step creates something new.

I'm going to read the completed dashboards — all three, since we just built January — pull the ultimate incurred claims from their "combined data" tabs, and build a restatement showing how claims developed across report dates.

ACTION: Read the "combined data" tab from each of the three completed dashboards:
- `Guided/202511/Claude Cowork for Actuaries - Claims Dashboard - 202511.xlsx`
- `Guided/202512/Claude Cowork for Actuaries - Claims Dashboard - 202512.xlsx`
- `Guided/202601/Claude Cowork for Actuaries - Claims Dashboard - 202601.xlsx`

For each dataset, add a `report_date` field: the 202511 data gets `202511`, the 202512 data gets `202512`, the 202601 data gets `202601`. Append all three into one combined dataset. This is what makes restatement possible — comparing the same incurred month across different report dates.

Important: the dashboards don't show data for lags 0 or 1 because paid claims at those lags are too low for the completed number to be reliable. The restatement should reflect this — the first restatement shown should be the movement from lag 2 to lag 3.

ACTION: Create `Guided/Claims Restatement - All Runs.xlsx` with three tabs:

**Tab 1 — Restatement Grid:**
Rows = incurred months. Columns = report dates (202511, 202512, 202601) showing ultimate incurred claims. Include dollar change and percent change columns between consecutive report dates. Only show incurred months that appear at lag 2 or later (first restatement is lag 2 to lag 3). Highlight any incurred month where restated claims moved more than 5% between report dates.

**Tab 2 — Restatement by Segment:**
Same structure as Tab 1, but broken out by plan type (HMO/PPO) and claim type (IP/Non-IP). Four segments total. This is where you'll see whether development is concentrated in a specific book or service category.

**Tab 3 — Summary of Findings:**
Narrative summary of key observations:
- Which incurred months showed the most development between report dates?
- Is development concentrated in IP or Non-IP? HMO or PPO?
- Are there any anomalies — months where claims moved in an unexpected direction?
- Note that lags 0 and 1 are excluded because completed claims at those lags are unreliable — this is by design, not a gap

Format the workbook professionally — consistent number formats, clear headers, frozen panes on the grids.

That's the fourth capability — Cowork can create new analytical deliverables, not just replicate existing ones. The restatement also doubles as validation: if the development pattern across report dates is consistent with what the completion factors imply, everything's hanging together.

Ready to move on to Step 5 — Review Completion Methodology?

WAIT: Wait for the user to respond. If they say something looks off, let them explain and address it using the restatement data. Then re-ask. Do not proceed to Step 5 until they confirm.

---

## Step 5: Review Completion Methodology

ACTION: Read the completion data and model:
- `Guided/Completion/clms_inc_paid_202511.csv`
- `Guided/Completion/clms_inc_paid_202512.csv`
- `Guided/Completion/clms_inc_paid_202601.csv`
- `Guided/Completion/completion_factors_202511.xlsx`

The Completion/ folder has the same claims data as the monthly folders, but with paid date included — that's what lets you build incurred/paid triangles. The completion factors model is based on November 2025 data, though it could be updated with the December or January triangles.

Understand the triangle structure and the factor model. Look at how factors were derived, what lag periods are used, whether there are separate factors by plan type or claim type, and how the tail is handled.

Then share what you see. Be specific to the data — reference actual numbers, months, or segments. For example:

- Are the completion patterns materially different between HMO and PPO?
- How does IP development compare to Non-IP? Is IP more volatile or slower to complete?
- The model is based on the November triangle. With December and January triangles now available, has the development pattern been stable, or do the newer triangles suggest the original factors need updating?
- If you were refreshing this model, would you rebuild from the January triangle alone, or blend all three?

Ready to move on to the Lesson Review?

WAIT: Wait for the user to respond. Do not proceed to Lesson Review until they confirm.

---

## Lesson Review

Here's what we covered:

- **Read** — I read the raw data and existing dashboards to understand what we're working with
- **Document** — I reverse-engineered the process and documented it without anyone explaining it
- **Execute** — I used that documentation to build the January dashboard to the same standard
- **Create** — I built a claims restatement that didn't exist before — new analysis, not replication
- **Review** — We talked methodology using your actual data and completion factors model

Five capabilities: understand your data, document your processes, execute your standards, create new analysis, think with you about methods.

When you're ready, open the **Unguided/** folder in a fresh Cowork session, type **"Find and run WELCOME.md"**, and try to replicate what we just did — in your own words, without a script. The data is identical; the only difference is there's no lesson driving Claude.

WAIT: If the user wants to know more about what we did, give a brief recap of the five capabilities and how they map to real actuarial workflows: reading and understanding inherited work, documenting undocumented processes, repeatable monthly execution, new analytics from existing data, and model review as a thought partner.
