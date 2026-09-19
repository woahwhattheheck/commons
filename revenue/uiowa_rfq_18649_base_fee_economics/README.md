# Economics of the proposed $24,000 base fee

**UIOWA-003.** A bottom-up cost model for the five base work packages — human production and
review time, compute and tooling, administration, correction effort, contingency — at **low /
expected / high** effort, with break-even hours, contribution margin, and a sensitivity sweep.

Built by seat `OP5-EMBER` (Claude · Opus 5). Python 3 standard library only, no network,
deterministic (no clock, no randomness, sorted traversal).

---

## The finding, stated first

**As modelled, the proposed $24,000 base fee does not cover the proposed scope.** Not at the
expected effort case, and not at any of the fifteen swept scenarios.

```
Low       cost=UNKNOWN   margin=UNKNOWN   NOT_COMPUTABLE
Expected  cost=UNKNOWN   margin=UNKNOWN   LOSS_CERTAIN_DESPITE_UNKNOWNS
High      cost=UNKNOWN   margin=UNKNOWN   LOSS_CERTAIN_DESPITE_UNKNOWNS

No swept scenario is profitable on the evidence available. 10 of 15 lose money regardless
of the missing estimates; 5 cannot be decided until those estimates exist.
```

Supply the one missing estimate and the picture completes — and gets no better:

```
$ python3 analyze.py --resolve WP5.correction_hours=14,22,40

Low       cost=$23,314.50   margin=    $685.50   MARGIN_COMPUTED   (+2.9%)
Expected  cost=$31,309.74   margin= -$7,309.74   MARGIN_COMPUTED  (-30.5%)
High      cost=$45,607.32   margin=-$21,607.32   MARGIN_COMPUTED  (-90.0%)

Only 3 of 15 swept scenarios are profitable, and every one sits at the low-effort case
with rates at or below the assumed card. This is a corner result, not a margin.
```

**This is a statement about the model's assumptions, not a recommendation to change the price.**
Every rate is `ASSUMED` and every hour figure is a working estimate; the honest reading is *"if
the effort is anything like this and the rates are anything like these, the fee is short"* — which
is a prompt to check the effort estimates and the rate card, not a conclusion about the bid.

---

## The three rules this model will not bend on

**1. A missing estimate is never a zero cost.** This is the one that matters. A zero cost
*inflates* margin, so the error always runs in the direction of "this bid looks profitable" — and
an optimistic margin is what gets a fixed-price bid signed at a loss. An absent input stays
`UNKNOWN`, propagates through every total that depends on it, and the affected package is excluded
from the headline margin, which is then reported as **not computable** rather than printed as a
number. `UNKNOWN` also refuses to be truthy and refuses to be compared, so it cannot slip into a
decision as "absent, therefore fine".

A test asserts a blank and a literal `0` produce different outputs, and a second one asserts the
zeroed version reports a *better* margin than the truth — demonstrating the hazard rather than
describing it.

**2. Every rate is an assumption, and has to say so.** There is no agreed rate card for this
engagement. Each rate carries a `basis` that must read `ASSUMED` or `SYNTHETIC-FIXTURE`; a rate
declaring itself `AGREED`, `CONTRACTUAL` or `OBSERVED` is **refused at load**, because quoting a
margin off an invented rate card is the specific way this artifact could mislead a reader.

**3. It reconciles to the commercial facts; it does not re-derive them.** The **$24,000** base,
**$4,000** option and **40/40/20** split ($9,600 / $9,600 / $4,800) are given inputs, already
established across this engagement's other lanes. A milestone that does not sum to the fee, or
whose amount does not match its stated share, is an **ERROR** — not a rounding note. `--check`
exits non-zero on it.

---

## Reasoning under partial information

"An estimate is missing, therefore nothing can be concluded" is as wrong as treating the gap as
zero, and this model does neither. Cost lines cannot be negative, so the cost of the packages that
*can* be priced is a **floor** on the whole bid. Three verdicts follow:

| Verdict | When | What it means |
|---|---|---|
| `MARGIN_COMPUTED` | every package costed | The margin is a computed figure. |
| `LOSS_CERTAIN_DESPITE_UNKNOWNS` | floor ≥ fee | The missing estimates can only **add** cost, so this case loses money whatever they turn out to be. The exact margin is unknown; **the sign of it is not.** |
| `NOT_COMPUTABLE` | floor < fee | The answer genuinely depends on the missing estimate. No margin is reported, because any number would be a guess wearing the formatting of an answer. |

The expected case of the shipped model is `LOSS_CERTAIN_DESPITE_UNKNOWNS`: costed packages total
$26,777.52 against a $24,000 fee, so the bid loses **at least $2,777.52** before the unknown is
counted at all. That is a sound conclusion from incomplete data, and it is the one a bidder most
needs to hear.

## Sensitivity, and why it says "corner result"

The sweep runs all three effort cases against rate assumptions at ×0.80 … ×1.20 of the assumed
card — fifteen scenarios. It reports not just how many are profitable but **where they sit**. When
every profitable scenario is at the low-effort case with rates at or below the card, the tool says
so in those words, because *"profitable under some assumptions"* would be true and misleading.

It also answers the obvious follow-up: **how far does one assumption have to move to flip the
answer?** Found by bisection, so it holds even if a future overhead rule is non-linear. For the
resolved model, the expected case only turns profitable **below $53.47/h** against the assumed
$70.00/h production rate — a 24% cut. A test verifies that flip point by evaluating the margin
on both sides of it.

---

## Run it

```bash
cd revenue/uiowa_rfq_18649_base_fee_economics

python3 analyze.py                                    # workbook, CSV and JSON into sample_output/
python3 analyze.py --check                            # reconcile to the fee; exit 1 on an error
python3 analyze.py --resolve WP5.correction_hours=14,22,40
python3 -m unittest test_cost_model                   # 52 tests
```

`--resolve` prices the unknown instead of arguing about it: supply the figure you believe and the
model says what it does to the bid. It refuses a partial resolution (one case only would leave the
others `UNKNOWN`) and refuses to overwrite an estimate that already exists.

Rendering is deterministic; a test renders twice into separate directories and compares bytes.

## Files

| File | What it is |
|---|---|
| `money.py` | Exact cents (`Decimal`) and the `UNKNOWN` that refuses to be zero, truthy or compared |
| `cost_model.py` | Packages, rates, overheads, reconciliation, the three verdicts, `resolve()` |
| `sensitivity.py` | The rate × effort sweep, the corner-result test, and rate break-even by bisection |
| `analyze.py` | CLI; renders the workbook (Markdown), the package sheet (CSV) and JSON |
| `fixtures/base_fee_model.json` | Five work packages with one deliberate, realistic unknown |
| `sample_output/` | A committed run, so a reviewer can read the result without running anything |
| `test_cost_model.py` | 52 tests |

Money is `Decimal` in whole cents throughout. Binary floats cannot represent `0.1`, and a total
that fails to reconcile to the quoted fee by one cent is indistinguishable from a real error.

## What is real and what is draft

**Real and working:** the exact-money arithmetic and the propagating `UNKNOWN`; the bottom-up cost
build; low/expected/high with an ordering check; reconciliation to the quoted commercial facts;
the three verdicts including the floor-above-revenue proof; `resolve()`; break-even hours; the
sensitivity sweep and the bisection flip-point; Markdown/CSV/JSON output; 52 tests.

**Draft:** the effort estimates themselves. The *shape* of the model is the deliverable; the
numbers in it are a starting point for someone who knows what this work actually takes.

**Fiction is labelled fiction.** Every artifact carries *"SYNTHETIC / PROPOSED. Every hour figure
and every rate below is an ASSUMPTION for modelling, not an agreed or observed figure. No
University of Iowa data appears here."* — and a test asserts it. The deliberate unknown
(`WP5.correction_hours`) is realistic, not contrived: correction workload depends on the volume of
consolidated University comments, which nobody can know before the draft is reviewed.

## UNKNOWN inputs — none of these is guessed at anywhere

- **The actual loaded rates.** Every rate is `ASSUMED`. The $70/$85 pair matches the figures used
  in the readout-option lane so the two models are comparable — that is consistency, not evidence
  that either is correct. Every margin here moves with them.
- **The real correction workload**, which is why `WP5.correction_hours` ships as `UNKNOWN`.
- **The real effort for every other package.** These are modelling estimates, not measured.
- **The Clark's / TJLabs work split**, which changes who carries which hours and therefore which
  rate applies.
- **Whether onsite attendance is required for the base packages.** Travel is excluded here and is
  carried separately in the readout option.
- **The actual admin overhead and contingency the business runs at.** Both are proposed figures.

No certification, compliance, maturity or peer-percentile claim is made anywhere, and no
individual's performance is estimated or scored. A test greps the rendered workbook for that
vocabulary and fails if it appears.
