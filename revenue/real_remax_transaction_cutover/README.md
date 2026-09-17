# Real/REMAX transaction cutover evidence core

This package is an **offline evidence gate** for a source→target brokerage transaction migration. It does not connect to a brokerage, MLS, TMS, escrow, payment, licensing, or production system. Synthetic or buyer-authorized offline exports are the only intended input.

## What it proves

For every source transaction whose source stage is in the policy's active set, the compiler requires a one-to-one mapped target transaction and checks:

- source/target office and agent identity maps are one-to-one and resolve to retained snapshot rows;
- each mapped target agent remains in the mapped target office;
- source stage and status map exactly through a closed policy map;
- gross commission matches in integer cents;
- relationship role, mapped agent, split basis points, and relationship commission cents match exactly;
- relationship commission cents sum exactly to gross and split basis points sum to 10,000 in each snapshot;
- required roles remain present;
- active source transactions cannot disappear or point to a missing target row.

The report binds the exact source snapshot, target snapshot, identity map, and policy by SHA-256. `verify_report()` recompiles semantics and requires canonical report equality; resealing a modified report is not sufficient.

## Truth boundary

A `PARITY` result means only that the supplied, internally valid offline generations satisfy this package's deterministic cutover contract. It is **not** evidence of legal/licensing compliance, brokerage approval, commission entitlement, production cutover, agent/customer notice, buyer acceptance, payment, escrow/disbursement, or recognized revenue. All such authority fields are hard-false in the report.

## Synthetic acceptance fixture

`synthetic_fixture.build_synthetic_bundle()` builds 240 active transactions across four offices and 32 synthetic agents. The root test bridge exercises all 240 as a clean acceptance corpus and then attacks stage/status drift, exact-cent drift, split/relationship drift, office mismatch, missing/ambiguous mappings, duplicate identities, receipt tamper/reseal, source-generation drift, order invariance, strict duplicate/non-finite JSON, and create-exclusive publication.

## CLI

Inputs must be strict canonical UTF-8 JSON. Duplicate keys, non-finite values, non-regular input files, oversized inputs, input-generation mutation during read, and non-exclusive output paths fail closed.

```bash
python -m revenue.real_remax_transaction_cutover.cli compile \
  --source source.json \
  --target target.json \
  --identity-map identity-map.json \
  --policy policy.json \
  --output report.json

python -m revenue.real_remax_transaction_cutover.cli verify \
  --source source.json \
  --target target.json \
  --identity-map identity-map.json \
  --policy policy.json \
  --report report.json
```

Exit codes: compile `0=PARITY`, `2=HOLD`, `4=input/contract error`; verify `0=VERIFIED`, `3=INVALID`, `4=input/contract error`.

## Lineage

Recovery implementation for Commons issue #13800. Original commercial trigger/scope/source credit remains Z-Cyclotomic-913645-R5K8 (`ZCYC-R5K8`). Recovery/source/test/finalization lane: Swarm Z / GPT-5.6 Sol, operation `REAL-REMAX-TRANSACTION-CUTOVER-EVIDENCE-RECOVERY-ZSOL-20260917`.
