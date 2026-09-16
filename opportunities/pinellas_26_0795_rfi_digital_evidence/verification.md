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

`custody_reference.py` retains the deterministic replay/integrity machinery. Its explicit root/witness parameters do not self-authenticate and are not the current-positive boundary.

`current_custody_service.py` owns the current-positive composition contract:

1. one host provider is captured when `CurrentCustodyService` is constructed;
2. individual operations cannot pass an expected witness, snapshot, trusted root, or trusted-root set;
3. an existing `Evidence` generation must match the witness already retained by the host before a current mutation can proceed;
4. mutation occurs on a candidate copy; the successor witness must be retained by the host before local state is exposed;
5. hold/destruction snapshots are obtained through the captured provider; and
6. current verification reacquires exact archived authority snapshots referenced by the retained events and rejects missing/root-mismatched provider results.

The hostile suite includes the predecessor killers missing from the old head: a caller can still manufacture a fully self-consistent low-level snapshot + its own root, or a freshly resealed local witness, but neither can become **current** because `CurrentCustodyService` accepts neither as request input. It also covers host-witness write failure atomicity, archived-snapshot mismatch, and provider-method rebinding after service construction, in addition to the existing coherent rehash, stale/revoked generation, missing schedule/notice, approval-separation, future-evidence and strict SHA-256 hostiles.

Exact-head hosted results must be read from GitHub Actions for the exact commit being evaluated; this file deliberately does not pre-claim a new PASS count before that provider receipt exists.

The carrier continues to reuse the **landed** Commons `tools/proposal_gate/proposal_gate.py` for response readiness instead of introducing another policy engine. `gate_requirements.json` + `gate_evidence.json` intentionally evaluate blocked until controlling packet/addenda/hash, OpenGov route, legal entity/signer, attestations and owner external-response approval are evidenced. Hosted CI pins the exact blocked IDs and cannot turn this package into external submission authority.
