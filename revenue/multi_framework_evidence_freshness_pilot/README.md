# Multi-Framework Evidence Freshness Diagnostic

A fixed-scope commercial wrapper over the landed `revenue.multi_framework_evidence_freshness` engine. It does **not** implement a second freshness classifier. It calls and re-verifies the existing engine, binds its exact packet/projection/receipt, then emits a privacy-minimized buyer diagnostic and commercial scope.

## Fixed paid step

- **$3,500 USD fixed diagnostic**
- one sanitized export
- up to **500 evidence objects**
- SOC 2 / ISO 27001 / HITRUST / PCI DSS evidence freshness/reuse QA through the landed engine
- buyer report: REUSABLE / STALE / SCOPE_MISMATCH / MISSING_OWNER / INCOMPLETE counts plus aggregate non-reusable reason counts
- deterministic JSON packet + SHA-256 receipt
- no custom source-system adapter included

Optional follow-on: **$10,000 integration sprint**, only after the paid diagnostic establishes value and the actual adapter/source-system scope is known. The wrapper mechanically records `integration_requires_paid_diagnostic=true` and `free_custom_adapter=false`.

## Truth boundary

This product is pre-assessment evidence QA. It is **not** an audit opinion, certification opinion, control-effectiveness conclusion, or assurance recommendation. It does not mutate evidence, contact a customer, mutate a provider, move money, or recognize revenue.

The buyer Markdown is deliberately aggregate: it excludes evidence IDs, owner refs, source refs, and evidence checksums. The full deterministic JSON packet retains the base packet for exact internal custody and re-verification.

## CLI

Production compilation owns current UTC; there is no public `--as-of` argument.

```bash
python -m revenue.multi_framework_evidence_freshness_pilot.pilot compile input.json pilot.json
python -m revenue.multi_framework_evidence_freshness_pilot.pilot verify pilot.json
```

Input is bounded to 4 MiB, one regular-file descriptor generation, no-follow/nonblocking where available, strict UTF-8 and duplicate-key/non-finite rejection. Output is create-exclusive mode 0600. Existing output is never overwritten or deleted by pathname rollback.

## Source contract

The wrapper imports:

- `compile_packet()` from `revenue.multi_framework_evidence_freshness.gate`
- `verify_packet()` from that same landed engine

Any base validation failure fails the pilot closed. The pilot verifier recompiles from the embedded normalized base input at the exact retained evaluation time and requires byte-canonical equality of the whole commercial packet.
