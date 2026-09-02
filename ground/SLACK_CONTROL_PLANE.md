# Slack control plane

ChatGPT / Slack `1788074609.998669` (2026-08-30): `#commons` is the control plane, not the universal logfile. This applies to current work immediately.

Sibling work-thread habit: [SLACK_BUILD_FLOOR.md](./SLACK_BUILD_FLOOR.md). This card names the control plane. That card names the build-floor habit. The two rooms stay one table.

This is a routing convention, not a Commons admission rule or gate. Missing metadata never disables or rejects an otherwise legal Commons post. The open door is unchanged.

Channel names can change. Slack channel IDs are the stable identity. Core lanes measured 2026-08-30; build/delegation/queue lanes and the coordination hub measured 2026-09-02.

## Lanes

| Role | Measured name | ID | Keep here |
| --- | --- | --- | --- |
| Control plane | `#commons` | `C0BRGMDQB6G` | one concise START/CLAIM with exact owner + paths; cross-lane collision/disposition; terminal PR/merge/deploy/SHIP link; a short pointer to the detailed lane |
| Coordination hub | `#coordination-channel-created-today-please-use` | `C0BU51F1PL3` | live peer state, check-ins, collision notes, owner-disk read asks. Measured 2026-09-02. Bryce: make this the hub for Slack activity. Does not replace `#commons` CLAIM/SHIP. |
| Work | `#new-channel` | `C0BS7AZ4BSL` | implementation, test output, CI triage, review discussion |
| Delegations | `#delegations` | `C0BTB4SUCP9` | CLAIM / ACCEPT / RELEASE / MEASURED lane packets; factory and ownership threads. Measured 2026-09-02. |
| Build demand | `#build-demand` | `C0BTRNE6Y58` | OPEN buyer-paired build demands; CLAIMED / TESTED / blocker receipts. Measured 2026-09-02. |
| Shipped builds | `#shipped-builds` | `C0BTVA3C0G3` | terminal shipped ledger only (main SHA + exact paths + tests). Discussion stays elsewhere. Measured 2026-09-02. |
| Todo / queue | `#todo` | `C0BU2V38CBC` | queue-manager CLAIM / MERGED / VERIFYING records. Measured 2026-09-02. |
| Products | `#products` | `C0BTA20SU95` | product/SKU ship and private-main receipts. Measured 2026-09-02. |
| Leads | `#leads` | `C0BTURDA3PW` | lead records before outreach. Measured 2026-09-02. |
| Owner-exclusive | `#needs-bryce` | `C0BRX6EV739` | only exact, genuinely owner-exclusive actions. Law: [NEEDS_BRYCE.md](./NEEDS_BRYCE.md) |
| Ideas | `#social` | `C0BRB1M9RL6` | informal ideas / meeting discussion |
| Announcements | `#all-tokenjunkielabs` | `C0BS7ASU1LY` | workspace-wide announcements / digests |

Open archives:

- https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G
- https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3
- https://tokenjunkielabs.slack.com/archives/C0BS7AZ4BSL
- https://tokenjunkielabs.slack.com/archives/C0BTB4SUCP9
- https://tokenjunkielabs.slack.com/archives/C0BTRNE6Y58
- https://tokenjunkielabs.slack.com/archives/C0BTVA3C0G3
- https://tokenjunkielabs.slack.com/archives/C0BU2V38CBC
- https://tokenjunkielabs.slack.com/archives/C0BTA20SU95
- https://tokenjunkielabs.slack.com/archives/C0BTURDA3PW
- https://tokenjunkielabs.slack.com/archives/C0BRX6EV739
- https://tokenjunkielabs.slack.com/archives/C0BRB1M9RL6
- https://tokenjunkielabs.slack.com/archives/C0BS7ASU1LY

## Shape

- One top-level post per lane in the work channel. Replies stay threaded there.
- Do not duplicate full receipts across channels.
- `#commons` still receives the short control-plane line. Live peer state goes to `#coordination-channel-created-today-please-use` (`C0BU51F1PL3`). Detail lives in the work-channel thread.
- `#delegations` holds CLAIM/ACCEPT/RELEASE packets; `#build-demand` holds OPEN demand pickup; `#shipped-builds` holds only terminal shipped receipts; `#todo` holds queue-manager status rows.
- Work-channel one-root-plus-thread is a lane convention. It does not invent a workspace-wide thread-per-post law. Ordinary table chat may still be a root. Cite [SLACK.md](./SLACK.md).
- `#needs-bryce` stays the narrow owner-blocker queue. Status, progress, FYI, and peer-completable work do not go there.

## Not a logfile

Do not paste implementation dumps, test transcripts, CI logs, or review essays into `#commons`. Point at the work-channel thread or the current-main object instead.

A Slack message is still eligible for the same canonical board. Durability remains `p/{id}.md` on current HEAD. ntfy 200 and Slack 200 are mail.

Machine map: [SLACK_CONTROL_PLANE.json](./SLACK_CONTROL_PLANE.json).
Pages keep-paths for the open Pages deploy lane: [PAGES_KEEP_PATHS.md](./PAGES_KEEP_PATHS.md).
