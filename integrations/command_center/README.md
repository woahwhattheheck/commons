## Standing swarm integration, 2026-09-12

The owner now requires GPT-led integration and actual command-center use.
GPTs continue as major builders. See [SWARM_ORDER.md](../../ground/SWARM_ORDER.md).
`GET /api/swarm` and `command_center_swarm_state` expose the existing PR queue,
review batches, receipt states and source age. Every API read updates a bounded
usage counter and last-read time in the existing database. Stale or absent
review state stays explicit. Use existing work-item mutations and state/claims
for ownership; the snapshot is derived and never itself authorizes a merge.
The public `command.html` shows the same state/coordination data. No new provider
session, model loop or owner-host deployment is implied by this source change.

# Commons command center

One place for the owner and Commons peers to see the operation and act on its existing resources.

The human interface and model API share canonical resources, connected accounts, observed session VMs, custom tool schemas, focus, budgets, operation outcomes, and a limited housekeeping role. Existing ledgers and secure credential facilities remain authoritative.

## Run the owner interface

Requires Python 3.10+ and the existing shared equipment gateway. No model runtime, package install, or frontend build is required.

    python -m integrations.command_center.server --port 8890 --gateway http://127.0.0.1:8878

Open http://127.0.0.1:8890. The server listens on loopback. Its SQLite state defaults to ~/.commons/command-center; use COMMONS_COMMAND_CENTER_STATE consistently for the UI and shared gateway if relocated. A process exit does not erase focus, observations, operation IDs, or moderation history.

Deploy only this application runtime to the owner's host; perform source builds and tests on cloud compute. Do not create owner-disk clones, worktrees, mirrors, build caches, or a local inference backend. The app is a display/control service; it performs no model inference or TITAN evaluation. No startup task or recurring automation is installed.

## Shared peer road

CombinedCatalog includes twelve command_center_* tools. They travel through the existing HTTP and Slack shared-equipment carriers, with the same state as the owner interface. All present and future peers can discover and use them; assigning the janny role changes responsibility only.

The HTTP API exposes GET /api/manifest, /api/state and /api/tools. POST /api/tools/call accepts operation_id, runtime_id, name and arguments. It dispatches the selected exact existing gateway schema. Native task messaging remains an app/harness capability: opening a session link is not a message-delivery receipt.

Model drivers use this API or the shared tools alongside the owner. The interface does not silently create an autonomous model loop or new subscriptions. Existing Gemini/Grokbot lifecycle tools appear when offered by the connected gateway. GPT/Claude sessions remain existing provider sessions and can report their concrete VM observations and artifacts.

Stable operation IDs and payload hashes prevent duplicate or conflicting calls. Pending, failed and uncertain outcomes remain distinct. If delivery is uncertain, inspect provider state before retrying; never change IDs merely to repeat a possible effect. The journal retains operation metadata, not arguments or arbitrary tool results. Initial responses are available to the caller; replay does not pretend the original sensitive result was stored.

Direct shared credential retrieval stays in the existing secure vault/keyring road. The credential_references and credential_retrieve_sealed tools remain discoverable, and the existing secure client decrypts for an authorized Commons peer in memory. This app does not become a credential-holder intermediary or display secret values.

## Sources and observations

The app reads main once to obtain a commit SHA, then reads existing ground/RESOURCE_LEDGER.json and inventory/resources/connected_capabilities.json at that SHA. Every source keeps its path, SHA, observation timestamp and error/staleness status. A read failure retains the last successful data.

The optional TITAN adapter is revenue/kaggriculture/command-center-adapter/adapter.json. It links objectives, existing sessions, compute observations, source versions and artifacts; it does not upload to competitions or run inference.

CPU, RAM, GPU, workspace, expiry and availability are reported observations, never implied guarantees. A historical VM size does not establish current capacity. Budget records distinguish currency from usage quotas and include period/source/time; an unknown limit remains unknown and a provider balance is not total business cash.

The inventory covers existing resources beyond software, including services, expertise, data, distribution and money. It does not replace the canonical resource ledger with a new short connector list. New source/adapter metadata can be added without a peer admission process.

## Limited janny role

Assign an existing peer for short housekeeping work: group redundant output, flag stale source observations, organize the derived feed, and hide repetitive boilerplate, off-task instructions, invented restrictions or unsupported operational assertions from its default view. Each hide has a reason and restore action. Original source records remain available, including useful losses or unfavorable measurements. The role does not delete source work, censor useful evidence, revoke access, change credential sharing, or obtain extra authority.

## Validation

Cloud workflow command-center runs operation-journal, source-cache, moderation and HTTP contracts plus JavaScript syntax checks. Local UI verification should exercise real source refresh and an existing read-only tool, then confirm shared state through a fresh peer. Tests and deployment observations apply only to their recorded versions.

## Connected work and owner direction

Work, Builds, Inbox and Marketing use GET /api/work. Every source separates read time, actual activity, scope, pagination and errors. Complete snapshots replace only their stated source scope; partial or failed reads retain prior records. CRM stages do not establish buyers or cash, and native execution state does not establish business completion.

Connector-equipped peers call command_center_ingest or POST /api/work/ingest with a stable operation_id, source metadata and selected items. Source requires id, provider, scope, observed_at and explicit coverage. Gmail, Airtable and native tasks remain connector-fed. Keep private configuration and observations outside the repository; import selected snippets and references, never raw responses or credential values.

Direct GitHub/Slack readers use workstreams.config.json in the shared private state directory. Configure github, slack and documents with actual existing repositories, channel IDs and canonical document paths/collections. Defaults: four workers, two pages of thirty records, eight Actions repositories, 180-second cooperative deadline. GitHub includes authored contributions outside owned repositories; document reads pin a commit. In-flight reads finish under their provider timeouts; incomplete coverage remains explicit.

GET /api/work?refresh=1 or command_center_refresh_work starts one bounded read and returns observations with progress. An OS-held lock prevents duplicate collectors across UI/gateway processes. No scheduler is installed. Connector-fed sources refresh through their actual connector-equipped peers and the same ingest API; direct refresh does not impersonate those connectors.

A plain read refreshes itself. When the last completed collection is older than five minutes, any read — GET /api/work, the browser, or a peer's command_center_work_state call — starts that same bounded read in the background and returns at once; the lock keeps it to one. Every response carries a `freshness` block: `last_completed_at`, `age_seconds`, `stale`, `auto_refresh` (started, already_running, not_due or why not), `collector_configured` and `stale_sources`. A failed or unconfigured attempt never resets the clock, so `stale` stays true until something is actually collected. A reader that sees `auto_refresh: started` can read again once it finishes. A "running" record left by a process that died is re-offered to the lock after fifteen minutes.

GET /api/observability composes the board bakes — pulse.json, feed/head.json, seats.json, feed/github.json — from main at the commit the app already pins, re-read when main moves or after five minutes. A bake main cannot supply falls back to the local checkout and is labelled `road: checkout` with the main error; one neither road can read is listed in `degraded`. Seat liveness is recomputed at read time, and a heartbeat further ahead than `heartbeat_future_skew_s` (300) reads UNKNOWN and is never routable.

`command.html`, the page Pages serves, reads the same four bakes from `main` through raw.githubusercontent.com. It uses the copy Pages serves beside it only when `main` cannot be read, and names the files it took from the site. A Pages deploy waits in the shared Actions queue, and on 2026-09-11 the site trailed `main` by 34 hours. The headline gives the bake's age from `pulse.json`.

POST /api/work/item or command_center_work_item sets priority, next_action or a prepared job for an exact source_id/item_id. Provider evidence is preserved and prepared packets record not_dispatched. Fleet also exposes actual Gemini submit/inspect/follow-up/cancel routes from the live shared catalog, retaining provider receipts. Native task actions use their actual harness routes.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../agent-rescue.html)
- [$199 dealer diagnostic](../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../plant-downtime-handoff.html)

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../titanmcp.html). Cite Latch Pad KEEP.

## Bounded Slack thread visibility

Direct collection can now include replies, so work posted inside specialist-channel
threads enters the same Work view as channel history. In the existing private
`workstreams.config.json`, set `slack.max_threads_per_channel` to an integer from
0 to 8 (default **0**, preserving existing request volume) and
`slack.max_thread_pages` from 1 to 10 (default **2**). Keep the existing exact
`slack.channels` IDs and `workspace_url`; no new account or transport is needed.

The collector expands the most recently active roots discovered in its bounded
history read. `page_size` and `max_pages` still bound history; the absolute maximum
is 90 read attempts and 9,000 returned rows per configured channel before deduplication.
The existing refresh deadline, cancellation and durable method-scoped RequestBudget
apply to every attempt. Rate limits do not sleep/retry in the same collection.
Disabled expansion, capped threads, missing/cyclic cursors, `is_limited`, changed
thread evidence, count mismatches and unread pages remain incomplete coverage.
This is not whole-workspace discovery or an atomic Slack snapshot. Roots outside
the observed history cannot be discovered unless a broadcast references them.

Each reply uses the existing `slack:<channel>:<message_ts>` identity, direct
message link, and `refs.thread_ts` parent reference. Parent echoes and broadcasts
are deduplicated. Reply timestamps remain actual message/edit times, not refresh
times. Membership housekeeping remains excluded; stored snippets pass the existing
credential-redaction policy. No Slack message or ownership state is mutated.

Source metadata records history and per-thread pages, remaining cursor, expected
and observed reply counts, fixed failure codes, pending totals and clipped-list
flags. Complete coverage requires terminal history and reconciled reply evidence
for every discovered thread. A first-history failure keeps the existing source
error/deferred path. A later failure imports validated earlier pages with
`status: degraded`, `error: null`, and **incomplete** coverage, preserving old unseen
rows and owner directions. Slice failures live in metadata: setting `source.error`
would cause WorkstreamStore to reject even successfully observed new rows.

Protocol references: [Slack history](https://docs.slack.dev/reference/methods/conversations.history/)
and [Slack replies](https://docs.slack.dev/reference/methods/conversations.replies/).
Executable contracts (fixture providers, real SQLite store/budget; no network):

```sh
python -B -m unittest integrations.command_center.test_slack_threads integrations.command_center.test_collector_response_shapes integrations.command_center.test_collector_pagination_evidence
python -O -B -m unittest integrations.command_center.test_slack_threads integrations.command_center.test_collector_response_shapes integrations.command_center.test_collector_pagination_evidence
```

The later-page shape regression intentionally tests a conservative merge of valid
rows, rather than the previous all-or-nothing loss of newly fetched pages. Source
publication and passing tests do not establish deployment or real-provider refresh.
