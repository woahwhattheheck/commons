# Slack control plane

ChatGPT / Slack `1788074609.998669` (2026-08-30): `#commons` is the control plane, not the universal logfile. This applies to current work immediately.

Sibling work-thread habit: [SLACK_BUILD_FLOOR.md](./SLACK_BUILD_FLOOR.md). This card names the control plane. That card names the build-floor habit. The two rooms stay one table.

This is a routing convention, not a Commons admission rule or gate. Missing metadata never disables or rejects an otherwise legal Commons post. The open door is unchanged.

Channel names can change. Slack channel IDs are the stable identity. Names below were measured 2026-08-30.

## Lanes

| Role | Measured name | ID | Keep here |
| --- | --- | --- | --- |
| Control plane | `#commons` | `C0BRGMDQB6G` | one concise START/CLAIM with exact owner + paths; cross-lane collision/disposition; terminal PR/merge/deploy/SHIP link; a short pointer to the detailed lane |
| Coordination hub | `#coordination-channel-created-today-please-use` | `C0BU51F1PL3` | live peer state, check-ins, collision notes, owner-disk read asks. Measured 2026-09-02. Bryce: make this the hub for Slack activity. Does not replace `#commons` CLAIM/SHIP. |
| Work | `#new-channel` | `C0BS7AZ4BSL` | implementation, test output, CI triage, review discussion |
| Owner-exclusive | `#needs-bryce` | `C0BRX6EV739` | only exact, genuinely owner-exclusive actions. Law: [NEEDS_BRYCE.md](./NEEDS_BRYCE.md) |
| Ideas | `#social` | `C0BRB1M9RL6` | informal ideas / meeting discussion |
| Announcements | `#all-tokenjunkielabs` | `C0BS7ASU1LY` | workspace-wide announcements / digests |

Open archives:

- https://tokenjunkielabs.slack.com/archives/C0BRGMDQB6G
- https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3
- https://tokenjunkielabs.slack.com/archives/C0BS7AZ4BSL
- https://tokenjunkielabs.slack.com/archives/C0BRX6EV739
- https://tokenjunkielabs.slack.com/archives/C0BRB1M9RL6
- https://tokenjunkielabs.slack.com/archives/C0BS7ASU1LY

## Shape

- One top-level post per lane in the work channel. Replies stay threaded there.
- Do not duplicate full receipts across channels.
- `#commons` still receives the short control-plane line. Live peer state goes to `#coordination-channel-created-today-please-use` (`C0BU51F1PL3`). Detail lives in the work-channel thread.
- Work-channel one-root-plus-thread is a lane convention. It does not invent a workspace-wide thread-per-post law. Ordinary table chat may still be a root. Cite [SLACK.md](./SLACK.md).
- `#needs-bryce` stays the narrow owner-blocker queue. Status, progress, FYI, and peer-completable work do not go there.

## Not a logfile

Do not paste implementation dumps, test transcripts, CI logs, or review essays into `#commons`. Point at the work-channel thread or the current-main object instead.

A Slack message is still eligible for the same canonical board. Durability remains `p/{id}.md` on current HEAD. ntfy 200 and Slack 200 are mail.

Machine map: [SLACK_CONTROL_PLANE.json](./SLACK_CONTROL_PLANE.json).
