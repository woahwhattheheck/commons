# UIOWA-111 — Integrated AI decision case (quality × lifecycle × economics)

Work order: *Connect AI evaluation, lifecycle, and economics.* Build a fictional
document-assistance example whose quality measurements, version history, analyst
checking effort, and cost assumptions feed the existing AI kits.

**Complete when:** a beneficial case and an unfavourable case are distinguishable
from their inputs, and changed assumptions flow through the explanation.

Everything in this directory is **synthetic fiction**. No University of Iowa
document, measurement, effort figure, rate, or cost appears anywhere in it.

---

## The problem this exists to solve

An AI-assistance business case has one number that is cheap to measure and
flattering: **generation time**. Six minutes against ninety-five is a 15×
headline and it is genuinely true. It is also the wrong basis for a decision,
because the document still has to be checked, repaired, accepted, and then
maintained — and that tail is where assisted drafting either pays for itself or
quietly doesn't.

So the two required cases are built to make that concrete:

| case | generation headline | verdict | net value over horizon |
|---|---|---|---|
| `fixtures/beneficial.json` | **15.75×** faster | `BENEFICIAL` | +17,640 to +58,740 |
| `fixtures/unfavourable.json` | **22.00×** faster | `UNFAVOURABLE` | −21,780 to −756 |
| `fixtures/undecidable.json` | UNKNOWN | `UNDECIDABLE` | UNKNOWN |

**The workflow that loses money has the better headline.** That inversion is
not a penalty term. It is produced by recorded `REWORK_AFTER_ACCEPT` events —
fabricated references that survived review and came back after the document was
accepted — and it disappears the moment you measure only the drafting step.

## How the guardrails work

**Effort is never an input.** There is no `checking_minutes_per_doc` field to
fill in optimistically. Effort is derived from a recorded version history of
`AUTHOR` / `GENERATE` / `CHECK` / `REPAIR` / `ACCEPT` / `REWORK_AFTER_ACCEPT` /
`MAINTENANCE_EDIT` events, and the ledger separates **pre-acceptance** from
**post-acceptance** cost. You cannot state a cost this model accepts without
also stating the events that produced it.

**UNKNOWN is a sentinel with no arithmetic.** `model.UNKNOWN` raises
`UnknownError` on any operation. An unrecorded checking step is not zero
minutes, and a document with no `ACCEPT` event is not a cheap success — it is
an undelivered one. Both are reported as named evidence gaps, and **any** gap
in a variant makes the whole case `UNDECIDABLE`. Incomplete documents are *not*
dropped so the rest can be averaged: the unrecorded steps are exactly the ones
most likely to be expensive, so excluding them biases the result in the
direction everybody already wants. An unbounded unknown cannot be bounded out.

**Minutes, money and volume are separate types.** Combining them raises
`UnitError`.

**Net value is an interval whose bound is the observed spread** across the
recorded documents — not an invented ±20% band — pushed through all sixteen
corners of the declared assumption ranges. `BENEFICIAL` requires the entire
range above zero, `UNFAVOURABLE` the entire range below; anything crossing zero
returns `NET_VALUE_UNCERTAIN` rather than a sign the evidence does not support.

**Quality is reported separately and never averaged into the money.** Fabricated
references that survived into accepted documents raise `quality_risk` whatever
the cost result says. A cheaper document that is wrong is not a better outcome.

**The explanation is audited against itself.** Every rendered line that states a
quantity must cite a record ID, and every cited ID must resolve to a record in
the case. `audit_explanation()` re-reads the *rendered text* — not the data
structure that produced it — so a renderer bug that drops a citation is caught
rather than trusted away. Failures are `UNCITED_QUANTITY` and
`DANGLING_CITATION`, and the CLI exits **1** if the audit fails: this tool will
not emit an unsourced number.

## Run it

```bash
python3 ai_decision_case.py --case fixtures/beneficial.json
python3 ai_decision_case.py --case fixtures/unfavourable.json --sweep
python3 ai_decision_case.py --case fixtures/undecidable.json --format json
python3 ai_decision_case.py --case fixtures/beneficial.json \
        --set analyst_hourly_cost=40 --diff
python3 -m unittest test_ai_decision_case -v
```

Python 3 standard library only. No network. No clock, no RNG, sorted traversal —
two runs on the same case produce byte-identical output (verified: the same
sha256 across repeat runs).

## "Changed assumptions flow through the explanation"

A mechanism, not a disclaimer. `--set` re-runs the case and `--diff` prints the
line-level change. Real output from `--set analyst_hourly_cost=40`:

```
-Over the declared horizon the net effect lies between 17,640 and 58,740 currency units.
+Over the declared horizon the net effect lies between 10,080 and 58,740 currency units.
-| analyst_hourly_cost | 85.00 currency_per_hour | 70.00–110.00 | ASSUMED |
+| analyst_hourly_cost | 40.00 currency_per_hour | 40.00–110.00 | OVERRIDE |
```

`--sweep` then classifies every assumption by **re-running the decision at its
own declared bounds** — measured, not argued. On all three cases the result is
the same and it is not where attention usually goes:

> `analyst_hourly_cost`, `documents_per_month` and `evaluation_horizon_months`
> are all **`SCALES_ONLY`**. They are strictly positive multipliers on a signed
> quantity, so they change how big the answer is and can never change its sign.
> **The cost assumptions cannot decide whether assistance helps.** The recorded
> checking and rework effort decides it.

`--sweep` also reports the break-even margin in minutes per assisted document:

- beneficial case: the verdict survives **+69.98** minutes of extra checking per
  document before it becomes `NET_VALUE_UNCERTAIN` — a wide margin.
- unfavourable case: only **−2.99** minutes. That verdict is *thin*, and the
  tool says so rather than presenting it as settled.

## What is real and what is draft

**Real and runnable now:** the loader and its validation, the lifecycle ledger,
the interval arithmetic and verdict rules, the citation audit, the sensitivity
sweep and break-even search, the CLI, and 34 passing tests (normal and `python -O`).

**Draft / illustrative:** all three cases, every effort figure, every quality
measurement and every cost assumption. They are shaped to demonstrate the three
verdicts and are not estimates of anything real.

## University inputs still UNKNOWN

None of these are supplied, none are guessed, and none default to a value:

- the **loaded hourly cost** of the staff who would do the checking
  (`analyst_hourly_cost` is a placeholder with a declared range);
- the real **document volume** per month for any candidate workflow
  (`documents_per_month`);
- the **evaluation horizon** leadership wants the case argued over;
- **any actual version history** — no real generate/check/repair/rework timings
  exist for any University workflow, and this kit will return `UNDECIDABLE`
  rather than estimate them;
- **any actual quality measurement** of assisted output against a known answer key;
- which workflows are even candidates.

Until those arrive, every number in `out/` is fiction demonstrating the
mechanism, and the correct reading of this component is *"here is the shape of
the argument and the evidence it would require"* — not *"here is what AI is
worth at Iowa."*

## Files

| file | role |
|---|---|
| `model.py` | typed quantities, the UNKNOWN sentinel, record types, loader + validation |
| `case.py` | lifecycle ledger, quality summary, interval arithmetic, verdict rules |
| `explain.py` | cited explanation renderer **and** the citation auditor |
| `sensitivity.py` | assumption override, classification, break-even search, explanation diff |
| `ai_decision_case.py` | CLI |
| `fixtures/` | three synthetic cases plus one hostile malformed case |
| `out/` | generated explanations, decision JSON, and the assumption-flow demo |
| `test_ai_decision_case.py` | 34 unittest cases incl. hostile/missing-data |

## Scope boundary

This component does **not** call or simulate any AI service — it scores
*recorded* outputs. It produces no maturity score, no certification or
compliance claim, no peer percentile, and no individual performance scoring:
the unit of analysis is a document and a workflow, never a person. It
recommends no product or vendor.
