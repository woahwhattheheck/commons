# Proposed $24,000 base fee - bottom-up economics

> SYNTHETIC / PROPOSED. Every hour figure and every rate below is an ASSUMPTION for modelling, not an agreed or observed figure. No University of Iowa data appears here. The $24,000 base, $4,000 option and 40/40/20 milestone split are the proposed commercial facts; everything else is a working estimate.

Reconciles to the quoted commercial facts: milestones sum to the base fee and each matches its stated share.

## Bottom-up cost by work package

### Low effort case

| Package | Hours | Labour | Compute/tooling | Admin overhead | Contingency | Total | Unknowns |
|---|---|---|---|---|---|---|---|
| **WP1** Evidence organization and intake | 48 h | $3,325.00 | $60.00 | $270.80 | $365.58 | **$4,021.38** | - |
| **WP2** Assessment matrix population | 58 h | $4,110.00 | $50.00 | $332.80 | $449.28 | **$4,942.08** | - |
| **WP3** Findings and traceability | 68 h | $4,870.00 | $40.00 | $392.80 | $530.28 | **$5,833.08** | - |
| **WP4** Report production | 62 h | $4,420.00 | $45.00 | $357.20 | $482.22 | **$5,304.42** | - |
| **WP5** Consolidated review and corrections | UNKNOWN | UNKNOWN | $25.00 | UNKNOWN | UNKNOWN | **UNKNOWN** | low.correction_hours |
| | UNKNOWN | | | | | **UNKNOWN** | |

**Verdict: `NOT_COMPUTABLE`**

Costed packages total $20,100.96, leaving $3,899.04 of the fee before this case turns to a loss. Whether it does depends entirely on WP5, which is not estimated. No margin is reported, because any number here would be a guess presented as an answer.

Costed packages total $20,100.96. **No margin is reported for this case.** A figure here would be a guess wearing the formatting of an answer.

### Expected effort case

| Package | Hours | Labour | Compute/tooling | Admin overhead | Contingency | Total | Unknowns |
|---|---|---|---|---|---|---|---|
| **WP1** Evidence organization and intake | 62 h | $4,285.00 | $80.00 | $349.20 | $471.42 | **$5,185.62** | - |
| **WP2** Assessment matrix population | 79 h | $5,590.00 | $70.00 | $452.80 | $611.28 | **$6,724.08** | - |
| **WP3** Findings and traceability | 92 h | $6,560.00 | $60.00 | $529.60 | $714.96 | **$7,864.56** | - |
| **WP4** Report production | 82 h | $5,830.00 | $65.00 | $471.60 | $636.66 | **$7,003.26** | - |
| **WP5** Consolidated review and corrections | UNKNOWN | UNKNOWN | $35.00 | UNKNOWN | UNKNOWN | **UNKNOWN** | expected.correction_hours |
| | UNKNOWN | | | | | **UNKNOWN** | |

**Verdict: `LOSS_CERTAIN_DESPITE_UNKNOWNS`**

The packages that can be costed already total $26,777.52 against a $24,000.00 fee. The missing estimates in WP5 can only add cost, never subtract it, so this case loses at least $2,777.52 whatever those estimates turn out to be. The exact margin is still unknown; the sign of it is not.

Costed packages total $26,777.52. **No margin is reported for this case.** A figure here would be a guess wearing the formatting of an answer.

### High effort case

| Package | Hours | Labour | Compute/tooling | Admin overhead | Contingency | Total | Unknowns |
|---|---|---|---|---|---|---|---|
| **WP1** Evidence organization and intake | 87 h | $6,020.00 | $120.00 | $491.20 | $663.12 | **$7,294.32** | - |
| **WP2** Assessment matrix population | 111 h | $7,845.00 | $110.00 | $636.40 | $859.14 | **$9,450.54** | - |
| **WP3** Findings and traceability | 130 h | $9,265.00 | $95.00 | $748.80 | $1,010.88 | **$11,119.68** | - |
| **WP4** Report production | 120 h | $8,535.00 | $100.00 | $690.80 | $932.58 | **$10,258.38** | - |
| **WP5** Consolidated review and corrections | UNKNOWN | UNKNOWN | $55.00 | UNKNOWN | UNKNOWN | **UNKNOWN** | high.correction_hours |
| | UNKNOWN | | | | | **UNKNOWN** | |

**Verdict: `LOSS_CERTAIN_DESPITE_UNKNOWNS`**

The packages that can be costed already total $38,122.92 against a $24,000.00 fee. The missing estimates in WP5 can only add cost, never subtract it, so this case loses at least $14,122.92 whatever those estimates turn out to be. The exact margin is still unknown; the sign of it is not.

Costed packages total $38,122.92. **No margin is reported for this case.** A figure here would be a guess wearing the formatting of an answer.

## Assumptions sheet

Every figure in this section is an **assumption**, not an agreed or observed value. Nothing here has been confirmed with the University or with Clark's.

### Rates

| Rate | Assumed | Basis | Note |
|---|---|---|---|
| **Administration and coordination** | $45.00/h | `ASSUMED` | Illustrative loaded rate for coordination time. NOT an agreed rate card. |
| **Production (analysis, build, evidence work)** | $70.00/h | `ASSUMED` | Illustrative loaded rate. NOT an agreed rate card. Chosen to match the $70/$85 pair already used in the readout-option model so the two are comparable; it is not evidence that either is correct. |
| **Senior review and professional judgement** | $85.00/h | `ASSUMED` | Illustrative loaded rate for senior time. NOT an agreed rate card. |

### Overheads

| Assumption | Value | What it covers |
|---|---|---|
| Admin overhead | 8% | Non-billed coordination load, applied to direct cost. |
| Contingency | 10% | Re-work not already carried in each package's correction hours. |

### Commercial facts (given, not derived)

| Item | Amount |
|---|---|
| Base fee | $24,000.00 |
| Optional readout | $4,000.00 |
| M1 - Written authorization and kickoff (40%) | $9,600.00 |
| M2 - Qualifying draft delivered (40%) | $9,600.00 |
| M3 - Written final acceptance (20%) | $4,800.00 |

## Break-even

- **Low:** not computable - an effort estimate is missing, so the blended rate and the break-even point cannot be computed.
- **Expected:** not computable - an effort estimate is missing, so the blended rate and the break-even point cannot be computed.
- **High:** not computable - an effort estimate is missing, so the blended rate and the break-even point cannot be computed.

Break-even hours are what the fee buys at the blended rate once non-labour cost is carried. A negative headroom means the plan spends hours the fee does not cover.

## Sensitivity

Every effort case against rate assumptions at x0.80, x0.90, x1.00, x1.10, x1.20 of the assumed card (15 scenarios).

| Rate factor | Case | Total cost | Margin | Verdict |
|---|---|---|---|---|
| x0.80 | Low | UNKNOWN | UNKNOWN | `NOT_COMPUTABLE` |
| x0.80 | Expected | UNKNOWN | UNKNOWN | `NOT_COMPUTABLE` |
| x0.80 | High | UNKNOWN | UNKNOWN | `LOSS_CERTAIN_DESPITE_UNKNOWNS` |
| x0.90 | Low | UNKNOWN | UNKNOWN | `NOT_COMPUTABLE` |
| x0.90 | Expected | UNKNOWN | UNKNOWN | `LOSS_CERTAIN_DESPITE_UNKNOWNS` |
| x0.90 | High | UNKNOWN | UNKNOWN | `LOSS_CERTAIN_DESPITE_UNKNOWNS` |
| x1.00 | Low | UNKNOWN | UNKNOWN | `NOT_COMPUTABLE` |
| x1.00 | Expected | UNKNOWN | UNKNOWN | `LOSS_CERTAIN_DESPITE_UNKNOWNS` |
| x1.00 | High | UNKNOWN | UNKNOWN | `LOSS_CERTAIN_DESPITE_UNKNOWNS` |
| x1.10 | Low | UNKNOWN | UNKNOWN | `NOT_COMPUTABLE` |
| x1.10 | Expected | UNKNOWN | UNKNOWN | `LOSS_CERTAIN_DESPITE_UNKNOWNS` |
| x1.10 | High | UNKNOWN | UNKNOWN | `LOSS_CERTAIN_DESPITE_UNKNOWNS` |
| x1.20 | Low | UNKNOWN | UNKNOWN | `LOSS_CERTAIN_DESPITE_UNKNOWNS` |
| x1.20 | Expected | UNKNOWN | UNKNOWN | `LOSS_CERTAIN_DESPITE_UNKNOWNS` |
| x1.20 | High | UNKNOWN | UNKNOWN | `LOSS_CERTAIN_DESPITE_UNKNOWNS` |

**No swept scenario is profitable on the evidence available. 10 of 15 lose money regardless of the missing estimates; 5 cannot be decided until those estimates exist.**

- **Administration and coordination:** an estimate is missing, so there is no margin to flip. Resolve WP5 first.
- **Production (analysis, build, evidence work):** an estimate is missing, so there is no margin to flip. Resolve WP5 first.
- **Senior review and professional judgement:** an estimate is missing, so there is no margin to flip. Resolve WP5 first.

## What this model does not know

- The actual loaded rates. Every rate here is `ASSUMED`; no rate card has been agreed, so every margin figure moves with them.
- The real correction workload, which depends on the volume of consolidated University comments and is not knowable before the draft is reviewed.
- Whether onsite attendance is required for the base packages. Travel is excluded here and is carried separately in the readout option.
- The actual split of work between Clark's and TJLabs, which changes who carries which hours.
