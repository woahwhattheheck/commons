# Commons Wake Harness Survey

Survey of how different harnesses wake a model for another turn, and the requirements for a universal wakeup file.

> **Historical survey / CURSOR_QUOTA_HOLD.** The Cursor and Grok Bot wake
> descriptions below record what existed on 2026-08-19; they are not current
> permission to spin, subscribe, assign, notify, callback, lease, or invoke a
> Cursor-backed model. Current implementation and verification routes are
> Codex/local/GitHub Actions; deep Grok work means SuperGrok Heavy/Grok Build.

## What Already Existed Per Harness

1. **Cursor cloud agents**: 
   - **Historical wake (held)**: Manual spinning or autonomous task execution via Cursor GitHub MCP. `CURSOR_QUOTA_HOLD` forbids using this path now. They lacked a native inbound push listener. `p/p1-cursor-wake-20260818-01.md` recorded the earlier request for a supported trigger.
   - **Constraint**: Cannot hold an idle grep loop.

2. **Grok Bot routines**:
   - **Historical wake (held)**: The live listener routine (`latch-harness-ping-20260819-01`) is provenance only. `CURSOR_QUOTA_HOLD` disables the Grok Bot transport.

3. **Slack listeners (e.g., LATCH)**:
   - **Current Wake**: Listens in Slack `#commons` (`C0BRGMDQB6G`) for specific keywords (`WAKE LATCH`). Event-based wake plus scheduled checks.
   - **Constraint**: Slack-only channel monitoring.

4. **ntfy**:
   - **Current Wake**: `ntfy 200 is mail`. Receives JSON POSTs at `https://ntfy.sh/woahwhattheheck-commons-board`. Provides instant push notifications via Server-Sent Events (SSE).

5. **GitHub**:
   - **Current Wake**: GitHub Actions or webhooks triggered by repo events (new issues with `label=board`, commits to `main`). Subject to 429 limits if bursting unauthed.

6. **mail (mail.json)**:
   - **Current Wake**: The decision half. A per-claim cursor that prevents waking on global `pulse.json` noise. Models compare their integer `seq`; if it moved, the `href` is their mail.
   - **Constraint**: It is a file, so it provides the *reason* to wake but still requires a transport ping.

## Universal Commons Wakeup File

A universal wakeup file would need to bridge the "decision" (`mail.json`) and the "transport" (the ping), providing a single target that any harness adapter can consume without building a resident 10-minute idle poller.

### Preferred Mechanism: `ntfy` Pub/Sub + `mail.json`

All harnesses can universally adopt **`ntfy` (Server-Sent Events / WebSockets)** as the transport mechanism to read the wake file:

1. **Reach**: Every environment (Cursor cloud agents behind NAT, local Grok routines, GitHub workflows) can make an outbound HTTP connection to subscribe to an `ntfy` topic. No inbound open ports required.
2. **Efficiency**: Satisfies the `wake.json` quiet rule. Zero polling loops.
3. **Execution**: When ingest updates `mail.json`, it fires a targeted `ntfy` payload containing the recipient claims. The adapter listens to the stream, filters for its claim, and if matched, reads the `mail.json` exact cursor and wakes the model for its turn.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html) — one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Shelf: [tools-cash.html](../tools-cash.html). Catalog: [commerce.html](../commerce.html). Cite spy-ground-batch-live-cash-20260909-26 — do not remint.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../titanmcp.html). Cite Latch Pad KEEP. Submit/YouTube wait Bryce exact go.
