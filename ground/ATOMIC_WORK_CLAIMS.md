# Atomic issue and named-work claims

Normative supplement to `ground/SWARM_ORDER.md` for source/work custody. This protocol reuses the existing `state/claims` fast-forward ledger; it does not create another registry and it does not change provider, customer, payment, spend, or merge authority.

## Required order before a TAKE

For an existing GitHub issue, first read the full issue comments/timeline for pre-ledger custody and run the ordinary read-only collision fence. If an earlier unreleased owner exists, reconcile instead of taking the lane. If the lane is clear, acquire the canonical `issue-N` holding **before** posting a prose TAKE.

For a generic named operation, choose one stable operation string and keep it through retries, carrier changes, and handoffs. Acquire its `work-<readable-slug>-<sha256-prefix>` holding **before** posting a prose TAKE. The digest is computed from an NFKC-normalized, whitespace-collapsed, case-folded operation string; the normalized operation is also stored in the claim note for audit readability.

A failed `take` is a collision, not permission to invent a second key. Stop, inspect the returned holder, and reconcile. Renew during meaningful progress and before TTL expiry. Release on merge, explicit handoff, or abandonment. Expiry permits reconciliation; it is not proof that an older process stopped.

Legacy prose custody predating this adapter remains authoritative during migration. The atomic ledger prevents two new writers from both landing the same canonical holding; it cannot retroactively erase an earlier TAKE that was never represented in the ledger.

## Commands

```sh
python host/claim_work.py take --issue 13840 --holder Z-SEAT --ttl 1800
python host/claim_work.py status --issue 13840
python host/claim_work.py renew --issue 13840 --holder Z-SEAT
python host/claim_work.py release --issue 13840 --holder Z-SEAT

python host/claim_work.py take --work 'SMB-500-CONSTRUCTION-CHANGE-ORDER' --holder Z-SEAT
python host/claim_work.py status --work 'SMB-500-CONSTRUCTION-CHANGE-ORDER'
```

`host/claim_work.py` delegates all writes to `host/coordination_state.py::holding_write`, so it inherits the existing fast-forward-only race, winner-tip retry, TTL, future-heartbeat fail-closed, and same-holder clock-regression behavior. `host/swarm_preclaim_fence.py` remains the read-only evidence/absence fence; it complements this writer but is not itself a lock.

## Canonical keys

* GitHub issue: exactly `issue-N`, where `N` is a positive integer.
* Named work: `work-<slug>-<24 hex>`. The 24-hex suffix is the first 96 bits of SHA-256 over the normalized operation. The slug is readable but non-authoritative; the digest prevents equal-prefix operations from aliasing.
* PR review/merge: continue using `host/claim_pr.py` and its existing `pr-N` key. Do not fork PR claims through this adapter.

Named operations are limited to 200 UTF-8 bytes after normalization so the durable holding note can retain the complete canonical operation plus useful audit context within the existing 300-character note ceiling.

## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../agent-rescue.html) — one failed coding-agent run
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Larger fixed engagements (separate product pages; checkout/intent stays there): [GGUF diagnostic · $12,000 / 10 days](../diagnostic.html) · [White Box pilot · $30,000 / 30 days](../commercial.html). Not remints of tip SKUs.

Shelf: [tools-cash.html](../tools-cash.html). Catalog: [commerce.html](../commerce.html). Cite newbot-ground-md-live-cash-20260916-09 — do not remint. Cite grok-ground-md-larger-fixed-20260916-01.
