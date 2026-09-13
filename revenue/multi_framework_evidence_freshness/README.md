# Multi-Framework Evidence Freshness Gate

A dependency-free, read-only pre-assessment QA gate for evidence reused across SOC 2, ISO 27001, HITRUST, and PCI DSS work.

It requires each evidence object to carry an opaque owner reference, collection time, assessment-period coverage, framework/control mapping, SHA-256 checksum, freshness-rule identity, and source reference. It emits exactly one state per object:

- `REUSABLE`
- `STALE`
- `SCOPE_MISMATCH`
- `MISSING_OWNER`
- `INCOMPLETE`

`REUSABLE` is deliberately narrow. It means the supplied record is complete, its declared mappings are inside the declared assessment scope, its coverage spans the declared assessment period, its collection time is current under the exact freshness policy, and its checksum/owner/source fields are present. It does **not** mean the evidence is authentic, sufficient for an audit, that a control is effective, or that any certification should be granted.

## Determinism and provenance

The compiler canonicalizes scope, mappings, and evidence order; emits a source-field trace for every result; commits the normalized input and projection with SHA-256; renders deterministic Markdown; and produces a content-addressed receipt. `verify_packet()` recompiles from the exact embedded normalized input and recorded evaluation instant.

The production CLI owns current UTC. There is no public `--as-of` option. Historical evaluation time injection exists only in the Python API for deterministic tests/verifier replay.

## CLI

```bash
python -m revenue.multi_framework_evidence_freshness.cli compile input.json packet.json review.md
python -m revenue.multi_framework_evidence_freshness.cli verify packet.json
```

Outputs are create-exclusive. A late second-output failure preserves the first visible publication for explicit reconciliation rather than deleting a pathname it may no longer own.

## Golden acceptance

`golden.py` deterministically materializes exactly 400 synthetic evidence objects and pins the canonical corpus SHA-256 so silent fixture drift fails. The focused test suite requires exactly:

- 240 `REUSABLE`
- 50 `STALE`
- 40 `SCOPE_MISMATCH`
- 35 `MISSING_OWNER`
- 35 `INCOMPLETE`

It also proves zero reusable rows outside period/scope or without owner, mapping, checksum, source reference, and exact freshness-rule binding; source-field trace presence; byte-identical canonical packet hashes across three independent compiles; input-order invariance; duplicate-key rejection; bool/int/type traps; future collection rejection; and receipt/Markdown tamper detection.

## Authority ceiling

This module performs no audit or certification opinion, control-effectiveness rating, evidence alteration, independence-sensitive recommendation, customer/assessor contact, provider/account mutation, submission, signature, payment, or revenue recognition. Human assessors retain those decisions.
