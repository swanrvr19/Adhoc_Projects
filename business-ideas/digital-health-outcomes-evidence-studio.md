# ProofStack Health

**One-sentence summary:** A productized evidence-design and ROI-measurement service that helps growth-stage digital-health vendors turn imperfect pilot data into buyer-credible outcomes plans, claims, and performance-contract terms.

## Executive Summary

ProofStack Health would sell a focused **Evidence Readiness Sprint** to U.S. digital-health companies that already sell—or are trying to sell—to self-funded employers and health plans. The buyer is usually a Chief Medical Officer, Head of Outcomes, VP of Health Economics, or commercial leader who needs to answer a purchaser's difficult questions: What population is eligible? What is the counterfactual? Are savings gross or net of program fees? How will regression to the mean, selection, credibility, and runout be handled? What portion of fees can safely be placed at risk?

The initial product is not an academic study and does not promise independent validation. It is a buyer-readiness package: an auditable measurement specification, metric dictionary, data-feasibility review, financial model, performance-guarantee term sheet, and reproducible Python/SQL analysis skeleton. A later service can execute the measurement in a client-controlled environment. This boundary makes the concept launchable alongside a full-time role and reduces the need to hold protected health information (PHI) during validation.

The demand signal is unusually direct. In a 2025 survey of 309 U.S. digital-health purchasing decision-makers, Peterson Health Technology Institute (PHTI) reported that buyers wanted evidence of improved outcomes and lower cost; nearly half were already using performance-based contracts, and most planned to use them in the following year.[1] The weakness is sales access: early digital-health firms often have limited budgets, long enterprise sales cycles, and founders who prefer optimistic marketing claims to rigorous measurement. The best test is therefore to pre-sell two fixed-scope sprints before building software.

> **Evidence convention:** Statements labeled **Verified** are supported by linked sources. Prices, conversion rates, revenue, cost, and time estimates labeled **Assumption** are planning hypotheses, not market facts.

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

Employer and health-plan buyers increasingly demand clinical and financial evidence, while many Series A–C digital-health vendors have data but not a defensible evaluation design. Their internal dashboards often report enrolled-user engagement, pre/post change, or modeled savings without adequately addressing selection, attrition, trend, credibility, program fees, or the correct comparison group. Weak evidence can stall an RFP, create an unpriceable performance guarantee, or produce a claim that is later challenged.

### The product

The core deliverable is a four-week **Evidence Readiness Sprint**:

| Deliverable | What the customer receives |
|---|---|
| Buyer-claim audit | A red/yellow/green inventory of every outcomes, savings, engagement, and ROI claim in sales materials |
| Measurement charter | Population, index date, baseline/follow-up windows, comparator, attribution, exclusions, runout, credibility, and sensitivity tests |
| Data feasibility map | Required fields, source system, grain, refresh cadence, missingness tests, and data-owner questions |
| Metric dictionary | Numerators, denominators, code sets, allowable stratifications, and version control |
| Financial model | Gross savings, program fees, implementation costs, net savings, ROI, confidence ranges, and break-even cases |
| Contract design | Recommended at-risk metrics, thresholds, corridors, caps, data latency provisions, and dispute rules |
| Reproducible starter kit | Client-specific Python/SQL notebook skeleton, test fixtures using synthetic data, and QA checklist |
| Executive readout | A buyer-facing evidence brief and a 60-minute working session with clinical, analytics, finance, and sales leaders |

An optional second phase executes the protocol inside the client's HIPAA-appropriate environment. ProofStack should initially avoid marketing language such as “validated,” “certified,” or “independent actuarial opinion” unless the engagement and credentials actually satisfy those claims.

## 2. Target Customer

### Initial beachhead

- **Company:** U.S. digital-health vendor with approximately $3 million–$50 million in annual revenue, an employer or payer channel, and at least one completed pilot.
- **Clinical segments:** virtual musculoskeletal care, cardiometabolic care, behavioral health, navigation, kidney care, women's health, and condition-management vendors whose value proposition includes avoided medical spend.
- **Economic buyer:** Chief Medical Officer, Chief Analytics/Data Officer, VP/Head of Outcomes or Health Economics; at smaller firms, the CEO or Chief Commercial Officer.
- **Internal champions:** director of analytics, payer partnerships lead, actuary, or sales engineer preparing for an RFP or renewal.
- **Trigger events:** a large prospect asks for an ROI methodology; an employer pilot is about to start; a renewal includes fees at risk; fundraising diligence exposes evidence gaps; or an outside validator requests better documentation.

### Explicit exclusions at launch

Do not initially target pre-revenue wellness apps with no usable data, pharmaceutical HEOR studies requiring specialized clinical/regulatory infrastructure, or mature public companies that expect a large consulting bench and formal attestations.

## 3. Why It Could Work

### Verified demand and trend evidence

- **Purchasers are still spending, but are more demanding.** PHTI's August 2025 survey covered 309 decision-makers. It reported that 84% of health plans and 79% of health systems had increased digital-health investment over the prior two years; 68% of employers maintained spending. It also found that 75% of contracts lasted two years or less and more than half of respondents reviewed offerings annually.[1]
- **Outcome-linked contracting is moving into the mainstream.** The same PHTI release states that nearly half of purchasers were using performance-based contracts and a majority planned to use them in the next year.[1]
- **Evidence standards are becoming more explicit.** PHTI evaluates clinical benefits and economic impact, and its published framework treats clinical effectiveness and economic impact as primary domains, informed by user experience, equity, privacy, and security.[2][3]
- **Employers want accountable analytics.** Business Group on Health has described employer interest in dashboards, vendor accountability, pilots, data-sharing, and privacy governance.[4]

These facts establish a problem, not willingness to buy this exact offer. **Assumption:** a vendor facing a $500,000–$2 million enterprise contract or renewal can rationally spend $7,500–$25,000 to improve evidence design and reduce contract risk. This must be confirmed in interviews and paid pilots.

### Founder advantage

The proposed founder can combine actuarial credibility, claims analytics, program measurement, financial modeling, and practical Python/Databricks implementation. Many competitors lean primarily clinical, academic, benefits-consulting, or marketing. The combination is valuable because a purchaser's question is usually both methodological and financial: “Did outcomes change?” and “Did the change create net, attributable savings under our contract?”

## 4. Existing Examples

| Example | What it validates | How ProofStack differs |
|---|---|---|
| [Validation Institute](https://resources.validationinstitute.com/) | A commercial market exists for third-party verification of savings, outcomes, metrics, and contractual integrity. Its site also offers a startup pathway and credibility guarantees.[5] | ProofStack is the preparatory layer before formal validation: hands-on protocol, data engineering specification, economics, and code. It would not issue a certification or guarantee. |
| [Peterson Health Technology Institute](https://www.phti.org/about-us/) | Purchasers value rigorous, independent assessment of digital health's clinical and economic impact.[2] | PHTI assesses categories and products for public decision support. ProofStack would be a paid, client-specific build service that helps a vendor design evidence and contracts before or during pilots. |
| [Milliman health actuarial consulting](https://www.milliman.com/en/health/actuarial-consulting) | Established actuarial firms sell health-program ROI, claims analysis, cost modeling, and validation capabilities.[6] | ProofStack would be narrower, faster, fixed-price, and designed for growth-stage vendors that cannot justify a broad consulting engagement. |

Competitor service prices are generally not published on the cited pages. Any ProofStack price below is therefore an **estimate to test**, not a claim about the competitors' price.

## 5. Competitive Positioning

### Positioning statement

> For digital-health vendors entering employer and payer procurement, ProofStack turns a pilot and a value story into a buyer-auditable measurement and performance-contract package—without requiring a six-figure research engagement or moving raw claims data into a new platform.

### Differentiation

1. **Narrow buyer moment:** RFP, pilot design, renewal, or performance guarantee—not generic analytics consulting.
2. **Actuarial plus engineering:** connect attribution and credibility choices to actual contract dollars, then express them in reproducible code and tests.
3. **Client-controlled data:** start with metadata, aggregate results, synthetic fixtures, and code that runs in the client's environment.
4. **Fixed artifacts and deadline:** a four-week decision product, not an open-ended staff-augmentation engagement.
5. **Claim restraint:** show uncertainty, net out fees, disclose assumptions, and distinguish forecast from observed impact.

### Barriers to entry

The first barrier is trusted judgment across claims, actuarial finance, causal measurement, and enterprise contracting. Over time, a proprietary library of measurement patterns, claims code mappings, test suites, benchmark structures, and anonymized failure modes becomes a stronger barrier. The service is initially easy to imitate in presentation; the defensibility must come from execution quality, references, and reusable intellectual property.

### Why customers would not simply hire an established firm

ProofStack is credible only where the customer values speed, senior attention, and a fixed scope more than brand name, formal certification, or large-team capacity. Customers needing an attestation, peer-reviewed publication, regulatory submission, or globally recognized validation should choose an established specialist. ProofStack should partner with, rather than pretend to replace, those firms.

## 6. Revenue Model

### Offer ladder — assumptions to validate

| Offer | Price | Revenue type | Customer value |
|---|---:|---|---|
| Evidence diagnostic | $2,500 | One-time | Two workshops, claim audit, and prioritized gap memo; credited toward a sprint |
| Evidence Readiness Sprint | $9,500 | One-time | Full four-week package using aggregate or synthetic data |
| Measurement execution | $18,000–$35,000 | One-time | Implement and QA a pilot analysis in the client's approved environment |
| Evidence office hours | $1,750/month, 3-month minimum | Recurring | RFP responses, result reviews, contract-metric support, and two calls per month |
| Template/code license, later | $6,000–$15,000/year | Recurring | Governed metric library, notebook tests, version updates, and team access |

Do not charge a percentage of claimed medical savings during the first year; it creates incentives that conflict with independent measurement. Use fixed fees and clearly disclose that the client funds the work.

### First-year scenarios — all assumptions

| Scenario | Sales mix | Revenue | Direct cash expense | Founder time |
|---|---|---:|---:|---:|
| Conservative | 3 diagnostics + 2 sprints | $26,500 | $6,000 | 260–350 hours |
| Base | 3 diagnostics + 5 sprints + 2 clients × 3 months office hours | $65,500 | $12,000 | 520–650 hours |
| Upside, capacity-constrained | 2 diagnostics + 7 sprints + 2 execution projects + 2 retainers × 6 months | about $128,500 | $25,000 | 850–1,050 hours; likely incompatible with a demanding full-time job |

The base case is approximately 10–12 hours per week over a year. It is revenue, not profit, and excludes income tax and the economic value of the founder's time. A realistic side-business target is **$25,000–$65,000 revenue**, not the upside case.

## 7. Minimum Viable Product

Build no SaaS product. Create:

1. A one-page offer with the exact buyer, trigger, outputs, timeline, exclusions, and $7,500 founding-client price.
2. A synthetic-data demonstration for one use case, such as virtual MSK: eligibility funnel, matched-comparison specification, PMPM trend, net-savings waterfall, and three sensitivity cases.
3. A sample eight-page evidence brief with every number labeled observed, modeled, benchmarked, or assumed.
4. A secure intake questionnaire that requests no PHI for the diagnostic.
5. A standard MSA/SOW, NDA, limitation-of-liability language, disclosure of independence, and an approved software list.

The MVP succeeds when two qualified buyers pay for a sprint. Compliments, email signups, and requests for free advice are not validation.

## 8. Customer Acquisition

### Three practical paths to the first 10 customers

1. **Trigger-based founder outreach.** Build a list of 60 Series A–C vendors that recently announced an employer/plan customer, outcomes report, funding round, or performance guarantee. Email the CMO/Head of Outcomes with one specific observation about the published measurement method and offer a 25-minute “buyer-objection teardown.” Never imply access to confidential employer knowledge.
2. **Referral partners.** Approach five benefits brokers/consultants, digital-health accelerators, fractional CMOs, healthcare law firms, and formal validation organizations. Offer a clearly bounded pre-validation/data-readiness package they can refer without competing with their core service. Use a transparent referral arrangement; avoid contingency incentives that undermine independence.
3. **Evidence-led professional content.** Publish four technically useful LinkedIn posts and one downloadable checklist: net versus gross savings, comparator traps, minimum claims runout, performance-guarantee metric design, and a synthetic notebook. Present the material to digital-health founder communities and healthcare analytics groups; end with a fixed offer, not a generic “contact me.”

The sequence should be relationship-led. Paid search is unlikely to work for ten high-trust, low-volume B2B sales.

## 9. Startup Requirements

| Item | Initial requirement |
|---|---|
| Cash | **Assumption:** $4,000–$12,000 before first PHI engagement: entity/accounting, attorney-reviewed agreements, professional/E&O and cyber insurance, domain/site, design, and secure collaboration tools |
| Time | 8–12 hours/week during validation; 12–18 hours/week while delivering a sprint |
| Technology | GitHub private repositories; Python, SQL, Quarto/Jupyter; synthetic test data; encrypted storage; video calls; project tracking; optionally client-hosted Databricks |
| People | No partner for MVP. Contract a healthcare/privacy attorney and, when needed, a biostatistician/clinician or credentialed actuary with the relevant qualification |
| Quality system | Versioned methods, peer review checklist, automated tests, documented assumptions, result reconciliation, and retention/deletion policy |

### Legal, professional, and data boundaries

If ProofStack creates, receives, maintains, or transmits PHI for a covered entity or business associate, it may become a business associate and will need appropriate contracts and safeguards. HHS explains that cloud providers handling ePHI also require a HIPAA-compliant BAA, even when the provider lacks the encryption key.[7] HHS recognizes Safe Harbor and Expert Determination as the two HIPAA de-identification methods.[8]

Start with aggregate or de-identified inputs, but do not casually declare a dataset de-identified. If PHI becomes necessary, use a signed BAA, minimum-necessary access, client-approved infrastructure, encryption, access logging, a risk assessment, incident response, subcontractor terms, and cyber coverage. Obtain counsel on state privacy laws and any FTC obligations relevant to the client's consumer-health data.

## 10. Risks

| Risk | Why it could fail | Mitigation |
|---|---|---|
| Weak willingness to pay | Prospects may agree evidence matters but reserve budget for sales or product. | Require a paid diagnostic; target firms with an active RFP/renewal and a named budget owner. Abandon if 15 qualified conversations produce no paid pilot. |
| Credibility gap | A solo firm may not satisfy a national employer or health plan. | Sell preparation, not certification; publish methods; use peer reviewers; partner for formal validation. |
| Long sales/procurement cycle | Vendor security and legal review can erase side-business economics. | Keep the first sprint PHI-free and fixed-scope; target the digital-health vendor rather than the ultimate plan. |
| Data quality/causal overclaim | Bad eligibility, selection, low credibility, and missing runout can invalidate conclusions. | Pre-register the measurement plan; show sensitivity ranges; reject unsupported savings claims; use independent review. |
| HIPAA/privacy/security | Claims data can create business-associate and breach exposure. | Default to aggregate/client-hosted data, execute BAAs where applicable, minimize/segregate access, and document deletion. |
| Professional liability | A financial model may be treated as actuarial advice or an opinion. | Define scope and intended users; follow applicable actuarial standards; do not issue opinions outside qualifications; carry E&O coverage. |
| Intellectual property | Employer code, methods, code sets, or prior-employer material could be reused improperly. | Build from public sources and clean-room original work; maintain source/provenance logs; obtain IP counsel for ambiguous assets. |
| Employer conflict | The side business could compete with the employer, serve clients/prospects, use work time, or violate moonlighting/IP rules. | Obtain written approval before outreach; exclude employer clients and prospects; use separate hardware/accounts; log work and sources. |
| Reputation conflict | Being paid by the vendor can undermine “independence.” | Say “vendor-sponsored evidence design,” disclose funding, separate readiness work from independent validation, and never guarantee favorable results. |
| AI misuse | Public AI tools could retain confidential claims, contracts, or code. | Ban client data in unapproved tools; use enterprise terms and client approval; review every generated artifact and maintain an AI-use policy. |

## 11. 30-Day Validation Plan

| Days | Actions | Expected cost | Measurable output |
|---|---|---:|---|
| 1–4 | Review employment agreement and conflict policy; define exclusion list; have a short attorney consultation if unclear | $0–$750 | Written go/no-go boundary before market contact |
| 3–8 | Create one-page offer, synthetic case, claim-audit scorecard, interview script, and founding price | $50–$250 | Shareable sample and landing page |
| 6–12 | Build 60-company list and identify 30 trigger events; request 15 warm introductions | $0–$150 | 45 personalized contacts sent |
| 10–24 | Conduct 12–15 interviews with Heads of Outcomes/CMOs; ask for actual artifacts and buying process, not opinions | $0 | At least 8 conversations with qualified companies |
| 15–27 | Offer five fixed-scope paid diagnostics at $1,500 or two founding sprints at $7,500 | $0 | Written proposals and objections log |
| 25–30 | Close, invoice, and schedule; revise scope based on objections | $0–$300 | Signed SOW and deposit |

### Decision rules

- **Continue:** at least 10 qualified interviews, 3 request proposals, and either 2 paid diagnostics or 1 paid sprint with a deposit; at least 60% rank evidence/RFP measurement among their top three commercial obstacles.
- **Adjust:** interviews validate pain but no purchase; narrow to one trigger (for example, performance-guarantee design) or one category and retest pricing for two weeks.
- **Abandon or pause:** fewer than 6 of 15 qualified prospects recognize an urgent problem, no proposal requests after 40 personalized contacts and 10 interviews, or employer restrictions make the target market impractical.

Budget for the month: **$100–$1,450**, depending mainly on legal review. Do not buy claims data or build a hosted platform during validation.

## 12. Growth Potential

### Phase 1: expert-led service

The founder sells and delivers diagnostics, sprints, and selected execution projects. Revenue is high-value but directly constrained by time. Templates improve margin, but the business remains consulting.

### Phase 2: standardized evidence operating system

After 10–15 engagements in one or two clinical categories, convert repeated components into a governed metric library, claims code modules, contract-term library, automated quality tests, and buyer-facing report generator. Sell annual team licenses plus implementation. The software must be based on repeated demand, not imagined requirements.

### Phase 3: partner network and benchmarks

Credentialed reviewers and implementation partners deliver category-specific modules. With client permission and robust de-identification, aggregate metadata can support benchmarks such as typical runout, engagement funnels, and metric feasibility—never pool or resell client data without explicit rights and expert privacy review.

| Work type | Initially dependent on founder time | Can eventually scale without founder |
|---|---|---|
| Interviews, scoping, executive judgment | High | Partly, through trained principals |
| Evidence protocol and financial model | High | Medium, via patterns and QA rules |
| Code generation and data QA | Medium | High, via tested libraries and client-run connectors |
| Education/templates | Low after creation | High, through licenses and cohorts |
| Formal independent validation | Not offered | Only through a structurally independent partner/entity |

The plausible scalable company is a software-enabled evidence consultancy, not a fully self-serve SaaS tool in year one. A narrow market and trust-heavy sale probably cap growth below a horizontal analytics platform, but specialization can support attractive margins.

## Sources

1. Peterson Health Technology Institute, “[PHTI Survey Reveals Digital Health Purchasers’ Priorities](https://www.phti.org/announcement/phti-survey-reveals-digital-health-purchasers-priorities/),” October 15, 2025.
2. Peterson Health Technology Institute, “[About Us](https://www.phti.org/about-us/),” accessed September 12, 2026.
3. ICER and PHTI, “[Value Assessment Framework for Digital Health Technologies](https://pmc.ncbi.nlm.nih.gov/articles/PMC10734316/),” 2023.
4. Business Group on Health, “[Leveraging Technology and Data for Improved Outcomes](https://www.businessgrouphealth.org/Resources/2025-Conference-Insights-Leveraging-Technology-and-Data),” May 29, 2025.
5. Validation Institute, “[Get the Right Validation for Your Organization](https://resources.validationinstitute.com/),” accessed September 12, 2026.
6. Milliman, “[Health Actuarial Consulting](https://www.milliman.com/en/health/actuarial-consulting),” accessed September 12, 2026.
7. U.S. Department of Health and Human Services, “[Guidance on HIPAA & Cloud Computing](https://www.hhs.gov/hipaa/for-professionals/special-topics/health-information-technology/cloud-computing/index.html),” accessed September 12, 2026.
8. U.S. Department of Health and Human Services, “[Guidance Regarding Methods for De-identification of Protected Health Information](https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html),” accessed September 12, 2026.

## Recommended Next Step

Before creating a company name, website, or codebase, obtain written employer clearance and schedule five 25-minute conversations with Heads of Outcomes at digital-health vendors currently entering an employer RFP or negotiating a performance guarantee. Bring a one-page sample measurement charter and ask one prospect to buy a $1,500 diagnostic. A paid “yes” is the smallest credible signal that this should become a business.
