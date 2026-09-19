# Roadmap coherence report

**Verdict: NOT ASSESSED**

> The report roadmap declares no prerequisites, so its coherence has not been assessed. This is reported as NOT ASSESSED rather than as a pass.

| Severity | Rule | Subject | Detail |
|---|---|---|---|
| warning | RC009_PROSE_DEPENDENCY_UNBACKED | S-A4 | slide S-A4 states R-004 depends on R-001, R-002, but those are not declared in the report roadmap. A dependency that exists only as a sentence cannot be checked: 'R-004 depends on R-001 and R-002 having reported, which is why it sits at 180+.' |
| warning | RC009_PROSE_DEPENDENCY_UNBACKED | S-A4 | slide S-A4 states R-002 depends on R-001, but that is not declared in the report roadmap. A dependency that exists only as a sentence cannot be checked: 'R-002 depends on R-001 because the approval record is what the restore is verified against.' |
| warning | RC001_REPORT_ROADMAP_NOT_ASSESSED | report | no roadmap item declares depends_on, so the report's dependency coherence is NOT ASSESSED. That is not the same as coherent: a plan nobody expressed prerequisites for has not been shown to be executable. |

## Declared prerequisites (report)

- `R-001` <- (none)
- `R-002` <- (none)
- `R-003` <- (none)
- `R-004` <- (none)

## Rules

| Rule | What it enforces |
|---|---|
| RC001_REPORT_ROADMAP_NOT_ASSESSED | A report roadmap declaring no prerequisites is NOT ASSESSED, never coherent. |
| RC002_REPORT_PREREQ_AFTER_DEPENDENT | No report prerequisite sits in a later phase than its dependent. |
| RC003_REPORT_DEPENDENCY_CYCLE | The report roadmap's prerequisite graph is acyclic. |
| RC004_REPORT_DANGLING_DEPENDENCY | Every declared prerequisite resolves to a recommendation on the roadmap. |
| RC005_PLAN_PHASE_DISAGREES_WITH_REPORT | The plan's phase for a recommendation equals the report's, naming both artifacts. |
| RC006_DECK_PHASE_DISAGREES_WITH_REPORT | The deck's phase claim for a recommendation equals the report's. |
| RC007_PLAN_DEPENDENCY_MISSING_FROM_REPORT | A prerequisite the plan enforces is also declared in the report. |
| RC008_REPORT_DEPENDENCY_MISSING_FROM_PLAN | A prerequisite the report declares is also enforced by the plan. |
| RC009_PROSE_DEPENDENCY_UNBACKED | A dependency asserted in deck prose is backed by a declared field. |
| RC010_DEPENDENCY_NEVER_PRESENTED | A dependency that drives the schedule is mentioned somewhere in the deck. |
| RC011_RECOMMENDATION_MISSING_FROM_PLAN | Every roadmap recommendation has at least one work item in the plan. |
| RC012_PLAN_ITEM_WITHOUT_RECOMMENDATION | Every plan item links back to a recommendation on the roadmap. |
| RC013_COLLAPSE_RULE_DECIDES | A phase disagreement that exists only under one collapse rule is named as such. |

