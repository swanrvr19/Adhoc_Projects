# NetSave Assurance

**One-sentence summary:** An independent, productized audit that tells regional health plans how much payment-integrity vendor “savings” became unique, realized value after overlap, fees, leakage, reversals, and administrative cost.

## Executive Summary

NetSave Assurance would serve regional U.S. health plans that already use several prepay and postpay payment-integrity vendors but cannot easily reconcile each vendor's reported savings to the value retained by the plan. The first product is not another claim-edit library. It is a 6–8 week **Vendor Savings Assurance Review** that defines a common savings ledger, maps vendor scope, detects duplicate attribution and exclusions, reconciles identified/accepted/avoided/recovered/retained dollars, calculates fees and reversals, and creates an executive roadmap for renewals and insourcing.

This is a specific and documented industry problem. ZS describes contingency fees, overlapping vendor capabilities, duplicate attribution, administrative reconciliation, and limited transparency; based on its reviews and interviews, it estimates 20%–30% overlap in vendor opportunity inventories.[1] ClarisHealth markets a platform that centralizes vendor inventory, overlap prevention, service-level tracking, and recovery workflow.[2] A 2025 annual filing from Claritev states that payment- and revenue-integrity services are generally priced as a percentage of savings achieved.[3] These sources validate both the economic category and the measurement problem, although vendor-authored claims should not be treated as independent market statistics.

The founder's payment-integrity, claims, program-measurement, actuarial, and data-engineering background is a strong fit. The weakness is launch friction: access to plan data, security review, procurement, professional liability, long sales cycles, and possible employer conflicts make this hard to start casually. The MVP should therefore use aggregate vendor extracts and pseudonymous claim keys inside the plan's environment, not build a hosted PHI platform. One paid diagnostic from a small plan is more meaningful than a sophisticated demo.

> **Evidence convention:** **Verified** facts are linked. Proposed pricing, revenue, expenses, customer counts, value, and time are **assumptions**. CMS improper-payment statistics describe federal program measurement and are not an estimate of recoverable commercial-plan savings.

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

A health plan can receive “savings” reports from claim edits, coding review, coordination of benefits, subrogation, data mining, clinical audit, and recovery vendors. Those reports may use different baselines, lag periods, attribution rules, fee bases, exclusions, reversal treatments, and definitions of success. Two vendors or an internal edit can touch the same claim. Identified dollars may never be accepted or recovered. Prepay avoidance and postpay cash can be mixed. Gross results can conceal contingency fees and internal administrative burden.

### Core product: Vendor Savings Assurance Review

| Workstream | Customer deliverable |
|---|---|
| Contract and definition inventory | Matrix of scope, exclusions, fee basis, SLAs, appeal/reversal terms, and savings definitions for each vendor |
| Common savings ledger | Data dictionary and waterfall from submitted opportunity to unique retained value |
| Overlap and attribution review | Claim/concept/time-level duplicate logic, first-touch/causal attribution options, and disputed-dollar inventory |
| Realization reconciliation | Identified → accepted → avoided/recovered → reversed → retained net of vendor fee and measurable internal cost |
| Cohort and concept analysis | Performance by vendor, concept, claim type, line of business, provider, lag, and disposition |
| Provider-friction indicators | Appeals, overturns, records requested, touches per dollar retained, and time-to-resolution where available |
| Executive decision pack | Renewal scorecards, renegotiation opportunities, insource/retire/test recommendations, and control owners |
| Implementation kit | SQL/Python tests and a monthly close checklist that run in a plan-controlled environment |

The service measures the existing ecosystem. It does not decide medical necessity, issue new claim denials, accuse providers of fraud, replace SIU/legal judgment, or guarantee recoveries.

## 2. Target Customer

### Beachhead

- **Organization:** regional Medicare Advantage, Medicaid managed-care, Blues, or commercial plan with approximately 100,000–1.5 million members, $500 million+ annual claims spend, and at least three internal/external payment-integrity programs.
- **Economic buyer:** CFO, Chief Claims/Operations Officer, or VP of Payment Integrity.
- **Operational champion:** Director of Payment Integrity, vendor-management lead, or claims finance/controller leader.
- **Other stakeholders:** procurement, internal audit, SIU, provider relations, legal, compliance, data engineering, and information security.
- **Trigger:** vendor renewal/RFP, savings miss, executive challenge to reported ROI, duplicate provider outreach, planned insourcing, acquisition/integration, or platform business case.

### Why this segment

National plans can buy enterprise platforms and large consulting teams. Very small plans may lack enough vendor complexity or security capacity. A regional plan with meaningful spend and a fragmented vendor stack can have a decision worth far more than a fixed-fee review while still valuing senior specialist attention.

## 3. Why It Could Work

### Market pain

- ZS identifies exactly the proposed pain: contingency fees, vendor overlap, duplicate recovery attribution, administrative burden, and limited transparency. It estimates 20%–30% overlap in vendor opportunity inventories based on concept reviews and interviews with payment-integrity leaders.[1] **Caution:** this is a consulting firm's estimate, not a universal audited benchmark.
- ClarisHealth says its Pareo platform centralizes claim inventory, exclusion management, overlap prevention, SLAs, and recovery workflow.[2] Its 2026 materials describe growing operational complexity as vendor footprints expand.[4] **Caution:** these are vendor claims.
- Claritev's 2025 annual report states that payment- and revenue-integrity offerings are generally priced as a percentage of savings achieved.[3] That pricing structure makes the definition and attribution of savings financially consequential.
- Cotiviti says it serves more than 100 payer clients in payment accuracy and can ingest claims, eligibility, fee schedules, and contracts across pre- and postpay programs.[5] Machinify reports 85+ customers and a platform spanning payment-integrity interventions.[6] The category is established and crowded.
- CMS estimated FY2025 improper payments of $28.83 billion in Medicare FFS and $23.67 billion in Part C.[7] These figures show the scale and policy attention around payment accuracy, but **do not equal savings available to a private plan** and should never be used to forecast client ROI.

### Willingness to pay

**Assumption:** if a review can support a vendor renewal, avoid duplicate contingency fees, shorten reconciliation, or identify a narrow insourcing case, a regional plan can pay $20,000–$50,000. The value proposition should be expressed as decisions and controlled dollars, not as a promised percent of medical spend.

### Founder advantage

The founder understands claim-level mechanics, program measurement, Medicare finance, forecasting, and the difference between activity, gross savings, realized cash, and net value. Python/Spark/Databricks skills make the analysis reproducible rather than a one-off spreadsheet. Actuarial discipline supports transparent assumptions and credibility, while payment-integrity experience makes vendor fields and operational exceptions legible.

## 4. Existing Examples

| Example | What it validates | How NetSave differs |
|---|---|---|
| [ClarisHealth Pareo](https://www.clarishealth.com/how-we-help/health-plans/) | Health plans buy technology for vendor oversight, overlap prevention, savings workflow, and reporting.[2] | Pareo is an enterprise operating platform. NetSave is an independent, fixed-duration diagnostic and control design for plans not ready to buy/replace a platform. It can help create the platform business case. |
| [ZS payment-integrity advisory](https://www.zs.com/insights/payment-integrity-for-health-plans) | Advisory firms see demand to measure net payment-integrity value, rationalize vendors, and consider insourcing.[1] | NetSave is narrower, fixed-price, and aimed at regional plans. A solo firm lacks ZS's bench and brand, so it must win on focus and senior attention. |
| [Cotiviti Payment Accuracy](https://www.cotiviti.com/solutions/payment-accuracy) | Large payers spend on integrated prepay, postpay, clinical, COB, and FWA programs; vendor scale demonstrates category demand.[5] | Cotiviti finds/prevents/corrects payment errors and is often part of the stack being measured. NetSave does not submit audit findings and should avoid conflicts by not taking contingency fees. |
| [Machinify](https://www.machinify.com/) | Buyers adopt AI-enabled platforms across payment-integrity interventions and value insourced/hybrid/managed models.[6] | NetSave evaluates definitions, net value, and operating controls without requiring a platform migration. |

No cited competitor page publishes comparable project pricing. All proposed NetSave prices are estimates to test.

## 5. Competitive Positioning

### Positioning statement

> “Before you renew, replace, or insource a payment-integrity vendor, know the unique dollars your plan actually kept—and the operational cost of keeping them.”

### Differentiation

1. **Independent economics:** fixed fees, no percentage of “savings,” and no claim-finding product to favor.
2. **Net-value waterfall:** separately report identified, accepted, avoided, recovered, reversed, fee-bearing, and retained dollars.
3. **Small-plan fit:** a 6–8 week review and implementation kit rather than a multi-year platform program.
4. **Code-backed controls:** reproducible reconciliation, tests, and versioned definitions that the plan can keep.
5. **Vendor-neutral decision:** renew, renegotiate, insource, retire, or instrument better—not an automatic recommendation to buy software.

### Barriers to entry

Healthcare claims/domain expertise, contract interpretation, data security, trust, and the ability to challenge vendor savings without disrupting provider relations are meaningful barriers. Over time, anonymized schema mappings, rule taxonomies, reconciliation tests, and benchmark metadata can deepen the moat. Client data and vendor contract terms must not be reused without explicit rights.

### Why a customer might still choose an incumbent

An enterprise platform is better for ongoing workflow orchestration; a national consultancy is better for board-level transformation, large procurement, or broad benchmarking; a payment-integrity vendor is better for generating audit findings. NetSave fits a narrower pre-decision diagnostic.

## 6. Revenue Model

### Offers — assumptions

| Offer | Price | Revenue | Scope |
|---|---:|---|---|
| Savings-definition workshop | $6,000 | One-time | Two sessions, contract/report review, common glossary, executive gap memo; no claim data |
| Vendor Savings Assurance Review | $28,000 | One-time | Up to four vendors, 12 months of aggregate/pseudonymous activity, waterfall, overlap sample, scorecards |
| Additional vendor/LOB | $5,000 | One-time | Extra mapping and reconciliation |
| Monthly assurance close | $4,500/month, 6-month minimum | Recurring | Refresh, exceptions, quarterly scorecard; client-controlled environment |
| RFP/renewal decision support | $15,000–$30,000 | One-time | Metrics, pricing scenarios, scorecard, negotiation support; not legal advice |

Use milestones such as 40% at signature, 30% after data acceptance, and 30% at readout. Do not make fees contingent on findings; independence is the product.

### First-year scenarios — assumptions

| Scenario | Mix | Revenue | Cash expense | Founder time |
|---|---|---:|---:|---:|
| Conservative | 2 workshops + 1 review | $40,000 | $12,000 | 300–420 hours |
| Base | 2 workshops + 3 reviews + 1 six-month close | $123,000 | $30,000 | 650–850 hours |
| Upside, not side-job friendly | 2 workshops + 5 reviews + 2 six-month closes | $206,000 | $55,000 | 1,100+ hours plus contractor capacity |

The base case is attractive but sales timing is uncertain; one delayed security review can move revenue into the next year. A prudent first-year planning range is **$0–$90,000**, with $40,000 as a credible success case. Cash expense excludes tax and founder labor.

### Customer value example — assumption, not promise

If a plan pays $2 million in annual contingency fees and a review supports a 5% reduction in disputed/duplicate/low-value fees, the gross annual decision value is $100,000. This arithmetic illustrates price logic; it is not a market benchmark or forecast.

## 7. Minimum Viable Product

Start with a no-PHI **Savings Definition and Vendor Report Diagnostic**:

1. Customer supplies two redacted contracts, two monthly aggregate vendor reports, and its current savings definitions.
2. NetSave maps fields and shows where identified, accepted, avoided, recovered, reversed, and net retained are conflated.
3. Deliver a standard waterfall, 20-control checklist, and sample vendor scorecard in ten business days.
4. Offer a phase-two, client-hosted overlap analysis using pseudonymous claim keys.

The MVP is a secure analysis and executive readout. Do not build a multi-tenant platform, receive medical records, create audit concepts, or store a full claims warehouse.

## 8. Customer Acquisition

### Three practical routes to the first 10 customers

1. **Trigger-based executive outreach.** Build a list of 40 regional plans and identify vendor renewals, payment-integrity leadership changes, insourcing announcements, or RFPs. Seek warm introductions to the VP of Payment Integrity/CFO and offer the $6,000 workshop. A one-page sample waterfall is more persuasive than a generic capabilities deck.
2. **Non-competing referral partners.** Partner with small actuarial firms, payer procurement advisors, health-plan internal-audit networks, and boutique healthcare attorneys that see vendor-definition disputes but do not implement payment-integrity platforms. Use written conflict and referral disclosures.
3. **Focused industry education.** Publish a rigorous “gross-to-net savings dictionary” and speak to payment-integrity/claims leadership groups. Use ZS/ClarisHealth market claims as hypotheses, clearly attributed, and show a neutral worked example. Never publish vendor-confidential contract terms.

The first ten customers may take 18–30 months because trust, security, and procurement are slow. Paid media is unlikely to help.

## 9. Startup Requirements

| Category | Requirement / estimate |
|---|---|
| Initial cash | **Assumption:** $10,000–$30,000 for entity/accounting, specialist legal review, E&O/cyber insurance, security assessment, encrypted tools, and limited contractor review |
| Time | 8–12 hours/week for selling; 15–25 hours/week during a review; capacity must be capped |
| Technology | Client-hosted Databricks/Snowflake where possible; Python/PySpark/SQL; GitHub Enterprise or client repo; SFTP; no unapproved AI; audit logs and test suite |
| People | Solo for no-data workshop; privacy/security counsel and a senior PI/claims reviewer for full reviews; later data engineer and clinician/coder |
| Contracts | NDA, MSA/SOW, data-use terms, BAA where applicable, subcontractor terms, security exhibit, reliance/limitation language, conflict disclosure |

### HIPAA and security

If the service handles PHI on behalf of a health plan, it will be a business associate in many engagements. HHS says a business-associate contract must define permitted uses, safeguards, breach reporting, subcontractor obligations, return/destruction, and related duties.[8] HHS also states that a cloud provider handling ePHI needs a HIPAA-compliant BAA, even if it only stores encrypted data without the key.[9]

Prefer client-hosted analysis and minimal fields. Pseudonymizing claim IDs does not automatically make data HIPAA-de-identified. HHS recognizes Safe Harbor and Expert Determination methods and notes that de-identification risk is very small, not zero.[10]

## 10. Risks

| Risk | Failure mode | Mitigation |
|---|---|---|
| Enterprise sales friction | Security, legal, procurement, and data access take 6–12 months. | Sell the no-PHI workshop first; partner with an approved vendor; require paid discovery; maintain a multi-client pipeline. |
| Incumbent retaliation/access | Vendors may dispute definitions or restrict contract/data access. | Obtain plan authorization, document lineage, allow factual response, avoid public accusations, and scope counsel review. |
| Measurement ambiguity | Prepay counterfactual, reversals, fee bases, and causal attribution may not be resolvable. | State confidence levels, use alternative attribution rules, separate observed from estimated value, and document unresolved items. |
| Competition | ClarisHealth, national consultancies, and internal audit can do similar work. | Target the pre-platform decision, fixed scope, regional plans, and reusable client-owned controls. |
| HIPAA/privacy/security | Claim IDs, diagnoses, provider/member details, and medical records create breach exposure. | Start aggregate; client-host PHI; sign BAAs; minimum necessary fields; encryption/MFA/logging; incident plan; cyber insurance; no medical records. |
| Professional liability | Executives may rely on dollar estimates in renewal decisions. | Qualified peer review, transparent methods, materiality thresholds, limitations on use, E&O insurance, and applicable actuarial standards. |
| Fraud/legal implications | Findings may touch SIU, legal privilege, provider disputes, or regulatory reporting. | Do not label fraud; define escalation to plan SIU/legal; preserve evidence; obtain counsel on privilege and reporting. |
| Employer conflict | Customers, vendors, data, methods, or opportunities may overlap with the founder's job. | Written employer approval, exclusion list, separate systems/time, clean-room IP, no employer/client solicitation, ongoing conflict checks. |
| IP/vendor terms | Edit logic, contract pricing, and report definitions may be confidential. | Analyze only under client authority; restrict deliverable distribution; keep provenance; never build a cross-client library from protected content. |
| Capacity/burnout | One review can exceed side-job hours, especially near renewals. | Limit data/vendors, use milestones, cap concurrent work at one, contract a reviewer, and decline emergency deadlines. |
| AI confidentiality | Claims/contracts pasted into consumer AI tools can leak or violate terms. | Prohibit unapproved AI, use enterprise/client-approved systems only, redact inputs, log use, and human-review all output. |

## 11. 30-Day Validation Plan

| Days | Actions | Expected cost | Success metric |
|---|---|---:|---|
| 1–5 | Review employment/conflict/IP documents; obtain written clearance; consult healthcare counsel | $500–$2,000 | Permitted target/exclusion list; stop if unclear |
| 3–8 | Build a synthetic two-vendor ledger, waterfall, scorecard, and one-page offer | $0–$250 | Demo reconciles gross to net and one overlap example |
| 6–16 | Conduct 8 interviews: 5 PI leaders, 2 claims finance/internal audit leaders, 1 payer procurement leader | $0 | 5 confirm a recurring reconciliation/attribution problem |
| 8–20 | Request 15 warm introductions and send 25 carefully tailored messages | $0–$150 | 8 qualified meetings and 3 follow-up requests |
| 15–26 | Offer four $3,500 founding workshops, 50% deposit, no PHI | $0 | 2 proposals and 1 signed/deposited workshop |
| 24–30 | Finalize attorney-reviewed MSA/SOW/security boundary and schedule delivery | $1,500–$4,000 | Executable contract and named executive sponsor |

### Decision rules

- **Continue:** 8 qualified interviews, at least 5 can identify an active vendor decision and inconsistent definitions, 2 request proposals, and 1 pays a deposit.
- **Adjust:** pain is strong but procurement blocks a solo vendor; offer through an approved consulting/security partner or target digital-health/TPA vendor finance teams with less PHI.
- **Abandon:** employer conflict cannot be cleared, buyers refuse even a no-data paid workshop, or no proposal request follows 10 qualified interviews and 30 targeted contacts.

Expected 30-day cost is **$2,000–$6,400**. Do not pursue HITRUST/SOC 2 or build hosting until a buyer's procurement process makes it necessary.

## 12. Growth Potential

### Phase 1: diagnostic consultancy

The founder delivers savings workshops and assurance reviews. High value per client but high personal-time, professional-liability, and security dependence.

### Phase 2: managed monthly close

Standardize vendor files, definitions, controls, and exception workflow inside client environments. Retainers create recurring revenue. A senior reviewer and data engineer extend capacity.

### Phase 3: software and benchmark layer

After at least 8–12 similar reviews, build secure connectors, normalized savings events, overlap logic, contract-fee engine, scorecards, and control evidence. Sell an annual license plus implementation. Cross-client benchmarks may use only lawfully permitted, robustly de-identified/aggregated metadata.

| Work | Founder-dependent initially | Scalable later |
|---|---|---|
| Executive interviews and contract interpretation | High | Medium with trained principals |
| Data mapping and reconciliation | High | High after connectors/tests |
| Monthly scorecards | Medium | High through automation |
| Renewal/insourcing judgment | High | Medium |
| Software license | Low after build | High |
| Clinical claim audit | Not offered | Outside the core business |

The concept can become a meaningful software-enabled assurance firm. However, reaching enterprise SaaS scale would require substantial security investment, integrations, implementation staff, and credibility; it is not a bootstrap assumption.

## Sources

1. ZS, “[Payment Integrity: What Health Plans Save and Keep](https://www.zs.com/insights/payment-integrity-for-health-plans),” accessed September 12, 2026.
2. ClarisHealth, “[Pareo for Health Plans](https://www.clarishealth.com/how-we-help/health-plans/),” accessed September 12, 2026.
3. Claritev Corporation, “[2025 Annual Report](https://www.sec.gov/Archives/edgar/data/1793229/000179322926000031/ctev2025report.pdf),” 2026 filing for fiscal 2025.
4. ClarisHealth, “[Have You Hit a Wall Scaling Your Payment Integrity Operation?](https://www.clarishealth.com/blog/scaling-payment-integrity/),” June 4, 2026.
5. Cotiviti, “[Payment Accuracy](https://www.cotiviti.com/solutions/payment-accuracy),” accessed September 12, 2026.
6. Machinify, “[Healthcare Payment Integrity Solutions](https://www.machinify.com/),” accessed September 12, 2026.
7. Centers for Medicare & Medicaid Services, “[Fiscal Year 2025 Improper Payments Fact Sheet](https://www.cms.gov/newsroom/fact-sheets/fiscal-year-2025-improper-payments-fact-sheet),” November 2025.
8. U.S. Department of Health and Human Services, “[Business Associate Contracts](https://www.hhs.gov/hipaa/for-professionals/covered-entities/sample-business-associate-agreement-provisions/index.html),” accessed September 12, 2026.
9. U.S. Department of Health and Human Services, “[Guidance on HIPAA & Cloud Computing](https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/cloud-computing/index.html),” accessed September 12, 2026.
10. U.S. Department of Health and Human Services, “[Guidance Regarding Methods for De-identification](https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html),” accessed September 12, 2026.

## Recommended Next Step

Secure written employer clearance, then create a synthetic two-vendor gross-to-net savings waterfall and show it privately to three payment-integrity leaders. Ask each for a redacted example of the monthly report they cannot reconcile. Offer one no-PHI Savings Definition Workshop for a founding price of $3,500 with a 50% deposit; do not build a platform or request claims until that workshop produces a concrete next-stage data decision.
