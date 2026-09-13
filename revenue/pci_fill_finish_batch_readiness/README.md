# PCI sterile fill-finish batch-readiness evidence core

Provider-free, synthetic/non-production evidence gate for the commercial pilot seam `pci-fill-finish-batch-readiness-preflight-01`.

It answers one bounded question: **does the supplied evidence packet satisfy the declared preflight invariants for a planned manufacturing slot, or must an owner review a named HOLD?** It does **not** release a batch or make a GMP/QP/quality/scientific decision.

## Evidence joined

A strict packet binds:

- approved recipe identity/version/digest to the recipe scheduled for the slot;
- released material-lot evidence;
- equipment calibration validity through the planned slot;
- isolator + environmental-monitoring state captured no later than the trusted `as_of`;
- fill-weight and inspection evidence to the exact batch and approved recipe digest;
- required device/label BOM to the exact staged component/version set.

Unknown durable fields, malformed identifiers/digests, noncanonical timestamps, duplicate material/equipment/BOM identities, future environmental evidence, and invalid time ordering fail closed before a decision is emitted.

## Decisions

`evaluate(packet)` emits only `READY` or `HOLD`, exact ordered HOLD codes, the canonical source digest, all evidence digests, a content-addressed receipt, and an explicit authority ceiling with every operational/release authority set to `false`.

Named HOLD reasons:

- `RECIPE_MISMATCH`
- `MATERIAL_UNRELEASED`
- `CALIBRATION_EXPIRED`
- `ENVIRONMENT_HOLD`
- `INSPECTION_LINEAGE_MISMATCH`
- `BOM_MISMATCH`

`verify_decision(packet, decision, verify_at=...)` recomputes the decision and requires an explicit verification time. It rejects source/decision tamper, verification before the packet `as_of`, and stale decisions beyond the configured maximum age.

## Acceptance contract

Run from repository root:

```bash
python -m revenue.pci_fill_finish_batch_readiness.acceptance
python -m unittest revenue.pci_fill_finish_batch_readiness.test_gate -v
python -O -m unittest revenue.pci_fill_finish_batch_readiness.test_gate -v
```

The deterministic acceptance suite evaluates exactly **180 synthetic packets**:

- 144 `READY`;
- 36 `HOLD`;
- exactly 6 HOLDs for each of the six named defect classes.

The acceptance report includes a digest of the complete decision-receipt set and verifies every decision before reporting success.

## Authority ceiling

This package is evidence/readiness support only. It has no production credentials or buyer data and performs no recipe authoring, equipment/environment mutation, label/device release, QA/QP/GMP/scientific determination, batch disposition/release, provider/account mutation, deployment, buyer contact, contract/payment action, or recognized-revenue claim. Human/institutional owners retain all regulated and operational authority.
