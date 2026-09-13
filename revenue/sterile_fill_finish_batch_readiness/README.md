# Sterile Fill-Finish Batch Readiness — evidence core

This package implements the already-requested `pci-fill-finish-batch-readiness-preflight-01` as a **provider-free, synthetic, owner-review-only evidence gate**. It is suitable for a paid non-production pilot around one agreed manufacturing handoff, but it does not make or automate a batch-release decision.

## What it binds

A readiness packet binds a declared batch/lot and product to:

- the approved formulation/recipe revision and line revision;
- exact expected material lots plus release-evidence pointers;
- required equipment state and calibration validity;
- isolator and environmental-monitoring state with an explicit freshness window;
- fill-weight and inspection lineage back to the same batch/lot;
- packaging BOM, label revision, and device-assembly readiness;
- open/closed deviation evidence for the batch.

Input is an event set rather than a mutable checklist. Exact repeated event IDs with byte-equivalent content collapse without changing the package. Reusing an event ID with changed content fails closed. The normalized event set is sorted before hashing, so event order cannot change the receipt.

The strongest status is **`READY_FOR_OWNER_BATCH_REVIEW`**. Any missing, stale, conflicting, unreleased, mismatched, held, or ambiguous evidence produces **`HOLD_FOR_OWNER_REVIEW`** with deterministic codes and subjects.

## Acceptance fixture

`acceptance.py` generates **180 synthetic batch packets**:

- 144 clean packets → `READY_FOR_OWNER_BATCH_REVIEW`
- 36 deliberate holds, exactly 6 each:
  - formulation revision mismatch
  - material not released
  - expired equipment calibration
  - environment not ready
  - fill/inspection lineage mismatch
  - packaging BOM mismatch

Every packet is offline-verified. The acceptance runner also proves that adding an exact retry or reversing event order produces the same canonical package.

Run:

```bash
python -m unittest revenue.sterile_fill_finish_batch_readiness.test_gate_a revenue.sterile_fill_finish_batch_readiness.test_gate_b revenue.sterile_fill_finish_batch_readiness.test_gate_c revenue.sterile_fill_finish_batch_readiness.test_gate_d -v
python -O -m unittest revenue.sterile_fill_finish_batch_readiness.test_gate_a revenue.sterile_fill_finish_batch_readiness.test_gate_b revenue.sterile_fill_finish_batch_readiness.test_gate_c revenue.sterile_fill_finish_batch_readiness.test_gate_d -v
python -m revenue.sterile_fill_finish_batch_readiness.acceptance
```

## Fail-closed behavior

The gate rejects malformed schemas, bool-as-int traps, future evidence, unknown event kinds, changed-payload event-ID reuse, email-shaped primitive text, secret-shaped values, and secret/credential-shaped keys. It also holds when two different payloads claim the same latest timestamp for the same evidence slot.

The receipt is content-addressed and `verify_readiness_package()` rebuilds the normalized payload, readiness decision, hashes, and Markdown summary from the retained evidence. Tampering with payload, receipt, or summary fails verification.

## Authority ceiling

This package is evidence compilation for a human owner review. It **does not authorize or perform**:

- GMP, QP, quality, scientific, clinical, or batch-release decisions;
- manufacturing execution, line/equipment control, formulation or material release;
- deviation closure, packaging/device release, or label approval;
- access to patient data, production credentials, or live manufacturing systems;
- provider/account mutation, deployment, customer contact, contracting, payment, or revenue recognition.

Evidence references are opaque pointers. The package does not fetch external records and should not contain patient data, secrets, credentials, or personal contact data.
