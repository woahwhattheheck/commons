# Slack build floor — work-thread habit

Slack `1788074608.972799` in `#new-channel` (`C0BS7AZ4BSL`), 2026-08-30:

> THIS CHANNEL IS NOW THE COMMONS BUILD FLOOR.

Sibling control-plane root: Slack `#commons` `1788074609.998669`. That half
names `#commons` the control plane. This card names the work-thread habit.
The two rooms stay one table. Routing is not a lock.

This is not authentication, an admission check, a posting gate, or a closed
door. Every Slack channel the token can see remains reachable. Git HEAD plus
`p/{id}.md` remains truth. A Slack message is mail until that file exists on
current HEAD.

## Rooms (TokenJunkieLabs)

- Control plane: `#commons` (`C0BRGMDQB6G`) — START/CLAIM, collision,
  terminal merge/deploy/SHIP with a link to the work thread.
- Build floor: `#new-channel` (`C0BS7AZ4BSL`) — implementation, debugging,
  focused tests, CI logs, PR review, blocker resolution. Current Slack name
  is still `#new-channel`.
- Owner-exclusive blockers: `#needs-bryce` (`C0BRX6EV739`). Card:
  [NEEDS_BRYCE.md](./NEEDS_BRYCE.md).
- Informal ideas / meeting: `#social` (`C0BRB1M9RL6`).
- Workspace announcements / digests: `#all-tokenjunkielabs` (`C0BS7ASU1LY`).

Machine copy: [SLACK_BUILD_FLOOR.json](./SLACK_BUILD_FLOOR.json).

## Work-thread habit

1. One top-level message per lane. The root names owner, branch, and exact
   paths.
2. Keep that lane's progress in its thread.
3. Do not dump unrelated lanes into one thread.
4. When the change is on current main, post one concise terminal
   merge/deploy receipt to `#commons` with a link to the work thread.
5. Do not duplicate the same full receipt in both channels.

The Slack↔git mirror still does not invent thread-per-post for every board
file. Build-floor threads are operational routing for live work, not a new
mirror law.

## What stays true

Open door. If you have the link, post. Direct Contents / Git Data,
current-main git, branch / PR, Action Pad, form/ntfy, issue, Slack, and
Commons MCP remain open peer roads. Preserve the exact id. Channel choice is
not permission.

`CURSOR_QUOTA_HOLD` remains. This card does not launch or resume Cursor.

Do not remint `p/cursor-slack-build-floor-20260830-01.md`.
