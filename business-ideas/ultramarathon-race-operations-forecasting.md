# AidStation Ops

**One-sentence summary:** A pre-race forecasting service for multi-event ultramarathon producers that converts registration, historical split, course, and weather data into aid-station arrival ranges, inventory plans, staffing loads, and cutoff-risk scenarios.

## Executive Summary

AidStation Ops applies forecasting and program-measurement skills to a narrow operational problem in ultrarunning. Race directors can register athletes and track them during an event, but they still have to decide—often in spreadsheets and from intuition—when each aid station will be busiest, how much food/water/ice to stage, when vehicles can resupply, where volunteers will be overloaded, and how weather or a faster/slower field changes those plans.

The deliverable is a **Race Operations Forecast Pack** produced 21–30 days before an event and refreshed after the final entrant file and weather forecast. It contains probabilistic arrival curves by aid station, expected concurrent load, food/water inventory with adjustable consumption assumptions, cutoff and sweep scenarios, staffing schedules, and a one-page race-command summary. It is an advisory planning tool, not live timing, emergency management, or a safety guarantee.

Existing platforms validate adjacent demand. UltraSignup and RunSignup monetize registration and offer race-management tools; OpenSplitTime collects endurance-event data and predicts in-progress arrival times.[1][2][3] The proposed niche is different: a platform-neutral, pre-event capacity and logistics model for trail/ultra producers operating a series of events. The business is cheap and enjoyable to validate, but its economic ceiling is the lowest of the five proposals. Most races are small, budgets are tight, directors rely on experience, and OpenSplitTime already covers part of the forecasting problem. This should be pursued only if five directors will share data and at least two pay for pilots.

> **Evidence convention:** **Verified** statements link to sources. Proposed prices, market size, conversion, revenue, expense, and time estimates are **assumptions** and must be tested.

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

### Customer problem

A 50K–100-mile race is a distributed service operation with uncertain arrivals, long durations, remote stations, changing weather, participant dropouts, scarce volunteers, perishable inventory, and hard cutoffs. Registration and timing software answer “who entered?” and “where is a runner now?” They do not necessarily produce a defensible pre-race procurement and staffing plan with uncertainty ranges.

### What the customer receives

| Artifact | Operational use |
|---|---|
| Data-readiness report | Identifies usable registration/results/split fields, missing stations, course changes, and assumptions |
| Arrival forecast | P10/P50/P90 cumulative and hourly arrivals at every staffed station, by distance/ wave where relevant |
| Load model | Runners on course, arrivals per 15/30/60 minutes, expected dwell, crew traffic proxy, and drop probability |
| Inventory calculator | Water, ice, calories, category mix, cups, and safety buffer under base/hot/slow-field scenarios |
| Staffing and transport schedule | Shift windows, peak service load, replenishment triggers, and vehicle movement constraints supplied by the director |
| Cutoff/sweep analysis | Expected count near each cutoff, sensitivity to start delays and weather, and post-race comparison |
| Command brief | Printable one-page table of peaks, triggers, and decision owners |

The model combines prior results/splits, entrant history where lawful and available, course distance/elevation, start waves, withdrawals, and director-supplied consumption and staffing assumptions. A final forecast can incorporate public weather forecasts, but the director—not the model—owns safety decisions.

## 2. Target Customer

### Primary segment

- **Organization:** U.S. trail/ultra producer running at least 4 events per year, or one event with 800+ participants across multiple distances and 6+ aid stations.
- **Buyer:** owner/race director or operations director who controls procurement and volunteer planning.
- **Champion/users:** aid-station captain coordinator, timing partner, logistics lead, medical director, and volunteer coordinator.
- **Trigger:** a new distance/course, growth above prior capacity, recurring stockouts/waste, a remote station that is expensive to resupply, sponsor reporting, or turnover of an experienced operations lead.

### Secondary segment

Timing companies serving multiple trail events. One timing partner can supply normalized split data and resell a pre-race forecast to its race clients.

### Deliberate exclusions

Do not initially sell to a 100-person volunteer race, road 5K, or a new race with no comparable data and no operations budget. RunSignup reports that 87% of races in its 2025 data had fewer than 500 participants.[4] That is a warning: the addressable high-budget segment is much smaller than the overall event count.

## 3. Why It Could Work

### Evidence of an active market

- RunSignup's 2025 RaceTrends report analyzes more than 97,000 race events and 12.2 million registrations in its own platform data. For races present in both years, average participation grew 5% in 2025; only 3.1% of 2024 races with more than 500 participants did not occur in 2025.[4] **Verified, but vendor-reported:** this indicates a substantial, fairly stable endurance-event operating market, not the size of the ultra-only niche.
- Race directors and participants already pay for event technology. RunSignup lists its standard processing fee at 6% + $1 for carts below $250 and says the race can pass it to the participant.[2] UltraSignup publishes U.S. hosting fees of 6.25% + $2.50 for registrations below $100 and 6.5% + $3.50 for $100–$999.[1]
- OpenSplitTime explicitly describes tools to collect, organize, archive, and analyze endurance-event data. Its monitoring tools use existing data to predict arrivals for athletes in progress.[3][5] This is both validation and competitive pressure.

### Pain and willingness-to-pay hypothesis

**Assumption:** a series operator can justify $3,000–$8,000 per year if the service prevents one remote-station stockout, reduces over-purchasing and waste, improves volunteer scheduling, or preserves reusable institutional knowledge. This has not been verified by the cited sources. The 30-day test must ask for invoices and paid pilots, not merely agreement that logistics are difficult.

### Founder advantage

Actuarial forecasting supplies uncertainty ranges and calibration discipline; claims/program analytics supplies messy longitudinal data skills; Python/Spark/automation enables repeatable models; ultramarathon experience supplies domain empathy and credible interview questions. The advantage is translating operations into measurable assumptions, not pretending an actuarial model can replace race experience.

## 4. Existing Examples

| Example | What it validates | How AidStation Ops differs |
|---|---|---|
| [OpenSplitTime](https://www.opensplittime.org/about) | Endurance events need specialized split-data collection, planning, analysis, and archival; its live tools already predict in-progress arrival times.[3][5] | AidStation Ops focuses on pre-race capacity, inventory, staffing, transport, and scenario bands. It should export to—not compete with—live timing. OpenSplitTime is also a potential data/community partner. |
| [UltraSignup](https://help.ultrasignup.com/hc/en-us/articles/30362746490637-What-are-the-event-hosting-fees-on-UltraSignup) | Trail/ultra events sustain a specialized registration platform with published transaction fees.[1] | UltraSignup's core is registration, discovery, results, and related race services. AidStation Ops is platform-neutral back-office forecasting and can accept an UltraSignup export. |
| [RunSignup](https://info.runsignup.com/2025/07/21/how-much-does-runsignup-cost/) | Race organizers adopt integrated technology, and participant-paid processing fees support a sizable platform.[2] | RunSignup offers registration, marketing, and race-day products plus graphical reports. AidStation Ops is narrower and deeper on long-duration, multi-station logistics. |

These examples demonstrate adjacent demand; none proves directors will buy a separate forecasting layer.

## 5. Competitive Positioning

### Niche and promise

> “Your timing system tells you where runners are. AidStation Ops tells you what every station should be ready for—and how uncertain the plan is—before the race starts.”

### Differentiation

1. **Trail/ultra only:** long duration, dropouts, cutoffs, remote replenishment, crew access, and multiple distances.
2. **Pre-event operations:** explicit inventory and staffing outputs, not just athlete tracking.
3. **Uncertainty, not false precision:** P10/P50/P90 arrival and consumption ranges, with scenario levers visible to the director.
4. **Platform-neutral:** ingest CSVs from UltraSignup, RunSignup, timing vendors, and OpenSplitTime where terms and permissions allow.
5. **Post-race learning loop:** compare forecast with actuals and preserve event-specific calibration for next year.

### Barriers to entry

Initially low: a competent analyst can make a spreadsheet. Defensibility grows through normalized course/station schemas, historical calibration, event-specific consumption data, integrations, reusable operations templates, and trust with timing partners. Data rights may limit cross-event learning.

### Competitive reality

OpenSplitTime is the most important substitute and potential partner. Experienced race directors also have their own spreadsheets and tacit knowledge. Registration platforms could add similar features. AidStation Ops wins only if it saves planning time and improves procurement/staff decisions enough to justify another vendor.

## 6. Revenue Model

### Pricing to test — assumptions

| Offer | Price | Revenue type | Scope |
|---|---:|---|---|
| Historical operations diagnostic | $750 | One-time | One past event, data review, two-station backtest, gap memo |
| Single-event Forecast Pack | $1,750 | One-time | Up to 3 distances/10 stations, two forecast refreshes, post-race calibration |
| Series Starter | $5,500/year | Recurring | Up to 5 events, common templates, annual calibration, email support |
| Series Pro | $9,000/year | Recurring | Up to 10 events, timing integration, quarterly planning call, priority refresh |
| Timing-partner license, later | $400/event + $2,500/year | Recurring/usage | Branded reports and standardized data import |

Avoid per-runner pricing initially; it makes the service look like a registration competitor and exposes the director to another visible fee.

### First-year scenarios — assumptions

| Scenario | Sales | Revenue | Cash expense | Founder time |
|---|---|---:|---:|---:|
| Conservative | 5 diagnostics + 2 event packs | $7,250 | $2,500 | 180–240 hours |
| Base | 4 diagnostics + 6 event packs + 3 Series Starter subscriptions | $30,000 | $6,000 | 380–500 hours |
| Upside | 4 event packs + 6 Series Starter + 2 Series Pro | $58,000 | $13,000 | 650–800 hours |

Base-case cash contribution before tax and founder labor is about $24,000. The low revenue per customer means custom work must be tightly controlled. The service is unlikely to replace a senior actuarial income without broader event-market expansion or a channel partner.

### Customer value measurement

For each pilot, measure hours of planning avoided, emergency resupplies, leftover units by category, volunteer understaffed hours, and station-level forecast error. A promise of improved safety should not be monetized or made without appropriate expertise and evidence.

## 7. Minimum Viable Product

The MVP is a spreadsheet/Python report, not an app:

1. Choose one public race with at least two years of results and multiple split points, subject to the site's terms.
2. Create a backtest: train on the earlier year and forecast station arrivals in the later year.
3. Publish a sample with anonymized bib IDs, actual-versus-forecast chart, staffing table, inventory assumptions, and error metrics.
4. Ask one director for registration and operations inputs; keep personal fields out.
5. Deliver a $750 historical diagnostic manually and record every repeated transformation.

Do not build live GPS, emergency communications, timing hardware, a mobile app, or weather-alert infrastructure in the MVP.

## 8. Customer Acquisition

### Three routes to the first 10 customers

1. **Direct race-director outreach anchored in a backtest.** Select 30 producers with 4+ events or a large multi-distance ultra. Send a one-page analysis of a public prior-year arrival curve and ask for a 30-minute operations interview. Offer a paid historical diagnostic, not a generic demo.
2. **Timing-company partnerships.** Interview 10 timing providers that serve ultras. Offer to normalize their export once and provide co-branded pre-race reports. A timing company with many clients can reduce acquisition cost and give the forecast legitimate workflow access.
3. **Race-director communities and in-person credibility.** Volunteer at aid stations, attend Running USA/race-management events and regional trail-running gatherings, and contribute a practical “forecast error and buffer” template. Ask organizers and insurers/medical contractors for introductions, but never use volunteer access to collect data without permission.

Paid consumer social ads are a poor fit. The buyer population is small and relationship-driven.

## 9. Startup Requirements

| Category | Requirement / estimate |
|---|---|
| Initial cash | **Assumption:** $2,000–$7,000 for entity/accounting, attorney-reviewed contract and privacy terms, E&O/cyber coverage, domain, hosting, and limited travel |
| Time | 6–10 hours/week during validation; 10–15 hours in the month before several client events |
| Technology | Python/pandas or Polars, DuckDB/Postgres, GitHub, Quarto, lightweight dashboard, encrypted storage, mapping/elevation and weather APIs only after terms review |
| People | Solo for MVP; later a race-operations advisor, UX contractor, and data engineer for integrations |
| Data | Director-authorized registration and split exports; public results only under applicable terms; minimize names, email, birthdate, and medical fields |

### Legal and operational boundaries

Race results are generally not PHI merely because they include performance data, but they can still be personal data. Collect only bib/event/timestamps and coarse attributes needed for the model. Use a data-processing agreement, stated purpose, access controls, retention schedule, deletion process, and contract terms addressing public-data/API rights.

The agreement must state that outputs are planning estimates; the race director, medical director, land manager, and public-safety authorities retain all safety and operational decisions. Carry E&O/cyber coverage. Counsel should review negligence, indemnity, consequential-damage, weather-data, and data-license issues. Never ingest participant medical declarations.

## 10. Risks

| Risk | Why the idea may fail | Mitigation |
|---|---|---|
| Low willingness to pay | Many events run on thin margins, volunteers, and experience. | Target series and large/complex events; demand two paid pilots; price a diagnostic low enough to test but not free. |
| Small market ceiling | Ultra events are a narrow subset and 87% of races in RunSignup's data are under 500 participants.[4] | Build a profitable niche first; expand only later to cycling, gravel, triathlon, relays, and festivals with similar distributed operations. |
| Existing substitutes | OpenSplitTime predicts arrivals and experienced directors have spreadsheets. | Focus on pre-race inventory/staff/transport decisions, integrate with timing, and prove error/time improvements. |
| Sparse/inconsistent data | Courses change, stations move, splits are missed, and weather shifts behavior. | Use ranges, mark comparability, require director review, backtest, and decline false precision. |
| Seasonal workload | Client deadlines cluster around weekends and peak seasons, conflicting with a full-time job. | Cap events, set data deadlines, automate refreshes, partner with an operator, and avoid real-time support. |
| Safety/liability | A director could rely on a bad forecast for water, medical, or cutoff decisions. | Conservative buffers; no safety guarantees; explicit decision ownership; advisor review; insurance; do not replace required plans. |
| Privacy/data rights | Registration exports contain sensitive contact, age, gender, or emergency information; scraping may violate terms. | Field minimization, customer authorization, no scraping without permission, encryption, short retention, and counsel-reviewed terms. |
| Employer conflict/IP | Analytics methods or time could overlap with employment. | Obtain written approval; separate equipment/accounts; use original code and public/event-authorized data; avoid employer vendors and working hours. |
| Reputation | Forecast errors are visible and can alienate a small community. | Publish calibration, explain uncertainty, use a pilot label, invite director overrides, and conduct a blameless post-race review. |
| Integration burden | Every timing export may be different. | Support one CSV schema first, charge for custom mapping, and partner with one timing platform before broad integrations. |

## 11. 30-Day Validation Plan

| Days | Action | Cost | Measurable result |
|---|---|---:|---|
| 1–3 | Confirm employer permission and define data/safety boundaries | $0–$500 | Written go/no-go constraints |
| 2–8 | Interview 5 directors and 2 timers; request real planning sheets, waste/stockout stories, and current spend | $0 | 5 share a repeated operational pain; 2 offer data |
| 5–14 | Build one backtest from permitted historical results and a sample forecast pack | $0–$200 | Station-hour error metrics and 6-page sample |
| 10–20 | Contact 30 qualified series/large-event directors with the sample; ask for 10 interviews | $0–$150 | 8 interviews and 4 data-sharing offers |
| 15–27 | Offer five $500–$750 historical diagnostics and two $1,250 founding event packs | $0 | 2 paid diagnostics or 1 paid event pack |
| 25–30 | Sign contract, collect deposit, document data flow, and schedule delivery | $250–$750 legal template review | Money received; named operations decision the output will change |

### Decision criteria

- **Continue:** 8 qualified interviews, at least 5 identify the same planning failure, 3 share usable data, and either 2 pay for diagnostics or 1 prepays an event pack.
- **Adjust:** directors want the output but will not add a vendor; test a timing-company white-label offer or a $300 self-serve template.
- **Abandon:** no one pays after 30 tailored approaches and 10 interviews, data cannot be used lawfully/reliably, or buyers expect real-time safety support incompatible with a side business.

Month-one cost: **$0–$1,600**. Expected founder time: 45–70 hours.

## 12. Growth Potential

### From service to product

1. **Manual service:** founder cleans data, reviews the course, produces forecasts, and facilitates the operations review.
2. **Standardized imports:** reusable schemas for one or two timing/registration systems, automated backtests, and templated reports.
3. **Series subscription:** customer retains event configurations and updates entrants, course, consumption, and weather scenarios.
4. **Channel distribution:** timing partners and race-management consultants resell reports.
5. **Adjacent endurance events:** gravel cycling, relays, triathlons, and multi-day events if the core workload model transfers.

| Work | Initially tied to founder | Potentially scalable |
|---|---|---|
| Course/station discovery and director judgment | High | Medium with structured intake |
| Data mapping | High | High after integrations |
| Forecast generation/backtesting | Medium | High |
| Operational recommendation review | High | Medium with trained race operators |
| Template or software subscription | Low after build | High |
| Real-time support | Avoid | Low; operationally risky |

The likely best outcome is a small, respected software-enabled service or an acquisition/partnership feature for a timing platform. A standalone venture-scale outcome is unlikely without expansion beyond ultrarunning.

## Sources

1. UltraSignup Help Center, “[What Are the Event Hosting Fees on UltraSignup?](https://help.ultrasignup.com/hc/en-us/articles/30362746490637-What-are-the-event-hosting-fees-on-UltraSignup),” updated September 18, 2024.
2. RunSignup, “[How Much Does RunSignup Cost?](https://info.runsignup.com/2025/07/21/how-much-does-runsignup-cost/),” July 21, 2025.
3. OpenSplitTime, “[About OpenSplitTime](https://www.opensplittime.org/about),” accessed September 12, 2026.
4. RunSignup, “[The 2025 Race Trends Report Is Here](https://info.runsignup.com/2026/02/02/2025-race-trends-report/),” February 2, 2026. Results are based on RunSignup platform data and should not be treated as a census of the industry.
5. OpenSplitTime Documentation, “[Monitoring](https://docs.opensplittime.org/management/monitor/),” accessed September 12, 2026.
6. RunSignup, “[View Graphical Reports](https://help.runsignup.com/support/solutions/articles/17000063215-view-graphical-reports),” accessed September 12, 2026.

## Recommended Next Step

Ask five race directors for the spreadsheet or document they used to plan their last race's busiest aid station. With permission, use one event's prior split data to backtest an arrival forecast and attach a proposed $750 historical diagnostic. Do not build an app unless at least two directors pay and identify a specific staffing, inventory, or transport decision the forecast would change.
