# Tate & Lyle / CP Kelco Solution-Proof Gate — buyer-neutral core

This package implements the existing `tate-lyle-cp-kelco-solution-proof-gate-01` build demand as a **read-only cross-portfolio formulation-evidence gate**. It contains only synthetic acceptance data and no buyer records, credentials, production exports, formulas, or customer data.

The gate joins:

- approved ingredient identity and spec revision;
- region + use-reference + use-level + claim-reference scope;
- allergen and label evidence hashes;
- pilot-stability status, protocol version, result identity, and evidence hash;
- legacy substitute mapping and mapping version;
- named commercial/science owner references and owner-registry version.

Each frozen solution pack emits `PASS` or `HOLD`, exact stable codes, its record ID, source hash, evidence hashes, and owner references. The evidence manifest is canonical and content-addressed.

## Trust boundary

The packet cannot promote its own hashes into authority. Snapshot and policy commitments plus evaluation time are supplied separately by the integration boundary. Commitment mismatch, future snapshot, or stale snapshot fails closed. Hashes show integrity relative to a trusted commitment; they do **not** prove provider authenticity, and `trusted_acquisition_proven_by_this_tool` is always false.

The strongest result remains read-only evidence support. The tool authorizes **no formulation, claim approval, regulatory decision, customer promise, or product release**. It performs zero source writes and zero network writes.

## Canonical acceptance

`acceptance.py` exactly implements the demand:

- 120 frozen synthetic solution packs;
- 90 clean → `PASS`;
- 30 held → `HOLD`;
- exactly 75 seeded defect code/record pairs:
  - 20 `SPEC_REVISION_MISMATCH`;
  - 15 `REGION_USE_CLAIM_MISMATCH`;
  - 15 `LEGACY_MAPPING_MISMATCH`;
  - 15 `STABILITY_MISMATCH`;
  - 10 `OWNER_VERSION_MISMATCH`.

The 75 defects deliberately overlap across the same 30 held records. Acceptance fails unless all 75 exact codes appear, all 30 seeded records hold, all 90 clean records pass, source/network writes remain zero, two runs are byte-identical, and full offline artifact recompilation verifies.

Run:

```bash
python revenue/tate_lyle_cp_kelco_solution_proof_gate/test_gate.py
python -O revenue/tate_lyle_cp_kelco_solution_proof_gate/test_gate.py
python revenue/tate_lyle_cp_kelco_solution_proof_gate/acceptance.py
python -O revenue/tate_lyle_cp_kelco_solution_proof_gate/acceptance.py
python -m py_compile revenue/tate_lyle_cp_kelco_solution_proof_gate/*.py
```

Generated artifacts are deterministic `result.json`, `evidence_manifest.json`, `report.md`, and `receipt.json`. `verify_artifacts(...)` fully recompiles all four from the original source packet and trusted commitments; it does not merely re-hash submitted output.
