# UIOWA-105 — Join economics and resource estimates to recommendations

Two component adapters plus an integrator that maps resourcing and economics onto the
recommendation register and the report tables, **keeping effort, recurring cost, cash cost and
released staff capacity separate, and counting shared work once.**

Built by seat `OP5-HALYARD` (Claude · Opus 5). Python 3 standard library only, no network,
deterministic (no clock, no RNG, sorted traversal).

## Run it

```
python3 integrate.py
python3 -m unittest discover -p "test_*.py"     # 102 tests across the lane
```

**Component authors — check your output before you land:**

```
python3 check_contract.py --explain  resource       # print the contract
python3 check_contract.py --resource  your_086_output.json
python3 check_contract.py --economics your_078_output.json
python3 check_contract.py --portfolio your_072_output.json
python3 check_contract.py --resource  your.json --json    # machine-readable
```
Exit status: `0` conformant, `1` non-conformant, `2` unusable input.

Run from a staging copy, before this lane sits next to the others under `revenue/`:

```
UIOWA_REPO_ROOT=/path/to/revenue python3 integrate.py
UIOWA_REPO_ROOT=/path/to/revenue python3 -m unittest test_integrate
```

Outputs land in `sample_output/`: `integrated.json` (full result + `content_digest`),
`resourcing_table.csv` (the report table, one row per recommendation), `portfolio_rollup.csv`
(the three-view accounting), `integration_report.md` (readable).

## What it joins

| Source | Status | What it supplies |
|---|---|---|
| `uiowa_rfq_18649_prioritization/fixtures/synthetic-recommendations.json` | **on `main`** | the recommendation register — 11 real `REC-SYN-*` ids |
| `uiowa_rfq_18649_ai_opportunity_portfolio/sample_output/portfolio.json` | **on `main`** | one-time hours, recurring FTE/yr, released capacity |
| `fixtures/resource_estimates.contract.json` | **contract fixture** | one-time effort, recurring staff load, specialist roles |
| `fixtures/economics.contract.json` | **contract fixture** | one-time cash, recurring cash, released capacity |

The resource-estimation kit (UIOWA-086) and the AI benefit / operating-cost model (UIOWA-078)
were not on `main` when this was built, so their adapters are written against **declared input
contracts** and exercised by fixtures labelled as fixtures. When those lanes land, point
`--resource-estimates` / `--economics` at their real output and the adapter tests say
immediately whether the contract held. The third adapter is proven end-to-end against a
component that *is* on `main`, so at least one path is real rather than self-referential.

## The design decisions worth knowing

**The register is extended, not mutated.** `uiowa_rfq_18649_prioritization/DATA_DICTIONARY.md`
states that any effect dimension other than `quality` / `security` / `delivery` is *refused
rather than ignored*. So an adapter that injected a cost dimension into that register would be
correctly rejected by its validator. Resourcing attaches as a **parallel record keyed by
`recommendation_id`**. No file in that lane is modified.

**Five ledgers, not four.** The work order names "effort, recurring cost, cash cost, and
released staff capacity". *Recurring cost* is genuinely two quantities — recurring staff load
and recurring cash — and merging them is how a resourcing table misleads. So:

| Ledger | Unit |
|---|---|
| `ONE_TIME_EFFORT` | hours (one-time implementation) |
| `RECURRING_EFFORT` | FTE-fraction per year |
| `ONE_TIME_CASH` | currency (one-time) |
| `RECURRING_CASH` | currency per year |
| `RELEASED_CAPACITY` | staff-hours released per year |

Adding across any two raises `LedgerUnitError`. The check is on the **unit string**, not the
dimension: one-time effort hours and released-capacity hours are both hours and would otherwise
add cleanly and silently into a number that means nothing. `test_no_two_ledgers_can_be_added`
walks all twenty ordered pairs.

**"The same work is not counted twice" — as accounting, not deduplication.** Work items carry a
`work_item_id`. Shared work is *both* things at once, so the tool publishes three numbers per
ledger:

| View | Answers | Shared work |
|---|---|---|
| `sum_of_per_recommendation` | "what does each recommendation cost" | repeated under each |
| `portfolio_rollup` | "what does the programme cost" | counted once |
| `shared_work_not_double_counted` | the difference | published explicitly |

Dropping shared work from one recommendation would understate that recommendation; keeping it in
both would inflate the programme. Neither is silently chosen. On the shipped fixture the
programme's one-time effort rolls up to **282 / 471 / 772 hours** while the per-recommendation
column sums to **407 / 677 / 1090** — the **125 / 190 / 318** difference is the shared CI change
and the shared training curriculum, named in the report.

**Adapters transport, they do not compute.** No labour rate is applied and no effort figure is
derived that an upstream kit did not state. Ranges, bases and source record ids survive the
mapping — `test_original_ranges_are_still_present_in_the_output` and
`test_resource_adapter_preserves_range_basis_and_source` assert it. The resource adapter refuses
to read cash and the economics adapter refuses to read effort, so the two cannot both claim the
same quantity.

**The crosswalk is asserted, never inferred.** The portfolio names candidates (`OPP-ESS-01`); the
register names recommendations (`REC-SYN-ESS-DEP-001`). Nothing in either file states the
correspondence, so `fixtures/crosswalk.json` records it with who asserted it and why. A candidate
absent from the crosswalk is reported as **unmapped**, not dropped — on the shipped run, five
work items land there. A title-similarity matcher would be manufacturing traceability.

**Disagreement between components is surfaced, not resolved.** The resource kit estimates
`WI-ESS-RELNOTES-001` at 60/90/140 hours; the opportunity portfolio's screening figure for the
same work is 25/45/80. The integrator reports the conflict, **holds that ledger at UNKNOWN**, and
`REC-SYN-ESS-DEP-001` shows `UNKNOWN` one-time effort rather than a quietly-chosen winner. Two
sources reporting the *same* range is corroboration and is not flagged.

**UNKNOWN is never zero, and a real zero is never UNKNOWN.** A total built from three known
amounts and one UNKNOWN is a **floor with a named gap**, marked `PARTIAL` and printed with a
`(floor)` marker. A total with no known contributor is `UNKNOWN`, not `0`. An *assessed* zero —
`{"low":0,"likely":0,"high":0,"basis":"assessed: no licence, internal effort only"}` — is a
complete total of zero. `REC-SYN-IAM-AI-001` has no resourcing record at all and reads
`NO_RESOURCING_DATA` across all five ledgers: not costed is not the same as costing nothing.

## A bug this found in its own first run

The first real run listed `WI-RIS-WINDOW-DOC-001` under "work shared by more than one
recommendation". It is not shared — it names `REC-SYN-ESS-XX-999`, which is not in the register.
A reference to a recommendation that does not exist was being counted as sharing, which repeated
16 hours in the per-recommendation sum that no row in the table ever charges. Fixed by resolving
each work item's references against the register before any expansion, and locked by
`test_dangling_reference_does_not_inflate_any_total`. The dangling id is still reported; it is
just no longer counted.

## What is real and what is draft

**Real and working:** the five typed ledgers, all three adapters, the merge with conflict
detection, the three-view accounting, the UNKNOWN handling, all four output writers, and the
102-test suite (45 integration, 33 conformance checker, 24 ledger bridge). The integrator runs against two components genuinely on `main` and produces the
files in `sample_output/`.

**Draft / placeholder:** every number in `fixtures/`. The contract fixtures are shaped like
UIOWA-086 and UIOWA-078 output, not taken from them. The crosswalk is a fictional reviewer's
assertion. The recommendation register and portfolio are themselves synthetic components.

## University inputs still UNKNOWN

1. **The real resource estimates and economics.** Everything in `fixtures/` is invented.
2. **The real crosswalk** between opportunity candidates and recommendations. Currently two
   asserted mappings out of six candidates.
3. **Recurring load for service-account rotation** — genuinely unestimated upstream (depends on
   whether rotation is automated), carried through as UNKNOWN.
4. **Recurring cash for assistive tooling** — depends on an undecided licensing model.
5. **Resourcing for `REC-SYN-IAM-AI-001`** — nothing names it.
6. **The correct resolution of the `WI-ESS-RELNOTES-001` conflict** — a human has to decide
   whether the screening figure or the build-up is right. The tool will not decide it.
7. **Currency and any escalation assumption** — carried as declared by the economics component
   (`USD`, flat). This lane does not convert, inflate or discount.

## `check_contract.py` — making the contract checkable by someone else

The 105 receipt promised that when UIOWA-086 and UIOWA-078 land, pointing the adapters at their
real output would say immediately whether the declared contract held. That promise initially
rested on tests exercising fixtures written by the same hand as the adapter — which proves the
adapter agrees with its author's guess, not that the contract is checkable by anybody else. This
closes that gap.

It reports a field-by-field verdict with exact JSON paths, **and** what the file would actually
do once adapted — which of the five ledgers populate, which land as UNKNOWN, which records end up
unmapped. A seat can see the downstream consequence of a schema choice before committing to it.

**It fails on what breaks a join:** an estimate written in words, a partial range, a boolean where
a number belongs, inverted bounds, a duplicate identifier, cash with no declared currency. Each
failure names the record and the path, so it is fixable without reading the adapter source.

**It tolerates what is harmless.** Unknown keys are reported as **carried extensions**, not
errors — refusing a field somebody took the trouble to emit is hostile, and UIOWA-102's own
completion criterion is that unsupported fields survive as explicit extensions rather than
disappearing. A field belonging to a *different* component's contract (a cash figure in a
resource file) is carried with a note saying which contract owns it and why it is not read here.
A point estimate warns rather than fails.

**The checker's own promise is tested.** `test_a_conformant_verdict_means_the_adapter_accepts_the_file`
asserts that CONFORMANT implies the real adapter runs the file — a checker that waves a file
through and then has the adapter refuse it is worse than no checker, because it sends a seat away
believing their output works. There is also a self-check: if the rules all pass but the adapter
still refuses, the output says *"the checker found no problem but the real adapter refused it —
that is a checker bug"* rather than reporting a silent pass.
`test_checker_self_reports_if_it_disagrees_with_the_adapter` proves that path fires.

`fixtures/resource_estimates.nonconformant.json` and `fixtures/economics.nonconformant.json` are
**deliberately broken fixtures** — every defect is one a component author could plausibly ship by
accident, so the checker's output can be demonstrated rather than described. On the broken
resource file it reports 5 fail, 1 warn, 3 info and exits 1.

## `ledger_bridge.py` — three seams between landed lanes

Found by scanning 52 landed lanes for numeric resourcing fields (21 files carry them).

**1. `uiowa_rfq_18649_capacity_feasibility` has no recurring ledger.** Its capacity unit is
"staff-hours available to this programme per phase window" and item effort is one-time
staff-hours per role; there is no recurring field anywhere in the lane. Its own `effort_source`
names UIOWA-086 and UIOWA-072 as upstreams, and both emit a recurring ledger. `to_roadmap_effort`
raises `BridgeRefusal` for any ledger that is not `ONE_TIME_EFFORT`; recurring load comes back in
`recurring_not_representable` instead. `test_recurring_load_is_refused_for_the_roadmap_effort_field`
and `test_no_recurring_figure_appears_inside_any_item_effort` hold it.

**2. `uiowa_rfq_18649_readout_deck` states recurring effort in "staff-hours per month".** This
lane uses FTE-fraction per year. Conversion needs an hours-per-FTE-year constant, so
`fte_year_to_hours_month` and `hours_month_to_fte_year` take one and refuse without it. The deck's
`RES-001` value of 4 staff-hours/month restates as 0.02308 FTE/yr; `RES-002` and `RES-003` are
UNKNOWN and stay UNKNOWN. `recurring_figures_agree` returns AGREE / DIFFER / UNKNOWN.

**3. Three recommendation-id conventions.** `REC-SYN-*` (prioritization, this lane), `R-NNN`
(readout deck, capacity feasibility), `OPP-*`/`WI-*` (opportunity portfolio, work items).
`identifier_islands` reports the split and produces no mapping between conventions.

Unestimated recommendations are listed in `unestimated` and are not emitted as items, so the
roadmap cannot read them as zero capacity consumed. Emitted metadata carries the receiving lane's
per-role, no-named-individual rule.

## Handoff

The adapters are plain callables over dicts (`adapters.adapt_resource_estimates(doc)`,
`adapters.adapt_economics(doc)`, `adapters.adapt_opportunity_portfolio(doc, crosswalk)`) with no
CLI-only logic, so the integration kit can carry them by import rather than reimplementing.
`integrate.build(...)` returns the whole result as a dict.

No product or vendor purchase recommendation, no certification/compliance/peer-percentile claim,
and no individual performance scoring appears anywhere in this lane.
