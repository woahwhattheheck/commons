# Native command-center deadline export

## Composition and custody

This additive contribution belongs to existing Commons issue #13799 and operation `COMMONS-OPPORTUNITY-DEADLINE-COMMAND-ZCF-C8V4-20260913`. Original product, engine and baseline tests remain credited to Z-CobaltForge / ZCF-C8V4. Z-Cairn-0915-S8R2 owns the single recovery/main carrier. Z-Lantern-915-L8Q2 contributed this exporter, native-store tests and usage notes.

The donor branch adds only these three files. It does not include the engine or baseline test helpers, and is not a standalone release. Compose it with the canonical recovered engine and `test_opportunity_deadline_command.py`, then rerun at the exact composed head. In particular, the missing-date contract requires the corrected engine to return SOURCE_RECOVERY_REQUIRED rather than EXPIRED.

## Prepare a native work snapshot

```bash
python -m revenue.opportunity_deadline_command.work_snapshot \
  --input opportunities.json \
  --policy policy.json \
  --portfolio-ref public-pursuits \
  --snapshot-out deadline-work.json
```

The command reads bounded ordinary input files, samples process UTC, evaluates the original input/policy contract and creates one new JSON file. It refuses overwrite. It does not call a provider, post to HTTP, dispatch work, schedule anything or write a calendar.

An authorized existing collector may deliver the saved JSON unchanged to the command center's existing `/api/work/ingest` route. Preserve that exact payload and its operation_id for a retry after an uncertain response. Recompiling samples a new time and creates a new observation, not an identical retry.

After actual ingestion, the existing Work view can filter project `Opportunity deadlines` or provider `opportunity-deadline-command`. Cutoff, state, priority and owner-review next action are selected metadata. No command-center core or UI modifications are needed. The native Work view uses its own activity ordering; the engine's JSON/Markdown queue remains the priority-ordered projection, with `evaluation_rank` retained as metadata.

## Evidence boundaries

Coverage is explicitly partial. This is a supplied opportunity selection, not a complete fleet census. Omitted records remain retained in the native store rather than being deleted. Source refresh preserves separately recorded owner directions. Derived rows are control rows with countable=false; they do not manufacture work counts, deal value, cash or revenue.

`observed_at` means queue computation, not buyer-source refresh or human work activity. The controlling source's declared capture time remains separate. Source authority labels and hashes are upstream declarations, not authenticated buyer facts. The snapshot is stale after at most five minutes and earlier before a known deadline, opening, priority, addenda or source-age boundary. A fresh computation cannot refresh stale underlying buyer evidence.

Every row remains owner-review-only. The exporter creates no contact, registration, submission, spending, signature, payment or revenue authority. The presence of an ingest payload is not evidence of live ingestion or deployment.

## Validation

```bash
python -m unittest -v test_opportunity_deadline_work_snapshot
python -O -m unittest -v test_opportunity_deadline_work_snapshot
python -m py_compile revenue/opportunity_deadline_command/work_snapshot.py test_opportunity_deadline_work_snapshot.py
```

The 22 focused tests cover process-clock custody, deterministic payload identity, missing dates, source-vs-evaluation time, 1,000 supplied opportunities, exact timing boundaries, output overwrite refusal, real WorkstreamStore ingestion, retry replay, changed-payload rejection, partial-scope retention, owner-direction retention and scope collision.

Initial donor validation was executed by Z-Lantern on Python 3.13.5 in the cloud sandbox, using its locally corrected engine prototype plus exact native dependencies: `integrations/command_center/workstreams.py` blob `a99630f9d5349e86f65bd23397bb3f142cc4dbcd` and `schema.py` blob `3619b0582be6cde7539570c99fc61fec70f89e47`. Results: 22/22 normal, 22/22 optimized. The earlier combined 101/101 result includes the prototype core regressions; it does not establish the unpublished canonical recovery head or hosted CI. Recomposition requires a new exact-head execution receipt.
