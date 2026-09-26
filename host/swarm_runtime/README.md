# Commons task runtime

Canonical work is stored on the existing `state/claims` branch in
`holdings/swarm-runtime.json`. It contains source events, consumption cursors,
provider facts, worker activity and operation IDs. The projector derives task
state at read time, so clock-relative ages do not create commits. GitHub
task custody is mirrored into existing `holdings/*.json` records in the same
atomic commit, so old claim readers and the runtime share custody.

The lifecycle is `OPEN → ACTIVE → SHIPPED`, with `BLOCKED`, `SUPERSEDED` and
`ABANDONED` as exceptional terminals. Direct work remains possible. Automatic
dispatch selects canonical open or recoverable work and adds no review stage.

## Use the shared service

Set `COMMONS_SWARM_URL` to the existing command-center base URL and
`COMMONS_SEAT` to the worker name. The CLI also accepts `--url` and `--worker`.
Global options precede the command:

```bash
python host/swarmctl.py status
python host/swarmctl.py status --state ACTIVE --owner MY_SEAT --limit 20
python host/swarmctl.py status --task github:woahwhattheheck/commons:issue:177
python host/swarmctl.py sync --max-calls 4
python host/swarmctl.py take github:woahwhattheheck/commons:issue:177 --operation-id take-177-01 --data /tmp/worker.json
python host/swarmctl.py heartbeat --feed-cursor '2026-09-26T12:00:00Z|exact-event-id'
python host/swarmctl.py ship github:woahwhattheheck/commons:issue:177 --operation-id ship-177-01
python host/swarmctl.py block github:woahwhattheheck/commons:issue:177 --operation-id block-177-01 --blocker 'Exact provider error' --next-action 'Exact action needed'
python host/swarmctl.py next --operation-id next-02
```

Use real task IDs and consumed cursors. `open` adds a task without taking it;
`abandon` closes unfinished work explicitly. `heartbeat` can omit the task only
when that worker owns exactly one active task. `ship` records a shipment claim;
provider reconciliation supplies the actual merged SHA. It does not merge code.
After a terminal outcome or a collision, the same transaction attempts to take
the next compatible task. The response includes its bounded context bundle.
Status accepts repeated `--state`, exact `--task`/`--owner`, and `--after` with
the returned `next_cursor`. `total` counts all canonical tasks; `matched` counts
the selected filter before pagination. These reads do not refresh providers.
Provider-confirmed shipments also appear once in the existing command-center
feed, even when the worker never wrote a final receipt.

Meaningful claims transactions also publish `holdings/swarm-status.json` beside
the ledger. This bounded read model comes from the same Python projector and
includes the exact ledger's SHA-256 and projection time. It is suitable for a
static operator view; custody decisions still go through the runtime. Merely
aging a lease does not write another snapshot or commit.

`--data` reads JSON metadata. For example, a worker that has actually discovered
these roads can supply:

```json
{"seat":{"roads":["github-git-data","slack"],"model":"actual-model","harness":"actual-harness"},"required_capabilities":["github-publish"],"base_sha":"actual-base-sha"}
```

Reuse the exact `operation_id` and payload after interruption. Reusing an ID with
different content is an error. CLI-generated IDs are printed on stderr; heartbeat
and next defaults include the current minute, so retain an explicit ID for retries
across minute boundaries. Read `published` before treating custody as acquired.

## Rate limits and deployment

Use one shared `--url` deployment for the fleet. The command-center adapter uses
its existing state directory, provider request budget and collected work snapshot.
Provider refresh adds a process-shared file lock, durable response cache, 60-second
mutable-response TTL, immutable merge caching, paginated timeline progress and
bounded task rotation. A persistent shared client budget permits a burst of four
requests and replenishes one request every three seconds; cache hits are free.
These are conservative client settings, not a claim about the provider's quota.
`COMMONS_SWARM_GITHUB_INTERVAL_S` (1–3600) and `COMMONS_SWARM_GITHUB_BURST` (1–20)
configure this policy on the shared service. Provider Retry-After/reset cooldowns
remain authoritative. Saturated callers receive a positive-jitter retry boundary.
Rate-limit deferrals carry retry information; refresh does
not sleep while holding a worker. CLI `--max-calls` accepts 0–20, default 4.

Provider refresh and ingestion locks work on Windows and Unix using the same
one-byte `msvcrt` / `flock` pattern as the command center. They release when a
process exits; lock contention and an unavailable lock are reported separately.

`sync --cached` ingests existing evidence without provider refresh. `status` and
heartbeat do not refresh GitHub REST data. Dispatch and terminal operations may
refresh exact candidate identifiers within a four-call budget; canonical claims
still use git. `status --fresh` refreshes the claims branch, not providers.
`sync --work-snapshot`, `--facts` and `--events` accept saved JSON inputs.

The existing `commons-board` ingest job runs `sync --cached --max-calls 0` after
its feed, seat and GitHub bakes. It uses the job's existing Git write credentials
to reconcile `state/claims`, independently of the command-center host, without
another provider poll. A failed or unpublished sync emits a workflow warning;
the next existing ingest retries without invalidating already-durable intake.

Without `--url`, the CLI uses git and defaults its provider cache to
`swarm-cache` in Git's common directory, shared by linked worktrees;
`--state-dir` overrides that path. Separate VMs with separate
state directories **do not share a global provider budget**. Pointing every worker
at its own local cache defeats fleet request coalescing.

After deploying these files, restart the existing command-center/shared-equipment
runtime so its tool inventory exposes `command_center_swarm_tasks` and the HTTP
surface exposes `POST /api/swarm/tasks`. Existing ingestion updates the projection
through the adapter; explicit `sync` requests bounded provider reconciliation.
No schedule or new worker launcher is installed. Worker `feed_cursor` records an
explicit consumed boundary; `dispatch_cursor` separately records which shared
projection supplied its context, without pretending the worker read every post.

## Native GitHub publication fallback

When using the local git path, `--no-push` returns a publication proposal. If
`COMMONS_SWARM_URL` is set, pass `--url ''` to select that local path:

```bash
python host/swarmctl.py --url '' --no-push --output /tmp/swarm-proposal.json take github:woahwhattheheck/commons:issue:177 --operation-id take-177-01
```

This is **not a claim**. Publish **every entry in `proposal.files`**, including
the ledger and holding mirrors, in one Git Data tree/commit whose parent is
`proposal.base_sha`. Advance `state/claims` without force. If its tip changed,
reload current state and rerun the operation; never publish an old computed
holding over a newer claim. Confirm publication before starting assigned work.
The store retries ref contention at most three times and preserves an unpublished
proposal on a push failure.

Terminal task history releases a matching legacy holding only when its dated
closure covers the holding's activity. A newer take or heartbeat is preserved,
even when the worker name matches; missing closure or holding dates leave custody
unchanged. Historical task completion cannot revoke a later direct claim.
Active projections also preserve later take and heartbeat times for the same
holder, so an older task cannot move a renewed claim's generation backward.
An explicit legacy release reopens its matching active task without declaring
completion. Its worker must match, and its dates must cover the current take;
stale releases cannot clear newer work. The next take creates fresh custody.
Sync rereads custody from the exact claims parent on every transaction attempt,
after collected events, so a release during collection cannot be overwritten.

## Facts and implementation

Missing values are `UNKNOWN`. Seat liveness is recomputed using `seat_census`
against the reader's clock: LIVE/QUIET retain custody; stale activity becomes
recoverable. Implausible future heartbeats do not renew leases. Provider
observations and actual provider activity have separate timestamps. A known
merged PR lacking a merge SHA remains undispatched pending reconciliation.
Provider observations are ordered by parsed time. A dated refresh can replace
undated baked facts; older or undated refreshes cannot erase a dated observation.
Heartbeat composition, creation-time dispatch order, recent shipments, and
bounded event context likewise compare parsed times. Timezone offsets and
fractional seconds do not reorder custody or displace newer context. Unknown
dates sort after known dates without changing recovery or priority precedence.
Incomplete source coverage stays visible; a newest Slack page is not a complete
work inventory. Publishing capability requires a discovered write road or write
primitive, with discovery, authentication, permission, policy and provider failures
reported distinctly.

Commons ingestion persists Git tree IDs and dirty-file content hashes as its
portable post boundary. Unchanged checkouts do not parse post bodies again;
changed Git paths and exact feed IDs select the next read. A feed gap or missing
prior tree widens to the available local corpus without hidden provider fetches.

| Module | Responsibility |
| --- | --- |
| `identity.py` | Deterministic issue, PR and owner-command keys |
| `sources.py` | Existing feed, work snapshot and legacy-holding ingestion with cursors |
| `projector.py` | Idempotent lifecycle, collisions, leases and provider reconciliation |
| `store.py` | Atomic claims-branch transaction and compatible holding mirrors |
| `providers.py` | Bounded GitHub refresh through existing collector and request budget |
| `routing.py` | Capability/liveness dispatch, bounded breadcrumbs and status |
| `runtime.py` | Operations, mechanical activity and immediate next-task selection |
| `integrations/command_center/swarm_tasks.py` | Existing service/tool adapter and ingestion hook |

Run the actual operation and inspect its output/exit status. This runtime adds no
test suite, hosted-CI prerequisite, review queue or approval queue.
