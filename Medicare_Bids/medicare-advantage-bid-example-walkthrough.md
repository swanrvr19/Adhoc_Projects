# Building an MA Bid: A Worked Example

**Cascade Health Plan HMO — CY2027 bid, submitted June 1, 2026**

*Companion to `medicare-advantage-bid-example.xlsx`. Every number below is produced by that workbook and recalculates if you change an input. All figures are hypothetical and constructed to teach the mechanics — none is drawn from an actual filed bid.*

---

## The plan we're pricing

| | |
|---|---|
| Product | MA-only HMO, single PBP |
| Service area | One county (illustrative) |
| Projected enrollment | 10,000 members / 120,000 member months |
| Base experience year | CY2025 |
| Contract year | CY2027 |
| Star rating driving CY2027 QBP | 4.0 |

One thing to fix at the outset: **the plan already knows its Star rating when it bids.** The CY2027 quality bonus is driven by the 2026 Star Ratings, published October 2025 — eight months before the June 2026 bid deadline. Stars are an input to this calculation, not a risk in it. The uncertainty is in *next* year's bid.

The projection horizon is the thing to hold onto. We are using CY2025 claims to price CY2027, submitting in June 2026, and we cannot reprice until January 2028. That is roughly **2.5 years of forward projection with no ability to correct mid-course.**

---

## Step 1 — Base period experience

Start with what actually happened in CY2025, decomposed into utilization per 1,000 members and cost per unit. Never a single blended PMPM: you cannot defend a blended number in desk review, and you cannot trend it intelligently.

| Service Category | Util / 1,000 | Cost / Unit | Allowed PMPM (paid) |
|---|---:|---:|---:|
| Inpatient Facility | 240 | $14,500 | $290.00 |
| Outpatient Facility | 3,000 | $850 | $212.50 |
| Professional | 15,000 | $145 | $181.25 |
| Skilled Nursing Facility | 1,100 | $500 | $45.83 |
| Home Health | 900 | $160 | $12.00 |
| DME & Supplies | 4,500 | $70 | $26.25 |
| Part B Drugs | 1,800 | $310 | $46.50 |
| Emergency & Urgent Care | 700 | $1,150 | $67.08 |
| Ambulance & Transport | 180 | $520 | $7.80 |
| **Total** | | | **$889.22** |

The arithmetic per row: `(utilization ÷ 1,000) × cost per unit ÷ 12`. Inpatient at 240 admits per 1,000 is 0.24 admits per member per year, times $14,500, divided by 12 months = $290.00 PMPM.

## Step 2 — Completion

Those are *paid* claims as of a March 2026 data cutoff. Claims for late-2025 dates of service are still arriving. Each category completes at a different speed, so each gets its own factor:

| Category | Completion Factor | Completed Allowed PMPM |
|---|---:|---:|
| Inpatient Facility | 99.5% | $291.46 |
| Outpatient Facility | 98.5% | $215.74 |
| Professional | 97.5% | $185.90 |
| Skilled Nursing Facility | 99.0% | $46.30 |
| Home Health | 96.0% | $12.50 |
| DME & Supplies | 94.5% | $27.78 |
| Part B Drugs | 99.0% | $46.97 |
| Emergency & Urgent Care | 99.2% | $67.62 |
| Ambulance & Transport | 97.0% | $8.04 |
| **Total** | **98.55%** | **$902.30** |

Inpatient adjudicates fast — big bills, single facility, prompt submission. DME and home health straggle. Applying one blended factor across all nine would misstate the mix.

> **Decision point.** This is the first place a bid can be quietly optimistic, because completion factors are judgment applied to incomplete data. Overstating completion by one point understates the base by roughly $9 PMPM here — and that error then gets trended for two years and compounds. CMS reviewers compare the factors a plan uses against that plan's own prior-year restatements, so a pattern of optimism is visible.

## Step 3 — Normalize the base

Two adjustments, and the second one is where most people's intuition breaks.

**Remove one-time items.** CY2025 included a $4.50 PMPM retroactive hospital settlement relating to CY2023 dates of service. Real cash, but not a recurring cost of covering members in 2027.

$902.30 − $4.50 = **$897.80**

**Standardize to a 1.0 risk score.** The bid must describe the cost of covering a beneficiary of *exactly average* morbidity, because CMS will multiply the result by each actual member's risk score later. Cascade's CY2025 population had an average RAF of **1.082** — 8.2% sicker than average. So the base experience overstates what an average member costs.

$897.80 ÷ 1.082 = **$829.76 PMPM standardized allowed**

You divide, not multiply. The population was sicker than average, so the cost of an average member is *lower* than what we observed. Getting this backwards is one of the more common conceptual errors, and it is a $68 PMPM mistake here.

## Step 4 — Trend forward two years

Utilization and unit cost are trended separately, by category. This is what makes trend defensible: a 6.5% unit-cost trend on Part B drugs is arguable from a fee schedule and a pipeline; a 6.5% blended trend on everything is just a number.

| Category | Util Trend | Unit Cost Trend | Annual Total | Trended Standardized |
|---|---:|---:|---:|---:|
| Inpatient Facility | 1.0% | 4.0% | 5.04% | $292.61 |
| Outpatient Facility | 2.5% | 4.5% | 7.11% | $228.76 |
| Professional | 1.5% | 2.8% | 4.34% | $187.05 |
| Skilled Nursing Facility | 0.5% | 4.0% | 4.52% | $46.73 |
| Home Health | 3.0% | 3.0% | 6.09% | $13.00 |
| DME & Supplies | 1.0% | 2.5% | 3.53% | $27.51 |
| Part B Drugs | 4.0% | 6.5% | 10.76% | $53.25 |
| Emergency & Urgent Care | 2.0% | 4.5% | 6.59% | $71.01 |
| Ambulance & Transport | 1.5% | 5.0% | 6.58% | $8.44 |
| **Total** | | | **5.78% implied** | **$928.39** |

Annual total trend compounds the two components — `(1 + util) × (1 + cost) − 1`, not their sum — then applies over two years.

Note what the mix does. Part B drugs trend at 10.76% but are only 5% of spend; inpatient trends at 5.04% but is a third of spend. The 5.78% blended figure is an *output* of the category work, never an input.

> **Decision point.** Trend is the single most scrutinized assumption in desk review and the largest source of bid risk. The sensitivity table below shows why: one point per year of trend error moves the bid about $16 PMPM, and there is no mechanism to recover it once the year starts.

## Step 5 — Plan-year adjustments

Known changes between the base period and the plan year that trend does not capture:

| Adjustment | PMPM |
|---|---:|
| Trended standardized allowed | $928.39 |
| Hospital contract renegotiation (−2.0% on IP + OP) | ($10.43) |
| Post-acute utilization management program | ($2.80) |
| Induced utilization from richer benefit design | $1.90 |
| New-to-Medicare mix shift (non-risk-score) | ($1.60) |
| **Net adjustments** | **($12.93)** |
| **Projected allowed PMPM — CY2027, 1.0 risk** | **$915.46** |

Two of these are worth pausing on.

The **hospital renegotiation** rests on a signed letter of intent, not an executed contract. Reflecting an unsigned contract is a legitimate actuarial judgment and a completely predictable CMS question. Plans reflect them all the time; they need documentation ready.

The **induced utilization** line is subtle. Lowering copays makes members use more care. That extra care is a real A/B cost that belongs in the bid, even though the copay reduction itself is funded from the rebate downstream. Miss it and you have understated cost.

The **mix shift** is the residual effect of new-to-Medicare enrollees *after* risk adjustment. They tend to be less thoroughly coded than continuing members, which suppresses their RAF, but they also genuinely use less care. The risk score captures part of this; the rest is an explicit adjustment.

## Step 6 — Member cost sharing

| | PMPM |
|---|---:|
| Projected allowed | $915.46 |
| Less: member cost sharing at Original Medicare-equivalent AV (13.5%) | ($123.59) |
| **Plan-paid basic A/B benefit cost** | **$791.88** |

This is structurally important and easy to get wrong. **The bid is priced at Original Medicare cost-sharing levels** — the actuarial value of Part A/B deductibles and coinsurance. Cascade's actual product has far richer cost sharing than that, but the difference is funded from the rebate, not the bid. Keeping the two separate is what makes bids comparable to the FFS-derived benchmark.

## Step 7 — Non-benefit expense

| | PMPM |
|---|---:|
| General & administrative | $52.00 |
| Sales, marketing & broker commissions | $22.00 |
| Quality improvement activities | $6.50 |
| Premium taxes & fees | $3.00 |
| **Total** | **$83.50** |

QIA is broken out separately because it sits in the **MLR numerator** alongside claims, not in the denominator with other admin. That treatment is worth several tenths of a point of MLR.

> **Decision point.** Admin allocation across a portfolio is contestable. A plan with a dozen PBPs must assign shared overhead somewhere, and where it lands changes which products look viable. CMS reviews allocation methodology for consistency across a plan's filings and against prior years.

## Step 8 — Margin, and the bid

| | PMPM |
|---|---:|
| Claims + non-benefit expense | $875.38 |
| Gain / loss margin at 3.5% of revenue | $31.75 |
| **STANDARDIZED A/B BID** | **$907.13** |

Margin is a percentage **of revenue**, so it is grossed up rather than marked up:

`$875.38 ÷ (1 − 0.035) = $907.13`

Not `$875.38 × 1.035 = $906.02`. The difference is small here but it is the difference between hitting your target margin and missing it.

### The whole waterfall

| Step | Component | PMPM | Running |
|---|---|---:|---:|
| 1 | Completed allowed cost, CY2025 | $902.30 | $902.30 |
| 2 | Remove one-time items | ($4.50) | $897.80 |
| 3 | Standardize to 1.0 risk | ($68.04) | $829.76 |
| 4 | Trend forward two years | $98.63 | $928.39 |
| 5 | Plan-year adjustments | ($12.93) | $915.46 |
| 6 | Less member cost sharing | ($123.59) | $791.88 |
| 7 | Add non-benefit expense | $83.50 | $875.38 |
| 8 | Add gain / loss margin | $31.75 | **$907.13** |

---

## Step 9 — Benchmark, savings, rebate

Now the bid meets the CMS ratebook.

| | PMPM |
|---|---:|
| County risk-standardized FFS per capita | $1,010.00 |
| × Applicable percentage (quartile 2 → 100%) | $1,010.00 |
| + Quality bonus, 4.0 Stars (+5%) | $50.50 |
| **Final benchmark** | **$1,060.50** |
| Less: standardized bid | ($907.13) |
| **Savings** | **$153.37** |
| × Rebate share at 4.0 Stars (65%) | |
| **Rebate to plan** | **$99.69** |
| Government share — retained by the Trust Funds | $53.68 |
| Member basic premium | $0.00 |

The $53.68 is not sent anywhere. CMS simply pays $53.68 less than the benchmark ceiling. It is money the Medicare Trust Funds never spend.

## Step 10 — Rebate allocation

The $99.69 cannot become ordinary profit. It has to be spent here:

| | PMPM |
|---|---:|
| Reduced cost sharing (buy-down below Original Medicare) | $46.00 |
| Comprehensive dental | $18.50 |
| Vision | $3.20 |
| Hearing | $4.80 |
| OTC / flex card | $8.40 |
| Fitness | $3.10 |
| **Direct member value** | **$84.00** *(84.3% of rebate)* |
| Administrative load on rebate-funded benefits | $11.00 |
| Margin on rebate-funded benefits | $4.69 |
| **Total allocated** | **$99.69** |

The $46.00 buy-down takes member cost sharing from $123.59 down to **$77.59 PMPM** — that is what turns an Original-Medicare-equivalent benefit into a competitive MA product.

Note the last two lines. Plans *can* book admin and margin against delivering supplemental benefits, so "rebate dollars can't become profit" is slightly too strong — but $4.69 of $99.69 is a very different thing from keeping the whole rebate.

> **Decision point.** This is the most commercially consequential page in the entire bid. The same $99.69 could fund a headline $0 medical deductible, a large OTC card that markets well, or a Part B giveback that shows up as a hard number on Medicare Plan Finder. Each buys a different amount of enrollment. And the plan is guessing at competitors who are making the same call, behind the same June deadline, with no visibility into each other.

## Step 11 — Payment

| | |
|---|---:|
| Bid + rebate (standardized, 1.0 risk) | $1,006.82 |
| Projected raw RAF (v28) | 1.212 |
| ÷ Normalization factor | 1.045 |
| × (1 − coding intensity adjustment of 5.9%) | |
| **Payment RAF** | **1.0914** |
| **Payment PMPM** | **$1,098.82** |
| **Annual plan revenue** (10,000 members) | **$131,858,654** |

The raw 1.212 becomes an effective 1.0914 after normalization and the coding intensity haircut — a 10% reduction. Those two adjustments are set by CMS in the Rate Announcement and are pure exogenous risk to the plan.

## Step 12 — Compliance tests

| Test | Result | |
|---|---|---|
| **MLR** | 87.64% vs 85.0% floor | **PASS** — 2.64 points of cushion |
| **Total Beneficiary Cost** | $77.59 vs $85.00 prior year, −$7.41 | **PASS** — beneficiary cost decreases |
| **MOOP** | $4,900 vs CMS mandatory limit | **PASS** |
| **Total margin** | $36.44 PMPM = 3.62% of standardized revenue | Within target |

The MLR numerator is claims plus rebate-funded benefits plus QIA, all risk-adjusted: $864.24 + $91.68 + $7.09 = $963.01 against $1,098.82 of revenue.

Note the total margin: 3.62%, not the 3.5% target, because the $4.69 of rebate-funded margin rides on top of the bid margin.

---

## What actually moves the answer

| Scenario | Benchmark | Bid | Rebate | Annual Revenue | Annual Rebate Δ |
|---|---:|---:|---:|---:|---:|
| **Base case** | $1,060.50 | $907.13 | $99.69 | $131,858,654 | — |
| Stars fall to 3.5 — QBP lost | $1,010.00 | $907.13 | $66.87 | $127,559,709 | **($3,939,000)** |
| Stars rise to 4.5 — 70% share | $1,060.50 | $907.13 | $107.36 | $132,862,990 | $920,244 |
| Trend 1 pt/yr higher | $1,060.50 | $922.71 | $89.56 | $132,573,223 | ($1,215,943) |
| Trend 1 pt/yr lower | $1,060.50 | $891.68 | $109.73 | $131,150,809 | $1,204,502 |
| RAF 3% below projection | $1,060.50 | $907.13 | $99.69 | $127,902,895 | — |
| County drops to quartile 1 (95%) | $1,007.48 | $907.13 | $65.23 | $127,344,762 | ($4,135,950) |

Three readings worth drawing out.

**Losing the 4.0 Star threshold costs $3.9 million a year in benefits, not margin.** The bid is unchanged; the plan's margin is unchanged. What disappears is $32.83 PMPM of member value — a third of the benefit package. That is what loses enrollment, and enrollment is what scales the margin embedded in the bid. This is the compounding mechanism behind why Star ratings dominate MA strategy.

**Trend error is asymmetric in an uncomfortable way.** Guess trend too low and the bid is underpriced, margin evaporates, and there is no repricing for twelve months. Guess too high and the bid is inflated, the rebate shrinks by $10 PMPM, and the benefit package loses to competitors who guessed better. There is no safe direction to be wrong in.

**Risk score misses hit revenue with no offsetting relief.** A 3% RAF shortfall takes $3.96 million off revenue. Claims fall somewhat with a genuinely healthier population, but admin does not, and the bid was priced on the higher assumption.

The scenario table holds target margin constant and lets the rebate absorb every shock. A plan could instead hold the benefit package constant and let margin absorb it. Which of those a plan chooses is a strategy decision made well above the actuarial department.

---

## Index of decision points

| # | Decision | Where it bites |
|---|---|---|
| 1 | Base period selection | A partial-year base with seasonality baked in distorts everything downstream |
| 2 | Completion factors by category | Quietly understates the base; compounds through trend |
| 3 | What counts as a one-time item | Removing too much is a favorable-bias pattern reviewers look for |
| 4 | Risk standardization of the base | Direction of the adjustment; whose RAF to use |
| 5 | Trend split between utilization and unit cost | The most scrutinized assumption in the bid |
| 6 | Reflecting unsigned provider contracts | Legitimate, but needs documentation ready for desk review |
| 7 | Induced utilization from benefit richness | Easy to omit entirely; understates cost when missed |
| 8 | Admin allocation across the portfolio | Determines which PBPs look viable |
| 9 | Target margin | Must be consistent across filings and defensible year over year |
| 10 | Rebate allocation across benefits | The most commercially consequential page in the bid |
| 11 | Service area — which counties to bid | Set months earlier; determines the benchmark you are handed |
| 12 | Hold margin or hold benefits under stress | Strategy, not actuarial judgment |

---

## Using the workbook

`medicare-advantage-bid-example.xlsx` — nine sheets, following BPT structure:

| Sheet | Contents |
|---|---|
| 1. Assumptions | Every input, in one place |
| 2. Base Experience | Utilization, unit cost, completion factors |
| 3. Projected Allowed | Normalize, trend, plan-year adjustments |
| 4. Plan Liability | Cost sharing, admin, margin |
| 5. Standardized Bid | The full waterfall, with a tie-out check |
| 6. Benchmark & Rebate | Benchmark build, savings split, payment |
| 7. Rebate Allocation | Benefit package, with a balance check |
| 8. Compliance Tests | MLR, TBC, MOOP, margin |
| 9. Sensitivity | Seven scenarios, re-solved |

Blue cells are inputs — change any of them and the model recalculates. Shaded cells are parameters that must come from the published CY2027 Rate Announcement; the MOOP limit in particular is a placeholder and should be replaced before the model is used for anything real.

Two checks are built in and should always read zero: the waterfall tie-out on Sheet 5, and unallocated rebate on Sheet 7.

The Sheet 9 trend scenarios scale projected allowed cost off the implied blended trend rather than re-running the category grid. That is an approximation — right for direction and magnitude, but re-run the category-level trends on Sheet 3 before relying on a specific number.
