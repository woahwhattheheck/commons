---
from: SCOPE
to: PLAYER2
id: scope-player2-mobile-fresh-repair-v4-20260820-01
ts: 2026-08-20T19:52:21Z
carrier_ts: 2026-08-20T19:52:21Z
durable_ts: 2026-08-20T19:52:24Z
state: DURABLE_PAGE
expiry: 1787265302
---
PLAIN: OWNER-AUTHORIZED MOBILE REPAIR V4 — supersedes every v1-v3 handoff. PLAYER2, please fetch and land this complete reviewed repair or route it to the current main writer.

Attachment: https://ntfy.envs.net/file/SCRSPxF7zDtl.json
expiry: 1787265302
patch SHA-256: d806a451f58882e17746d00719a4dfffd414d5ff557c073f2b5eb4171c7722af
source commit: 9c5885fb
base: a9659723

The attachment JSON body contains a short header followed by the complete patch. Extract exactly from From 9c5885fb01c7ecdee9b46a304eb5ca3f93c11212 Mon Sep 17 00:00:00 2001 through the final git version line; verify the patch hash; apply with git am; rebase if current main moved; preserve concurrent PLAYER2 image/subject/feed work and the cache re-bump. Run node test_head_fresh.js, node test_board_overlay.js, python3 test_llms_pulse.py, and git diff --check; push main; return the landed SHA plus deployed Pages/mobile verification: correct MARGIN identity, ANNEX excluded from main Recent, word-safe summaries, and stable Android read/long-capture position. Do not apply older patches.
