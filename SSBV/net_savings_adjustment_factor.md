# Net Savings Adjustment Factor (NSAF)
## Offsetting Outpatient Rebill Payments Against Inpatient Level-of-Care Recoveries

**Status:** Draft for review
**Version:** 0.1
**Date:** August 21, 2026
**Owner:** _[TBD]_
**Applies to:** SSBV savings reporting — post-pay inpatient level-of-care / medical necessity denials

> **Reviewer note:** Placeholders marked _[TBD]_ require input from the business. All numeric values in Sections 6 and 7 are illustrative and are included to demonstrate mechanics only; they are not derived from actual claims data. Please confirm the expansion of "SSBV" for the final version.

---

## 1. Purpose

This document establishes a methodology for adjusting reported savings from post-pay inpatient level-of-care denials to reflect **net** rather than **gross** financial impact. It defines the scenario being corrected, the conceptual basis for the correction, the claim linkage methodology, the calculation of the adjustment factor, the treatment of edge cases, and the governance required to maintain the factor over time.

It also addresses whether and how the correction should be applied to previously reported periods.

---

## 2. Background and Problem Statement

### 2.1 The claim lifecycle

The scenario at issue follows a consistent five-step sequence:

| Step | Event | Financial effect on the plan |
|---|---|---|
| 1 | Provider submits a claim billed as an inpatient admission. | Plan pays the inpatient claim. |
| 2 | Post-pay review determines the admission did not meet inpatient criteria and was inappropriately billed as inpatient. | None yet. |
| 3 | The inpatient claim is denied in full and the payment is recovered post-pay. | Plan recovers the full inpatient payment. |
| 4 | The provider is required to resubmit the services correctly as an outpatient claim. | None yet. |
| 5 | The resubmitted outpatient claim adjudicates and pays. | **Plan pays the outpatient claim.** |

### 2.2 What current reporting captures

Current SSBV savings reporting captures **Step 3 only**. The full inpatient recovery is recorded as savings.

### 2.3 Why this overstates savings

Step 5 is a direct and foreseeable consequence of Step 3. The outpatient claim exists *because* the inpatient claim was denied. Reporting the recovery without the offsetting payment states the gross recovery as if it were the net financial benefit.

The gap is not an error in the recovery figure — the recovery is real and correctly measured. The gap is that reporting stops one step short of the end of the transaction.

**Illustration of a single claim:**

| Line | Amount |
|---|---|
| Inpatient claim — plan paid | $24,500 |
| Inpatient recovery (post-pay) | $24,500 |
| **Savings as currently reported** | **$24,500** |
| Outpatient rebill — plan paid | ($7,350) |
| **True net savings** | **$17,150** |
| Overstatement | $7,350 (30.0%) |

---

## 3. Guiding Principle: the Counterfactual

The correction rests on a single principle that should govern every rule in this document:

> **Reported savings should equal the difference between what the plan actually paid and what the plan would have paid had the review not occurred.**

Applying that test to this scenario:

- **Without the review:** the plan pays the inpatient claim. Nothing else happens.
- **With the review:** the plan pays the inpatient claim, recovers it, and pays the outpatient rebill.
- **Difference:** inpatient payment recovered, less outpatient payment made.

This principle also resolves most edge cases. When a rule is unclear, ask what the plan would have paid absent the review, and measure against that.

**Corollary — attribution is total, not partial.** The outpatient payment is not an unrelated claim that happens to fall nearby. It would not exist absent the denial. Therefore **100%** of the outpatient payment offsets the recovery; there is no basis for offsetting only a portion of it.

---

## 4. Definitions

| Term | Symbol | Definition |
|---|---|---|
| **Gross Recovery** | GR | The plan-paid amount recovered on the denied inpatient claim, measured as **realized** (cash or offset actually collected), not adjudicated. |
| **Outpatient Payment Offset** | OPO | The plan-paid amount on the outpatient claim linked to the denied inpatient claim. |
| **Net Realized Savings** | NRS | GR − OPO. The amount reported as savings under this methodology. |
| **Claim-level Offset Ratio** | *r* | OPO ÷ GR for a single linked claim pair. |
| **Cohort Offset Ratio** | *R* | Σ OPO ÷ Σ GR for a defined cohort of recoveries. |
| **Net Savings Adjustment Factor** | **NSAF** | 1 − *R*. The multiplier applied to gross reported savings to state them net. |
| **Recovery Cohort** | — | The population of inpatient denials grouped by the period in which the recovery was **realized**. |
| **Maturity** | — | Months elapsed between the recovery date and the measurement date. |
| **Rebill Window** | — | The maximum period during which a provider may resubmit the outpatient claim (timely filing or contractual limit). _[TBD — confirm standard and any contract-specific variations]_ |

### 4.1 Measurement basis conventions

Three conventions must be applied consistently on both sides of the calculation, or the factor will be distorted:

1. **Plan-paid, not allowed.** Both GR and OPO are measured net of member cost share. If member cost share on the inpatient claim was refunded and new cost share applied on the outpatient claim, the plan's savings should reflect only the plan's own dollars. _[Decision required — see Section 11.]_
2. **Realized, not adjudicated.** A recovery that is adjudicated but never collected is not savings. GR should reflect collected dollars.
3. **Same currency of time.** GR and its linked OPO are attributed to the **recovery cohort period**, not to the period in which the outpatient claim paid. This keeps the pair together and prevents an offset from landing in a period that never received the corresponding recovery.

---

## 5. Core Methodology

### 5.1 The formulas

**Claim level:**

```
NRS(claim) = GR(claim) − OPO(claim)
```

**Cohort level:**

```
R    = Σ OPO(cohort) ÷ Σ GR(cohort)
NSAF = 1 − R
```

**Applied to reporting:**

```
Adjusted Reported Savings = Gross Reported Savings × NSAF
```

Both forms are used. Claim-level netting is the calculation of record. The cohort-level NSAF is a derived summary statistic used for reporting, trending, forecasting, and for estimating offsets on immature or unmatched populations.

### 5.2 Claim linkage

Claim-level netting requires reliably connecting each denied inpatient claim to its resubmitted outpatient claim. This is the operationally difficult part of the methodology and the primary source of measurement risk.

Linkage should be evaluated in tiers, stopping at the first tier that produces a match:

| Tier | Match basis | Confidence | Treatment |
|---|---|---|---|
| **1** | Explicit reference on the rebilled claim to the original claim number (or a related-claim / adjustment indicator carried by the claims system) | Definitive | Accept |
| **2** | Same member ID + same billing provider (TIN/NPI) + exact match on statement from and through dates | High | Accept |
| **3** | Same member ID + same billing provider + statement dates overlapping within ±3 days, and no other candidate claim | Probable | Accept, flag for periodic audit |
| **4** | Same member ID + same billing provider + service dates within the rebill window, with corroborating clinical or authorization identifiers | Possible | Route to manual review |
| **—** | No candidate found | — | Unmatched — see Section 7 |

**Rules governing linkage:**

- A denied inpatient claim may link to **more than one** outpatient claim (facility outpatient/observation plus separately billed ancillaries). All linked payments are summed into OPO.
- An outpatient claim may be linked to **only one** inpatient denial, to prevent an offset being counted twice.
- Once matched, a pair is **locked**. Subsequent adjustments to either claim flow through as adjustments to the existing pair rather than creating a new match.
- Tier 3 and Tier 4 matches should be sampled and audited at a defined rate to validate precision. _[TBD — sampling rate.]_

**Strong recommendation:** if the plan can require or systematically capture the original claim number on the rebilled outpatient claim, Tier 1 matching becomes the dominant path and measurement risk drops substantially. This is worth pursuing as a parallel operational change, independent of this methodology.

---

## 6. Timing and Completion

### 6.1 The problem

The recovery and its offset do not occur at the same time. A recovery realized in March may not see its outpatient rebill adjudicate until August, or later. A cohort measured too early will show an artificially low offset ratio and an artificially high NSAF.

This creates a direct tension: reporting periods close on a fixed schedule, but the data needed to state them net is not yet complete.

### 6.2 Recommended approach: lag development

Track the cohort offset ratio by months of maturity and develop immature cohorts to an estimated ultimate, in the same manner as a claims lag triangle.

**Illustrative development pattern:**

| Maturity (months since recovery) | Observed cohort offset ratio *R* | Development factor to ultimate |
|---|---|---|
| 3 | 9.4% | 3.064 |
| 6 | 20.5% | 1.405 |
| 9 | 26.0% | 1.108 |
| 12 | 28.3% | 1.018 |
| 15 | 28.7% | 1.003 |
| 18 (treated as ultimate) | 28.8% | 1.000 |

A cohort observed at 6 months maturity with *R* = 20.5% develops to an estimated ultimate of 20.5% × 1.405 = **28.8%**, giving an estimated NSAF of **71.2%**. (This pattern develops to the same ultimate as the fully mature cohort worked through in Section 7.1, and the two examples are intended to be read together.)

### 6.3 Reporting cadence

| Reporting stage | Basis | Label |
|---|---|---|
| Initial close | Observed offsets to date, developed to ultimate | **Estimated net savings** |
| Quarterly refresh | Re-observed at greater maturity, redeveloped | **Estimated net savings (updated)** |
| Final true-up at full maturity | Actual matched offsets, no development | **Final net savings** |

The development pattern must be rebuilt on actual experience once sufficient history exists and refreshed on a defined cadence. The illustrative pattern above is not a substitute for observed data.

### 6.4 Alternative if development is not viable

If insufficient history exists to build a credible development pattern, the fallback is to **hold reporting open** until cohorts reach a defined maturity threshold (e.g., 12 months) before stating savings as final, reporting gross with a clearly disclosed pending-offset note in the interim. This is more accurate but less timely, and it delays recognition. _[Decision required — see Section 11.]_

---

## 7. Treatment of Unmatched Recoveries

Not every recovery will link to an outpatient payment. The unmatched population must be decomposed, because the categories have opposite implications.

| Category | Description | Correct offset |
|---|---|---|
| **A — Not yet rebilled** | Rebill window still open; the outpatient claim has not yet been submitted or adjudicated. | Estimate via development (Section 6). |
| **B — Never rebilled** | Rebill window has closed with no submission, or the provider wrote off the claim. | **Zero.** The full recovery is genuine net savings. |
| **C — Rebilled but unmatched** | An outpatient claim exists but linkage failed due to data limitations. | Estimate using the matched-population offset ratio. |
| **D — Denial overturned** | The inpatient denial was reversed on appeal. | Not an unmatched recovery — see Section 8. |

Category B is the reason a blanket factor applied to all recoveries would be wrong. Where the provider never rebills, gross recovery *is* net savings, and reducing it would understate performance just as surely as the current method overstates it.

### 7.1 Illustrative cohort calculation

**Cohort:** recoveries realized Q1 2026, measured at full maturity.

| Component | Claims | Gross Recovery | Offset applied | Basis |
|---|---|---|---|---|
| Matched (Tiers 1–4) | 375 | $7,500,000 | $2,700,000 | Actual linked outpatient payments |
| Category B — never rebilled | 100 | $2,000,000 | $0 | No outpatient claim exists |
| Category C — rebilled, unmatched | 25 | $500,000 | $180,000 | Matched ratio (36.0%) applied |
| **Total** | **500** | **$10,000,000** | **$2,880,000** | |

```
R    = $2,880,000 ÷ $10,000,000 = 28.8%
NSAF = 1 − 0.288 = 0.712  (71.2%)

Net Realized Savings = $10,000,000 × 0.712 = $7,120,000
```

Note the distinction between the two ratios in this example. The offset ratio **within the matched population** is 36.0% ($2,700,000 ÷ $7,500,000). The **cohort-wide** offset ratio is 28.8%, lower because Category B carries no offset. Reporting must be explicit about which ratio is being cited; conflating them is the most likely analytical error in this methodology.

---

## 8. Business Rules and Edge Cases

| # | Scenario | Treatment | Rationale |
|---|---|---|---|
| 1 | **Denial overturned on appeal** | Reverse the recovery from savings **and** reverse the associated outpatient payment offset. If the outpatient payment was not recouped from the provider, it remains a plan cost and savings for that claim are negative. | Counterfactual: absent the review the plan pays the inpatient claim once. If it ends up paying both, the review produced a loss. |
| 2 | **Partial denial** (e.g., DRG downgrade rather than full level-of-care denial) | Out of scope for this factor. Applies only to full inpatient denials followed by outpatient rebill. | Different mechanic; no rebill occurs. |
| 3 | **Outpatient payment exceeds inpatient recovery** | Record the negative net savings; do not floor at zero. | Flooring biases the factor and conceals cases where the review destroys value. Disclose separately if material. |
| 4 | **Interim / split inpatient billing** (multiple claims for one stay) | Aggregate all claims for the stay into a single recovery unit before matching. | Prevents partial matching and double counting. |
| 5 | **Multiple outpatient claims from one denial** | Sum all linked outpatient payments into OPO. | Full attribution per Section 3. |
| 6 | **Recovery adjudicated but not collected** | Exclude from GR until realized. | GR is defined on a realized basis. |
| 7 | **Recovery collected via future-claim offset rather than cash** | Include in GR at the point of offset. | Economically equivalent to cash. |
| 8 | **Member cost share differs between the inpatient and outpatient claims** | Measure both GR and OPO on a plan-paid basis. | Member dollars are not plan savings. |
| 9 | **Plan is secondary (COB)** | Measure the plan's own liability on both sides. | Same principle as #8. |
| 10 | **Provider disputes but does not formally appeal; rebill window lapses** | Category B — no offset. Monitor for late appeals. | No outpatient payment was made. |
| 11 | **Interest, penalties, or prompt-pay obligations attached to the recovery or the rebill** | Include in the relevant side if the plan actually paid or received them. | Real cash effects. |
| 12 | **Recovery vendor contingency fees** | Out of scope for this factor; handle in a separate fee adjustment if savings are reported net of fees. | Keep adjustments single-purpose and independently auditable. |
| 13 | **Claim voided or replaced rather than denied and rebilled** | Treat as the same event pattern if the net effect matches; confirm the claims system representation. _[TBD]_ | Substance over form. |
| 14 | **Self-funded (ASO) vs. fully insured business** | Apply the same methodology; stratify reporting by funding arrangement. | The factor is likely to differ, and client-facing reporting obligations differ. |

---

## 9. Stratification

A single global factor will mask meaningful variation and will drift as mix changes. The offset ratio should be calculated and monitored at minimum by:

- **Line of business** (Commercial / Medicare Advantage / Medicaid)
- **Funding arrangement** (ASO vs. fully insured)
- **Facility contract type** (DRG vs. per diem vs. percent-of-charges) — the relationship between inpatient and outpatient reimbursement varies sharply by contract structure, making this the strongest expected driver of variation
- **Review type / vendor**, if more than one program generates these denials
- **Market or region**, if contracting varies materially

Where a stratum lacks credible volume, blend it toward the aggregate factor using a stated credibility standard. _[TBD — credibility threshold and blending method.]_

---

## 10. Application to Reporting

### 10.1 Prospective application

Effective _[TBD]_, SSBV savings reporting for this denial category should present three lines rather than one:

| Line | Description |
|---|---|
| Gross Inpatient Recovery | Unchanged from current reporting |
| Less: Outpatient Rebill Offset | New |
| **Net Realized Savings** | **New — the headline savings figure** |

Retaining the gross line preserves comparability with historical reporting, makes the adjustment transparent and auditable, and avoids the appearance that recovery performance declined when only the measurement basis changed. Do not replace the gross figure with the net figure alone.

### 10.2 Restatement of prior periods

Whether to restate prior reported savings is a decision for _[TBD — finance / program leadership]_. The relevant considerations:

**Arguments for restating:**

- Prior figures are overstated on a known, measurable, and directional basis.
- Trend comparisons between restated and unrestated periods are not meaningful; the year-over-year change would blend a real performance change with a methodology change.
- If prior savings figures were reported externally — to clients, regulators, or in support of contractual guarantees — the exposure from not correcting them may exceed the exposure from correcting them.
- The correction can be computed from historical data using the same claim linkage logic.

**Arguments against restating:**

- Historical claim linkage may be less reliable, particularly if the original claim reference was not captured in earlier periods; a restatement built on weak matching substitutes one measurement error for another.
- Restatement is a material effort with no forward-looking benefit if the amounts are immaterial.
- Prior figures may already be embedded in settled financials, executed contracts, or completed incentive calculations, where reopening carries its own cost.

**Recommended path:**

1. Quantify first. Compute the historical offset for the trailing _[TBD — suggest 24]_ months using the claim linkage logic in Section 5. This is required regardless, since it is also the source of the development pattern in Section 6.
2. Assess materiality against a stated threshold and identify every downstream use of the historical figures.
3. Decide restatement scope based on that quantification — not before it.
4. Whatever is decided, **disclose the methodology change** in the first reporting period in which the net basis appears, with a bridge from the prior basis to the new basis so that the trend break is explainable.

Deciding restatement before quantification risks either an unnecessary restatement or an uninformed decision not to restate.

---

## 11. Open Decisions

| # | Decision | Owner | Notes |
|---|---|---|---|
| 1 | Confirm SSBV definition and reporting audience | _[TBD]_ | Affects tone and disclosure requirements of final document |
| 2 | Plan-paid vs. allowed basis for GR and OPO | _[TBD]_ | Section 4.1; recommend plan-paid |
| 3 | Lag development vs. hold-open reporting | _[TBD]_ | Section 6; recommend development with quarterly true-up |
| 4 | Maturity threshold treated as ultimate | _[TBD]_ | Section 6; suggest 12–18 months, confirm against rebill window |
| 5 | Restatement scope | _[TBD]_ | Section 10.2; quantify before deciding |
| 6 | Effective date for prospective application | _[TBD]_ | Section 10.1 |
| 7 | Stratification levels for production reporting | _[TBD]_ | Section 9 |
| 8 | Factor refresh cadence | _[TBD]_ | Recommend quarterly recalculation, annual formal revalidation |
| 9 | Audit sampling rate for Tier 3/4 matches | _[TBD]_ | Section 5.2 |
| 10 | Feasibility of capturing original claim number on rebills | _[TBD]_ | Section 5.2; highest-leverage operational improvement available |

---

## 12. Governance and Controls

**Ownership.** A named owner is accountable for the factor's calculation, documentation, and refresh. _[TBD]_

**Refresh cadence.** Recalculate the cohort offset ratio and development pattern quarterly. Perform a formal revalidation annually, or sooner if a trigger below is hit.

**Recalibration triggers.**

- Observed offset ratio moves more than _[TBD]_ percentage points from the ratio in use.
- Material change in facility contracting terms or outpatient fee schedules.
- Material change in denial volume, mix, or review criteria.
- Change in the rebill window or timely filing standards.

**Validation controls.**

1. Reconcile GR to the claims and recovery systems of record independently of the savings report.
2. Sample-audit Tier 3 and Tier 4 matches at the defined rate; report precision.
3. Monitor the unmatched rate over time — a rising unmatched rate signals linkage degradation, not improved provider behavior, and must be investigated rather than accepted.
4. Compare estimated (developed) offsets to actual offsets at each true-up and track estimation error. Persistent bias in one direction indicates the development pattern needs rebuilding.
5. Independent review of the factor calculation prior to each reporting cycle.

**Documentation.** Retain the factor calculation, source data extract, and match results for each reporting period sufficient to allow an independent party to reproduce the reported figure.

---

## Appendix A — Required Data Elements

| Element | Source | Purpose |
|---|---|---|
| Original inpatient claim number | Claims | Linkage Tier 1 |
| Member identifier | Claims | Linkage Tiers 2–4 |
| Billing provider TIN / NPI | Claims | Linkage Tiers 2–4 |
| Statement from / through dates | Claims | Linkage Tiers 2–4 |
| Admission and discharge dates | Claims | Stay aggregation (Edge case #4) |
| Inpatient plan-paid amount | Claims | GR |
| Recovery amount, date, and method (cash vs. offset) | Recovery system | GR, cohort assignment |
| Recovery status (adjudicated vs. realized) | Recovery system | GR realized basis |
| Bill type / place of service on rebill | Claims | Confirms outpatient status |
| Outpatient plan-paid amount and paid date | Claims | OPO, maturity measurement |
| Member cost share, both claims | Claims | Plan-paid basis |
| Appeal status and outcome | Appeals system | Edge case #1 |
| Line of business, funding arrangement, contract type | Enrollment / contracting | Stratification |
| Review type / vendor identifier | Program data | Stratification |

---

## Appendix B — Summary of the Correction

| | Current method | Proposed method |
|---|---|---|
| Measures | Gross inpatient recovery | Gross recovery less linked outpatient payment |
| Reflects | One step of a five-step transaction | The completed transaction |
| Direction of error | Overstates savings | — |
| Magnitude | Equal to the outpatient payment | — |
| Reported as | Single savings figure | Gross, offset, and net |
