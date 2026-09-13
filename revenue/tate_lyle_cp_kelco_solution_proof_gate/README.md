# Tate & Lyle / CP Kelco portfolio integration solution-proof gate

Offline, read-only synthetic evidence gate for cross-portfolio solution packs.
It joins approved ingredient/spec revision, region/use-level/claim references,
allergen/label hash, pilot-stability result, legacy substitute mapping, and
named commercial/science owner version.

Strongest state: `READY_FOR_OWNER_INTEGRATION_REVIEW`.

This is not formulation approval, claim approval, regulatory decision, product
release, buyer acceptance, payment, or recognized revenue.

## Acceptance fixture

`fixture.make_acceptance_batch()` builds 120 frozen synthetic packs:

- 90 PASS
- 30 HOLD
- 75 seeded defects: 20 spec + 15 region/use/claim + 15 legacy + 15 stability + 10 owner/version

## Run

From repository root:

```bash
python -m unittest revenue.tate_lyle_cp_kelco_solution_proof_gate.test_gate -v
python -O -m unittest revenue.tate_lyle_cp_kelco_solution_proof_gate.test_gate -v
python -m py_compile revenue/tate_lyle_cp_kelco_solution_proof_gate/*.py
```
