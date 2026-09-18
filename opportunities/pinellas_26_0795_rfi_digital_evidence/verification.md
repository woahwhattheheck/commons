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
3. host current time bounds predecessor verification and successor construction/full replay;
4. host retained witness is the exact predecessor generation;
5. successor advancement is atomic expected-predecessor → successor compare-and-retain;
6. the complete successor is independently replayed before CAS;
7. target raw storage identity/shape and cloned successor publication values are preflighted before CAS;
8. caller-visible publication after CAS updates only the target's already-existing exact built-in dictionary keys through a captured `dict.__setitem__`, never `Evidence` attribute assignment;
9. authority-record fields and Evidence state are read from raw instance storage through captured `object.__getattribute__`, so later class data-descriptor/property rebinding does not redirect CURRENT semantics;
10. the concrete `NoneType` and other builtin/runtime primitives are captured while the private graph is built; the exact builtin-shadow predecessor no longer resolves module-global `type(None)` at call time;
11. canonical JSON bytes are produced by the current graph itself from captured primitives rather than late-delegated through `json.JSONEncoder`;
12. current authority record roots, snapshot roots, event hashes, witnesses and semantic replay are recomputed inside the current graph instead of delegating to mutable low-level authority helpers; and
13. authority snapshots referenced by current events must be reacquirable through the host archive surface by recomputed exact root.

## Predecessor killers

The focused current-authority suite now contains **18 tests** covering:

- public-constructor attempts to inject alternate time normalizer, Evidence type, AuthoritySnapshot type or copy semantics;
- future authority at T3 while host current time is T2, including attempted request `at=T4` injection;
- rebinding `custody_reference._utc` after service construction;
- rebinding low-level `AuthoritySnapshot.root`, `AuthoritySnapshot.bind_current`, `AuthorityRecord.root`, `Evidence.witness` and `Evidence.verify` after service construction;
- rebinding `AuthorityRecord` field descriptors (`evidence_id`, `decision`, `issuer`, `at`, `revoked`) after snapshot construction;
- shadowing ordinary builtin names in the current module after factory construction, including creation of a fresh service through the already-built public factory;
- late `hashlib.sha256` rebinding after module import;
- provider-method and current-module low-level-name rebinding after service construction;
- attempted reassignment of bound service operations/trust attributes;
- deterministic two-writer same-predecessor concurrency where exactly one host CAS commits;
- host witness-write failure with no caller-visible mutation;
- all seven `Evidence` state/event names replaced with raising data descriptors while a destruction transition must still CAS, publish raw state and verify with the retained witness aligned;
- direct coherent low-level/caller mutation without host witness advancement;
- archived snapshot root mismatch;
- current snapshot that is not already reacquirable from the host archive surface; and
- host clock rollback beneath a retained event.

The predecessor generation had a contract-equivalent local 14/14 normal + 14/14 `python -O` development harness. The superseded 17-test head had **no exact-byte local PASS**. **Neither receipt binds this current 18-test successor.** An attempt to materialize the exact GitHub branch in this chat runtime failed before source retrieval because the container has no DNS route to GitHub (`Could not resolve host: github.com`). Therefore current exact-byte local execution remains truth-labeled **NOT RUN / UNKNOWN**, not green.

Exact-head review `5223468493` on predecessor `bfb51b4e80b73b24e42bfe89c281eb23d173551b` found the late `type(None)` resolution and post-CAS descriptor-dispatch publication seam. Both findings are consumed in this successor and that review is audit evidence only; it is not approval for the repaired head.

## Hosted truth requirement

`.github/workflows/pinellas-26-0795-rfi.yml` compiles both custody sources and both test modules, runs the complete test directory under normal Python and `python -O`, and asserts that the landed Commons proposal gate still reports `submission_ready: false` with at least one blocker. An exact-head hosted GitHub Actions receipt is required before merge. No queued/pending run is called green.

The response package remains externally blocked until the controlling packet/addenda/hash, OpenGov route, legal entity/signer, required attestations and owner response authority are evidenced through the existing gate. Nothing in this recovery grants County contact, OpenGov submission, pricing/contract/payment authority or recognized revenue.