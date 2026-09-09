# TRACE-POLAR-AS9100 named-human gate repair

Operation: `trace-polar-as9100-human-gate-repair-20260909-01`
Date: 2026-09-09
Source review blocker: PR #11191 review `5157640009`

## Problem

The original free-text reviewer validator rejected reserved identities only when the entire string matched or a hyphen-delimited piece matched. Multi-token values such as `System Reviewer`, `AI Reviewer`, and `Bot Reviewer` therefore satisfied the two-token check and could be labeled as a named-human disposition.

## Repair

- Normalize the supplied reviewer string as before.
- Tokenize the case-folded identity across whitespace and punctuation.
- Reject the identity if any resulting token is a reserved automation/service token.
- Preserve the existing requirement for at least two alphabetic identity tokens.
- Preserve copy-only/unsent disposition behavior, held-pack denial, and automatic-disposition denial.
- Add adversarial coverage for multi-token, slash, underscore, hyphen, and dotted automation identities while retaining `Jordan Reviewer` as the positive control.

## Validation

Fresh preimage at test time:
- source blob `028b4fc1df1c0078623f03be65a87ae85631bf9d`
- test blob `edc52fcc716c7657055b6dac12edd201651bb83b`

Repaired blobs:
- source blob `ebc1e23f0b74886861ad427cb09652e9884abcff`
- test blob `512757f764dd05e0a4df268f66a7d781d7b4d1de`

Commands/results:
- `python -m unittest -v test_trace_polar_as9100.py` — **10/10 PASS**
- `python -m py_compile trace_polar_as9100.py test_trace_polar_as9100.py` — **PASS**
- `python trace_polar_as9100.py` — **PASS**

Frozen acceptance remains unchanged: 3 synthetic wafers / 36 steps; W1 `REVIEW_READY`; W2 `HOLD_REVISION`; W3 `HOLD_CAL_AND_SIGNATURE`; exactly 3 exceptions and 3 evidence packs; replay zero-add; state SHA-256 `e6dbbea685fa7846004f27a6f1acae0c06baa4a62bf935352edf5f8defb18741`; evidence-manifest SHA-256 `2d12420515c0d0146accd9adc70de2c9c79042b879167e8a4a16072ab0c761aa`; authoritative fingerprint `77b0f85f640d3b22f6bb1e7bc2cb0fa4733669be9a757a7ede0a57390cf59a77`.

## Boundary

Synthetic/mock read-only evidence only. No live QMS/NCR/traveler/recipe/instrument/material/customer/production/disposition/certification/reporting write, no external send, no compliance/accreditation determination, and no autonomous disposition. This repair changes only free-text reviewer gating plus regression coverage; it does not authenticate a real human identity or replace a future buyer-owned authorization system.
