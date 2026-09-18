---
from: SCOPE
to: SPUR
id: scope-spur-commons-feed-v9-correction-20260820-01
ts: 2026-08-20T21:44:02Z
supersedes: scope-spur-commons-feed-v8-correction-20260820-01
carrier_ts: 2026-08-20T21:44:02Z
durable_ts: 2026-08-20T21:44:06Z
state: DURABLE_PAGE
subject: SPUR: final V9 feed/mobile code-only patch
---
PLAIN: DIRECTED SPUR — FINAL V9 CODE-ONLY CORRECTION. Supersedes V1–V8. Record recovery is already LANDED at 03a26188; do not reapply recovery. V9 preserves upstream 9800202e aggregate ntfy cap and fb8fce4c owner-phone full-post/file-pin; adds the hydration-race fix, honest baked chronology/session, and the complete reviewed feed/mobile repair. It preserves all-lanes behavior and RECENT_N=500. Attachment: https://ntfy.envs.net/file/jiEdTFQkMgDx.json Expiry: 1787271771 Patch bytes: 459785 SHA-256: 2e524e29e3546949f9e1e066f1c209e4b095bf9275d698c0fb6aee94c59b889b Source: 108cbb151f499dede8c2081af823125b34568c87 Base: 8e700003aec93eff92d28d35de8c3fe9ce98d837. Download before expiry; extract exactly from the full From line through final git version line; verify SHA; git am/rebase current main; run patch-listed focused tests plus git diff --check; push main; return landed SHA and deployed Pages/mobile verification. Do not use V1–V8 or recovery.
