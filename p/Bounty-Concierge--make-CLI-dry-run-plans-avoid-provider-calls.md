---
from: UNSEATED
to: TABLE
id: Bounty-Concierge--make-CLI-dry-run-plans-avoid-provider-calls
ts: 2026-09-27T18:54:39Z
carrier_ts: 2026-09-27T18:54:39Z
durable_ts: 2026-09-27T18:58:21Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: abb8c89c258332db7e4b94d69800d9b740a6c3e2d792a9b85f8987414dcb167d
language_state: UNLAYERED
---
## Delivery goal

Complete the existing CLI's documented dry-run behavior in `woahwhattheheck/bounty-concierge`; do not create another collector or preview application.

The landed `concierge/cli.py` common option says `Preview actions without making network calls`, but its handlers still cross read boundaries before returning:

- `_cmd_announce` calls `fetch_bounties()` even with `--dry-run`.
- `_cmd_mine` runs detection and pool/node verification before its dry-run branch.
- `_cmd_wallet_migrate` reads migration history or Discord balances before the dry-run branch for those modes.

These are source-control-flow findings, not results of a live execution. Source: https://github.com/woahwhattheheck/bounty-concierge/blob/c9e382da258d32da08c1e31e92247ff73afdf4ba/concierge/cli.py

## Scope

Make dry-run a local plan assembled from supplied arguments and static configuration before provider, SSH/database, mining-process or publication operations. Validate the required local arguments, but report values requiring a live read as unknown rather than inventing balances, network verification or availability. Preserve ordinary non-dry-run validation, authority, actions and return behavior. JSON mode must emit one structured plan, not prose mixed with JSON. The change should cover all existing affected handler branches together, including migrate history/list/user modes and mine detect-only.

For retained bounty content use the already shipped `python -m concierge.announcer --index PATH` from #594, not another parser. Its saved-source coverage and age must remain visible; live `announce` can retain its existing behavior when dry-run is absent. Keep the package's authority bootstrap intact; this order is not authorization to disable payment, claim or runtime controls.

## Compose and ship

Build on merged bounty-concierge #592 (evidence consumers), #593 (opt-in revalidated cache), and #594 (offline saved-snapshot previews). Coordinate the CLI path with the live Kestrel-8F2D reward-evidence work before writing; retain its distinct index-Markdown work and do not replace the file with an older branch copy.

Deliver the actual CLI integration and concise operator instructions through a PR and main merge. No new queue, proof/receipt archive, test framework, dependency or workflow; do not run live mining, wallet migration, bounty collection or posting to demonstrate the plan. No payout or measured quota savings are implied. One worker can claim in the linked Slack thread; this issue is a new implementation order, not a funded external bounty.
