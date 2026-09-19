# Deck-to-report agreement report

Deck `AIS-READOUT-EXAMPLE-2026` checked against report `AIS-ASSESS-EXAMPLE-2026`.

**Result: FAIL** - 1 error(s), 0 warning(s).

| Severity | Rule | Slide | Detail |
|---|---|---|---|
| error | R018_ROADMAP_PREREQ_AFTER_DEPENDENT | R-004 | R-004 is scheduled in 0-90 but its prerequisite R-002 is scheduled in 90-180, which is later; the plan cannot be executed in that order |

## Rules applied

| Rule | What it enforces |
|---|---|
| R001_SECTION_ORDER | Core sections are all present, once each, in the canonical readout order. |
| R002_DANGLING_CITATION | Every claim cites an id that exists in the report. |
| R003_FIGURE_DISAGREEMENT | A figure stated on a slide equals the report's value and unit. |
| R004_UNKNOWN_FABRICATION | A measure the report leaves UNKNOWN is not asserted as a number on a slide. |
| R005_OMITTED_PRIORITY_FINDING | Every high-priority report gap is cited by at least one core slide. |
| R006_UNVALIDATED_STRENGTH | A slide calls something a validated strength only if the report validated it. |
| R007_PHASE_DISAGREEMENT | A recommendation's phase on a slide equals its phase in the report roadmap. |
| R008_MAIN_CLAIM_WITHOUT_APPENDIX | A core slide stating a figure names an appendix slide that carries the same id. |
| R009_ORPHAN_APPENDIX | Every appendix slide is reachable from at least one core slide. |
| R010_AGENDA_OVERRUN | Core slide minutes fit the declared session length. |
| R011_MISSING_SPEAKER_NOTES | Every core slide carries at least one speaker-note prompt. |
| R012_DETAIL_IN_MAIN_BODY | Core slides stay inside the executive readability budget. |
| R013_UNRESOLVED_MEASURE | A cited measure name exists on the cited report object. |
| R014_DECISION_UNLINKED | A decision resolves to a recommendation whose phase agrees with the decision's. |
| R015_REPORT_MISMATCH | The deck's report_ref is the report it is being checked against. |
| R016_AGENDA_UNDERRUN | Core slide minutes use a reasonable share of the declared session (advisory). |
| R017_ROADMAP_DEPENDENCY_UNDECLARED | A roadmap that declares no prerequisites is reported as NOT ASSESSED, never as coherent. |
| R018_ROADMAP_PREREQ_AFTER_DEPENDENT | No roadmap prerequisite sits in a later phase than the item that depends on it. |
| R019_ROADMAP_DEPENDENCY_CYCLE | The roadmap's prerequisite graph is acyclic. |
| R020_ROADMAP_DANGLING_DEPENDENCY | Every declared prerequisite resolves to a recommendation on the roadmap. |

