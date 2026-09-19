# Cross-artifact roadmap coherence (OPS lane)

Checks that a report's roadmap, a work plan and a readout deck describe the same, executable plan.

Each of those artifacts has its own checker and each can pass on its own. Nothing checked the
triangle. A phase corrected in one artifact and not the others, or a dependency that exists only as
a sentence in a speaker note, passes every individual check.

## Why this lane exists

The deck-to-report agreement checker in `uiowa_rfq_18649_readout_deck` (UIOWA-088, commit
`4056207a`) reported `PASS - 0 error(s), 0 warning(s)` on a report whose roadmap placed `R-004`
("extend the practice to the remaining groups") in `0-90`, before the recommendations that
establish the practice, with a deck that agreed with it perfectly. Verbatim, before the fix:

```
Result: PASS - 0 error(s), 0 warning(s).
exit=0
```

The dependency was already in the deck, as prose on appendix slide S-A4: *"R-004 depends on R-001
and R-002 having reported, which is why it sits at 180+."* The report format had no field to hold
it, so no rule could check it.

Two changes followed:

1. `depends_on` became a real field on report roadmap items, and UIOWA-088 gained rules R017-R020.
   The same pair now returns `FAIL - 1 error(s)` naming `R018_ROADMAP_PREREQ_AFTER_DEPENDENT`. The
   broken report and its agreeing deck ship in that lane as committed artifacts.
2. This lane, for the part no single artifact's checker can see: agreement across all three.

## Run it

```bash
cd revenue/uiowa_rfq_18649_roadmap_coherence

python3 roadmap_coherence.py check  --report data/coherent-report.json \
                                    --plan   data/coherent-plan.json \
                                    --deck   data/coherent-deck.json

python3 roadmap_coherence.py report --report data/coherent-report.json \
                                    --plan   data/coherent-plan.json \
                                    --deck   data/coherent-deck.json \
                                    --outdir examples

python3 roadmap_coherence.py rules
python3 -m unittest -v test_roadmap_coherence
```

`--plan` and `--deck` are optional; with only `--report` it checks the report's roadmap alone.
Python 3 standard library only, no network, deterministic.

## Files

| Path | What it is |
|---|---|
| `roadmap_coherence.py` | Engine + CLI. Thirteen rules. |
| `data/coherent-report.json` · `coherent-plan.json` · `coherent-deck.json` | The agreeing set. |
| `data/incoherent-report.json` | `R-004` scheduled before `R-002`. |
| `data/drifted-plan.json` | Plan work for `R-002` slipped to `180+`; report still says `90-180`. |
| `data/undeclared-report.json` | No `depends_on` anywhere — the shape every roadmap artifact had before this lane. |
| `examples/` | Generated: ASCII three-way table, Markdown report, phase-agreement CSV, and a check run per broken fixture. |
| `test_roadmap_coherence.py` | 36 tests, `unittest`. |

## Rules

| Rule | What it enforces |
|---|---|
| RC001_REPORT_ROADMAP_NOT_ASSESSED | A roadmap declaring no prerequisites is NOT ASSESSED, never coherent. *(warning)* |
| RC002_REPORT_PREREQ_AFTER_DEPENDENT | No report prerequisite sits in a later phase than its dependent. |
| RC003_REPORT_DEPENDENCY_CYCLE | The report roadmap's prerequisite graph is acyclic. |
| RC004_REPORT_DANGLING_DEPENDENCY | Every declared prerequisite resolves to a recommendation on the roadmap. |
| RC005_PLAN_PHASE_DISAGREES_WITH_REPORT | The plan's phase for a recommendation equals the report's, naming both artifacts and both values. |
| RC006_DECK_PHASE_DISAGREES_WITH_REPORT | The deck's phase claim equals the report's. |
| RC007_PLAN_DEPENDENCY_MISSING_FROM_REPORT | A prerequisite the plan enforces is also declared in the report. *(warning)* |
| RC008_REPORT_DEPENDENCY_MISSING_FROM_PLAN | A prerequisite the report declares is also enforced by the plan. *(warning)* |
| RC009_PROSE_DEPENDENCY_UNBACKED | A dependency asserted in deck prose is backed by a declared field. |
| RC010_DEPENDENCY_NEVER_PRESENTED | A dependency that drives the schedule appears somewhere in the deck. *(warning)* |
| RC011_RECOMMENDATION_MISSING_FROM_PLAN | Every roadmap recommendation has work behind it. |
| RC012_PLAN_ITEM_WITHOUT_RECOMMENDATION | Every plan item links back to a recommendation. |
| RC013_COLLAPSE_RULE_DECIDES | A phase disagreement that exists only under one collapse rule is named as such. *(warning)* |

## NOT ASSESSED is not a pass

A report with no `depends_on` on any roadmap item reports **NOT ASSESSED**, never `COHERENT`. An
empty list `[]` is a different, accepted answer: considered, none. Absence of a declaration is not
a clean bill of health.

Prose dependencies are read conservatively: only a sentence literally of the form
`<rec> depends on <rec>[, <rec>]` is treated as a claim. A looser parser would manufacture findings
about prose that was not asserting anything.

## The collapse rule

A plan has many work items per recommendation; a report roadmap has one phase per recommendation.
Collapsing many into one requires a rule, and the first real cross-lane run exposed that the two
artifacts meant different things by "the phase of a recommendation": when the work starts, versus
when it completes.

The rule is therefore named, selectable (`--rec-phase-rule last|first`), and printed in the finding.
Default is `last`: a recommendation is not delivered until its final item is. When a disagreement
exists under one rule and not the other, `RC013_COLLAPSE_RULE_DECIDES` says so, because that is a
semantic mismatch between artifacts rather than a scheduling error.

### Result of the first cross-lane run

Run against the two landed lanes (`uiowa_rfq_18649_readout_deck` report and deck,
`uiowa_rfq_18649_capacity_feasibility` item set):

```
error   RC005_PLAN_PHASE_DISAGREES_WITH_REPORT  R-003
  report roadmap says R-003 is in '0-90'; the plan's last item for it is in '90-180'
  (collapse rule: last -- a recommendation is not delivered until its final item is)
warning RC013_COLLAPSE_RULE_DECIDES             R-003
  R-003 agrees with the report under the 'first' rule and disagrees under 'last'
```

Both lanes pass their own checkers. The disagreement is real and is left reported rather than
auto-corrected: which reading the report intends is a decision for whoever owns the report, and the
tool does not make it.

## CSV provenance

Every CSV this lane writes carries a provenance statement as line 1:

```
# PROVENANCE: SYNTHETIC. FICTION. ...
```

A CSV is the most portable artifact here and the one most likely to be opened away from this
README. The statement is taken from the source data's `meta.provenance`, or implied from a
`meta.fiction_notice`; a source that declares neither produces
`PROVENANCE NOT DECLARED IN SOURCE`, never a guess in either direction — the requirement is a
provenance statement, not a fiction label, and a real measurement must not be stamped synthetic.

The banner is a `#` line, so a reader that takes line 1 as the header will misparse. The
documented contract is `read_csv_rows(path)`, which returns `(statement, rows)` and strips leading
`#` metadata lines. A test asserts the naive read misparses and the contract does not.

## What is real and what is draft

**Working now:** the thirteen rules, the graph checks, the prose parser, the three renderers, the
CLI, determinism, and the 36 tests.

**Draft:** the field names (`rec`, `phase`, `depends_on`, `proposed_phase`, `prerequisites`) follow
the shapes the readout-deck and capacity-feasibility lanes already emit. Other lanes may name these
differently; identifier reconciliation across the kit is UIOWA-103's lane, not this one.

**Fiction:** every fixture. Northgate State University does not exist. Nothing here is a University
of Iowa finding, recommendation or plan.

## University inputs that stay UNKNOWN

- The real recommendation set, its real phase assignments, and its real prerequisites.
- Whether a recommendation's roadmap phase is intended to mean start or completion — the
  `RC013` ambiguity above is unresolved and is not guessed at.
- Which dependencies the assessment team considers binding versus preferred. Everything here is
  binding-or-absent; a softer category does not exist in the data yet.

## Scope limits

No maturity score, no rating, no certification or compliance verdict, no peer percentile, no
individual performance scoring. The checker reports disagreements between artifacts; it does not
choose which artifact is right and never edits one.
