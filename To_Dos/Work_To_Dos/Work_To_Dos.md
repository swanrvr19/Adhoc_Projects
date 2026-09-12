# Work To Dos

Running checklist. Add new items to the bottom of **Open**. Check the box and move it to **Done** when finished.

## Open

- [ ] **Gap-assess the ML forecast codebase against the continuous intelligence doc** — Read [Forecasting as a Continuous  Intelligence System.txt](Modernization/Forecasting%20as%20a%20Continuous%20%20Intelligence%20System.txt) alongside the [ML_Forecast/](ML_Forecast/) codebase (pipeline, `run_stage.py`, `signals_units.py`, `SEASONALITY_ADJUSTMENT.py`, LightGBM training). Identify where the code already meets the doc's principles and where it doesn't, then write the gaps up as their own to-do items here.

- [ ] **Build out the ML forecast** — [ML_Forecast/](ML_Forecast/)
  - [ ] Get Dan implementing Rachel's grouping logic suggestion
  - [ ] Build the display layer for the forecast output
  - [ ] Compare the new forecasts against the existing forecasts
  - [ ] Establish a best practice guide for git branching, committing, etc.
  - [ ] Ask Claude what unit tests need to be done
  - [ ] Add tree data to the RA Analytic Catalog

- [ ] **Lay out the business case for Judah** — Cover three projects:
  - [ ] The forecast
  - [ ] Member mix
  - [ ] A leading indicator report to identify emerging experience

- [ ] **Figure out what Joe, Matt, and Wooddarsky should be working on** — Decide where each of them is best pointed and get them assigned.

- [ ] **Sweep up the historical forecasts and load them into Databricks** — Gather the historical forecasts and get them loaded into our Databricks environment.

- [ ] **Summarize how the CI/CD GitHub deploy pipeline works** — Use the Duplicates project as the worked example. Write up how a push/merge triggers the pipeline through to deploy, so it can serve as a reference for setting up or explaining CI/CD on other projects.

## Done

- [x] 2026-09-11 — Set up email filtering rules

<!-- Move completed items here with the date, e.g.:
- [x] 2026-09-11 — Example finished item
-->
