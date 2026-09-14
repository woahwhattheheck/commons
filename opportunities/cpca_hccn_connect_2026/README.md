# CPCA HCCN Connect 2026 - qualification and revenue carrier

This package turns the buyer-delivered **CPCA HCCN Connect** RFP into a deterministic, fail-closed owner-review gate. It does not fabricate healthcare qualifications and it cannot submit an application.

## Why this opportunity matters

CPCA is building a multi-vendor Technical Assistance / Group Training marketplace for participating health centers, with qualification potentially running through **2028-07-31**. Engagements are project-specific SOWs, time-and-materials, and approved hours are paid monthly. Marketplace approval does **not** guarantee referrals or volume.

The deadline in the controlling 16-page RFP is **2026-09-18 at 5:00 PM Pacific**.

## Controlling packet

- Buyer-delivered filename: `2026.09.03_CPCA HCCN Connect Marketplace RFP.pdf`
- Pages: 16
- SHA-256: `37c61b76500fee4639e1499d7683d4882da294f65d77e5e59c224ada3fc52529`
- The public repository stores the digest and extracted requirements, not the buyer PDF bytes.

## Current truth state

**HOLD for direct prime submission.** The packet requires prior FQHC/look-alike/safety-net primary-care experience and, for every selected domain, at least one qualifying safety-net engagement. Default-branch Commons searches on 2026-09-14 returned no code hits for `FQHC`, `health center`, or `safety-net`. That is a repository evidence gap, not proof that no qualifying experience exists.

The strongest technical adjacency is Objective 5 Artificial Intelligence, especially AI Governance, AI Vendor Evaluation and AI Use Case Education, but those routes remain HOLD until the healthcare/safety-net and comparable-engagement requirements are proven.

## Files

- `source_snapshot.json` - source-bound buyer facts, packet digest, domains, experience rules, evaluation and submission mechanics.
- `requirements.json` - hard gates and recommended initial technical route.
- `owner_inputs.template.json` - owner/private facts required to evaluate readiness.
- `evidence_inventory.md` - current proof gaps and exact next evidence.
- `response_outline.md` - buyer-aligned internal response skeleton with unsupported-claim guards.
- `revenue_model.md` - post-qualification packaging and cash-state model.
- `preflight.py` - deterministic `HOLD` / `READY_FOR_OWNER_SUBMISSION_REVIEW` compiler.
- `test_preflight.py` - hostile, eligibility, time and authority tests.

## Safe workflow

1. Copy `owner_inputs.template.json` outside public source control.
2. Fill only with current, supportable facts and evidence references.
3. Refresh the buyer packet if CPCA issues an addendum or replacement.
4. Run:

```bash
python3 opportunities/cpca_hccn_connect_2026/preflight.py \
  --source opportunities/cpca_hccn_connect_2026/source_snapshot.json \
  --owner /path/to/private-owner-inputs.json \
  --trusted-now 2026-09-14T21:46:27Z
```

5. `READY_FOR_OWNER_SUBMISSION_REVIEW` means deterministic completeness gates passed. It is not a qualification decision, legal/compliance certification, buyer submission, award or revenue claim.

## Authority ceiling

The carrier never sends email, submits the Smartsheet, signs Appendix C, contacts references, certifies licensing/insurance/privacy/HIPAA/BAA status, commits pricing, accepts an Engagement Agreement/SOW, or claims approval, work volume, invoice, payment or cash.
