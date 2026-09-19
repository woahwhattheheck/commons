# UIOWA-072 — AI opportunity and value portfolio

A runnable method for comparing plausible AI opportunities in AIS delivery across the five
dimensions the work order names — **task suitability, expected benefit, input availability,
integration effort, measurable success** — and producing a ranking that stays revisable when
real University evidence replaces the placeholders.

Built by seat `OP5-HALYARD` (Claude · Opus 5). Python 3 standard library only, no network,
deterministic (no clock, no RNG, sorted traversal).

## Run it

```
python3 opportunity_portfolio.py
python3 opportunity_portfolio.py --composite          # also emit the blended score
python3 opportunity_portfolio.py --candidates mine.json --out /tmp/run
python3 -m unittest test_opportunity_portfolio -v
```

Outputs land in `sample_output/`:

| File | What it is |
|---|---|
| `portfolio.json` | Full machine-readable result, with a `content_digest` so a second operator gets a byte-identical run or a loud mismatch. |
| `portfolio_ranking.csv` | The ranking table — one row per candidate, every range as three columns. |
| `assumption_register.csv` | Every ranged assumption with its basis, its source, and whether it is decision-critical. |
| `portfolio_report.md` | The readable workbook, including the paste-ready **Input for the AI strategy section**. |

## What it does differently, and why

Most AI-opportunity workbooks fail the same two ways. They mash five dimensions into one
composite score, so a candidate nobody has evidence for outranks one with real evidence —
because "no evidence" quietly scored as some middling default. And they rank everything as
worth doing, which makes them a sales sheet rather than an assessment. The design here is
aimed at exactly those two failures.

**The five dimensions do not collapse into one number by default.** The primary output is a
per-candidate profile plus a rule-derived decision class: `PURSUE`, `PURSUE-BUT-EFFORT-HEAVY`,
`UNCERTAIN-NET-VALUE`, `DO-NOT-PURSUE`, `BLOCKED-UNKNOWN`. A composite exists behind
`--composite`, declares its weights, and is **refused per candidate** whenever any dimension is
UNKNOWN.

**UNKNOWN is a state, never a zero.** An absent input propagates to the candidate, blocks the
composite, and leaves it `UNRANKED — pending <dimension>` with a named evidence request. It is
never averaged away and never dropped from the table — a candidate that vanishes from a report
reads as "nothing here", which is a different and stronger claim than "we have not asked yet".
A partial range (`low` and `high` but no `likely`) is an error rather than something the tool
completes for you.

**Three ledgers that cannot be summed.** One-time implementation (`hours (one-time)`), recurring
maintenance (`FTE-fraction per year (recurring)`), and expected benefit (`staff-hours released
per year (recurring)`) are typed `Quantity` values. Adding across units raises `LedgerUnitError`.
Recurring load is deliberately carried as an FTE fraction so it cannot be mistaken for, or
concatenated onto, a one-time hour count. Note that two of these are measured in hours — which
is exactly why the check is on the unit string, not on the dimension.

Simple payback is reported as a ratio with its units intact (`one-time hours ÷ hours-per-year`
= years) and explicitly ignores the recurring ledger. Where recurring upkeep is larger than the
benefit, the tool raises `RECURRING-LOAD-EXCEEDS-BENEFIT` and **leaves both numbers alone**. It
does not do the subtraction for you: business-process hours released and technical upkeep
capacity consumed are drawn from different people and are not interchangeable.

**Benefit is an interval and is allowed to be negative.**
`volume × (baseline − assisted − checking − rework_rate × repair)`, with proper interval
arithmetic: the low bound takes the pessimistic corner of every term, and the product is taken
over all four corners so that a *negative* per-item result correctly gets **worse** with more
volume. Nothing is clamped at zero.

**Overlapping ranges report a tie.** Two candidates whose benefit intervals overlap could flip
order within their own stated ranges, so they share a rank and say `TIED — not separable on
current evidence`. Ranking is competition-style, so a two-way tie at 1 is followed by 3.
Tie grouping compares against the group *leader*, not the previous member — chaining would let a
run of slight overlaps collapse the whole portfolio into one meaningless tie.

**Revisability is a mechanism, not a disclaimer.** The work order asks that "rankings remain
revisable when University evidence arrives." Every ranged input carries a `basis`
(`ASSUMED` / `SYNTHETIC-FIXTURE` / `UNIVERSITY-EVIDENCE`) and a source note, and
`revision_impact` swings each one to its own stated bounds to find which ones actually change a
rank or a decision class. On the shipped fixture that is **7 of 46** — so 39 assumptions can move
anywhere inside their range without changing the answer, and 7 are where evidence is worth
collecting. UNKNOWN inputs are *not* swept: sweeping them would mean inventing bounds.

## The worked portfolio — all of it fiction

`candidates.json` carries six candidates across three fictional groups (ESS, RIS, IAM). The
fiction notice is machine-readable and is reprinted at the top of every generated report.
**None of it is a University of Iowa finding and none of it came from University systems.**
They are structurally different on purpose:

| Candidate | Shape it demonstrates | Result |
|---|---|---|
| `OPP-ESS-01` release-note drafting | Structured inputs, cheap build, light upkeep | `PURSUE`, rank 3 |
| `OPP-ESS-02` ticket auto-routing | Baseline task already fast; checking + rework can exceed it | `UNCERTAIN-NET-VALUE`, benefit straddles zero at `−1041.7 / −256.7 / 10.4` |
| `OPP-RIS-01` sponsor-policy checklists | Good fit, but the inputs must be built first | `PURSUE-BUT-EFFORT-HEAVY`, rank 1 (tied) |
| `OPP-RIS-02` effort-certification reminders | **The honest "don't use AI here"** — a template is already correct by construction | `DO-NOT-PURSUE`, benefit negative across the whole range |
| `OPP-IAM-01` plain-language denial explanations | **Cheap to build, expensive to keep** — 0.40-year payback, ~374 h/yr upkeep against ~138 h/yr released | `PURSUE`, rank 1 (tied), flagged |
| `OPP-IAM-02` quarterly access-review summaries | Genuinely unasked input availability | `BLOCKED-UNKNOWN`, unranked, carries its evidence request |

Measures carry numerator, denominator, cadence and a baseline state. A measure whose baseline has
not been taken renders as **baseline required**, never as `0%` — "we have not measured it" and
"it is currently zero" are different claims.

## Scope boundary (deliberate)

Benefit here is **screening arithmetic in staff-hours**. There are no labour rates, no currency,
no break-even and no cash conversion — that is the AI benefit and operating-cost model's job
(UIOWA-078, `ZZ-KESTREL-V78`). Detailed effort build-up is the resource estimator's job
(UIOWA-086, `ZZ-Kestrel-42`). Both are consumed here as declared input contracts: replace the
`one_time_implementation_hours` and `recurring_maintenance_fte_per_year` ranges in
`candidates.json` with their outputs and everything downstream recomputes. This lane does not
re-implement either, and does not edit either lane.

This tool also **does not recommend buying anything.** It compares workflows. No product, no
vendor, no procurement recommendation appears in any output.

## What is real and what is draft

**Real and working:** the engine, the interval arithmetic, the classification rules, the tie
logic, the revision-impact sweep, all four output writers, and the 39-test suite. Run it and it
produces the files.

**Draft / placeholder:** every number in `candidates.json`. The candidates are invented to
exercise the model, and the `bases` block on each one records that — currently `ASSUMED` or
`SYNTHETIC-FIXTURE` throughout, with not a single `UNIVERSITY-EVIDENCE` value anywhere.

## University inputs still UNKNOWN

The model runs on placeholders until these arrive. Nothing here is scored in their absence.

1. **Real candidate workflows.** These six are invented. The actual candidate list has to come
   from the AI-use inventory work, not from this file.
2. **Volumes.** Every `volume_items_per_year` is fiction. These are the inputs most likely to be
   directly available from existing systems, and the cheapest to replace.
3. **Baseline timings.** No timing has been collected for any task here. `baseline_minutes_per_item`
   is the assumption that most often decides whether a candidate is worth anything.
4. **Rework rates and repair cost.** Unmeasured everywhere. On `OPP-ESS-02` these are
   decision-critical — the sweep says so explicitly.
5. **One-time and recurring effort.** Placeholders pending UIOWA-086.
6. **Measure baselines.** Three measures across the fixture are `NOT-BASELINED`, including every
   measure on `OPP-IAM-02`.
7. **`OPP-IAM-02` input availability.** Genuinely unasked: whether prior quarterly access-review
   records are retained in a comparable form. This is why it is `BLOCKED-UNKNOWN` rather than
   scored low.

## Guardrails the tests hold

`test_opportunity_portfolio.py` — 39 tests under `unittest`, including hostile and missing-data
cases. The ones that matter most:

- `test_one_time_and_recurring_cannot_be_added` / `test_benefit_cannot_be_added_to_either_effort_ledger`
- `test_missing_estimate_stays_unknown`, `test_unknown_candidate_is_unranked_but_still_listed`
- `test_composite_is_refused_when_any_dimension_is_unknown`
- `test_negative_benefit_is_reported_not_clamped`, `test_more_volume_makes_a_losing_workflow_lose_more`
- `test_overlapping_intervals_share_a_rank`, `test_tie_grouping_does_not_chain_the_whole_portfolio`
- `test_upkeep_larger_than_benefit_is_flagged_not_netted`
- `test_unbaselined_measure_is_not_recorded_as_zero`
- `test_csv_guard_preserves_negative_numbers` — the formula-injection guard must neutralise
  `=SUM(...)` and `@cmd` **without** mangling `-346.0`, because negative benefit is a result this
  tool is specifically built to be able to report
- `test_partial_range_is_an_error_not_a_filled_in_default`, `test_non_numeric_estimate_is_rejected_not_coerced`,
  `test_inverted_range_is_rejected_rather_than_silently_sorted`, `test_cli_reports_a_data_error_instead_of_crashing`

No certification claim, no compliance claim, no peer-percentile claim, and no individual
performance scoring appears anywhere in this lane.
