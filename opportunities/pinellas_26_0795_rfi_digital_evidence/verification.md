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

The custody reference now has two external trust inputs that are intentionally absent from the mutable `Evidence` object:

1. an independently retained custody witness binding event count, chain head and current state; and
2. independently retained trusted roots for every archived `AuthoritySnapshot` consumed by hold/release/destruction events.

The hostile suite covers coherent fully rehashed alternate history, authority-root transplant, stale/revoked authority generations, caller-minted release/destruction attempts, missing schedule/notice evidence, approval separation of duty, future authority evidence and strict lowercase SHA-256 grammar. Exact-head hosted results must be read from GitHub Actions for the exact commit being evaluated; this file deliberately does not pre-claim a new PASS count before that provider receipt exists.

The carrier continues to reuse the **landed** Commons `tools/proposal_gate/proposal_gate.py` for response readiness instead of introducing another policy engine. `gate_requirements.json` + `gate_evidence.json` intentionally evaluate blocked until controlling packet/addenda/hash, OpenGov route, legal entity/signer, attestations and owner external-response approval are evidenced. Hosted CI pins the exact blocked IDs and cannot turn this package into external submission authority.
