# Proposal validity / expiry / requote gate

This is an **owner-review commercial-truth gate** for an offer that was already proposed. It does not send anything, accept terms, sign a contract, operate a checkout rail, authorize payment, or recognize revenue.

The compiler compares an immutable issued-offer snapshot with the current offer/source snapshot and emits exactly one state:

- `CURRENT_FOR_OWNER_USE`
- `EXPIRED_REQUOTE_REQUIRED`
- `SUPERSEDED`
- `HOLD_NO_VALIDITY_BASIS`
- `HOLD_SOURCE_DRIFT`

The issued snapshot binds `offer_id`, `source_generation`, `pricing_revision`, `currency`, exact scope/economics JSON, `issued_on`, explicit validity semantics, and an optional buyer/solicitation deadline. The current snapshot binds the same live commercial semantics plus explicit later `AMENDMENT`, `REDLINE`, or `CHANGE_ORDER` evidence.

A change in pricing revision, currency, scope, or economics is `SUPERSEDED`; it is never silently rolled into the old quote. A later applicable amendment/redline/change-order is also `SUPERSEDED`. Source-generation movement without an explicit changed commercial snapshot is `HOLD_SOURCE_DRIFT`. `NO_EXPIRY_STATED` remains an owner hold while still respecting an already-passed buyer deadline as an expiry cap. Missing timezone information fails closed.

`requote_delta` is always labeled `PROPOSED_NOT_ACCEPTED`; it shows exact issued/current differences and applicable superseding events. A stale checkout URL or payment rail is non-authoritative context and never becomes buyer acceptance, payment authorization, a signed contract, outbound authority, or revenue.

The production CLI obtains its evaluation time from the runtime UTC clock. Offer/current JSON cannot inject `as_of`, `now`, or `evaluated_at`: strict unknown-key rejection closes that backdating seam. The verifier recomputes the exact packet at its bound evaluation instant and source snapshots; if that packet claimed `CURRENT_FOR_OWNER_USE`, it also re-evaluates against the live runtime clock so an old green packet cannot remain green after expiry or other current-state loss.

## Run

```bash
python revenue/proposal_validity_expiry_requote_gate/gate.py compile \
  --issued revenue/proposal_validity_expiry_requote_gate/example_issued.json \
  --current revenue/proposal_validity_expiry_requote_gate/example_current.json \
  --out /tmp/proposal-validity-packet.json

python revenue/proposal_validity_expiry_requote_gate/gate.py verify \
  --issued revenue/proposal_validity_expiry_requote_gate/example_issued.json \
  --current revenue/proposal_validity_expiry_requote_gate/example_current.json \
  --packet /tmp/proposal-validity-packet.json
```

## Tests

```bash
python -m py_compile revenue/proposal_validity_expiry_requote_gate/gate.py tests/test_proposal_validity_expiry_requote_gate.py
python -m unittest -v tests/test_proposal_validity_expiry_requote_gate.py
python -O -m unittest -v tests/test_proposal_validity_expiry_requote_gate.py
```

The hostile suite covers expired quotes copied into later pursuits, source drift, currency/scope/economics/pricing drift, all three superseding event classes, buyer deadline caps, timezone omission, packet clock injection, stale payment rails, bool/float money, duplicate/non-finite JSON, tampered receipts, an old-current packet replayed after runtime expiry, and create-exclusive CLI output.
