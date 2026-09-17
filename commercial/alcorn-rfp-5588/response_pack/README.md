# Alcorn State RFP #5588 response-pack carrier

This directory is the **owner-internal deadline-completion layer** for the already source-bound Alcorn State University RFP #5588 qualification carrier in the parent directory.

It is deliberately downstream of `../qualification_spec.json` and `../current_result.json`. It can prepare a complete internal response package, but it cannot make an unqualified pursuit qualified and cannot create external authority.

## Source lineage

- whole pursuit / buyer / submission custody: `ZLF-B8R3` / `ALCORN-AI-LABS-RFP5588-ZLFB8R3-20260913`
- source qualification carrier: `ZCV-L9Q4` / merged PR #14543
- Addendum 1 source + semantic finalization: `ZSF-N6Q8` + `ZTV-R7Q3` / merged PR #14758
- deadline-completion donor design: `ZMB-0308` / `ALCORN-5588-DEADLINE-CLOSURE-DONOR-ZMB0308-20260917`
- recovery implementation: `Z-Sol` / GPT-5.6 Sol

## What is here

- `response_plan.json` — source bindings, artifact manifest, readiness policy, and authority ceiling.
- `compliance_matrix.md` — normalized mandatory/material/submission/commercial/owner/logistics gate map plus scoring map.
- `technical_approach.md` — internal two-lab Spark-environment architecture and acceptance draft.
- `implementation_training_support.md` — phased delivery, training, warranty, and support workplan.
- `responsibility_matrix.md` — role/authority split that prevents credential inheritance.
- `pricing_basis.json` — unpriced cost-basis ledger; no quote/customer amount.
- `risk_redline_questions.md` — source, qualification, commercial, legal, logistics, and schedule risks.
- `sealed_package_checklist.md` — final physical package checklist with explicit last-inch authority fence.
- `response_pack.py` — deterministic compiler/verifier.
- `test_response_pack.py` — hostile tests, including optimized-mode runs.
- `current_response_result.json` — deterministic snapshot of the current carrier state.

## State machine

The compiler has three internal states:

- `HOLD_QUALIFICATION`: canonical `../current_result.json` is not `PRIME_READY` or `TEAMING_READY`, or still has blockers.
- `HOLD_RESPONSE_ARTIFACTS`: upstream qualification is ready but a required internal response artifact or invariant is missing/invalid.
- `OWNER_READY_FOR_SUBMIT`: upstream qualification is ready with no blockers and every required internal response artifact passes the compiler's invariants.

`OWNER_READY_FOR_SUBMIT` still means **internal owner review readiness only**. It does not set `proposal_submission_authorized`; the compiler's entire external-authority map remains false by design.

Current canonical qualification is `HOLD`, so the committed current response result must be `HOLD_QUALIFICATION` regardless of how complete the narrative artifacts become.

## Run

From repository root:

```bash
python commercial/alcorn-rfp-5588/response_pack/response_pack.py compile
python -O commercial/alcorn-rfp-5588/response_pack/response_pack.py compile
python -m unittest commercial/alcorn-rfp-5588/response_pack/test_response_pack.py -v
python -O -m unittest commercial/alcorn-rfp-5588/response_pack/test_response_pack.py -v
python commercial/alcorn-rfp-5588/response_pack/response_pack.py verify \
  commercial/alcorn-rfp-5588/response_pack/current_response_result.json
```

## Truth boundary

The compiler source-binds the buyer packet digest, Addendum 1 digest, buyer/RFP/deadline identity, scoring weights, missing buyer-controlled artifacts, normalized gate IDs, canonical qualification result, artifact inventory, unpriced pricing ledger, and all-false external authority ceiling.

It rejects attempts to:

- substitute another buyer/RFP/deadline;
- rewrite Addendum 1 as NVIDIA/OEM authority;
- hide any of the three missing buyer artifacts;
- treat a canonical qualification `HOLD` as ready;
- omit required response artifacts;
- publish a customer price in the internal basis ledger;
- mark pricing as approved/released in the internal ledger;
- set any external authority or award/payment/cash/revenue field true.

The strongest possible output is therefore a deterministic internal readiness receipt, never an externally authoritative action.
