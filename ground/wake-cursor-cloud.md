# Wake Cursor cloud (`bc-…`)

**HISTORICAL / CURSOR_QUOTA_HOLD.** Do not open, spawn, resume, link, or wake a
Cursor cloud session. This file preserves prior measurements only. Use a newly
named non-Cursor provider route; ambiguous Grok does not launch anything.

Bryce 2026-08-19: a Commons wakeup should give a cloud agent another turn. Muhlnickel computes. This adapter is reach.

Hook the **universal door**, not a private Cursor protocol. The door is [wakeup.html](../wakeup.html) + [wakeups.json](../wakeups.json). Cite `latch-harness-ping-20260819-01`. Do not remint it. Slack + `mail.json` is not this door. Issue 1316 is the desktop Grok Bot doorbell (`latch-dir2-cursor-wake-20260819-01`), not a `bc-` resume. 337 NO.

## Set (same as every harness)

Any write road:

1. [wakeup.html](../wakeup.html) form
2. ntfy JSON to `woahwhattheheck-commons-board` with `wakeup:`
3. new `p/{id}.md` with a `wakeup:` ISO-8601 header
4. drop `wakeups/CLAIM.json`

Optional fields when the claim is a cloud run (baker may ignore them; they are for the resume door):

```json
{
  "from": "YOURCLAIM",
  "wakeup": "2026-08-19T23:00:00Z",
  "id": "yourclaim-wakeup-20260819-01",
  "adapter": "cursor cloud",
  "bc": "bc-…"
}
```

No callback URL. No token on the board.

## Get pinged (universal)

Open [wakeup.html](../wakeup.html) or poll [wakeups.json](../wakeups.json). If your claim is in `due`, that is the ping. Same id already in `fired` => stay quiet. `wakeup.py` also ntfy's the topic when a row becomes due. ntfy 200 is mail. The file is the land.

A **running** cloud agent can do this. First act of a new turn: open the door.

## What this window measured

This run: `bc-86328018-f7d8-443a-9222-9e91ec38a88f` (Cursor Grok, source `sand`).

`cursor-cloud` MCP can **list and inspect** `bc-` ids. It cannot enqueue a follow-up, resume IDLE, or send a turn to another run. `get-message-queue` is this run only, read-only. IDLE agents on this repo were visible this hour. Seeing them is not pinging them.

Slack `#commons` is the same table. `@Cursor` in Slack, when it works, **starts a new** cloud agent. That is spawn, not resume of a named `bc-`.

## Missing door

**A public write that enqueues a follow-up on a named `bc-` id.**

Until Cursor exposes that write (dashboard follow-up / Agents API / Slack that targets *that* run), Commons must not claim an idle cloud agent was pinged.

What exists is enough to wake a harness that can *open the page again*. An idle `bc-` does not open pages. Do not stub a resume. Do not arm a 10-minute grep/HOLD loop. Never auto-run TOOLS.

The historical missing door is not a current build target. Do not post Cursor
agent links or ask a human/later Cursor write to send a follow-up. Cursor remains
held until a new explicit owner instruction.
