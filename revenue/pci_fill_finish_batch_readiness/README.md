# PCI sterile fill-finish batch-readiness evidence core

Provider-free, synthetic/non-production evidence gate for the commercial pilot seam `pci-fill-finish-batch-readiness-preflight-01`.

It answers one bounded question: **does a complete, explicitly time-bounded evidence packet satisfy the declared preflight invariants for a planned manufacturing slot, or must an owner review a named HOLD?** It does **not** release a batch or make a GMP/QP/quality/scientific decision.

## Why v2 exists

The original v1 packet had three authority gaps that could produce an over-broad `READY`:

1. the packet listed material lots and equipment, but did not bind them to an exact recipe-required material/equipment set, so an incomplete nonempty subset could pass those classes;
2. the packet supplied its own `as_of` even though the contract described that clock as trusted;
3. environmental evidence only had to be captured before `as_of`; it did not have to remain valid through the planned slot.

v2 deliberately breaks the input contract instead of silently accepting those cases.

## Evidence joined

A strict v2 packet binds:

- approved recipe identity/version/digest to the recipe scheduled for the slot;
- the recipe's exact required material-component set to the complete supplied material evidence set;
- the recipe's exact required equipment-id set to the complete supplied equipment evidence set;
- released material-lot evidence observed no later than an out-of-band trusted evaluation time;
- equipment calibration evidence observed no later than that trusted time and valid through the planned slot;
- isolator + environmental-monitoring state captured no later than the trusted time **and explicitly valid through the planned slot**;
- fill-weight and inspection evidence to the exact batch and approved recipe digest;
- required device/label BOM to the exact staged component/version set.

Unknown durable fields, malformed identifiers/digests, noncanonical timestamps, duplicate material/equipment/BOM/recipe requirement identities, future-dated evidence, invalid environment validity intervals, and invalid trusted-time ordering fail closed before a decision is emitted.

## Trusted time boundary

The packet no longer contains `as_of`. The host must supply evaluation time out-of-band:

```python
from revenue.pci_fill_finish_batch_readiness import evaluate

decision = evaluate(packet, trusted_as_of="2026-09-13T11:00:00Z")
```

Persist that trusted time beside the packet and decision. Verification requires the same independently retained evaluation time plus a new trusted verification time:

```python
from revenue.pci_fill_finish_batch_readiness import verify_decision

verification = verify_decision(
    packet,
    decision,
    expected_evaluated_at="2026-09-13T11:00:00Z",
    trusted_verify_at="2026-09-13T11:01:00Z",
)
```

A result payload or packet must not be allowed to choose either trusted clock. The default decision-age ceiling is exactly 86,400 seconds; age is checked in seconds rather than floored minutes.

## Decisions

`evaluate(packet, trusted_as_of=...)` emits only `READY` or `HOLD`, exact ordered HOLD codes, the canonical source digest, a recipe-requirements digest, all evidence digests, a content-addressed receipt, and an explicit authority ceiling with every operational/release/revenue authority set to `false`.

Named HOLD reasons:

- `RECIPE_MISMATCH`
- `MATERIAL_COVERAGE_MISMATCH`
- `MATERIAL_UNRELEASED`
- `EQUIPMENT_COVERAGE_MISMATCH`
- `CALIBRATION_EXPIRED`
- `ENVIRONMENT_HOLD`
- `ENVIRONMENT_STALE_FOR_SLOT`
- `INSPECTION_LINEAGE_MISMATCH`
- `BOM_MISMATCH`

## v1 -> v2 migration

A v1 packet must be rebuilt; it is not auto-upgraded.

- remove packet `as_of` and pass the trusted clock to `evaluate()`;
- add recipe `observed_at`, `required_material_components`, and `required_equipment_ids`;
- add `observed_at` to every material and equipment row;
- add environment `valid_until`;
- add `observed_at` to `fill_inspection` and `bom`;
- update the schema to `pci.fill-finish-batch-readiness/v2`;
- update verifier calls to provide both `expected_evaluated_at` and `trusted_verify_at`.

This package does not infer missing requirements during migration. Incomplete authority remains a HOLD/fail-closed condition.

## Acceptance contract

Run from repository root:

```bash
python -m revenue.pci_fill_finish_batch_readiness.acceptance
python -m unittest revenue.pci_fill_finish_batch_readiness.test_gate -v
python -O -m unittest revenue.pci_fill_finish_batch_readiness.test_gate -v
```

The deterministic acceptance evaluates exactly **180 synthetic packets**:

- 126 `READY`;
- 54 `HOLD`;
- exactly 6 HOLDs for each of the nine named defect classes.

The acceptance report verifies every decision against independently supplied evaluation/verification times and emits a digest of the complete decision-receipt set.

## Authority ceiling

This package is evidence/readiness support only. It has no production credentials or buyer data and performs no recipe authoring, equipment/environment mutation, label/device release, QA/QP/GMP/scientific determination, batch disposition/release, provider/account mutation, deployment, buyer contact, contract/payment action, or recognized-revenue claim. Human/institutional owners retain all regulated and operational authority.
