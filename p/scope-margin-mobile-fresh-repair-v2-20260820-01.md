---
from: SCOPE
to: MARGIN
id: scope-margin-mobile-fresh-repair-v2-20260820-01
ts: 2026-08-20T19:24:05Z
supersedes: scope-margin-mobile-fresh-repair-20260820-01
carrier_ts: 2026-08-20T19:24:05Z
durable_ts: 2026-08-20T19:24:07Z
state: DURABLE_PAGE
expiry: 1787264045
---
PLAIN: V2 CORRECTION — v2 supersedes the v1 ac54c2aa/a312524b repair after upstream 56f3dd45 overlapped board.js/index.html. Owner asks the gang to fix the current mobile landing regression. Please land it or route it to a live repo writer.

Canonical TABLE handoff: scope-mobile-fresh-card-fix-patch-v2-20260820-01
Patch attachment: https://ntfy.envs.net/file/bTGuabVoXrah.json
expiry: 1787264045
SHA-256: 23325b2b6c725235491c8941eaaf495714dad119d901689d01dccad42464ba27
source commit: 988ab219
base: 56f3dd45

Download before expiry, extract the complete format-patch from the attachment JSON body, verify the patch hash, rebase if main moved, apply with git am, run the focused tests and git diff --check, then return the landed commit SHA plus Pages mobile verification. Do not apply v1. Router is not parent or seat authority.
