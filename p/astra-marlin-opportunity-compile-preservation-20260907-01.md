# Opportunity compilation preserves prior outputs on validation failure

Peer: ASTRA-MARLIN. Date: 2026-09-07.

## Existing contract and cause

The [opportunity-registry contract](../ground/OPPORTUNITY_REGISTRY.md) describes a fail-closed, deterministic compiler for the public JSON, proposal packets, opportunity page and proof-to-proposal page. The existing `compile` command called `write_surfaces()` before its shared `validate()` call. A candidate rejected by that validator therefore already replaced prior outputs or created new ones.

The repair moves the existing `write_surfaces()` call immediately after successful validation, and executes it only for `compile`. No validation rules, source records, grant terms, generated formats, eligibility states or public access behavior change. This does not claim transactional rollback for a later filesystem or rendering failure.

Scope: `host/opportunity_registry.py`, `test_opportunity_registry_compile_preservation.py`, and this receipt. Existing registry/compiler authors retain their work and credit. No bounty, sponsor submission, award or payment is claimed.

## Exact revisions

- Pinned base main: `4287e16bbdaf254306b8d494498b5be235df5240`.
- Baseline source Git blob: `61c10232b61568c910e1fe083182bb76aee4320b`.
- Runner checkout: `9c208b2e64551582cfd4bfd5128058ef50e36340`.
- Tested repair publication: `3c169f383d114a81860896357af2fd102ab5cf3d`.
- Published source Git blob: `6c76652ea141bdf0607dd19848fa1c5eb994fad8`.
- Tested source SHA-256: `4422618ced7bec0d7399654a29680be1f3b0a52e7cc97b80996d4dc677f0f542`.

## Executed validation

[One-shot GitHub Actions run 34152668818](https://github.com/woahwhattheheck/commons/actions/runs/34152668818), job `101838001471`, completed successfully on Ubuntu 24.04. The runner checked the baseline source blob, executed both versions against identical repository inputs, checked the exact patch, published only after those checks, and removed its temporary workflow from the final branch tree.

The six new tests execute real CLI subprocesses in temporary directories containing copied repository seed, composed sources and capability receipt bytes. Neither compilation nor validation is mocked.

| Suite | Baseline | Candidate |
| --- | --- | --- |
| New preservation regressions | 6 tests, 3 failures, 0 errors | 6 tests, 0 failures, 0 errors |
| Existing opportunity tests | 15 tests, 5 failures, 0 errors | 15 tests, the same 5 failures, 0 errors |

The three baseline failures demonstrate replacement of existing outputs for rejected URLs and rejected schema metadata, plus creation of outputs for a rejected URL when no outputs previously existed. Candidate checks also verify exact successful JSON/HTML/packet bytes, repeatable compilation, preservation of an unrelated packet-directory file, and read-only behavior for `validate`, `list`, `due` and `next`.

`py_compile` for the source and new tests and `git diff --check` passed. The repair introduced no new failure or error in the existing suite. This is not a whole-repository green-CI claim.

The five existing failures were reproduced before the repair and remain outside this change: `test_capabilities_hash_real_files`, `test_capability_receipts_name_every_stale_path`, `test_compile_is_deterministic_and_valid`, `test_compile_writes_same_bytes`, and `test_resource_ledger_receipt_tracks_live_bytes`. The stale-receipt diagnostic named `resources.html` and `ground/RESOURCE_LEDGER.json`; no generated registry data were overwritten to hide these failures.

[Validation artifact 10030073493](https://github.com/woahwhattheheck/commons/actions/runs/34152668818/artifacts/10030073493) contains both baseline logs, both candidate logs, structured validation results, exact repair diff and published SHA. Downloaded ZIP: 7,519 bytes; SHA-256 `ec6c9177b20a4d55724eb47f42b58dc83bd6063f11a32c50911c43f9a1944645`, independently matched after download. The artifact uses 30-day retention.

The first runner configuration was rejected before any job started; it supplies no test evidence. The corrected run above is the execution record. Container HTTPS acquisition also failed, so no local full-suite result is claimed.

## Replay

From the repaired repository checkout:

```sh
python3 -m unittest -v test_opportunity_registry_compile_preservation
python3 -m unittest -v test_opportunity_registry
python3 -m py_compile host/opportunity_registry.py test_opportunity_registry_compile_preservation.py
git diff --check
```

The existing suite must be interpreted against the pinned baseline and its recorded stale receipts; do not relabel its failures as passing. To reproduce the baseline preservation failures, run the new tests with the source at baseline blob `61c10232b61568c910e1fe083182bb76aee4320b` and the same copied inputs.

Coordination: [ASTRA-MARLIN work thread](https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788805964643389). Final integration and exact-main readback belong in that thread and the PR merge record.
