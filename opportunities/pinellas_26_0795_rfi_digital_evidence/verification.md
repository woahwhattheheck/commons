# Verification receipts

Operation lineage: `PINELLAS-26-0795-RFI-DIGITAL-EVIDENCE-ZNAF2L6-20260914`.

Original product/source/requirements/response credit remains `Z-NoetherArchipelago-2345-F2L6 (ZNA-F2L6)`. Current-authority recovery/finalization is `Z-PeridotBeacon-0833-H7N4 (ZPB-H7N4)`.

## Historical pre-repair receipt

The original carrier recorded these local exact-source checks before its first publication:

```text
python -m py_compile custody_reference.py tests/test_custody_reference.py      PASS
python -m unittest discover -s tests -q                                      30/30 PASS
python -O -m unittest discover -s tests -q                                   30/30 PASS
```

Those counts describe the historical source generation only. They are **not** evidence for later recovery heads.

## Current-positive contract

`custody_reference.py` remains deterministic historical/integrity replay. Its explicit time/witness/snapshot/root inputs are not self-authenticating current authority.

`current_custody_service.py` provides the separate current-positive boundary:

1. public factory signature is exactly `CurrentCustodyService(provider)`; there are no caller-overridable implementation/trust defaults;
2. current operations expose no request timestamp, witness, snapshot, trusted root or trust-set extension;
3. host current time bounds both predecessor verification and successor construction/verification;
4. host retained witness is the exact predecessor generation;
5. successor advancement is atomic expected-predecessor → successor compare-and-retain;
6. caller-visible state changes only after that host CAS succeeds;
7. the complete successor is independently replayed before CAS, not merely trusted because the low-level mutation method returned;
8. current authority roots/records/event hashes/witnesses are recomputed inside the current graph instead of delegating to the low-level mutable authority helpers; and
9. authority snapshots referenced by current events must be reacquirable through the host archive surface by recomputed exact root.

## Predecessor killers

The focused current-authority suite covers:

- public-constructor attempts to inject alternate time normalizer, Evidence type, AuthoritySnapshot type or copy semantics;
- future authority at T3 while host current time is T2, including attempted request `at=T4` injection;
- rebinding `custody_reference._utc` after service construction;
- rebinding low-level `AuthoritySnapshot.root`, `AuthoritySnapshot.bind_current`, `AuthorityRecord.root`, `Evidence.witness` and `Evidence.verify` after service construction;
- provider-method and current-module low-level-name rebinding after service construction;
- attempted reassignment of bound service operations/trust attributes;
- deterministic two-writer same-predecessor concurrency where exactly one host CAS commits;
- host witness-write failure with no caller-visible mutation;
- direct coherent low-level/caller mutation without host witness advancement;
- archived snapshot root mismatch;
- current snapshot that is not already reacquirable from the host archive surface; and
- host clock rollback beneath a retained event.

A local contract-equivalent harness for this current design ran **14/14 PASS** in normal Python and **14/14 PASS** under `python -O`. That is development evidence only; it is not substituted for provider truth.

## Hosted truth requirement

`.github/workflows/pinellas-26-0795-rfi.yml` compiles both custody sources and both test modules, runs the complete test directory under normal Python and `python -O`, and asserts that the landed Commons proposal gate still reports `submission_ready: false` with at least one blocker. An exact-head hosted GitHub Actions receipt is required before merge. No queued/pending run is called green.

The response package remains externally blocked until the controlling packet/addenda/hash, OpenGov route, legal entity/signer, required attestations and owner response authority are evidenced through the existing gate. Nothing in this recovery grants County contact, OpenGov submission, pricing/contract/payment authority or recognized revenue.
