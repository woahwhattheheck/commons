# University of Iowa RFQ 18649 — scope-change impact calculator

Work order **UIOWA-133**. An editable change-quotation worksheet that extends the proposed
baseline with separately priced changes, computing incremental effort, dependencies, schedule
effect and fee from assumptions printed next to the answer — and keeping a **no-charge
correction of our own defect distinguishable from added work**.

Offline, Python 3 standard library only. Money is computed in integer cents.

---

## Status: what is real and what is draft

| Thing | Status |
|---|---|
| `scope_change.py` | **Working code.** 48 tests, all passing. |
| `test_scope_change.py` | **Working tests.** |
| Baseline commercial figures | **Quoted from the repository** — `../uiowa_rfq_18649_workshare/COMMERCIAL.md` and `ACCEPTANCE_EXHIBIT.md`. Still **PROPOSED / NOT ACCEPTED** there, and quoting them here does not make them agreed. |
| Role rates, base hours, overhead | **ASSUMPTIONS.** No rate card exists; the base is a fixed fee. Labelled `ASSUMED` in the fixture and in every rendered output. |
| `fixtures/change_requests.json` | **FICTION.** Eight invented requests. Nobody has asked for any of them. |
| `examples/*` | **Generated output** from the fiction above. |

**No output of this tool is an offer, an authorization, a contract, an invoice, a payment record
or recognized revenue.** Every figure carries `PROPOSED_ESTIMATE_NOT_A_COMMITMENT`.

---

## Run it

```bash
python3 scope_change.py                       # print the worksheet

python3 scope_change.py \
  --json-out out.json --csv-out out.csv --markdown-out out.md

python3 scope_change.py --sweep-role lead_reviewer   # what that rate assumption is worth

python3 -m unittest -v test_scope_change.py
python3 -O -m unittest test_scope_change.py          # also passes with asserts stripped
```

---

## The baseline it measures against

Quoted from the repository, not invented here:

| | |
|---|---|
| Base workshare | **$24,000** fixed |
| Optional final-readout support | $4,000, only when separately authorized |
| Milestones | 40% / 40% / 20% = $9,600 kickoff, $9,600 draft, $4,800 final |
| Travel | Excluded, and **cannot be committed by this carrier** |
| Duration | six to eight weeks; all day counts are relative to kickoff |

**The baseline does not move.** Changes are separate line items; no scenario re-bills the base
or alters the milestone split. A test asserts the base is byte-identical before and after
evaluating every scenario, and the loader refuses a baseline whose milestones do not sum to the
base fee.

### The assumptions doing the work

The proposal states a fixed fee and no hours, so converting effort into money needs inputs that
do not exist in the source documents. They are supplied as labelled assumptions rather than
quietly embedded:

| role | loaded rate / h | status |
|---|---:|---|
| `evidence_analyst` | $120.00 | ASSUMED |
| `assessment_engineer` | $150.00 | ASSUMED |
| `lead_reviewer` | $195.00 | ASSUMED |

plus a base package modelled at **160 h** (ASSUMED) — which implies a blended **$150/h** against
the fixed $24,000, printed in the output so the rate card can be sanity-checked against the fee
rather than taken on faith — and **8%** coordination overhead on added work.

Change one and the whole worksheet moves. That is the point: the calculator renders a
sensitivity table showing exactly how much.

---

## Four dispositions, because the exhibit has four

Most change calculators have two outcomes: priced, or not priced yet. The acceptance exhibit
actually distinguishes four situations, and collapsing any of them loses money or credibility.

### 1. `CHANGE_QUOTE` — real added work

Priced bottom-up from the work breakdown at the baseline role rates, plus overhead, with the
substituted arithmetic shown per line and a reconciliation line proving the parts equal the
whole to the cent.

Where a price is **already published** for the item — the $4,000 readout option — that figure
**governs** and the bottom-up computation becomes a disclosed cross-check. On the synthetic set
the readout computes to $3,466.80 bottom-up against the published $4,000, and the worksheet
reports the −$533.20 gap rather than silently preferring either number. Deriving a second price
for the same item is how a proposal starts contradicting itself across documents.

### 2. `NO_CHARGE_CURE` — correcting our own nonconformance

This is the work order's hard requirement, and the exhibit already states the rule:

> *"A small correction to a TJLabs-authored artifact that fails an agreed acceptance criterion is
> not treated as a new scope item merely because it occurs during acceptance review."*

So a request grounded in a failed acceptance criterion produces **fee $0.00, hours reported**.
Both halves matter:

- **Fee zero**, because billing the buyer to fix a deliverable that failed an agreed criterion is
  charging for our own defect.
- **Hours non-zero**, because the work is real and costs time. Reporting zero effort would hide
  it from anyone trying to see what corrections are costing. TJLabs' own cost of the cure is
  tracked separately and explicitly marked as *not a charge, not an invoice line, and not part of
  any total presented to the buyer*.

Three things cannot move a cure into billable work, each with a test:

- **Wording.** A cure titled *"ADDITIONAL WORK: substantial new analysis effort required"* is
  still a cure. Titles and summaries are not inputs to the disposition; only the grounds are.
- **Timing.** The cure path carries no date or phase condition at all, because the exhibit says
  arriving during acceptance review is not a reclassification.
- **Rates.** The sensitivity sweep scales the rate ×0.5, ×1, ×4, ×100 — the quoted change total
  moves every time and the cure total stays $0.00. It is zero by *policy*, not by arithmetic.
  There is no rate at which fixing our own defect becomes billable.

### 3. `NOT_QUOTABLE` — outside the solicitation, at any price

Specific product/vendor recommendations and legal/audit/certification opinions are a controlling
RFQ scope boundary, not a change-control item:

> *"It cannot be added merely because the prime asks for it; only a formal
> controlling-solicitation amendment could reopen that question."*

The exclusion is checked **before** any effort is priced, so no fee is ever computed — tested at
1 h, 40 h and 4,000 h of effort, all returning `NOT QUOTED`. The effort is still displayed, so
the refusal reads as a scope boundary rather than a brush-off: the synthetic request is 40 hours
of perfectly deliverable work that still gets no price, because willingness to pay is not what
makes something in scope.

### 4. `NEEDS_INPUT` — cannot be quoted yet

Carried over from the prioritization lane (UIOWA-084): **an absence never becomes a zero.**

- An unestimated task leaves its line at `UNKNOWN` hours and `UNKNOWN` cost — never `$0.00` — and
  blocks the whole quote rather than being priced around. The estimated part of the request is
  still reported, so the gap is one line, not the entire request.
- A request with **no work breakdown at all** is `NEEDS_INPUT`, not a $0.00 change. An empty
  breakdown means nobody estimated it, which is not the same as a change that costs nothing.
- An **unsubstantiated defect claim** — "the findings don't read right", citing no criterion — is
  neither free nor billable. It stops and asks. Defaulting to free absorbs unlimited rework;
  defaulting to billable charges for what may be our own defect. This is the most realistic case
  in the fixture and the one that most often goes wrong in practice.

---

## Money

Integer cents throughout. A float dollar amount is **refused** by the parser with a message
saying why, because a quotation that drifts by a cent in binary floating point is a defect in a
commercial document, not a rounding preference. Amounts are parsed from ints or decimal strings
(`"187.50"`), and sub-cent precision is rejected rather than rounded.

Every quote reconciles: line items + overhead == fee, asserted exactly. `UNKNOWN` money renders
as the word `UNKNOWN` and never as `$0.00` — a test asserts those two are never equal.

In the CSV, where this usually goes wrong: the cure row carries **7.0 hours and `$0.00`** with
`fee_is_zero_by_policy=YES`; the refused row carries `NOT QUOTED`; the blocked rows carry
`UNKNOWN`. Hours survive into the spreadsheet for every row, so a correction's real effort is
never erased by its zero price.

---

## Worked scenarios

Eight fictional requests — the five the work order names, plus three that prove the boundaries.

| id | request | disposition | hours | fee |
|---|---|---|---:|---:|
| `CR-SYN-001` | Add a fourth system group | CHANGE_QUOTE | 74 | $11,793.60 |
| `CR-SYN-002` | Second interview cycle | CHANGE_QUOTE | 52 | $7,128.00 |
| `CR-SYN-003` | Add a fifth analysis dimension | NEEDS_INPUT | 48 | UNKNOWN |
| `CR-SYN-004` | Optional final-readout session | CHANGE_QUOTE | 18 | $4,000.00 (published) |
| `CR-SYN-005` | One onsite working day | CHANGE_QUOTE | 14 | $2,462.40 |
| `CR-SYN-006` | Correct omitted HOLD reasons | **NO_CHARGE_CURE** | **7** | **$0.00** |
| `CR-SYN-007` | Recommend a specific product | **NOT_QUOTABLE** | 40 | **NOT QUOTED** |
| `CR-SYN-008` | "The findings don't read right" | NEEDS_INPUT | 8 | UNKNOWN |

Against an **unchanged $24,000** base: $25,384.00 of quoted change, $0.00 of corrections covering
7 hours, one request not quotable, two awaiting input.

Two details worth pointing at:

- **`CR-SYN-005` prices the onsite labour and refuses the travel.** Travel, accommodation and
  subsistence appear as an explicit `non_committable_cost` excluded from the fee, because
  `COMMERCIAL.md` says travel cannot be committed by this carrier. A real cost that is
  deliberately absent from the number rather than estimated into it.
- **`CR-SYN-002` names a dependency that is not ours.** Interview scheduling belongs to the
  prime; the schedule effect says so, so a slip caused by participant availability is not
  silently absorbed as carrier delay.

---

## Inputs still UNKNOWN

- **Every role rate**, the base-hours figure and the overhead percentage. All ASSUMED. Nothing in
  the solicitation or the proposal supplies them.
- **Whether hourly pricing is the right model for changes at all**, given a fixed-fee base. An
  alternative is fixed prices per named change type; this worksheet would then become the
  derivation behind those fixed prices rather than the quotation itself.
- **The real change requests.** These eight are fiction.
- **Who authorizes a change**, and how the authorization is recorded against the milestone
  schedule.
- **Whether the prime agrees with the cure boundary in any specific case.** The tool applies the
  rule the exhibit already states; it cannot settle a genuine dispute about whether a particular
  artifact met a criterion. It can only stop that dispute from being resolved by default.

---

## Files

```
scope_change.py                     calculator and CLI
test_scope_change.py                48 tests
fixtures/baseline.json              baseline (repo facts + labelled assumptions)
fixtures/change_requests.json       8 fictional change requests
examples/worksheet.md               generated worksheet
examples/change-quotations.csv      generated quotation table
examples/worksheet.json             generated machine-readable bundle
```

---

Built by seat OP5-CINDER (Claude Opus 5) for work order UIOWA-133.
