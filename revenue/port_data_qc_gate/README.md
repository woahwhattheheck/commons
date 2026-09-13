# Data Consolidation QC Evidence Gate

This package is a buyer-neutral, offline evidence primitive for data-consolidation and reporting work. It was motivated by a bounded integration-QA teaming seam around Port of Tacoma / Northwest Seaport Alliance RFP **072026-1047**, but it contains no buyer data, maritime credentials, proposal language, or buyer-specific implementation.

## What it proves

Given an approved source/schema policy, one **complete** bounded snapshot, and a trusted evaluation time, the gate builds a deterministic report projection and evidence receipt. It proves only that the supplied evidence is internally coherent under that policy.

The v1 contract provides:

- exact source + schema-version authority;
- bounded canonical JSON and scalar values;
- exact event identity with byte/content-bound SHA-256 evidence;
- duplicate-event collapse only when the entire canonical event is identical;
- out-of-order arrival tolerance by predecessor-chain reconstruction;
- fail-closed conflicting event IDs;
- record quarantine for missing predecessors, branching histories, non-single-chain histories, and business-key drift;
- an explicit hold when an approved source is silently missing from a supposedly complete snapshot;
- source-to-report lineage and per-lineage digest;
- deterministic report, exception-ledger, snapshot, policy, and receipt digests;
- trusted-time snapshot freshness and future-time fences, including exact fractional-second lease boundaries;
- a verifier that requires the caller's current trusted evaluation time, rejects a receipt that tries to choose a different clock, and rejects changed policy, source snapshot, report, exception ledger, receipt, or added receipt authority fields, including self-consistent rehashed forgeries.

A `PASS` is **evidence only**. The receipt hard-codes `authority = EVIDENCE_ONLY_NO_OPERATIONAL_RELEASE`. It does not authorize ingestion into production, customer-facing publication, operational release, payment, proposal submission, buyer acceptance, or revenue recognition.

## Minimal shape

Policy:

```json
{
  "schema": "port-data-qc-policy/v1",
  "max_snapshot_age_seconds": 600,
  "sources": {
    "edi": {
      "schema_version": "v1",
      "allowed_fields": ["container", "status"],
      "required_fields": ["container", "status"]
    }
  }
}
```

Snapshot:

```json
{
  "schema": "port-data-qc-snapshot/v1",
  "capture_complete": true,
  "captured_at": "2026-09-13T08:59:00Z",
  "events": [
    {
      "source_id": "edi",
      "event_id": "evt-1",
      "record_id": "record-1",
      "business_key": "CONT-1",
      "schema_version": "v1",
      "previous_event_id": null,
      "effective_at": "2026-09-13T08:57:00Z",
      "observed_at": "2026-09-13T08:58:00Z",
      "values": {"container": "CONT-1", "status": "ARRIVED"}
    }
  ]
}
```

Run it from Python. Verification must receive its trusted evaluation time from the verifier/integration boundary; a historical receipt cannot supply its own freshness clock:

```python
from revenue.port_data_qc_gate.gate import evaluate, verify

trusted_now = "2026-09-13T09:00:00Z"
result = evaluate(policy, snapshot, evaluated_at=trusted_now)
assert verify(result, policy=policy, snapshot=snapshot, evaluated_at=trusted_now)
```

## Acceptance boundary

The test suite exercises reordered events, exact duplicates, conflicting duplicate identities, missing predecessors, branching histories, business-key drift, incomplete and stale snapshots, fractional-second expiry, trusted-time rollback attempts, missing approved sources, unknown source/schema/fields, required-field absence, nested/float payload refusal, future timestamps, and report/receipt/policy/snapshot tampering.

Run:

```bash
python -m unittest revenue.port_data_qc_gate.test_gate -v
python -O -m unittest revenue.port_data_qc_gate.test_gate -v
python -m py_compile revenue/port_data_qc_gate/gate.py revenue/port_data_qc_gate/test_gate.py
```
