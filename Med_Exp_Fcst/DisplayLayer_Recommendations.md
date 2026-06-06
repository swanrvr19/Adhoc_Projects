# Display Layer Recommendations
## Actual vs. Expected Medical Expense Reporting

---

## Recommendation: Power BI Connected to Databricks

Power BI connected to Databricks is the recommended approach for a healthcare payer executive audience. Most health plans are already in the Microsoft stack, which means executives likely have Power BI access and are already familiar with it. The Databricks connector for Power BI is mature and well-supported — point it at the `expected_allocated` and `hcta_actuals` output tables, build the core measures in Power BI (actuals, expected, variance, A/E ratio), and publish to a shared workspace. Executives get a clean, filterable view without ever needing a Databricks login.

---

## Options Considered

### Option 1: Power BI + Databricks (Recommended)
**How it works:** Databricks handles all data processing (Steps 1–5); Power BI connects directly to the output Delta tables via the Databricks connector and serves as the presentation layer.

| Pro | Con |
|---|---|
| Executives already have access and are familiar with it | Requires Power BI license (Pro or Premium) |
| Richest UX — filters, drilldowns, charts, mobile support | Adds a second tool to the stack |
| Mature Databricks connector (DirectQuery or import mode) | Premium/Fabric capacity needed for broad sharing without per-user Pro licenses |
| Row-level security handles PHI compliance cleanly | |
| Can publish to Teams tab or SharePoint — no new login for executives | |

**Best for:** Executive distribution, polished presentation, organizations already on Microsoft 365.

---

### Option 2: Databricks AI/BI Dashboards (Lakeview)
**How it works:** Dashboard is built and hosted entirely within the Databricks workspace, reading directly from the output Delta tables.

| Pro | Con |
|---|---|
| Zero additional tooling — everything stays in Databricks | Executives need a Databricks login (common blocker at health plans) |
| Fast to build for a focused A/E use case | UX less polished than Power BI for executive audiences |
| No data movement — queries live data | Better suited for analyst/internal use than C-suite distribution |
| Capabilities have improved significantly with Lakeview | |

**Best for:** Internal analyst use, teams that want to minimize tool sprawl, or orgs where executives already have Databricks workspace access.

---

### Option 3: Custom Web Application
**How it works:** A bespoke front-end application built on top of the Databricks output tables.

| Pro | Con |
|---|---|
| Maximum flexibility in UX design | Highest build and maintenance cost |
| No dependency on third-party BI licensing | Requires dedicated engineering effort |

**Best for:** Only appropriate if specific requirements cannot be met by Power BI or Databricks dashboards (e.g., embedding in a proprietary portal).

---

## Key Decision Question

Before committing to Power BI, confirm your organization's license tier:

- **Power BI Premium or Microsoft Fabric capacity** → Power BI is a clear no-brainer. Publish to a workspace and share broadly without per-user licensing friction.
- **Power BI Pro licenses only** → Sharing is limited to other Pro users. Still workable if executives have Pro licenses, but worth validating before building.
- **No Power BI licenses** → Default to Databricks AI/BI Dashboards to avoid new procurement, with the understanding that executives will need Databricks workspace access.

---

## Recommended Architecture

```
Databricks (Steps 1–5)
  └── hcta_actuals (Delta table)
  └── expected_allocated (Delta table)
        │
        ▼
  Power BI (Step 6)
  └── Databricks Connector (DirectQuery)
  └── Measures: Actual $, Expected $, Variance $, A/E Ratio %
  └── Published to Power BI Workspace
        │
        ▼
  Executive Access
  └── Power BI Service (browser)
  └── Teams tab or SharePoint embed
  └── Power BI Mobile (optional)
```
