# Alcorn State RFP #5588 response-pack carrier

This directory is the **owner-internal deadline-completion layer** for the already source-bound Alcorn State University RFP #5588 qualification carrier in the parent directory.

It is deliberately downstream of `../qualification_spec.json`, `../current_evidence.json`, `../qualification.py`, `../qualification_guarded.py`, and `../current_result.json`. It can prepare a complete internal response package, but it cannot make an unqualified pursuit qualified and cannot create external authority.

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
- `pricing_basis.json` — public-safe cost-basis ledger; no customer amount or price release. A future private approval may be referenced only by source-bound evidence ID after the controlling buyer cost form is present.
- `risk_redline_questions.md` — source, qualification, commercial, legal, logistics, and schedule risks.
- `sealed_package_checklist.md` — final physical package checklist with explicit last-inch authority fence.
- `response_pack.py` — deterministic compiler/verifier with authenticated upstream replay.
- `test_response_pack.py` — hostile tests, including optimized-mode runs.

The receipt is an output, not a manually maintained source file. Generate it from exact current inputs with `compile --write`; `verify` then exact-recompiles and compares it.

## Authenticated upstream replay

The response compiler does **not** trust `current_result.json` merely because it contains a plausible state, blocker list, or `receipt_sha256`. On every compile it loads the exact sibling `qualification.py` and `qualification_guarded.py`, evaluates canonical `qualification_spec.json` + `current_evidence.json`, recomputes the upstream receipt exactly, and requires the resulting object to equal `current_result.json`.

That makes caller edits such as `state=TEAMING_READY` plus `blockers=[]` insufficient even if the caller also locally reseals a replacement receipt. The result must be reproducible by the retained source-bound evaluator. The response receipt additionally records SHA-256 identities for both upstream implementations and every canonical input.

The compiler also fails closed on the controlling source model: this version source-binds the three buyer-controlled artifacts still recorded absent — Section VIII Cost Information, Section IX References, and Section VII Item 12 Requirements Matrix. A future ready state therefore requires a deliberate source-model/code update plus authenticated upstream evidence; an internal narrative cannot erase those gaps.

## Owner-gate enforcement

`response_plan.json` declares last-inch owner gates as mandatory, and the compiler now enforces the declaration as an exact contract rather than treating it as prose. The source-backed owner-gate map covers:

- private owner pricing approval whose evidence ID matches the upstream qualified entity and whose buyer cost form is present;
- authorized signature-officer readiness plus evidence ID;
- legal-entity evidence;
- current liability-insurance evidence through the proposal due date;
- E-Verify evidence;
- taxpayer-ID confirmation evidence;
- order/remit-address evidence;
- sealed-delivery-plan readiness plus evidence ID.

The public pricing basis never stores or releases the customer amount. `pricing_approved=false` with no approval evidence is valid as a draft, but cannot satisfy owner readiness.

## State machine

The compiler has five internal states:

- `HOLD_QUALIFICATION`: the authenticated canonical replay is not `PRIME_READY` or `TEAMING_READY`, has blockers, or still reports missing buyer artifacts.
- `HOLD_BUYER_ARTIFACTS`: a hypothetical authenticated qualification is ready but this compiler's controlling source model still records buyer-controlled artifacts absent.
- `HOLD_RESPONSE_ARTIFACTS`: upstream/source gates are ready but a required internal response artifact or invariant is missing/invalid.
- `HOLD_OWNER_GATES`: qualification/source/artifact gates are ready but one or more source-backed owner gates are unproven.
- `OWNER_READY_FOR_SUBMIT`: authenticated qualification, controlling buyer artifacts, internal response artifacts, and all declared source-backed owner gates are ready.

`OWNER_READY_FOR_SUBMIT` still means **internal owner review readiness only**. It does not set `proposal_submission_authorized`; the compiler's entire external-authority map remains false by design.

Current canonical qualification is `HOLD`, so compiling the current response layer must produce `HOLD_QUALIFICATION` regardless of how complete the narrative artifacts become.

## Run

From repository root:

```bash
python commercial/alcorn-rfp-5588/response_pack/response_pack.py compile
python -O commercial/alcorn-rfp-5588/response_pack/response_pack.py compile
python -m unittest commercial/alcorn-rfp-5588/response_pack/test_response_pack.py -v
python -O -m unittest commercial/alcorn-rfp-5588/response_pack/test_response_pack.py -v
python commercial/alcorn-rfp-5588/response_pack/response_pack.py compile \
  --write /tmp/alcorn-5588-response-receipt.json
python commercial/alcorn-rfp-5588/response_pack/response_pack.py verify \
  /tmp/alcorn-5588-response-receipt.json
```

## Truth boundary

The compiler source-binds the buyer packet digest, Addendum 1 digest, buyer/RFP/deadline identity, scoring weights, missing buyer-controlled artifacts, normalized gate IDs, canonical evidence, authenticated canonical qualification result, exact upstream implementation identities, artifact inventory, public-safe pricing ledger, source-backed owner gates, and all-false external authority ceiling.

It rejects attempts to:

- substitute another buyer/RFP/deadline;
- rewrite Addendum 1 as NVIDIA/OEM authority;
- hide any of the three missing buyer artifacts;
- edit or reseal the canonical qualification result without the upstream evaluator reproducing it;
- disable any declared owner gate;
- omit required response artifacts;
- publish a customer price amount in the public ledger;
- mark pricing approved without a source-bound approval evidence ID and controlling buyer cost form;
- use local pricing approval that does not match upstream source evidence;
- set any external authority or award/payment/cash/revenue field true.

The strongest possible output is therefore a deterministic internal readiness receipt, never an externally authoritative action.
