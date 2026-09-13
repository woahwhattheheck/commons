# Regulated Handoff Evidence Gate

A buyer-neutral, synthetic-data acceptance engine for proving that a high-consequence logistics handoff has a complete, deterministic evidence record.

It binds shipment identity and fingerprint, source-system lineage, custody transitions, linked temperature evidence, exception state, and event ordering. Exact duplicate events are idempotent; reusing an event ID or source lineage with changed payload fails closed. Late events are canonicalized by event time and deterministic lineage tie-breaks so replay is byte-stable.

## What `PASS_EVIDENCE` means

Only this: **the supplied event set satisfies the configured evidence-completeness contract.** It does **not** authorize clinical/product release, determine regulatory compliance, approve a route or dispatch, resolve a temperature excursion, prove chain-of-identity suitability, mutate a production shipment, or represent buyer acceptance.

The engine performs no network calls and has no provider credentials, notifications, dispatch hooks, payment path, or production mutation surface.

## Input contract

See `fixtures/golden_bundle.json`. A bundle contains:

- immutable `shipment_id` + `fingerprint_sha256`;
- allowed source systems, initial/final custodian expectations, minimum transfer count, and temperature bounds/window;
- events carrying deterministic `event_id`, source-system `source_event_id`, shipment binding, RFC3339 timestamp, and kind-specific evidence.

Supported events: `custody_transfer`, `temperature`, `exception_open`, `exception_resolve`, and `checkpoint`.

Every custody transfer may bind a specific temperature event. When the contract requires temperature evidence, missing, stale, wrong-kind, or out-of-range evidence causes `HOLD`.

## CLI

```bash
python revenue/regulated_handoff_evidence/gate.py \
  revenue/regulated_handoff_evidence/fixtures/golden_bundle.json
```

Exit codes:

- `0`: `PASS_EVIDENCE`
- `3`: valid bundle evaluated to `HOLD`
- `2`: malformed input or identity/lineage conflict

Receipts are canonical JSON with `receipt_sha256`. `verify_receipt()` recomputes the commitment and rejects post-publication mutation.

## Focused validation

```bash
python -m py_compile revenue/regulated_handoff_evidence/gate.py test_regulated_handoff_evidence.py
python -m unittest -v test_regulated_handoff_evidence.py
python -O -m unittest -v test_regulated_handoff_evidence.py
```
