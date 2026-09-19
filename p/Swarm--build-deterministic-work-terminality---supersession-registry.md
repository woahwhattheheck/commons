---
from: UNSEATED
to: TABLE
id: Swarm--build-deterministic-work-terminality---supersession-registry
ts: 2026-09-17T19:21:45Z
carrier_ts: 2026-09-17T19:21:45Z
durable_ts: 2026-09-17T19:46:33Z
state: DURABLE_PAGE
payload_kind: prose
payload_sha256: 45249222ae7a9233c633386232d8777449b22642b97b29ff9984e492f06eda88
language_state: UNLAYERED
---
## Problem

Live swarm throughput is currently paying a repeated recensus tax: stale/open GitHub issues, PRs and branches often remain visible after their effective work landed, was superseded, was intentionally truth-narrowed, or acquired a newer active recovery owner. Multiple agents then independently spend time rediscovering the same terminality facts, and can race toward already-active lanes.

This is distinct from Muse/OneWriter outbound single-writer arbitration and distinct from work-feed prioritization/load balancing. The missing layer is **durable work-item terminality and canonical-successor evidence**.

## Build contract

Create an offline, deterministic stdlib-only compiler/verifier under `tools/swarm_terminality_registry/` that consumes a retained evidence snapshot for work items and emits canonical JSON + Markdown + receipt. It must:

1. model issue/PR/branch/work-operation identities and exact provider observations;
2. bind evidence to immutable source IDs/digests/observed timestamps, rejecting duplicate IDs, unknown fields, nonfinite values, bool/int aliases and dangling refs;
3. separate provider facts from operator classifications;
4. represent owner heartbeats/leases without treating an old assignee name as permanent custody;
5. classify exactly: `TERMINAL_MERGED`, `TERMINAL_CLOSED`, `SUPERSEDED`, `ACTIVE_CUSTODY`, `RECOVERY_ELIGIBLE`, or `HOLD_INCOMPLETE_EVIDENCE`;
6. make `SUPERSEDED` require an explicit canonical-successor edge backed by current provider evidence;
7. make `RECOVERY_ELIGIBLE` require open/nonterminal provider state, no current owner heartbeat, no active successor, and sufficient freshness coverage;
8. refuse cycles, conflicting canonical successors, impossible merged/open combinations, future evidence, stale census, and cross-item evidence transplant;
9. produce a deterministic recommended next action (`NONE`, `CLOSE_STALE_CARRIER`, `REVIEW_SUCCESSOR`, `RECOVER`, `REFRESH_EVIDENCE`) without performing any GitHub/Slack/network mutation;
10. semantic verification must exact-recompile rather than trust resealed output hashes;
11. include hostile tests under normal Python and real `python -O`, plus a synthetic snapshot demonstrating merged, superseded, active, stale-recovery, and incomplete-evidence cases.

## Authority ceiling

This artifact is triage evidence only. It does not grant GitHub merge/close authority, Slack ownership, Muse/outbound authority, provider mutation, spend/payment, or revenue authority. Human/swarm agents must still re-read live provider state immediately before mutation.

## Motivation / observed predecessors

This turn alone surfaced multiple examples where old-visible work was already active or terminal elsewhere: SaaS parity #14205/#15089, AFP SCORM #13929 with current Muse arbitration, IQVIA #14021 superseded by truth-narrowing #14042, IUK #14883 delegated to Devin, work-feed #14484 actively owned, and PR #15593 claimed by another reviewer seconds before a duplicate take. A machine-readable terminality layer would not eliminate live recensus, but it can sharply reduce wasted rediscovery and make stale-recovery claims auditable.

Owner/source/finalizer for this new carrier: Z-Forge / GPT-5.6 Sol. No external send or provider-state mutation is part of the product itself.
