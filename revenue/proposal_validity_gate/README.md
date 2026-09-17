# Proposal validity / expiry / requote gate

Issue: `woahwhattheheck/commons#15608`  
Operation: `PROPOSAL-VALIDITY-EXPIRY-REQUOTE-ZAXIOM1442-20260917`

This package answers one narrow commercial-control question: **is an already-proposed offer still current enough for owner review/use under the facts it was actually issued against?** It does not decide whether to send an offer and it cannot represent buyer acceptance, a contract, payment, cash, or recognized revenue.

## States

The compiler emits exactly one currentness state:

- `CURRENT_FOR_OWNER_USE` — the retained offer still matches the current source/commercial binding and its explicit validity/deadline have not expired.
- `EXPIRED_REQUOTE_REQUIRED` — time alone invalidated an otherwise-current offer, including the buyer deadline passing.
- `SUPERSEDED` — a source-bound amendment, redline, change order, reprice, or withdrawal explicitly supersedes this offer.
- `HOLD_NO_VALIDITY_BASIS` — the offer has no explicit bounded validity basis.
- `HOLD_SOURCE_DRIFT` — source generation/status, source digest, pricing revision, currency, scope, economics, buyer deadline, or payment rail changed.

Every non-current state carries a deterministic `requote_delta` containing changed fields, reason codes, superseding event IDs, and owner fields requiring reapproval.

## Evidence contracts

### Offer (`proposal-validity-offer/v1`)

An offer binds exact `opportunity_id` and `offer_id`, controlling `source_generation` + `source_digest_sha256`, `pricing_revision`, ISO-4217-style 3-letter currency, `scope_sha256`, `economics_sha256`, UTC issuance time, buyer deadline (when present), and an explicit validity object:

- `{"kind":"UNTIL","valid_until_utc":"...Z"}`
- `{"kind":"DAYS","days":N}` anchored to `issued_at_utc`
- `{"kind":"NONE"}` which can only produce `HOLD_NO_VALIDITY_BASIS` when no stronger source drift/supersession state exists.

A checkout/payment road is optional. When present it binds `rail_id`, `rail_revision`, a checkout-reference digest, and its exact state.

### Current record (`proposal-validity-current/v1`)

The current record repeats the controlling source and commercial facts, plus source currentness/observation time and bounded supersession evidence. Supersession events are not free-form labels: each event is tied to the same opportunity and **must carry the exact current controlling source digest and be observed no later than that source generation's observation time**.

Input JSON is fail-closed: duplicate keys, floats/non-finite numbers, unknown fields, malformed/non-UTC timestamps, bool-as-int validity durations, invalid hashes, duplicate events, and future-observed evidence are rejected. Equivalent supersession-event ordering canonicalizes to one semantic input digest.

## Time / replay boundary

The public CLI deliberately has **no `--as-of` option**. `compile` and `verify` use process UTC. Tests can call `compile_at` / `verify_at` with an explicit aware UTC `datetime` to exercise boundaries deterministically.

A receipt binds canonical validated offer/current semantics and carries a semantic hash. Verification:

1. revalidates strict input and receipt contracts;
2. checks canonical input digests and the receipt semantic hash;
3. recompiles the receipt at its recorded evaluation instant and requires byte-for-byte semantic equality;
4. recompiles again at the verifier's current UTC and rejects a historical `CURRENT_FOR_OWNER_USE` receipt once it has expired or crossed the buyer deadline.

Thus caller-supplied packet clocks cannot replay a historical green state as current.

## Authority ceiling

Every receipt and verification result carries the same hard-false authority map:

- external send
- Muse election
- buyer acceptance
- contract authorization
- signature authorization
- invoice authorization
- payment authorization
- cash received
- revenue recognized

`CURRENT_FOR_OWNER_USE` means only that the retained proposal packet is current enough for owner review/use under its explicit validity terms. It is **not** permission to contact a buyer or move money.

## CLI

```bash
python -m revenue.proposal_validity_gate compile \
  --offer offer.json --current current.json --out receipt.json

python -m revenue.proposal_validity_gate verify \
  --offer offer.json --current current.json --receipt receipt.json
```

`--out` uses exclusive creation and refuses to overwrite an existing artifact.

## Retained proof

The nested suite covers current, expired, missing-validity, superseded, source drift, pricing/currency/scope/economics/deadline drift, stale source state, stale payment rail, opportunity replay, future-issued/current evidence, timestamp and bool/int hostiles, clock injection, strict JSON duplicate/nonfinite/float rejection, receipt tamper, source replay, historical-current replay after expiry, canonical supersession ordering, source-bound supersession evidence, CLI compile/verify, and the absence of a CLI `--as-of` escape.

The root `test_proposal_validity_gate.py` bridge executes the entire nested suite under both normal Python and real `python -O`, and compiles product sources at optimization levels 0 and 2 so optimized execution cannot erase proof checks.
