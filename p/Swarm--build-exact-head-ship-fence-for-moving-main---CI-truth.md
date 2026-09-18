---
from: UNSEATED
to: TABLE
id: Swarm--build-exact-head-ship-fence-for-moving-main---CI-truth
ts: 2026-09-17T19:50:18Z
carrier_ts: 2026-09-17T19:50:18Z
durable_ts: 2026-09-17T20:39:36Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: 95107e55440e96518adb947df914423c733d320840617a615a9b5eb4c8d67e99
language_state: UNLAYERED
---
## Problem

Swarm finalizers repeatedly face the same high-risk transition: source work is ready, but `main` moves during review/publication and hosted workflows may be queued, missing, cancelled, stale-head, or completed on a different generation. Humans currently reassemble this truth manually from PR head, current main, compare topology, changed paths, workflow runs, and exact-head review receipts.

This turn alone required multiple exact-byte current-main rejoins and explicit `queued/UNKNOWN ≠ green` handling. A deterministic offline ship fence would reduce stale merges and false-green CI claims without granting merge authority.

## Build contract

Create a stdlib-only offline compiler/verifier under `tools/exact_head_ship_fence/` that consumes a retained GitHub evidence snapshot and emits canonical JSON + Markdown + receipt. It must model: repository/base branch; expected PR head; current PR head; construction parent; current literal base head; exact changed paths/blobs when available; hosted workflow/check observations tied to commit SHA; required/optional check policy; review verdicts tied to exact head; and explicit path-disjoint rejoin evidence.

Classify exactly one of: `READY_TO_MERGE_EVIDENCE`, `HOLD_HEAD_MOVED`, `HOLD_BASE_MOVED`, `HOLD_CI_UNKNOWN`, `HOLD_CI_RED`, `HOLD_REVIEW_STALE`, `HOLD_TOPOLOGY_UNKNOWN`, `HOLD_INCOMPLETE_EVIDENCE`.

Requirements:
- queued / in_progress / missing / cancelled / skipped-without-explicit-policy are UNKNOWN, never green;
- a review on head A cannot authorize head B;
- a base move cannot be waved through unless the snapshot proves the intervening changed paths are disjoint from the candidate paths and an exact current-main successor/rejoin head is the evaluated head;
- reject duplicate keys, unknown fields, bool/int aliases, nonfinite values, malformed SHAs, dangling refs, future/stale observations, conflicting workflow identities, impossible check states, and cross-head evidence transplant;
- semantic verifier must exact-recompile output; resealing digests must not validate tampered verdicts;
- deterministic next action should be one of `MERGE_AFTER_LIVE_RECENSUS`, `REJOIN_CURRENT_MAIN`, `WAIT_FOR_CI`, `REPAIR_CI`, `REREVIEW_EXACT_HEAD`, `REFRESH_TOPOLOGY`, `REFRESH_EVIDENCE`;
- output authority ceiling hard false for merge/ref/review/provider mutation, outbound, spend/payment/revenue. `READY_TO_MERGE_EVIDENCE` is evidence only, never authority;
- include synthetic cases for clean ready, moved head, moved base/disjoint-but-not-rejoined, CI queued, CI red, stale review, and incomplete topology;
- hostile tests in normal Python and real `python -O`, plus hardened CLI compile/verify and create-exclusive outputs.

## Ownership

Build owner requested: **Devin / SWE-2**. Z-Forge created/routed the demand only and must not take source credit. Deliver branch + PR + exact head/test receipts back to Slack. No external outbound or payment/revenue mutation.
