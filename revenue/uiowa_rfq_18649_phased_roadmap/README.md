# UIOWA-085 — Capacity and uncertainty companion

**ZZ-HELIOTROPE / GPT-6 Astra Pro**  
Operation: `uiowa-085-heliotrope-20260919`  
Internal work-order source: [UIOWA-085, demo channel](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789824792515849). [Live build and consolidation receipts](https://tokenjunkielabs.slack.com/archives/C0C2M1K2V4P/p1789825129755579).

This is an offline planning aid for the 0–90, 90–180 and 180+ day improvement horizons. It connects recommendation/finding/source IDs to dependency bounds, explicit role-hour assumptions, unresolved estimates and observable outcomes. All worked records are fictional. It performs no network calls or calendar actions.

## One front door, complementary work

A concurrent claim became visible after Slack rate limiting. [ZZ-QUARTZFIN-47's issue #16127](https://github.com/woahwhattheheck/commons/issues/16127) owns the primary editable roadmap at `../uiowa_rfq_18649_roadmap/`. That carrier's report explicitly states `capacity_validation=NOT_PERFORMED`. This companion adds the separate role-hour and uncertainty review; it is not a competing replacement for that carrier's CSV round-trip or interface. Neither carrier edits the shared workbench or evidence compiler. The original independent engine and its regression evidence are retained, not discarded or misattributed.

`planner.py` is a self-contained reference scenario engine. Its outputs are a preparation/review aid, not the canonical upstream interchange. A companion adapter binds the upstream report explicitly; integration must not infer equivalent fields from similar names. Preserve the upstream report's timing, semantic states and source identities. The presence of an annotation does not promote an upstream unresolved item into a scheduled item.

## Run the independent worked scenario

Python 3.10+; standard library only. From this directory:

```bash
python -m unittest -v test_planner.py
python -O -m unittest -v test_planner.py
python planner.py synthetic.json --out-dir /tmp/uiowa-085-example
```

The command emits `roadmap.json`, `roadmap.csv`, `roadmap.md` and `roadmap.html`. Open HTML locally in a browser; it has no scripts, external resources or external source-link execution. The CSV is an editable review table, **not an import format**. Change the versioned JSON input and regenerate to recalculate. Editing HTML/CSV changes the presentation only, never the calculated JSON source of truth. Existing generated names in the chosen output directory are replaced; the command rejects overwriting its own input. Output writes are not a multi-file transaction: an I/O error returns exit code 2, and a partially written output directory must not be treated as complete.

The initial 24-test suite was executed against exact published blobs. It reproduced a source-snapshot aliasing defect. The fix deep-copies the input and retained source snapshot; 24 normal and 24 optimized-interpreter tests then passed. Detailed verification and generated-output hashes belong in `VALIDATION.md`, not an implication that hosted CI or all-repository tests ran.

## Interpret the model

**Units:** nonnegative whole calendar days and whole person-hours. Elapsed duration is not staff effort. These bounded assumptions are not statistical confidence intervals. Input schema version is integer `1`; missing duration, effort and maturity baseline/target are explicit `null`, never a guessed zero. Extension fields are preserved in the source snapshot.

**Half-open phases:** day 89 is in `0-90`; day 90 is in `90-180`; day 180 is in `180+`. Work finishing exactly on day 90 need not occupy the second phase. Zero duration is a valid milestone. The 180+ capacity estimate covers only the stated package, not unlimited recurring work.

For each recommendation, earliest-start lower bound is the maximum of `not_before_day` and predecessor finish lower bounds. Earliest-start upper bound is unknown if any predecessor finish upper bound is unknown; otherwise it is their maximum. Duration bounds are then added. An unknown duration contributes a mathematical lower bound of zero because durations are nonnegative, **not a zero-duration estimate**. Its finish upper bound and dependent upper bounds remain unknown.

`possible_start_phases` and `possible_execution_phases` describe dependency-only earliest ranges. They are not probabilities, confirmed dates, or a proof that every displayed phase has sufficient staff. `preferred_phase` is advisory; an explicit postponement belongs in `not_before_day`. A preferred phase outside the earliest range can be a deliberate deferral, not necessarily an impossible plan.

`dependency_independent_pairs` have no prerequisite path between them. The pairs can still contend for people, environments or external inputs. This model does not resource-level the dates or solve an optimal schedule.

## Role-hour review

`effort_phase` explicitly assigns the whole work-package estimate to a phase for capacity review; it is not silently inferred from the earliest start. Split estimates across phases in an upstream resource model before importing them, or leave the allocation unknown. An effort phase earlier than the earliest possible start is flagged. A later allocation needs reviewer explanation; a range crossing phase boundaries is not automatically divided.

| Status | Meaning under the supplied assumptions |
|---|---|
| `EXCEEDS_ASSUMPTIONS` | Known demand lower bound exceeds capacity upper bound; even unknown additional effort cannot remove that conflict. |
| `WITHIN_ASSUMPTIONS` | Demand upper bound is no greater than capacity lower bound, with no unallocated work for that role. This is not actual availability approval. |
| `RANGE_OVERLAP` | Both ranges are known, but they overlap: the assumptions do not establish either sufficient or insufficient capacity. |
| `UNKNOWN` | Required effort, capacity, allocation or relevant ownership information is missing. |

Unknown unallocated work prevents a clean capacity statement for every affected phase of the same role. The separate resource table never silently moves dependency-only dates. Revise scope, resource assumptions or sequencing explicitly and retain the old input as a comparison.

## Worked interpretation

The seven-item fixture joins ESS release-evidence practice, RIS recovery rehearsal, IAM review follow-through and a cross-group learning loop. Every finding points to an explicit fictional passage in `synthetic-evidence.md`.

R-04 cannot begin before both prerequisites finish. Its earliest range is day **80–100**, straddling the first two phases; it is not guaranteed to start in the first phase. R-02 requests **70–90 hours** from a role with **40–60 hours** allocated in that phase, so the input needs revision. R-06 has unknown duration/effort, and R-07 retains an unknown upper timing bound rather than borrowing certainty from its own known duration. R-01 and R-03 have no dependency path and are candidates for parallel work, subject to real constraints.

A sensitivity exercise shortens only R-02's assumed duration upper bound from 40 to 25 days. R-04's earliest range becomes **80–85**, removing the cross-phase timing risk but **not** fixing the role-hour overload. That distinction is deliberate: a faster estimated duration does not create staff capacity. The regression suite exercises this change.

## Maturity and evidence collection

Baseline and target are **hypotheses**, not actual University ratings. A proposed difference of one or two levels receives `ONE_TO_TWO_LEVEL_HYPOTHESIS_NOT_VALIDATED`; it is never labeled achieved. Unknown baseline/target stays unknown. A larger, zero or negative difference is preserved and flagged for scope review rather than rewritten. The tool cannot authenticate sources, establish evidence quality, calculate an assessment score or approve recommendations.

For each work package, record the practice expected to change, a sample showing its current state, the source IDs and observation scope, the role that could own it, and the observable outcome that would show whether it helped. Ask separately for elapsed duration, one-time work, recurring work, ordinary-service commitments and usable availability. Record why each dependency exists and which missing evidence would revise it. Do not substitute names for unconfirmed roles or infer capacity from an empty calendar.

## Interchange boundary

JSON is the lossless machine output and retains a separate deep-copied `source_input`. `source_sha256` hashes canonical UTF-8 JSON (`sort_keys`, compact separators, Unicode preserved), not the original file bytes. It is a reproducibility identifier, not an independent authenticity proof. CSV list cells use JSON arrays. Unknown values are spelled `UNKNOWN`; unallocated effort is `UNALLOCATED`. Human-readable CSV prefixes formula-like text with an apostrophe; use JSON rather than the display CSV for exact text interchange.

Validation rejects duplicate JSON keys, IDs and repeated references; dangling findings/prerequisites; dependency cycles; booleans masquerading as integers; invalid ranges; and nonfinite JSON values. The JSON Schema describes shape; Python also checks cross-record and range-order semantics. All checks remain active under `python -O`.

This kit does not claim University architecture, actual staffing, accepted recommendations, appointments, procurement decisions, employee performance, maturity improvements, delivery acceptance or financial outcomes.
