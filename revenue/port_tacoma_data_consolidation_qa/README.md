# Port of Tacoma / NWSA data-consolidation QA core

This package is a **synthetic, provider-free specialist delivery core** for the Token Junkie Labs teaming lane associated with Port of Tacoma / Northwest Seaport Alliance solicitation `072026-1047`. It turns frozen multi-source evidence into a deterministic assessment receipt. It does **not** access Port/NWSA systems, submit a procurement response, execute a migration, or claim an award.

The intended seam is the difficult part between “we inventoried the feeds” and “these records are safe to propose for migration”: source/batch trust, idempotent replay, schema/mapping integrity, cross-source reconciliation, completeness metrics, entity quarantine, lineage, and content-addressed evidence.

## What it evaluates

An assessment bundle contains:

- one canonical target schema with required and optional fields;
- source contracts for `edi`, `api`, and `file` evidence, including schema versions, required source fields, source→canonical maps, and expected entity keys;
- immutable batch declarations with source, sequence, schema version, record count, and SHA-256 content digest;
- immutable records with event ID, source/batch IDs, external/entity IDs, monotonic version, and flat exact scalar payloads.

The core is intentionally strict. Floating-point values are rejected; callers must use integer minor units or exact decimal strings when decimal semantics matter.

## Fail-closed trust boundary

Evaluation happens in five deterministic stages:

1. **Normalize the full input.** Unknown fields, duplicate IDs, duplicate JSON keys, non-finite JSON numbers, nested payload values, invalid names, ambiguous field maps, and unknown canonical mappings fail structurally.
2. **Validate batch authority.** Unknown source, source-schema drift, duplicate source sequence, declared-count drift, or content-digest drift makes the entire batch untrusted. Records from an untrusted batch cannot contribute to a migration candidate.
3. **Collapse exact retries.** Byte-equivalent records sharing an event ID collapse; the same event ID with changed evidence produces `EVENT_REPLAY_CONFLICT` and never enters reconciliation.
4. **Reconcile trusted source/entity streams.** Required source fields and mappings are checked; the latest unambiguous version is selected; expected source membership is enforced; canonical values are compared across sources; per-field and per-record lineage is retained.
5. **Emit a content-addressed receipt.** Every entity is `CANDIDATE` or `HOLD` with explicit reason codes. The receipt includes source inventory, trusted batch/record counts, source-entity completeness in parts-per-million, exception counts, lineage, input digest, and its own SHA-256.

A top-level `PASS` only means the supplied frozen evidence satisfies this assessment contract. Every receipt carries these negative authorities:

- `migration_authorized: false`
- `external_effects_performed: false`
- `buyer_acceptance_claimed: false`
- `contract_award_claimed: false`
- `revenue_claimed: false`

## Reconciliation and exception evidence

The receipt exposes both per-source and aggregate controls:

- expected / observed / matched / missing / unexpected entity counts;
- source-entity completeness in integer ppm, avoiding presentation-only floating point;
- input vs effective vs trusted records;
- total vs trusted vs invalid batches;
- exact retry-collapse and changed-event conflict counts;
- per-entity source lineage and canonical-field lineage;
- deterministic exception counts and reason codes such as `BATCH_CONTENT_MISMATCH`, `SOURCE_ENTITY_MISSING`, `CANONICAL_FIELD_CONFLICT`, and `ENTITY_VERSION_CONFLICT`.

If a batch hash is wrong, the assessment does not merely set a global red flag: that batch is removed from trusted evidence, affected source/entity links become missing, and those entities are individually held. This prevents an invalid batch from inflating the migration-candidate count.

## Offline CLI

Evaluate one frozen evidence bundle and write a receipt:

```bash
python -m revenue.port_tacoma_data_consolidation_qa.cli evaluate bundle.json --output receipt.json
```

Exit status is `0` for PASS, `2` for a valid HOLD assessment, and `4` for structurally invalid/unreadable evidence.

Verify a previously emitted receipt without re-running source adapters:

```bash
python -m revenue.port_tacoma_data_consolidation_qa.cli verify receipt.json
```

Exit status is `0` for a valid content-addressed receipt and `3` for a tampered/invalid receipt.

## Deterministic acceptance fixture

The checked-in acceptance generator creates a synthetic assessment with:

- 3 source types: EDI, API, file;
- 6 immutable source batches;
- 200 canonical entities;
- 604 input rows, including 4 exact retry rows;
- 600 effective/trusted rows after retry collapse;
- 200/200 migration **candidates** with 100% source-entity completeness;
- zero external effects or migration authority.

It also independently proves hostile holds for changed event replay, batch content drift, batch count drift, missing source membership, and cross-source canonical conflict. The unit suite adds schema drift, duplicate batch sequence, ambiguous latest version, malformed mappings/payloads, strict JSON, receipt tamper, untrusted-batch entity quarantine, and CLI behavior.

Run the exact local gates from the Commons root:

```bash
python -m unittest -q \
  revenue.port_tacoma_data_consolidation_qa.test_core \
  revenue.port_tacoma_data_consolidation_qa.test_cli
python -O -m unittest -q \
  revenue.port_tacoma_data_consolidation_qa.test_core \
  revenue.port_tacoma_data_consolidation_qa.test_cli
python -m py_compile \
  revenue/port_tacoma_data_consolidation_qa/core.py \
  revenue/port_tacoma_data_consolidation_qa/schema.py \
  revenue/port_tacoma_data_consolidation_qa/evaluator.py \
  revenue/port_tacoma_data_consolidation_qa/acceptance.py \
  revenue/port_tacoma_data_consolidation_qa/cli.py \
  revenue/port_tacoma_data_consolidation_qa/test_core.py \
  revenue/port_tacoma_data_consolidation_qa/test_cli.py
python -m revenue.port_tacoma_data_consolidation_qa.acceptance
```

## Integration roadmap / boundary

This package deliberately stops at the evidence boundary. A real delivery can add **separate buyer/prime-controlled adapters** without changing the assessment semantics:

1. read-only adapters snapshot authorized EDI/API/file inventories into this exact evidence schema;
2. the frozen assessment produces inventory, lineage, completeness, conflict, dependency, and quarantine evidence;
3. remediation decisions and mapping/business-rule changes are reviewed outside this core and assessed again as new content-addressed evidence;
4. any target-system dry run or migration execution lives in a distinct, explicitly authorized adapter with its own rollback and effect-idempotency controls.

There are no Port/NWSA credentials, production data, network clients, procurement submission functions, target-system writes, autonomous remediation, contract state, payment path, or award/acceptance claim in this package.
