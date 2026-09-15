# TTUHSC 739-SL3821039 — Enterprise AI Adoption & Enablement

Original pursuit/source owner: **Zeta / GPT-5.6 Sol**  
Original operation: `TTUHSC-739-SL3821039-ENTERPRISE-AI-ZETA-20260913` / issue #14290 / PR #14310  
RED-recovery finalizer: **Z-Sol-61 (`ZS61`) / GPT-5.6 Sol**  
Recovery operation: `TTUHSC-739-SL3821039-PURSUIT-BRIDGE-RECOVERY-ZS61-20260914`

This package preserves Zeta's substantive buyer analysis, requirements, technical response and workflow portfolio while replacing the old caller-authored readiness compiler. Current readiness now flows through the shared `revenue.pursuit_evidence_bridge`, whose trust-bearing source roots, deadline and bidder-evidence roots live outside the runtime envelope.

## Current posture

**HOLD. No external action is authorized.**

The checked-in binding `ttuhsc-739-sl3821039-main-v1` pins:

- the exact canonical JSON root of `source_ledger.json`;
- the exact canonical JSON root of `submission_manifest.json`;
- the proposal deadline `2026-09-21T21:30:00Z`;
- static source holds for missing first-party packet bytes and the unreconciled buyer addenda generation; and
- no bidder-vault roots yet.

Because the bidder-vault roots are null, runtime evidence cannot upgrade this carrier. Because the two source holds are checked into the binding registry, neither source status can be asserted away by input JSON. The shared bridge owns current UTC; there is no caller `as_of`, deadline, expected-root, or alternate-binding parameter.

## Buyer/source state retained from the original carrier

The first-party Texas Tech TechBid public event identifies **RFP 739-SL3821039 — Consulting Services - Enterprise AI Adoption and Enablement**, closing **2026-09-21 4:30 PM Central Time**. The original carrier did not retain the current first-party packet bytes or a complete buyer addenda generation, so detailed requirement extraction remains secondary evidence and cannot authorize submission.

The written-question deadline in the extracted packet was 2026-08-21. **Do not send procurement questions from this lane.**

The buyer-shaped response remains materially useful: it covers strategy/governance, leadership/change, role-based training, workflow engineering and prototypes, agentic controls, adoption/proficiency/ROI analytics, regulated-data boundaries and knowledge transfer. These artifacts are drafting evidence, not entity/compliance/staffing/reference/pricing proof.

## Current gate

Run the process-owned current gate from repository root:

```bash
python -m opportunities.ttuhsc_739_sl3821039_enterprise_ai.qualify
```

Exit status is `0` only for `OPPORTUNITY_EVIDENCE_READY`, `2` for a valid current `HOLD`, and `3` for malformed/tampered input or I/O failure. An optional `--vault PATH` may supply the already-defined bidder-vault envelope only after exact vault roots have been independently retained in the checked-in binding. With the current null roots, supplying runtime vault bytes is rejected rather than self-authorized.

## What must happen before any readiness upgrade

A later reviewed source generation must retain and bind the current first-party RFP packet and every buyer-issued addendum/answer generation. Separately, the existing bidder qualification vault must contain independently retained authority/registry/query roots covering the real entity, authorized signer, tax/VetHUB/insurance, references/partner authority, staffing, security/compliance and owner commercial evidence required for this pursuit. Only then may a reviewed binding change pin those exact roots.

The runtime caller never supplies the trust roots, deadline, or current time.

## Package

- `source_ledger.json` — source authority and unresolved first-party-byte/addenda gaps.
- `requirements.json` — 32 buyer requirements and evaluation weighting.
- `technical_response.md` — substantive buyer-shaped delivery response.
- `workflow_portfolio_template.json` — non-invented workflow/prototype evidence structure.
- `submission_manifest.json` — proposal components and literal owner/source/commercial blockers.
- `qualify.py` — narrow current wrapper over the shared pursuit evidence bridge.
- `test_qualify.py` — hostile regressions for root drift, runtime vault self-authorization and current HOLD semantics.

## Authority ceiling

Authorized here: public-source recovery, internal drafting, qualification code/tests/docs/CI, GitHub/Slack coordination and guarded merge of internal artifacts.

Not authorized here: buyer/reference contact; TechBid mutation/upload/submission; signatures or certifications; entity/tax/registration acts; invented references/compliance; staffing/subconsultant commitments; final customer price; contract acceptance; spend; award/payment/revenue claims; or use of TTUHSC institutional data.

`external_submission_authorized` remains `false`, and every action-authority bit emitted by the bridge remains `false`.
