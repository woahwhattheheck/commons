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

POST /api/work/item or command_center_work_item sets priority, next_action or a prepared job for an exact source_id/item_id. Provider evidence is preserved and prepared packets record not_dispatched. Fleet also exposes actual Gemini submit/inspect/follow-up/cancel routes from the live shared catalog, retaining provider receipts. Native task actions use their actual harness routes.
