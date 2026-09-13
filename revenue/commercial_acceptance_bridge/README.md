# Commercial Acceptance Bridge

This package closes one specific revenue-operations gap: it turns a **human-reviewed, normalized buyer response** into a deterministic closing handoff state that can sit between inbound-reply custody and paid-fulfillment/payment gates.

It deliberately does **not** parse raw email or infer intent from prose. A caller must supply the reviewed response class and SHA-256 reviewer attestation. It also does not determine signer/legal authority, create or execute contracts, create invoices/checkouts, charge money, start fulfillment, or recognize revenue.

## Evidence contract

An offer version is bound to exact offer series/version lineage, counterparty + provider thread, SHA-256 scope/acceptance/commercial-term snapshots, exact currency + minor-unit price, and canonical UTC issue/expiry times. A reviewed response is bound to the same offer version, counterparty/thread, received time, provider message ID, content snapshots, price/currency, review class, and reviewer-attestation digest.

`EXACT_ACCEPT` only becomes `HUMAN_CLOSING_READY` when all bound commercial fields equal the current non-superseded offer version and the response falls inside the issue/expiry/snapshot window. Even then all contract, signer, payment, fulfillment and revenue authority flags remain `false`; the next action is human closing review.

Other response classes route conservatively: `COUNTEROFFER` → `COUNTEROFFER_REVIEW`, `PARTIAL_ACCEPT` → `CLARIFICATION_REQUIRED`, `QUESTION` → `OWNER_REPLY_REQUIRED`, `DECLINE` → `DECLINED`, and `AMBIGUOUS` → `HUMAN_REVIEW_REQUIRED`.

Changed payload under one event ID fails idempotency. Same provider message mapped to different normalized responses fails closed. Superseded-version replies are quarantined; current-scope temporal/thread/counterparty/exact-match inconsistencies block closing rather than falling back to an earlier reply.

## Receipt trust boundary

`receipt_self_digest_matches()` answers only whether the receipt's embedded checksum matches its current bytes. That is an integrity check, **not** proof that the receipt came from this bridge or that its semantics are trusted; anyone who can author arbitrary JSON can also calculate its checksum.

`verify_receipt()` therefore requires an independently trusted expected receipt SHA-256 and then validates the exact bridge schema, state vocabulary, state/next-action relationships, counts, derived state/quarantine roots, and every authority flag. The expected digest must come from a trusted channel outside the receipt being inspected; copying `receipt_sha256` out of the same untrusted file does not create authenticity.

The deterministic acceptance fixture has frozen expected receipt commitment:

`dede4ae4fb681198b46e5d4433f182f05afe4583539d2f62487672bda27767fb`

## Acceptance fixture

`acceptance.py` produces 60 synthetic offer series / 65 versions and a 125-record input batch with 120 unique events + five exact retries. Expected states are 15 `HUMAN_CLOSING_READY`, 10 `COUNTEROFFER_REVIEW`, 5 `CLARIFICATION_REQUIRED`, 5 `OWNER_REPLY_REQUIRED`, 5 `DECLINED`, 10 `HUMAN_REVIEW_REQUIRED`, 5 `AWAITING_RESPONSE`, and 5 `EXPIRED_NO_ACCEPTANCE`. It also forces five superseded-version acceptance attempts and five exact-accept content mismatches into quarantine. The receipt must remain identical when all input events are reversed.

## Run

From the Commons repository root:

```bash
python -m unittest revenue.commercial_acceptance_bridge.test_gate -v
python -O -m unittest revenue.commercial_acceptance_bridge.test_gate -v
python -m revenue.commercial_acceptance_bridge.acceptance --write-receipt /tmp/commercial-acceptance-receipt.json
python -m revenue.commercial_acceptance_bridge.acceptance \
  --verify-receipt /tmp/commercial-acceptance-receipt.json \
  --expected-receipt-sha256 dede4ae4fb681198b46e5d4433f182f05afe4583539d2f62487672bda27767fb
```

No production validation depends on Python `assert`, so optimized mode preserves the same fail-closed checks.
