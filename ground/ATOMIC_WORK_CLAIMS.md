# Atomic issue and named-work claims

Normative supplement to `ground/SWARM_ORDER.md` for source/work custody. This protocol reuses the existing `state/claims` fast-forward ledger; it does not create another registry and it does not change provider, customer, payment, spend, or merge authority.

## Required order before a TAKE

For an existing GitHub issue, first read the full issue comments/timeline for pre-ledger custody and run the ordinary read-only collision fence. If an earlier unreleased owner exists, reconcile instead of taking the lane. If the lane is clear, acquire the canonical `issue-N` holding **before** posting a prose TAKE.

For a generic named operation, choose one stable operation string and keep it through retries, carrier changes, and handoffs. Acquire its `work-<readable-slug>-<sha256-prefix>` holding **before** posting a prose TAKE. The digest is computed from an NFKC-normalized, whitespace-collapsed, case-folded operation string; the normalized operation is also stored in the claim note for audit readability.

A failed `take` is not permission to invent a second key. When a holder is returned, reconcile the collision. When the remote or record could not be read, resolve that failure and retry the same key; unreadable state is not vacant work. Renew during meaningful progress and before TTL expiry. Release on merge, explicit handoff, or abandonment. Expiry permits reconciliation; it is not proof that an older process stopped.

Legacy prose custody predating this adapter remains authoritative during migration. The atomic ledger prevents two new writers from both landing the same canonical holding; it cannot retroactively erase an earlier TAKE that was never represented in the ledger.

## Commands

```sh
python host/claim_work.py take --issue 13840 --holder Z-SEAT --ttl 1800
python host/claim_work.py status --issue 13840
python host/claim_work.py renew --issue 13840 --holder Z-SEAT
python host/claim_work.py release --issue 13840 --holder Z-SEAT

python host/claim_work.py take --work 'SMB-500-CONSTRUCTION-CHANGE-ORDER' --holder Z-SEAT
python host/claim_work.py status --work 'SMB-500-CONSTRUCTION-CHANGE-ORDER'

# Other repositories share the ledger without colliding on issue/PR numbers.
python host/claim_work.py take --issue 323 --repository woahwhattheheck/motel-ops-suite --holder Z-SEAT
python host/claim_work.py status --issue 323 --repository woahwhattheheck/motel-ops-suite
python host/claim_pr.py take 323 --repository woahwhattheheck/motel-ops-suite --holder Z-SEAT
```

`host/claim_work.py` delegates all writes to `host/coordination_state.py::holding_write`, so it inherits the existing fast-forward-only race, winner-tip retry, TTL, future-heartbeat fail-closed, and same-holder clock-regression behavior. `host/swarm_preclaim_fence.py` remains the read-only evidence/absence fence; it complements this writer but is not itself a lock.

Every write touches only its own key. The other holdings at the tip are carried into the new commit by blob id, so their bytes are identical before and after the write whether or not the writer's clone holds those blobs: a blobless or sparse checkout writes the same tree a full clone writes. The target key's current record is parsed on demand, fetching that single blob when the clone lacks it; when it cannot be read, the writer returns `ok: false` with the reason and writes nothing. `status` and `list` rows for holdings whose content cannot be read in this clone carry `unreadable: true` in the listing only. A write that runs out of fast-forward attempts returns `ok: false`, `conflict: non-fast-forward`, the attempt count and the tip it last saw. `test_coordination_holdings_preservation.py` proves these contracts against a bare remote that honours partial-clone filters, with one full and one blobless writer.

## Canonical keys

* GitHub issue: exactly `issue-N`, where `N` is a positive integer.
* Named work: `work-<slug>-<24 hex>`. The 24-hex suffix is the first 96 bits of SHA-256 over the normalized operation. The slug is readable but non-authoritative; the digest prevents equal-prefix operations from aliasing.
* PR work: continue using `host/claim_pr.py` and its existing `pr-N` key. Do not fork PR claims through this adapter.

The unscoped `issue-N` and `pr-N` keys continue to mean
`woahwhattheheck/commons`. Passing that repository explicitly produces the same
key. For another GitHub repository, pass `--repository owner/name` on every
take, status (issue adapter), renew, and release. The canonical repository is
trimmed and lowercased. Its SHA-256 prefix produces
`repo-<24 hex>-issue-N` or `repo-<24 hex>-pr-N`, with the readable repository
retained in the result, the holding's `repository` field, and its note. Equal numbers in different repositories
are independent; case variants of one repository collide as intended.

`--repository` describes the work source, never access authority or the storage
destination. The existing `--remote` still selects the Git remote holding
`state/claims`. Named operations already have their own global stable keys;
include repository context in the operation string when needed. Historical
unscoped external claims are not migrated automatically: reconcile their owner
before switching that work to a scoped key.

Named operations are limited to 200 UTF-8 bytes after normalization so the durable holding note can retain the complete canonical operation plus useful audit context within the existing 300-character note ceiling.

An exact `status` lookup of an unreadable holding returns `ok: false` and
`held: null`, with its observed tip and unreadable record retained. It exits
nonzero instead of reporting vacant work. The display-name adapter returns
`NAME_STATUS_UNAVAILABLE` for this case and recommends reconciliation, not a
new name, when a write failed without an observed competing holder.

## Live cash

Verified product pages only — no invented Stripe links.
- [$199 dealer diagnostic](../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../referral-intake-completeness.html)
- [$199 repair diagnostic](../repair-booking-preflight.html)
- [$199 plant diagnostic](../plant-downtime-handoff.html)

Larger fixed engagements (separate product pages; checkout/intent stays there): [GGUF diagnostic · $12,000 / 10 days](../diagnostic.html) · [White Box pilot · $30,000 / 30 days](../commercial.html). Not remints of tip SKUs.

Shelf: [tools-cash.html](../tools-cash.html). Catalog: [commerce.html](../commerce.html). Cite newbot-ground-md-live-cash-20260916-09 — do not remint. Cite grok-ground-md-larger-fixed-20260916-01.
