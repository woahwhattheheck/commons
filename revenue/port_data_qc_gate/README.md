# Data Consolidation QC Evidence Gate

This package is a buyer-neutral, offline evidence primitive for data-consolidation and reporting work. It was motivated by a bounded integration-QA teaming seam around Port of Tacoma / Northwest Seaport Alliance RFP **072026-1047**, but it contains no buyer data, maritime credentials, proposal language, or buyer-specific implementation.

## Temporal authority

The public current API owns its clock.

```python
from revenue.port_data_qc_gate import evaluate, verify

result = evaluate(policy, snapshot)
assert verify(result, policy=policy, snapshot=snapshot)
```

`evaluate(policy, snapshot)` accepts no caller-supplied evaluation timestamp. It captures process UTC inside the current API boundary and emits a receipt with `temporal_authority = PROCESS_UTC_CURRENT`. `verify(...)` independently captures process UTC again and re-evaluates freshness from the bound policy and snapshot. A receipt that was a valid current `PASS` at T0 therefore stops verifying as a current PASS once the snapshot is stale at the verifier's T1.

Deterministic explicit-time replay exists only as the private `_evaluate_historical_at(...)` / `_verify_historical(...)` test and forensic surface. Those receipts are permanently labeled `HISTORICAL_INTEGRITY_ONLY`; changing the label and re-addressing the receipt does not promote them into current authority.

Snapshot expiry compares the exact `timedelta`, not a truncated whole-second counter. For example, an age of 60.5 seconds is stale under a 60-second policy even though `snapshot_age_seconds` is retained as an integer display field.

## What it proves

Given an approved source/schema policy and one complete bounded snapshot, the gate builds a deterministic report projection and evidence receipt. It proves only that the supplied evidence is internally coherent under that policy and, for the public current API, fresh at process-owned verification time.

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
- process-owned current-time freshness and future-time fences;
- strict separation between current authority and historical replay;
- a verifier that rejects changed policy, source snapshot, report, exception ledger, receipt, added authority fields, temporal-label escalation/downgrade, and self-consistent rehashed forgeries.

A `PASS` is **evidence only**. Every receipt hard-codes `authority = EVIDENCE_ONLY_NO_OPERATIONAL_RELEASE`. It does not authorize ingestion into production, customer-facing publication, operational release, payment, proposal submission, buyer acceptance, contract formation, provider action, or revenue recognition.

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

## Acceptance boundary

The test suite exercises reordered events, exact duplicates, conflicting duplicate identities, missing predecessors, branching histories, business-key drift, incomplete and stale snapshots, exact fractional expiry, missing approved sources, unknown source/schema/fields, required-field absence, nested/float payload refusal, future timestamps, report/receipt/policy/snapshot tampering, historical-to-current readdress attempts, current-to-historical label drift, caller-time injection, stale historical PASS replay, and module-global datetime rebinding.

Run:

```bash
python -m unittest revenue.port_data_qc_gate.test_gate -v
python -O -m unittest revenue.port_data_qc_gate.test_gate -v
python -m py_compile revenue/port_data_qc_gate/gate.py revenue/port_data_qc_gate/test_gate.py
```

No Port, NWSA, Kalé, customer, provider, proposal, deployment, payment, or revenue action is performed by this package or its tests.
