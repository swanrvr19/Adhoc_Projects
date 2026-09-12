# MA Forecast Control Room

**One-sentence summary:** A productized quarterly forecasting and actual-to-expected service for regional and provider-sponsored Medicare Advantage plans that need a transparent financial early-warning system between annual bid cycles.

## Executive Summary

MA Forecast Control Room would help smaller Medicare Advantage organizations turn enrollment, CMS revenue, risk-score, claims, utilization, Part D, Star/quality, and operating assumptions into one reconciled quarterly outlook. The buyer receives a baseline forecast architecture, automated actual-to-expected bridge, scenario library, assumption/change log, executive memo, and a monthly or quarterly operating cadence. The initial offer is a fixed-scope **Forecast Reliability Sprint** using aggregate plan reports; implementation can later run in the plan's own Databricks or cloud environment.

The niche is deliberately below full bid consulting and above generic financial planning. It does not submit or certify a bid, replace the appointed/qualified actuary, or promise a new enterprise data warehouse. It answers management questions such as: Which membership, risk, utilization, unit-cost, completion, Star, and benefit assumptions explain the variance from bid/budget? How much of the outlook is observed versus estimated? What changes if utilization trend, risk-score realization, or enrollment mix moves outside plan?

The need is durable and current. The 2026 Medicare Trustees Report says 69.3 million people were enrolled in Medicare during 2025 and about 51% chose Part C private plans.[1] CMS's final 2027 MA/Part D payment policies project a 2.48% average payment increase and include risk-adjustment policy changes whose plan-level effects vary.[2] Wakely has published that many Medicare Advantage organizations reforecast monthly or less frequently and recommends regular revenue accrual and reforecasting; Optum markets Part C reporting that combines medical expense, revenue/risk score, actual-to-expected, cohort analysis, and bid integration.[3][4]

This is the strongest fit with the founder's background and can command meaningful B2B fees. It is not easy: health-plan procurement, PHI/security, actuarial professional standards, a lumpy bid calendar, and employer conflicts can block launch. Validation must begin with employer clearance and a paid, no-PHI aggregate diagnostic before software.

> **Evidence convention:** **Verified** facts are linked. Proposed customer-size bands, pricing, revenue, cost, time, conversion, and value estimates are **assumptions** to test. CMS publishes program-average changes; they are not forecasts for any individual plan.

## Table of Contents

1. [Business Concept](#1-business-concept)
2. [Target Customer](#2-target-customer)
3. [Why It Could Work](#3-why-it-could-work)
4. [Existing Examples](#4-existing-examples)
5. [Competitive Positioning](#5-competitive-positioning)
6. [Revenue Model](#6-revenue-model)
7. [Minimum Viable Product](#7-minimum-viable-product)
8. [Customer Acquisition](#8-customer-acquisition)
9. [Startup Requirements](#9-startup-requirements)
10. [Risks](#10-risks)
11. [30-Day Validation Plan](#11-30-day-validation-plan)
12. [Growth Potential](#12-growth-potential)
13. [Sources](#sources)
14. [Recommended Next Step](#recommended-next-step)

## 1. Business Concept

### The problem

An MA plan's bid, budget, general ledger, membership/revenue reports, risk-adjustment projections, claims triangles, utilization dashboards, quality outlook, and operational initiatives are often maintained by different teams at different grains and cadences. Management sees “forecast changed” without one transparent bridge from prior expectation to current outlook. Smaller plans may have capable people but limited Medicare actuarial bench depth and too little engineering capacity to automate the close.

### What the customer receives

| Module | Deliverable and decision supported |
|---|---|
| Baseline reconciliation | Tie membership, CMS revenue, medical/pharmacy claims, reinsurance/risk-sharing where relevant, admin, and margin to the plan-approved baseline |
| Claims forecast | Paid/incurred completion, utilization × unit cost × mix, large-claim/seasonality treatment, credibility, and sensitivity ranges |
| Revenue/risk forecast | Membership/mix, benchmark/bid/rebate inputs supplied by plan, risk-score realization/accrual, and payment-timing bridge |
| Quality/Stars scenarios | Management-supplied measure outlook translated into explicit financial scenarios; no quality prediction claim without data |
| Actual-to-expected bridge | Prior forecast to current outlook by controllable and non-controllable driver, with audit trail |
| Scenario library | Base/downside/upside cases for trend, risk score, membership, mix, benefits, and operational initiatives |
| Governance | Data dictionary, assumption owner, versioned parameter store, tests, sign-offs, runbook, and model limitations |
| Executive packet | 10–15 page quarterly memo, forecast range, driver waterfall, emerging issues, and decisions required |

### Offer boundary

MA Forecast Control Room is management forecasting and reporting. Any certified bid, reserve opinion, statutory filing, or formal actuarial opinion remains with appropriately qualified actuaries under a separate, explicit scope. Part D, provider risk, and quality components are included only when the plan supplies adequate inputs and the founder has relevant qualifications or peer review.

## 2. Target Customer

### Primary segment

- **Organization:** regional or provider-sponsored MA organization with approximately 10,000–250,000 members, one to five contracts, and a 3–15 person actuarial/finance analytics team.
- **Economic buyer:** Medicare CFO, Chief Actuary, or VP of Medicare Finance.
- **Champion:** Director of Actuarial/Financial Planning, Medicare performance leader, or controller who owns quarterly outlooks.
- **Users:** actuarial, finance, risk adjustment, medical economics, product/bid, quality/Stars, and market presidents.
- **Trigger:** a material budget miss, new contract/service area, loss of a model owner, acquisition, migration to Databricks, auditor concern, board demand for driver transparency, or a compressed forecast/bid calendar.

### Why this segment

National carriers have large internal teams and incumbent consultants. Tiny startups may not have stable experience or procurement capacity. A regional plan has meaningful financial exposure, recurring need, and a plausible gap between spreadsheet-based processes and enterprise products.

### Secondary segment

Provider organizations taking delegated/global risk under MA contracts and needing a payer-revenue/medical-cost forecast. This can be attractive, but contract economics differ from plan bids and should be a later module, not mixed into the MVP.

## 3. Why It Could Work

### Verified need and trend

- The 2026 Trustees Report says 69.3 million people were enrolled in Medicare in 2025 and about 51% chose Part C private plans.[1] This demonstrates the scale of the operating environment, not the size of the target-customer market.
- CMS projected the final CY2027 payment policies to increase MA payments by 2.48% on average, or more than $13 billion, while addressing coding differentials and excluding most diagnoses from unlinked chart-review records from risk-score calculation.[2] A national average does not indicate any one plan's result.
- CMS publishes annual rate announcements, county ratebooks, risk-adjustment information, benchmarks, and supporting data, creating both a changing input set and a foundation for transparent tools.[5]
- Wakely's revenue-management paper says many MA organizations conduct monthly reforecasts while others reforecast less frequently, and it recommends regular monthly or quarterly revenue accrual/reforecasting to detect issues and inform operations.[3]
- Optum's Part C reporting material explicitly lists full-year forecasting, medical expense forecasting, revenue/risk-score forecasting, actual-to-expected, cohort analysis, and bid integration.[4]

### Willingness-to-pay hypothesis

**Assumption:** for a plan with $1 billion of annual revenue, a 0.1% forecast miss is $1 million. The arithmetic shows why management visibility can be valuable; it is not a claim that the service will improve accuracy by 0.1%. A fixed $20,000–$50,000 implementation or $3,000–$8,000 monthly service can be rational if it shortens the close, preserves key-person knowledge, or changes a benefit, risk, care-management, or capital decision.

### Founder advantage

Healthcare actuarial forecasting, Medicare payment knowledge, claims analytics, financial modeling, program measurement, Python/Spark/Databricks, GitHub, and automation map directly to the deliverable. A general FP&A vendor lacks MA mechanics; a data engineer may not understand actuarial completion or risk revenue; a traditional actuarial engagement may deliver analysis without durable code and controls.

## 4. Existing Examples

| Example | What it validates | How MA Forecast Control Room differs |
|---|---|---|
| [Wakely Medicare Advantage Services](https://www.wakely.com/focus-areas/medicare-advantage-services/) | Plans buy MA bid, audit, risk-score accrual, benchmarking, market-feasibility, and proprietary-tool support.[6] | The Control Room is a narrow recurring management forecast for smaller plans, implemented transparently in the client's stack. It does not try to replace full bid/certification services. |
| [Optum Medicare Advantage Part C Reporting](https://campaign.optum.com/content/dam/optum/resources/productSheets/ActuarialConsultingCampaign_MedicarePartC.pdf) | There is demand for an integrated reporting model spanning medical expense, CMS revenue/risk, cohorts, actual-to-expected, and the bid process.[4] | Optum offers scale, data, and consulting breadth. The proposed service offers fixed scope, senior attention, client-owned logic, and a lighter entry point. |
| [Milliman Health Actuarial Consulting](https://www.milliman.com/en/health/actuarial-consulting) | Large actuarial firms sell claim-experience analysis, cost modeling, Medicare Advantage bids, and analytics products.[7] | The Control Room is deliberately not a broad actuarial shop. It focuses on forecast operations and reproducible delivery for a regional plan. |

The cited firms do not publish directly comparable prices. Proposed prices below are estimates, not competitor-price claims.

## 5. Competitive Positioning

### Positioning statement

> “A Medicare forecast your CFO can trace, your actuaries can challenge, and your data team can rerun—between bid season and year-end.”

### Differentiation

1. **Between-bid cadence:** monthly/quarterly early warning and actual-to-expected, not a once-a-year bid artifact.
2. **Regional-plan scope:** standard inputs and fixed deliverables, avoiding enterprise transformation.
3. **Transparent and client-owned:** parameter tables, tests, change log, runbook, and code in the client's approved environment.
4. **Actuarial plus engineering:** experienced judgment translated into a reproducible pipeline.
5. **Range and decisions:** surface uncertainty and decision thresholds rather than a single unexplained point estimate.

### Barriers to entry

MA payment/claims expertise, trust, professional qualifications, data integration, model governance, and references create a meaningful services barrier. A scalable moat requires a reusable canonical model, input adapters, validation tests, CMS-public-data ingestion, assumption libraries, and aggregated/de-identified implementation benchmarks—built only with appropriate rights.

### Reasons not to buy

A plan should use its incumbent bid actuary when continuity, certification, and broad benchmark data matter more than implementation speed. It should build internally if it has sufficient Medicare actuarial and engineering capacity. The Control Room wins when the plan needs a bridge, operating cadence, or transparent handoff—not because it is categorically better than established firms.

## 6. Revenue Model

### Proposed offer ladder — assumptions

| Offer | Price | Revenue type | Scope |
|---|---:|---|---|
| Forecast Reliability Sprint | $8,500 | One-time | Aggregate-only process map, baseline reconciliation review, risk/control gaps, prototype bridge |
| Control Room implementation | $32,000 | One-time | Up to two products/LOBs, client-hosted code, assumptions, tests, runbook, two forecast cycles |
| Quarterly managed forecast | $4,500/month, 12-month term | Recurring | Data refresh, model run, variance review, quarterly executive packet; material changes separately scoped |
| Additional contract/LOB | $7,500 setup + $1,500/month | Mixed | Incremental mapping and reporting |
| Annual CMS update module, later | $8,000/year | Recurring | Public-data/rate-model version update and release notes; not plan-specific certification |

Use fixed fees and milestone billing. Avoid charging on forecast “savings”; the deliverable supports decisions and accuracy, not a guaranteed cost reduction.

### First-year scenarios — assumptions

| Scenario | Sales mix | Revenue | Cash expense | Founder time |
|---|---|---:|---:|---:|
| Conservative | 2 sprints + 1 implementation | $49,000 | $12,000 | 350–450 hours |
| Base | 3 sprints + 2 implementations + 1 managed client for 6 months | $116,500 | $28,000 | 650–850 hours |
| Upside, incompatible with a normal side job | 4 sprints + 3 implementations + 2 managed clients averaging 8 months | $202,000 | $50,000 | 1,100+ hours and contractor support |

Because procurement and data access are slow, a realistic first-year target is **$35,000–$100,000 revenue**, with the conservative case a genuine success. Cash expense excludes tax and founder labor.

### Customer value

Value should be measured through forecast-cycle days saved, manual reconciliations removed, variance explained by named drivers, issue-detection lead time, and decisions changed. Do not claim savings from a forecast unless the plan documents a causal action and outcome.

## 7. Minimum Viable Product

The MVP is the **Forecast Reliability Sprint**, not software:

1. Obtain the plan's aggregate monthly membership, revenue, incurred claims, risk-score, budget, and current forecast outputs—no member rows.
2. Map the existing close and identify inconsistent grain, timing, assumption ownership, and unexplained plugs.
3. Build a synthetic/client-aggregate actual-to-expected waterfall with base/downside/upside scenarios.
4. Deliver a control matrix, 90-day implementation backlog, and 60-minute CFO/actuarial readout.
5. Offer implementation only after the diagnostic identifies a funded decision and data owner.

Do not build a multi-tenant data platform, buy claims datasets, recreate bid software, or accept PHI in the first pilot.

## 8. Customer Acquisition

### Three practical paths to the first 10 customers

1. **Warm, trigger-based outreach to regional plans.** Ask actuarial peers, former colleagues, vendors, and professional contacts for introductions to 20 Medicare CFOs/Chief Actuaries. Reference a specific trigger—model-owner departure, expansion, forecast miss, or cloud migration—and offer the fixed $8,500 sprint.
2. **Complementary consulting partnerships.** Approach small bid/Stars/risk-adjustment firms and Databricks implementation partners that do not want ongoing forecast operations. Provide a co-delivery boundary: they retain certification/strategy or platform work; the Control Room implements the operating forecast.
3. **Authoritative technical content.** Publish a public-data-only quarterly “MA Forecast Change Map” translating CMS updates into driver categories, plus a synthetic actual-to-expected notebook. Present to Medicare/actuarial forums. Never present CMS national averages as plan forecasts or disclose employer methods.

Ten paying plan customers may take 24–36 months. The first-year goal should be two implementations and one recurring client, not ten.

## 9. Startup Requirements

| Category | Requirement / estimate |
|---|---|
| Initial cash | **Assumption:** $8,000–$25,000 for entity/accounting, actuarial and healthcare legal review, E&O/cyber insurance, security controls, domain, and contractor peer review |
| Time | 8–12 hours/week selling/building; 15–25 hours/week during implementation; one implementation at a time |
| Technology | Client-hosted Databricks/Snowflake or secure cloud; Python/PySpark/SQL; GitHub/CI; Quarto/BI; SFTP; parameter store; test and audit logging |
| Partners | None for aggregate sprint; a credentialed Medicare actuary/peer reviewer, privacy/security counsel, and data engineer for full implementations |
| Data strategy | Aggregate first; client-hosted minimum-necessary data later; public CMS rate/enrollment files with recorded versions |

### Legal, actuarial, and security considerations

- Obtain written employer permission and exclude employer clients, prospects, vendors, code, data, methods, and work time as required.
- A qualified actuary should determine which communications are actuarial services or statements of actuarial opinion, comply with applicable standards, and define reliance/limitations. Do not imply bid certification.
- If handling PHI for a health plan, execute a BAA and appropriate security controls. HHS states that a cloud service provider handling ePHI is a business associate and requires a HIPAA-compliant BAA.[8]
- Prefer client-hosted access, MFA, least privilege, logging, encryption, separate accounts, no local downloads, retention/deletion rules, incident response, and cyber coverage.
- Ban client data from unapproved AI tools. Document any AI-assisted code and require deterministic testing and human review.

## 10. Risks

| Risk | Failure mode | Mitigation |
|---|---|---|
| Employer conflict | Direct overlap with current duties, clients, prospects, or IP can make the idea impossible. | Written clearance before outreach; explicit exclusion list; clean-room code; separate devices/accounts/time; periodic conflict checks. |
| Procurement and trust | Plans prefer established actuarial firms and approved vendors. | Begin with no-PHI diagnostic; partner with incumbents; publish methods; carry E&O/cyber; use peer review; obtain references. |
| Actuarial qualification/liability | A forecast could be relied upon as an actuarial opinion or affect bids/capital. | Narrow intended use, qualified review, applicable standards, written reliance/limitations, no certification without qualifications, E&O insurance. |
| PHI/security | Claims and membership data create business-associate and breach obligations. | Aggregate-first MVP, client hosting, BAA, least privilege, audit logs, approved subcontractors, incident plan, no unapproved AI. |
| Model error | Completion, seasonality, risk-score timing, membership, or mapping errors can materially distort results. | Source-to-output reconciliation, independent review, unit/data tests, backtesting, ranges, materiality thresholds, version control. |
| Scope explosion | Part D, Stars, provider risk, bids, reserving, and operations can become one huge model. | Standard module boundary, explicit dependencies, change orders, and one LOB/two products in first implementation. |
| Data latency/quality | The plan may not have timely, reconciled data; output becomes a polished version of bad inputs. | Paid data-readiness gate, acceptance criteria, lineage, limitations, and stop-work clause when inputs fail. |
| Competition | Wakely, Optum, Milliman, internal teams, and FP&A platforms have stronger brands or scale. | Focus on recurring forecast operations, regional plans, senior execution, and client-owned transparent code. |
| Seasonality/capacity | Bid season and quarter close collide with full-time job demands. | Avoid bid certification, cap concurrent clients, define blackout periods, schedule quarterly work, and add reviewer capacity. |
| Policy volatility | CMS changes can obsolete assumptions and code quickly. | Version all public inputs, release notes, automated regression tests, and annual update fee; never hard-code unexplained values. |
| Overclaiming value | A management model may not change decisions or forecast accuracy. | Baseline cycle time/error/decision use, post-cycle review, renewal tied to measured adoption rather than promised savings. |

## 11. 30-Day Validation Plan

| Days | Actions | Expected cost | Measurable evidence |
|---|---|---:|---|
| 1–5 | Review employment/IP/conflict rules; obtain written clearance; consult counsel/actuarial peer on scope | $500–$2,500 | Written permitted market and service boundary |
| 3–9 | Build public/synthetic prototype: membership, revenue, claims completion, risk scenario, driver waterfall | $0–$300 | 8–10 page sample plus reproducible notebook |
| 6–16 | Interview 8 target buyers: 3 CFO/finance, 3 actuarial, 2 data/operations leaders | $0 | 5 describe a repeated forecast-control problem and current workaround |
| 8–20 | Request 15 warm introductions and send 20 personalized messages | $0–$150 | 8 qualified meetings, 3 second meetings |
| 15–27 | Offer four founding sprints at $5,000–$6,500, 50% deposit, aggregate data only | $0 | 2 proposals and 1 paid deposit |
| 24–30 | Finalize MSA/SOW, peer-review checklist, and aggregate intake | $1,500–$4,000 | Signed engagement with executive sponsor and data owner |

### Decision rules

- **Continue:** 8 qualified interviews; 5 identify forecast reconciliation/driver transparency as a top-three pain; 2 request proposals; 1 prepays a sprint.
- **Adjust:** pain exists but plans will only use approved firms—sell through a complementary actuarial/technology partner or narrow to a public-data CMS update module.
- **Abandon:** employer permission fails, buyers insist on certified bid work outside scope, or no proposal request follows 10 qualified interviews and 30 targeted approaches.

Expected 30-day spend: **$2,000–$6,950**. Expected founder time: 55–80 hours.

## 12. Growth Potential

### Phase 1: productized actuarial analytics

Forecast Reliability Sprints and implementations are founder-intensive. Templates, tests, and a canonical model improve margin, but customer trust and judgment remain personal.

### Phase 2: recurring managed control room

Standard adapters and a calendarized close turn implementation clients into annual subscriptions. Hire a data engineer and qualified Medicare actuary; create segregation between model development, run, and review.

### Phase 3: software-enabled platform

Only after repeated implementations, build public CMS-data ingestion, client-side connectors, parameter management, scenario UI, forecast ranges, actual-to-expected bridges, sign-offs, and automated release tests. Keep PHI in the client's environment where possible.

| Work | Founder-dependent initially | Scalable later |
|---|---|---|
| Executive scoping and actuarial judgment | High | Medium with qualified team |
| Data mapping and reconciliation | High | High after adapters |
| Routine forecast runs | Medium | High with automation and controls |
| Scenario engine/CMS update | Medium | High as licensed software/data |
| Executive interpretation | High | Medium |
| Bid certification/opinions | Outside initial offer | Professional-service dependent |

This concept could become a multi-million-dollar specialist platform/service if it wins a repeatable small-plan segment. That outcome requires several years, security and implementation investment, and proof that recurring software value exceeds the founder-led advice.

## Sources

1. Centers for Medicare & Medicaid Services, “[2026 Medicare Trustees Report](https://www.cms.gov/oact/tr/2026),” June 2026.
2. Centers for Medicare & Medicaid Services, “[CMS Finalizes 2027 Medicare Advantage and Part D Payment Policies](https://www.cms.gov/newsroom/press-releases/cms-finalizes-2027-medicare-advantage-part-d-payment-policies-strengthen-accountability-long-term),” April 6, 2026.
3. Wakely Consulting Group, “[Medicare Advantage Organization Revenue Projection and Management](https://www.wakely.com/wp-content/uploads/2024/04/medicare-advantage-organization-revenue-projection-and-management.pdf),” January 2024.
4. Optum, “[Medicare Advantage Part C Actuarial Reporting](https://campaign.optum.com/content/dam/optum/resources/productSheets/ActuarialConsultingCampaign_MedicarePartC.pdf),” accessed September 12, 2026.
5. Centers for Medicare & Medicaid Services, “[Medicare Advantage Rates & Statistics](https://www.cms.gov/medicare/payment/medicare-advantage-rates-statistics),” accessed September 12, 2026.
6. Wakely Consulting Group, “[Medicare Advantage Services](https://www.wakely.com/focus-areas/medicare-advantage-services/),” accessed September 12, 2026.
7. Milliman, “[Health Actuarial Consulting](https://www.milliman.com/en/health/actuarial-consulting),” accessed September 12, 2026.
8. U.S. Department of Health and Human Services, “[Guidance on HIPAA & Cloud Computing](https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/cloud-computing/index.html),” accessed September 12, 2026.

## Recommended Next Step

Before contacting a plan, obtain written employer clearance. Then build one public/synthetic 10-page “quarterly forecast change pack” with an actual-to-expected waterfall, three scenarios, explicit limitations, and a model-change log. Show it to five Medicare CFO/actuarial leaders and ask one to prepay a $5,000 aggregate-data Forecast Reliability Sprint. Do not build hosted software until two sprints reveal the same recurring data and decision workflow.
