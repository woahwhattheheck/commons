# UIOWA-030 — Feasible one-to-two-level improvement paths

A method plus an executable path checker: translates a stated current practice profile into
a realistic next one or two maturity levels, and **refuses any target the path's evidence
cannot actually reach**.

Offline, Python 3 standard library only.

## Status

| Thing | Status |
|---|---|
| `30-progression-method.md` | **The named deliverable.** The method, with worked paths for all four assessment areas. |
| `progression.py` | **Working code.** 44 tests, all passing. |
| `test_progression.py` | **Working tests**, including all five refusal classes. |
| `fixtures/profiles.json` | **FICTION.** Six invented practice profiles. |
| `fixtures/paths.json` | **FICTION.** Eleven invented candidate paths; five written to be refused. |
| `examples/` | Generated output. |

Every profile is a synthetic assumption set. None describes the University of Iowa's
practice, and no level, path or effort figure here is a University baseline, a finding or a
commitment.

## Run

```bash
python3 progression.py
python3 progression.py --markdown-out out.md --csv-out out.csv --json-out out.json
python3 -m unittest -v test_progression.py
python3 -O -m unittest test_progression.py
```

## How the completion bar is implemented

The order's bar is *"no aspirational endpoint or unverified University baseline is presented
as fact."* Four executable checks, not four paragraphs of prose:

1. **A target must be earned by the evidence the path produces.** Each step declares the
   kind of evidence it creates; the kind bounds the level it can support, whatever the
   effort. A path reaching for level 4 with 22 person-days of documents is refused, because
   documents cap at level 2. The refusal names the evidence kinds that would reach the
   target. Tested at 1 day and at 1000 days — same refusal.
2. **At most two levels.** The boundary is inclusive; a gain of 3 is refused as an
   aspiration by name. A target at or below the baseline is refused too.
3. **Advancement must be observable.** A step with no stated observable is refused and
   named, not emitted with a TBD.
4. **An unestablished baseline produces no path.** `unassessed`, `not_applicable`, or no
   stated evidence gives `maturity_rank = None` — never a fallback to level 1 — and the
   refusal names what would settle it. In CSV the cell reads `UNKNOWN`, never blank and
   never `0`, so an unassessed practice cannot sort to the bottom of the scale.

Supporting rules: an evidence assumption with no stated basis is refused (an assumption with
no origin is indistinguishable from an observation); an unrecognized evidence kind is refused
(an uncapped kind could buy any level); an unmet prerequisite is refused unless declared
`EXTERNAL:`, in which case it is surfaced as somebody else's to deliver; an unestimated step
makes the effort total a **floor**, labelled, never completed to a round number.

## Result over the synthetic set

```
FEASIBLE                      6
BASELINE_UNKNOWN              1
REFUSED_EVIDENCE_CAP          1
REFUSED_ASPIRATIONAL_JUMP     1
REFUSED_NO_OBSERVABLE         1
REFUSED_UNMET_PREREQUISITE    1

assessment areas with a feasible path: 4 of 4
```

| path | area | variant | baseline → target | effort |
|---|---|---|---|---|
| `PATH-SYN-SD-01` | software development | direct | 3 → 4 | 7 d |
| `PATH-SYN-SEC-01` | security | direct | 2 → 3 | 5 d |
| `PATH-SYN-SEC-02` | security | limited capacity | 2 → 3 | 2 d |
| `PATH-SYN-SEC-06` | security | shared service | 3 → 4 | 7 d |
| `PATH-SYN-DEP-01` | deployment | direct | 4 → 5 | 8 d |
| `PATH-SYN-AI-01` | AI readiness | limited capacity | 3 → 4 | 1 d floor |

The limited-capacity variant reaches the **same** target level for less effort by narrowing
the first cycle's population and writing the scope limit down — a different route, not a
lower ambition. A test asserts the target levels match and the effort differs.

## Relationship to other lanes

Consumes the **UIOWA-021** maturity anchor contract (`maturity_rank`, `maturity_label`,
`assessment_status`, and the evidence-kind caps) as declared in the build channel by
`OP5-EMBER`. This lane does not define a second maturity scale and does not edit that lane.
A test asserts `30-progression-method.md` states the same caps the code enforces, so the
document cannot drift from the checker.

## Inputs still UNKNOWN

- Every profile, every effort figure, every skill need. All stated assumptions.
- Whether the evidence-kind caps are the right ones — UIOWA-021 owns them and may revise
  them.
- Whether two levels is the right maximum for this engagement.
- Which practices are in scope, and who owns each.
- Whether a given target level is worth reaching at all. A `FEASIBLE` verdict is not a
  recommendation.

---

Built by seat OP5-CINDER (Claude Opus 5) for work order UIOWA-030.
