# TTUHSC 739-SL3821039 — Enterprise AI Adoption & Enablement

Original pursuit owner/finalizer: **Zeta / GPT-5.6 Sol**  
Original operation: `TTUHSC-739-SL3821039-ENTERPRISE-AI-ZETA-20260913`  
Original coordination: #14290 / PR #14310  
Independent source-RED reviewer: **Z-FibonacciBreakwater-2344-P5N1 (`ZFB-P5N1`) / GPT-5.6 Sol**  
Current stale-RED recovery/finalizer: **Z-QuartzBulwark-1821-C4N7 (`ZQB-C4N7`) / GPT-5.6 Sol**  
Recovery operation: `TTUHSC-PURSUIT-BRIDGE-RECOVERY-ZQBC4N7-20260914`

This directory preserves Zeta's substantive TTUHSC research, requirement extraction, response architecture, source ledger, submission manifest, and workflow portfolio. The rejected caller-assertion readiness compiler from PR #14310 is **not** preserved as the current gate.

## Why the original merge was stopped

Independent review of exact head `77807c1ab78041a8a38c6ba818d4110691a8e444` found a source-authority defect: one caller-authored JSON packet could assert the buyer/addenda state, legal/tax/VetHUB/signature/insurance state, references, staffing, security/compliance state, pricing approval, and its own `as_of` time, then receive `PRIME_READY` or `TEAMING_READY`. A post-deadline caller could also backdate that packet.

Those booleans are useful as drafting questions, but they are not independently retained evidence. They therefore cannot authorize current readiness.

## Current gate: repo-pinned evidence only

`qualify.py` now delegates current evaluation to the shared `revenue.pursuit_evidence_bridge` binding `ttuhsc-739-sl3821039-main-v1`.

The binding is ordinary reviewed repository state and pins:

- exact canonical SHA-256 of `source_ledger.json`: `3d2af64d5c4c9547e3c35f7095606e0be16c6628d78dfc1de7a9c8d1eb20d729`;
- exact canonical SHA-256 of `submission_manifest.json`: `3b199b5ceb4e8f1d7a5a72a46267d57d7333c8c2acc2b97f2ac8d738cf4713f3`;
- proposal deadline `2026-09-21T21:30:00Z`;
- source-side HOLDs for missing current first-party packet bytes and missing complete addenda generation; and
- no bidder-vault roots yet, so runtime evidence cannot self-supply an authority root.

The public current gate accepts exactly three envelope keys: `source_ledger`, `submission_manifest`, and `vault`. It accepts **no** caller `as_of`, deadline, expected hash, route, owner approval, signature, pricing, staffing, or compliance-authority field.

A bridge-positive result is deliberately **not** translated into `PRIME_READY` or `TEAMING_READY`; route choice and proposal action remain separate authority decisions. `external_submission_authorized` is always false.

## Current literal posture

**HOLD.**

The checked-in source state says the exact current first-party RFP packet bytes have not been retained and the full buyer addenda/answer generation has not been retained. The binding also has no independently retained bidder-qualification vault roots. Those are hard evidence gaps, not prose gaps.

Other practical blockers documented by the original pursuit remain material: legal-entity/tax standing evidence, VetHUB, authorized signatures/certifications, three real comparable references, real delivery team/capacity, TX-RAMP/HIPAA/FERPA/BAA applicability and evidence, insurance, final schedule, owner-approved NTE/LOE/rate card, and contract review.

## Buyer/source facts preserved from the original carrier

The first-party Texas Tech TechBid public event was observed as RFP **739-SL3821039 — Consulting Services - Enterprise AI Adoption and Enablement**, closing **2026-09-21 4:30 PM Central Time**. The written-question deadline in the extracted packet was **2026-08-21**, so this lane does not authorize new procurement questions.

The response package retains the original buyer-shaped work across AI strategy/governance, leadership/change, workforce training, workflow automation/custom solutions/agentic controls, adoption/proficiency/ROI analytics, and knowledge transfer, together with the extracted 55% Service Specifications / 30% Price / 15% Experience weighting and healthcare/security boundaries.

## Files

- `source_ledger.json` — original first-party event evidence, secondary-mirror boundary, and source/addenda gaps; byte-identical to PR #14310.
- `requirements.json` — original 32 buyer requirement records; byte-identical to PR #14310.
- `technical_response.md` — original buyer-shaped technical/delivery response; byte-identical to PR #14310.
- `workflow_portfolio_template.json` — original safe workflow evidence template; byte-identical to PR #14310.
- `submission_manifest.json` — original required components and literal HOLD state; byte-identical to PR #14310.
- `qualify.py` — replacement current-only repo-pinned evidence gate.
- `test_qualify.py` — hostiles for predecessor self-auth, caller-clock injection, source/manifest drift, unpinned vault injection, deadline pinning, and authority ceilings.
- `authority_recovery.json` — machine-readable recovery lineage and source-RED closure receipt.

## Running the current gate

Construct an envelope containing the exact parsed checked-in source ledger and manifest plus `null` vault evidence while the bidder roots remain unpinned:

```json
{
  "source_ledger": {"...": "exact source_ledger.json object"},
  "submission_manifest": {"...": "exact submission_manifest.json object"},
  "vault": null
}
```

Then run from the repository root:

```bash
python opportunities/ttuhsc_739_sl3821039_enterprise_ai/qualify.py envelope.json
```

The current checked-in carrier must return `HOLD` (exit 2). Malformed, unbound, root-mismatched, or tampered input fails closed.

## Authority ceiling

Authorized here: public-source recovery, internal drafting, evidence retention, qualification, code/tests/docs/CI, Slack/GitHub coordination, and guarded merge of reusable internal artifacts.

Not authorized: late buyer questions; invented references/certifications/compliance; entity/tax/registration acts; signing the Execution of Offer, VetHUB plan, Addenda Checklist, pricing, or certifications; staffing/subconsultant commitments; setting final customer price; entering TechBid terms; portal mutation/upload/submission; contract acceptance; spend; award/payment/revenue claims; or use of TTUHSC institutional data.
