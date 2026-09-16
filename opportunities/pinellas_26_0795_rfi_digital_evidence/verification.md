# Verification receipts

Operation: `PINELLAS-26-0795-RFI-DIGITAL-EVIDENCE-ZNAF2L6-20260914`

## Historical pre-repair receipt

The original carrier recorded these local exact-source checks before its first publication:

```text
python -m py_compile custody_reference.py tests/test_custody_reference.py      PASS
python -m unittest discover -s tests -q                                      30/30 PASS
python -O -m unittest discover -s tests -q                                   30/30 PASS
```

Those counts describe the historical source generation only. They are **not** evidence for later repair heads.

## Current verification contract

`custody_reference.py` remains the deterministic integrity/historical replay layer. Its explicit event time, witness and authority-root parameters are not self-authenticating current authority.

`current_custody_service.py` owns the current-positive composition contract:

1. the service captures the host's current-time, retained-witness, atomic compare-and-retain, current-authority and archived-authority callables once at construction;
2. individual current operations cannot pass an event timestamp, expected witness, authority snapshot, trusted root or trusted-root set;
3. a retained generation must match the host witness and contain no event later than the host current time;
4. mutation occurs on a copied candidate using that host time;
5. the host must **atomically** compare the exact predecessor witness and retain the successor; stale same-predecessor writers fail closed;
6. the caller-visible object is replaced only after successful host advancement;
7. hold/destruction gets the current snapshot through the captured provider; and
8. current verification reacquires exact archived snapshots referenced by retained events.

The current hostile suite includes predecessor killers for:

- a caller-minted low-level authority snapshot + its own root;
- a coherent local history + freshly minted local witness;
- future authority that cannot be promoted by passing a future request timestamp (current APIs expose no `at` argument);
- two deterministic same-predecessor writers where only one atomic host CAS may commit;
- witness-store failure atomicity;
- archived-snapshot root mismatch;
- host clock rollback below a retained current event; and
- ordinary rebinding after construction of provider methods, imported low-level type globals and the module factory name, plus attempted reassignment of service operation fields.

The closure-binding claim is not a Python sandbox claim. Arbitrary closure inspection, reflective interpreter mutation, debugger/source replacement, interpreter compromise, or a malicious host provider is outside this reference boundary.

A local contract-equivalent harness exercised the new focused suite as **11/11 PASS** in normal Python and **11/11 PASS** under `python -O`, and both new Python files syntax-compile. That harness is development evidence only; the exact repository head must still earn hosted GitHub Actions receipts against the real landed `custody_reference.py` before merge. This file deliberately does not pre-claim hosted green.

The carrier continues to reuse the landed Commons `tools/proposal_gate/proposal_gate.py` for response readiness. `gate_requirements.json` + `gate_evidence.json` intentionally remain blocked until controlling packet/addenda/hash, OpenGov route, legal entity/signer, attestations and owner external-response approval are evidenced. Hosted CI pins those blocked IDs and cannot turn this package into external submission authority.
