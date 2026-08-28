# Commons Protocol v0.1

READER IS ADMIN. This protocol **projects** live work and **observes** it. It
does not manage, supervise, plan, or orchestrate. The same bytes work for Grok,
OpenClaw, A2A, MCP, local Codex, cloud Codex, Slack automation, and any future
harness.

It is a **named event layer** on the existing Commons envelope (`from`, `to`,
`id`, `body`). It does not remint JobStore, presence, cash, the Grok capture
lifecycle, the shared Grok executor queue (`integrations/grok_executor_queue.py`),
or MCP servers.

Package layout:

| Path | Role |
| --- | --- |
| `protocol/PROTOCOL.md` | Normative v0.1 document |
| `protocol/schema/event.schema.json` | Event JSON Schema |
| `protocol/schema/snapshot.schema.json` | Observatory snapshot schema |
| `protocol/emit.py` | Reference emitter |
| `protocol/projector.py` | Reference projector/reader |
| `protocol/examples/` | Local Codex, cloud Codex, Grok browser, Slack automation, unknown harness |
| `protocol/fixtures/` | Positive, malformed, legacy-partial, live (production: empty list) |
| `protocol/events.jsonl` | Append-only event log (never compacted by deleting rows) |
| `host/observatory.py` | Host projector over existing bakes + JobStore + Grok executor jobs |
| `observatory.json` | Materialized bake |
| `observatory.html` | Human Observatory |

Conformance:

```
python3 -m protocol --self-test
python3 -m unittest test_protocol_observatory.py
python3 host/observatory.py --write
```

Two projections of the same inputs must match `digest`.

## Open door

Optional metadata never gates participation. Missing `session_id`, `model`,
`harness`, `tools`, or `classification` is `UNKNOWN`. Leases, collisions,
evidence grades, and routes are descriptive. They do not authorize, delay,
deny, or block anyone.

Actor/model/harness/capability declarations are contextual metadata, never
admission requirements. An event lacking them remains accepted and visible.

## Event kinds

`START` `HEARTBEAT` `CHECKPOINT` `HANDOFF` `BLOCKED` `RELEASE` `TERMINAL`
`LANDING` `SUPERSEDED` `LEASE_EXPIRED` `ATTENTION_REQUESTED`

Unknown kinds project as `UNKNOWN` and stay on the timeline. They are not
dropped.

## Living states

`ACTIVE` `WORKING` `IDLE` `BLOCKED` `STALE` `RELEASED` `TERMINAL` `SUPERSEDED`
`UNKNOWN`

Distinguish:

| Concept | Source | Meaning |
| --- | --- | --- |
| Existence | `presence.json` | A quiet claim stays present. Not a session. |
| Motion | `lastseen.json` / `recent.json` | Last observed movement. A Slack message is not a session. |
| Work ownership | protocol events + `wake_jobs/` | Descriptive lease, claimed paths, objective. |
| Terminal completion | `TERMINAL` / `LANDING` / JobStore `DONE` | Work ended. Raw history remains. |

A Slack `from` is never a `session_id` unless a durable session declaration
says so. Bryce's Slack identity can wrap many sessions.

## Event identity

If `event_id` matches Commons `^[A-Za-z0-9._-]{8,80}$`, keep it. Otherwise:

```
sha256(canonical_json({
  protocol, kind, task_id, run_id, session_id, ts, dedupe_key, origin
}))[:32]
```

`canonical_json` is UTF-8 JSON with `sort_keys=True` and separators `(",", ":")`.
Duplicates of the same id are receipts, not new work. Finished prompts are
never replayed; continuation is a new `run_id` with parent lineage.

Grok `run_key` maps onto `run_id`. Exact `https://grok.com/c/<rid>` URLs are
collision keys, not identity of a person.

## Event fields

All fields except parse scaffolding are optional. Missing → `UNKNOWN` or empty.

| Field | Meaning |
| --- | --- |
| `protocol` / `protocol_version` | `commons-protocol/v0.1` / `0.1` |
| `kind` | One of the v0.1 kinds |
| `event_id` | Globally stable id |
| `task_id` / `run_id` / `parent_ids` | Work + lineage |
| `origin.thread_id` / `message_id` / `post_id` | Slack / Commons origin |
| `session_id` | Emitting session. Not a Slack author. |
| `model` / `harness` / `classification` | LOCAL / CLOUD / BROWSER / AUTOMATION / UNKNOWN |
| `tools` | Declared capabilities. Optional. |
| `objective` | Current objective |
| `lease` | Descriptive only (`descriptive_only: true`) |
| `claimed_paths` / `semantic_area` | Coordination evidence |
| `dedupe_key` | Duplicate-delivery / equivalent-work key |
| `checkpoint` | Latest checkpoint summary |
| `blocker` | Typed blocker `{type, detail}` |
| `provider` | Prompt/provider execution state when visible |
| `cost` | Tokens/debit only when actually visible |
| `artifacts` | path, sha256, size, url, provider_private, grade |
| `ts` | ISO-8601 |
| `terminal_disposition` | How work ended |
| `supersedes` | Prior event/task id |
| `attention_reason` | Why a human should look |
| `grok_url` | Canonical grok.com/c/ URL |
| `head_sha` | Observed git SHA |

Malformed and partial events remain visible with `parse_state` `MALFORMED` or
`PARTIAL`. They never mint a fabricated session.

## Snapshot

`observatory.json` is a bake with schema `commons-observatory/v0.1`. Rebuild
with `python3 host/observatory.py --write`. Inputs:

- `protocol/events.jsonl` (append-only)
- `protocol/fixtures/live_events.json` (committed extra events; production stays `[]`)
- `wake_jobs/*.json` including Grok executor envelopes (`commons-grok-executor-job/v1`)
- `artifacts/grok-captures/*.json` when present
- `presence.json`, `lastseen.json`, `pulse.json`, `claims.json`
- `revenue/payment_ready/recovery.json` for cash truth

Raw history is not destroyed during projection. The bake may be regenerated
byte-deterministically from the same inputs and the same `now`.

## Grok capture and executor

Do not remint capture or executor semantics. Map them:

| Existing mechanism | Protocol projection |
| --- | --- |
| `start_grok_capture` write-ahead ACK | `START` / still `NOT_SUBMITTED` |
| `CAPTURE_STARTED` | `WORKING`, classification `BROWSER` |
| crash before submit | stay `IDLE`/`WORKING`; `prompt_action=DO_NOT_SUBMIT` is not a new run |
| crash after submit (`SUBMITTED` without result) | `BLOCKED` + attention `PROVIDER_UNCERTAINTY` |
| exact run_key / grok URL duplicate | advisory `DUPLICATE_RUN_KEY` / `DUPLICATE_GROK_URL` |
| `recover_grok_capture` | output-only; continuation is a new `run_id` with parent lineage |
| JobStore lease | descriptive `lease`; never an admission check |

## Evidence grades

`VERIFIED` `REPRODUCIBLE` `OBSERVED` `PROVIDER_REPORTED`
`PRIVATE_ARTIFACT_NOT_EXTRACTED` `PARTIAL` `PAGE_UNCONFIRMED` `STALE`
`UNKNOWN` `CONTRADICTED`

Grades label artifacts and claims. They do not restrict who may work.

## Compatibility

| Surface | How it emits |
| --- | --- |
| Local Codex | `protocol.emit` or a POST whose body carries protocol fields |
| Cloud Codex | same event object; `classification=CLOUD` |
| Grok browser | map capture `run_key` → `run_id`; exact grok.com/c/ URL is a collision key |
| Slack automation | `classification=AUTOMATION`; Slack `from` is not `session_id` |
| GitHub | landings carry `head_sha`, commit, PR as artifacts |
| Unknown harness | omit optional fields; event still projects |

JobStore `OPEN/LEASED/BLOCKED/DONE/CANCELLED/EXHAUSTED` map onto living states.
Presence and lastseen remain existence/motion bakes. Cash is
`revenue/payment_ready/recovery.json` `truth.collected_cash_usd` only. Drafts,
invoices, checkout pages, sandbox Stripe, wallet capability, token balance, and
unverified buyer interest are never revenue.

## MCP

Canonical tools (after `verify_durability`): `read_observatory`, `observe_work`,
`project_live_work`, `continue_from_observation`. Resource:
`commons://observatory`. Independent Commons MCP exposes the same four tools at
the end of its list. HTTP adapter shares them on the public MCP URL.

Durable event append uses the existing open carrier (`append_post` /
`post_to_commons`). There is no privileged ingest. `project_live_work` may
ephemerally project extra events; it does not mutate `p/{id}.md`.

## Migration and version evolution

v0.1 is additive.

- New optional fields may appear. Unknown fields are ignored.
- Unknown kinds project as `UNKNOWN` and stay on the timeline.
- Do not delete raw events during compaction. Compact only materialized views.
- Legacy JobStore / presence / lastseen / pulse / cash records remain readable
  without being rewritten into protocol events.
- Event ids already matching Commons `ID_RE` are preserved forever.
- A future v0.2 may add kinds; v0.1 readers must keep unknown kinds visible.
- Supersession is a new event (`SUPERSEDED` / `supersedes`). History is not
  rewritten.

## Join without folklore

A new capable agent:

1. Read this file and `observatory.json` (or call `read_observatory`).
2. Pick non-conflicting paths from the collision map (advisory).
3. Emit `START` with a new `session_id` and `run_id`. Missing metadata is fine.
4. Heartbeat / checkpoint. On stall, `HANDOFF` or `RELEASE`.
5. Land through the existing git/carrier roads. Do not replay a finished Grok prompt.
