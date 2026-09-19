# UIOWA-085 — dependency-aware phased roadmap planning

**Draft planning aid. Checked-in examples are entirely synthetic, not University findings.**

This kit turns recommendation records into a 0–90 / 90–180 / 180+ day planning view while keeping prerequisite conflicts, unestimated work, ownership questions and source references visible. It neither rates maturity nor replaces the existing assessment compiler, workbench, prioritization method or resource estimator.

Builder: **ZZ-QUARTZFIN-47 / GPT-6 Astra Pro**. Operation: `uiowa-085-quartzfin47-20260919`. Work record: Commons issue **#16127**. Python **3.10+**, standard library only for the planner and unit tests. The optional browser acceptance script needs an existing Playwright/Chromium installation; the planner does not install anything or contact a service.

## Run the actual sample

From this directory, use a **new** output directory each time:

```sh
python roadmap.py synthetic_recommendations.json /tmp/uiowa-roadmap-original
python roadmap.py /tmp/uiowa-roadmap-original/planning_table.csv /tmp/uiowa-roadmap-roundtrip
python -m unittest -v test_roadmap.py
python -O -m unittest -v test_roadmap.py
python -m py_compile roadmap.py test_roadmap.py
```

Open the generated `roadmap.html` in a browser. It is self-contained, with no JavaScript, network requests or telemetry. The narrow-screen table has its own keyboard-focusable horizontal scroll region; the whole page does not need to scroll sideways. The same information is available as `roadmap.md` and `roadmap.json`. `planning_table.csv` is the editable source table plus clearly derived planning columns. `manifest.json` records the exact output hashes and is written last.

The demonstration returns:

```json
{"phase_at_risk":1,"phase_conflicts":1,"planned":10,"total":12,"unscheduled":2}
```

A successful run means a valid report was produced, **not** that every recommendation is feasible. `--require-plannable` still writes the report but returns exit code **3** for any unscheduled item, phase risk or phase conflict. Invalid input or filesystem errors return **2**; ordinary valid reports return **0**. An existing destination is never overwritten. An interrupted write may leave an incomplete new directory; absence of its final manifest distinguishes that condition. No pre-existing files are deleted as cleanup.

## Three-minute operator rehearsal

First inspect **R08 and R09**. R08 has no duration or owner; its dependent R09 receives no invented start or finish. In a copy of the exported CSV, set R08 `duration_days` to `[10, 15]` and `owner_role` to an explicitly fictional role. Re-run into a new directory. R09 becomes calculable while the original report stays unchanged.

Then inspect **R11 and R12**. R11 depends on R10, whose assumed duration is 80–110 days. R11 can start at D80–D110, so a phase-1 start is at risk. R12 depends on R11 and cannot start before D105: its phase-1 request is infeasible even under optimistic assumptions. Change the requested phases to `90-180` only as a documented hypothetical planning revision, then re-run. The planner never silently moves these requests or interprets revised dates as approval.

Finally inspect **R02/R04** and **R03/R05**. Each pair is dependency-independent, but parallel execution still requires actual staff capacity. R06 waits for both pilot paths and its second-phase floor, giving D90 start and D130–D150 finish in this synthetic example. R07 starts no earlier than D180. These are relative-day model results, not calendar bookings, staffing assignments or promised delivery dates.

## Input contract and formulas

`schema.json` is a portable shape description; `roadmap.validate` is the executable contract. Every record needs stable `id`, `title`, `group`, requested `phase`, `owner_role`, `depends_on`, `duration_days`, `finding_refs`, `evidence_refs`, `practice_change`, `observable_outcome` and `assumptions`. Unknown duration or owner is JSON `null`, not zero or an empty invented name. Groups are `ESS`, `RIS`, `IAM` or `DEPARTMENT`; this is an organizational label, not proof that any real group owns the work.

Duration is an inclusive **[minimum, maximum] range in elapsed calendar days**. It is not person-days, working days, a confidence interval, a probability distribution or a service commitment. Zero-duration milestones are valid and different from unknown duration. Every duration assumption should identify what real observation would change it.

Requested start phases are half-open horizons: `[0,90)`, `[90,180)`, and `[180,infinity)`. Day 90 is in the second phase; day 180 is in the third. For a row with known prerequisites and duration:

```text
start_min  = max(phase_start, each prerequisite.finish_min)
start_max  = max(phase_start, each prerequisite.finish_max)
finish_min = start_min + duration_min
finish_max = start_max + duration_max
```

`ON_PHASE` means both estimated start bounds fit the requested horizon. `AT_RISK` means only the optimistic bound fits. `OUTSIDE_PHASE` means even the optimistic bound misses it. Finishing in a later phase is separately marked `work_may_span_phase_boundary`; that alone does not constitute a start-phase conflict. The HTML shows possible work envelopes, not continuous committed occupation of those entire intervals.

Missing prerequisites, unknown durations and dependencies on unresolved work receive explicit statuses and null dates. A cycle leaves its members and downstream dependents unresolved; `CYCLE_OR_BLOCKED_BY_CYCLE` deliberately does not assert that every dependent is itself in a cycle. Independent components still produce useful estimates. Duplicate identifiers/keys, unsupported fields, invalid groups, negative/reversed durations and Boolean substitutes for integers are rejected.

The planner sorts identifiers and traverses iteratively. It does not impose a fake order on otherwise independent recommendations. Source list order is included in the canonical input fingerprint, so a reordered source can have a different input hash while yielding the same planning results.

## Editing and interchange

The CSV repeats `document_title`, `synthetic` and JSON-encoded `document_assumptions` on every row. They must agree across rows. Arrays use JSON inside a CSV cell: `[]`, `["R01","R04"]` or `[10,20]`; ordinary CSV quoting is handled by the writer. An empty duration cell represents unknown. The column names are part of the contract; do not rename them.

Input columns are editable. `planning_state`, start/finish bounds, `layer`, `status`, `phase_state` and `issues` are **derived**, ignored on import and recomputed. Editing a derived `APPROVED` status cannot promote a draft or clear a missing estimate. UTF-8, long locators, Unicode and multiline notes are covered by round-trip tests.

Formula-like leading text is apostrophe-prefixed in exported CSV and reversibly decoded by this importer. This is a CSV transport convention, not a guarantee about every spreadsheet application's import/save behavior. Preserve cell text and UTF-8 when using a spreadsheet editor; inspect changed inputs before adopting its export. No Excel formulas or macros are supplied.

## Assessment and integration seams

The planner accepts **already formulated draft recommendations**. It retains their finding IDs, exact evidence locators, proposed qualitative practice change and observable outcome; it does not authenticate sources, infer a favorable finding from a reference, prioritize automatically or emit a maturity score. Empty supporting references are flagged instead of filled in. The synthetic fixture's references resolve into `synthetic_evidence.md`, version `quartzfin47-example-v1`.

For a proposed one-to-two-level maturity progression, the assessment team must first establish the current practice from evidence and choose applicable anchors from its existing rating method. Use `practice_change` for the concrete next capability and `observable_outcome` for the evidence required to judge it. Review after the pilot, then propose a further step only if sustained-use and outcome evidence support it. The example illustrates baseline → practice pilot → reviewed adoption → sustained-outcome review; it does not predict a numeric institutional score.

* **084 prioritization:** preserve the producer's recommendation ID and ranking rationale; use this planner to expose dependency constraints on that prioritization, not to replace its score.
* **086 resources:** compare the producer's staffing/skill/maintenance estimates with these elapsed-duration assumptions. They are different units. No capacity reconciliation has been performed by this kit.
* **090 report visuals:** `roadmap.json` has `recommendations[]`, input fields plus nullable `start_min/start_max/finish_min/finish_max`, `phase_state`, `status`, `issues`, and `dependency_layers`. Render unknowns and requested-versus-feasible horizons distinctly; retain `planning_state` and `synthetic` labels. Field `id` is the stable recommendation join key.
* **098/100 integration/handoff:** use `plan(document)` and the CLI's outputs; maintain the parent compiler's authority and original assessment receipts separately. This input SHA is reproducibility metadata, not an evidence-authority root.

Real evidence, approved recommendations, staffing availability, priorities, effort estimates, external dependency windows and current maturity anchors remain inputs to collect during an actual authorized engagement. Do not commit private University, prime, staff or customer records into this public repository. No code here submits a bid, contacts anyone, selects products/vendors, changes access, signs an agreement, spends money or schedules a meeting.

## Files

`roadmap.py` implements the planner, strict input/CSV interchange and exports. `test_roadmap.py` supplies deterministic tests and a real CLI round-trip. `synthetic_recommendations.json` and `synthetic_evidence.md` form the coherent fictional sample. `schema.json` describes its input shape. `browser_acceptance.py` exercises actual browser layout and disclosures when optional QA dependencies are already available. `VALIDATION.md` records measured runs and their limitations. `example_bundle.zip` contains the generated sample outputs; source inputs remain separate and editable.
