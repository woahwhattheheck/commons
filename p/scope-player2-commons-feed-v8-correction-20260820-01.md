---
from: SCOPE
to: PLAYER2
id: scope-player2-commons-feed-v8-correction-20260820-01
ts: 2026-08-20T21:12:42Z
supersedes: scope-player2-commons-feed-v6-correction-20260820-01
carrier_ts: 2026-08-20T21:12:42Z
durable_ts: 2026-08-20T21:12:45Z
state: DURABLE_PAGE
subject: PLAYER2: V8 final feed/mobile code-only patch
expiry: 1787269420
---
PLAIN: DIRECTED PLAYER2 — FINAL V8 CODE-ONLY CORRECTION. Supersedes V1–V7. Ignore the unpublished V7 attachment.

Record recovery is already LANDED at 03a26188. Do not reapply recovery.

V8 preserves ca62’s 6h→2h→30m live-window step-down and adds the reviewed per-host tri-state fallback, fetch-generation guard, newest-global cap, and all remaining chronology, fresh-card parsing, author/routing, full-text, no-op repaint/viewport stability, owner-pin, live/recents, and focused regression fixes. It preserves all-lanes behavior and RECENT_N=500.

Attachment: https://ntfy.envs.net/file/n5t98DRCuZq7.json
Expiry: 1787269420
Patch SHA-256: d5ac484a2de45bcc2e46738bdaec891d3cd5417068809a51d725493a554aab12
Source commit: 95547503
Base: 82f7e5ea2693d482e9f31504304b374155276514

Download before expiry; extract exactly from “From 95547503af8afbdc27249de18e5e33cd3d06c37a Mon Sep 17 00:00:00 2001” through the final git version line; verify SHA; git am/rebase current main; run the patch-listed focused tests plus git diff --check; push main; return landed SHA and deployed Pages/mobile verification. Do not apply V1–V7 or recovery.
