# T09 saved-checkpoint recovery

This directory preserves the original reconciliation artifact for operation `flow-opponent-league-20260907`. It does not contain a completed tournament panel or replace the league implementation.

## Exact recovered artifact

`flow-opponent-league-reconciliation.json` is a byte-for-byte copy of the persistent 691-byte file saved on September 7, 2026 at 19:53:05 UTC. No fields or completion flags were changed during recovery.

- SHA-256: `67f1dfa8d0ff38b868955d7ac2256b2ed27a72eb534cfc7d777dfcc049908468`
- Git blob: `dabbde98ba40f87a341c17135c27fffc136f9b30`
- Release freeze: `9bd9e4bd977d7c36de9cc2fd06d0859f7f8c7c3fa4871544732c9f294b717653`
- Original checkpoint publication: `fbb243330284a488f4331e4f4697136e22c40823`

The original file records development `games_recorded: 0` of 60, `verified_complete: false`, and evaluation `No saved result file.` Its `result_sha256` identifies a development result that was not included in this recovery. The underlying result JSON, runtime freeze manifest, and loss traces were not recovered here.

The `no_invalid_games` and `full_length_games` booleans do not demonstrate successful game execution when there are no result rows. Conversely, this historical checkpoint does not establish that later runs failed or never completed. A later saved output must retain its own source, freeze, seed, and completion provenance.

## Continue from existing files

The existing [league README](../cloud-opponent-league/README.md) defines the result contract. In the original execution workspace, locate the already-created `results.json` files in the supplied development/evaluation output directories, together with the freeze manifest and any `loss-traces/` files. Preserve partial outputs as well as complete ones. Publish their exact bytes and source references rather than replacing this historical checkpoint.

For each claimed completed panel, inspect the final completion flag, exact 60-game matrix, freeze binding, and invalid-game accounting. The announced evaluation seeds `9790101` and `9790119` have uncertain prior-use status in the recovery record and must not be represented as fresh holdouts. This recovery does not authorize or require rerunning them.

Recovery consumed no tests, games, seeds, jobs, or new source exports. The original runner, opponent variants, policies, and result ownership remain unchanged. Its existing source merge is separate from panel completion.

Coordination and subsequent results: [T09 task thread](https://tokenjunkielabs.slack.com/archives/C0C0Z8AHGP2/p1788805928334039).

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
