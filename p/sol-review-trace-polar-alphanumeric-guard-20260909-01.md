# SOL-REVIEW-TPOLAR — alphanumeric reviewer-token follow-through

Demand: `trace-polar-as9100-lims-01`
Reviewed repair: PR #11205, merge `f1301233e293cc6498305f3c4915db4739bfa868`
Date: 2026-09-09

## Reproduced follow-through defect

PR #11205 correctly rejected reserved automation/service labels separated by whitespace and punctuation, but its reviewer tokenizer used `re.findall(r"[^\\W_]+", ...)`, which retains letters and digits in the same token. Exact current logic therefore accepted obvious automation labels with numeric suffixes, including `System2 Operator`, `AI2 Reviewer`, `bot123 user`, `agent007 reviewer`, and `service2 account` for the REVIEW_READY W1 disposition-copy path.

Held W2/W3 packs remained denied, automatic disposition remained disabled, and the returned disposition remained copy-only with `sent=false`.

## Minimal repair

Change only the tokenization character class to `r"[^\\W\\d_]+"`, so digits are separators and the reserved alphabetic automation token is still visible to the existing reserved-token check. Add the five exact alphanumeric bypasses to the existing disposition regression list. No fixture, manifest, replay, evidence-pack, status, or send behavior changes.

Reviewed current preimages before publication:
- `trace_polar_as9100.py`: `ebc1e23f0b74886861ad427cb09652e9884abcff`
- `test_trace_polar_as9100.py`: `512757f764dd05e0a4df268f66a7d781d7b4d1de`

Candidate blobs:
- source: `562bc76d68f025a794062f42968b164832b63afd`
- test: `c1fe4b190899bd8724b27dc725b12ef259a8fe62`

## Executed acceptance

Using connector-read current source/test/fixture/manifest bytes with only this candidate patch applied in the cloud runtime:
- existing unittest module: 10/10 PASS
- `py_compile` for source + tests: PASS
- CLI acceptance: PASS
- statuses unchanged: W1 `REVIEW_READY`, W2 `HOLD_REVISION`, W3 `HOLD_CAL_AND_SIGNATURE`
- exception count 3, evidence-pack count 3, replay-zero-add true, `sent=false`
- state digest `e6dbbea685fa7846004f27a6f1acae0c06baa4a62bf935352edf5f8defb18741`
- evidence-manifest SHA256 `2d12420515c0d0146accd9adc70de2c9c79042b879167e8a4a16072ab0c761aa`
- authoritative fingerprint `77b0f85f640d3b22f6bb1e7bc2cb0fa4733669be9a757a7ede0a57390cf59a77`

An unrelated spreadsheet-runtime warmup emitted a timeout warning during Python startup, but the unittest process returned 0 and all 10 named tests passed; py_compile and CLI also returned 0.

Publication boundary: exactly current source + current test + this additive receipt. My earlier PR #11201 was closed unmerged after exact diff inspection showed unrelated carrier ancestry; no force update or merge occurred. No live QMS, traveler, recipe, NCR, instrument, material, production, disposition, certification, compliance, provider/customer, external-send, spend, or owner-PC action.
