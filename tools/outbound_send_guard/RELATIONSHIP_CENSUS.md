# Provider relationship census / custody gate

`relationship_census.py` closes a gap that exact-recipient dedupe and atomic send leasing cannot close by themselves: a worker can see a clean target route while an older relationship already belongs to another worker on a different route or in older provider history.

The module is deliberately **not a sender**. It performs one offline, fail-closed projection from an authority-signed provider/history census to one of:

- `CUSTODY_CLEAR` — complete current evidence says the target is `UNSEEN` on every requested route;
- `CUSTODY_HELD` — the current worker is the owner of the live relationship generation (including an explicitly proved transfer);
- `HOLD` — every other state.

Every public receipt contains `external_send_authorized=false`. A clear/held custody result is only one prerequisite; callers still need the existing content/dedupe/route/DNR/provider gates and the buyer+offer atomic lease.

## Composition with existing controls

This module does not replace:

- `guard.py` / PR #13625 — mailbox + Slack evidence and same-offer/cooldown decisions;
- `buyer_scope.py` — aggregation across routes already verified to be the same buyer;
- `atomic_lease.py` / PR #13689 — one-touch buyer+offer serialization;
- `capability_lease.py` — proof the current worker possesses the winning lease generation.

`buyer_scope.py` explicitly treats membership as caller-supplied evidence rather than identity discovery. The census fills the historical relationship/custody seam before a worker treats a target as net-new.

## Request

The request names an opaque target scope, current worker, expected provider and census authority key id, required coverage horizon, freshness budget, and the SHA-256 identifiers of every route that must be covered. Raw email addresses are not part of the request/receipt contract.

```json
{
  "schema":"relationship-census-request/v1",
  "target_scope":"funto-network",
  "current_worker":"Z-Solstice",
  "as_of":"2026-09-14T02:30:00Z",
  "max_snapshot_age_seconds":3600,
  "coverage_required_from":"2026-09-01T00:00:00Z",
  "expected_provider":"gmail",
  "expected_key_id":"gmail-export-v1",
  "route_sha256":["<64 hex>"]
}
```

## Census authority

A census is signed with HMAC-SHA256 by the trusted provider-export boundary. This is a **local authority attestation**, not a claim that Gmail or another provider cryptographically signs exports. The raw authority key never appears in the census or receipt. The CLI reads it only from an environment variable (default `RELATIONSHIP_CENSUS_KEY`) and rejects keys shorter than 32 bytes.

The signature covers the complete census object except `attestation`, including target scope, provider, snapshot/coverage fields, relationship generation, all route observations, and transfer proof. Tampering after export therefore becomes `HOLD`.

## Fail-closed rules

A request cannot produce clear/held custody unless all of the following are true:

1. HMAC authority and expected key id match;
2. provider and target scope match the request;
3. every route observation is bound to the same target scope (cross-target transplant is `HOLD`);
4. census is complete, not future-dated, within the freshness budget, and covers at least the requested history horizon;
5. every requested route hash is present;
6. no route event occurs after the census snapshot;
7. the relationship state is semantically consistent.

`DNR`, `HARD_BOUNCE`, `TRANSFER_PENDING`, and `CLOSED` always hold. `ACTIVE_OWNER`, `WAITING_REPLY`, and `INBOUND_NEEDS_OWNER` hold unless the current worker exactly matches the live owner generation. `UNSEEN` is clear only when every route has `NONE` history.

## Explicit transfer

`TRANSFERRED` requires a signed `relationship-transfer/v1` proof bound to the same target. The proof must show:

- different prior/new owners;
- generation `N -> N+1` exactly;
- release by the prior owner, or a named admin actor;
- acceptance by the new owner;
- release <= acceptance <= census snapshot;
- new owner/generation exactly equals the census' current relationship.

Missing, stale, cross-target, skipped-generation, wrong-acceptor, or non-owner release proofs fail closed.

## PII-minimized receipt

Receipts include opaque target scope, route hashes, provider, snapshot-time metadata, canonical object digests, owner/current-worker SHA-256 commitments, state/generation, decision/reason, and an integrity digest. They do **not** echo raw email routes or owner names.

`evaluate_bytes()` additionally records the SHA-256 of the exact request/census byte streams consumed. Canonically equivalent JSON therefore keeps the same object digest but has different byte-custody digests.

## CLI

```bash
export RELATIONSHIP_CENSUS_KEY='at-least-32-bytes-of-secret-material'
python -m tools.outbound_send_guard.relationship_census \
  --request request.json \
  --census census.json \
  --out receipt.json
```

The CLI strict-parses JSON (duplicate keys and non-finite numbers rejected), reads each input once, forbids input/output path aliasing, and atomically publishes the receipt via same-directory temporary file + `fsync` + `os.replace`.

Exit codes:

- `0` — `CUSTODY_CLEAR` or `CUSTODY_HELD`;
- `4` — semantically valid evidence produced `HOLD`;
- `2` — malformed input, missing/short secret, unsafe alias, or I/O failure.

## Regression gate

```bash
python -m py_compile tools/outbound_send_guard/relationship_census.py tools/outbound_send_guard/test_relationship_census.py
python -m unittest -v tools.outbound_send_guard.test_relationship_census
python -O -m unittest -v tools.outbound_send_guard.test_relationship_census
```

The hostile suite covers valid current owner, truly unseen target, other-owner collision, tamper/wrong-secret/key-id failures, stale/future/incomplete/shallow coverage, missing route, cross-target transplant, DNR/bounce, transfer proof and acceptance failures, admin release, exact-byte custody, strict JSON, receipt tamper/PII checks, key length, atomic CLI output, and path-alias rejection.
