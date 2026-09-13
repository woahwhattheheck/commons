# NASPO SW1045 — qualification + teaming production lane

This package turns the live **NASPO ValuePoint SW1045 Emerging Technologies Consulting and Services** solicitation into three independently auditable commercial routes:

- `PRIME_CATEGORY_1_CONSULTING`
- `PRIME_CATEGORY_2_SERVICES`
- `TEAMING_SUBCONTRACT`

It is intentionally source-authority-aware. NASPO's official public page confirms the solicitation identity, open status, release/close dates, cooperative purpose, and public-sector reach. The exact Oklahoma controlling RFP attachment bytes were **not acquired by this research seat**: NASPO's `View RFP` route redirected into Oklahoma PeopleSoft cookie/sign-in handling. Public mirrors expose useful discovery snapshots and document names, but those mirrors cannot green a mandatory requirement, evaluation score, price unit, certification, or prime qualification.

## Current truthful disposition

The committed `current_qualification_receipt.json` evaluates repository-visible evidence at a fixed trusted time:

| Route | Current state | Why |
| --- | --- | --- |
| Category 1 prime | `HOLD_OFFICIAL_PACKET_REQUIRED` | exact controlling packet/addenda/evaluation model not captured |
| Category 2 prime | `HOLD_OFFICIAL_PACKET_REQUIRED` | same; categories are deliberately kept independent |
| Teaming subcontract | `TEAMING_DRAFT_READY_FOR_OWNER_REVIEW` | bounded technical evidence and a concrete specialist scope exist, but no prime commitment or buyer compliance is asserted |

Recommended route today: **teaming/subcontract development while the official packet is recovered and bound**. That is materially different from calling a prospect a partner or calling generic AI engineering public-sector past performance.

## Official facts bound here

`source_snapshot.json` binds the official NASPO ValuePoint solicitation pages. As checked September 13, 2026:

- lead state: Oklahoma;
- solicitation: `SW1045` / public event mirror identifier `EV00000871`;
- title: Emerging Technologies Consulting and Services;
- release: August 14, 2026;
- close: October 15, 2026 at 3:00 PM Central Time (`2026-10-15T20:00:00Z`);
- phase/status: Public Posting Activities / Open;
- purpose: establish cooperative Master Agreements with qualified bidders;
- eligible public use includes states, higher education, political subdivisions, D.C., territories, and other eligible entities subject to local approval.

The RFP is open competition, **not an award**. Nothing in this package claims an award, booked revenue, acceptance, or buyer relationship.

## What public mirrors may tell us — and what they cannot

`requirements.json` records only noncontrolling discovery observations. Public mirrors currently describe two independently evaluated categories:

1. **Consulting** — readiness/assessment, roadmaps, governance/risk, change management and related advisory/implementation support.
2. **Services** — implementation/integration, custom development, testing/QA, managed services and related delivery.

Mirrors also surface apparent data-location/offshore language and several attachment names. Those observations guide diligence and drafting only. The compiler rejects mandatory buyer requirements unless `source_authority=CONTROLLING_PACKET` and the exact source document SHA-256 is bound.

## Existing technical evidence reused, not overstated

The already-landed `revenue/naspo_sw1045_agent_workflow_acceptance/` package is reusable specialist evidence. Its README and manifest explicitly prove a buyer-neutral offline reliability seam for deterministic approvals, idempotency, reconciliation, tamper-evident receipts and hostile testing. They equally explicitly **do not** assert prime qualification, procurement compliance, external action, payment or recognized revenue.

This qualification lane preserves that boundary. `technical_evidence.public_sector_past_performance=true` is itself a hard blocker.

## Files

- `source_snapshot.json` — exact official-summary facts, source classes, deadline and authority ceiling.
- `attachment_manifest.json` — discovery inventory with `MIRROR_NAME_ONLY` status; no fabricated hashes.
- `requirements.json` — independent category skeleton + mirror observations; no invented mandatory minima or scoring.
- `repo_evidence_candidate.json` — current repository-visible candidate package; legal-entity status explicitly unasserted.
- `current_qualification_receipt.json` — deterministic receipt for that candidate.
- `owner_inputs.template.json` — fail-closed input contract for real owner/partner/evidence facts.
- `qualification.py` — strict route compiler/verifier.
- `test_qualification.py` — hostile source/evidence/category/file-boundary tests.
- `capability_matrix.md` — proven vs partner-curable vs missing/unknown.
- `teaming_subcontract.md` — prime-insertable specialist scope and acceptance boundaries.
- `partner_profile.md` — concrete prime-partner profile and evidence required before “committed.”
- `evaluation_model.md` — what can/cannot be modeled until Attachment C / H and the RFP overview are official-byte-bound.
- `packet_recovery_runbook.md` — exact recovery/hash/addenda workflow without guessing.
- `red_team.md` — hostile commercial-claim review.

## Run

```bash
python -B -m unittest -v opportunities.naspo_sw1045_qualification_2026.test_qualification
python -O -B -m unittest -v opportunities.naspo_sw1045_qualification_2026.test_qualification

python opportunities/naspo_sw1045_qualification_2026/qualification.py verify \
  --source opportunities/naspo_sw1045_qualification_2026/source_snapshot.json \
  --attachments opportunities/naspo_sw1045_qualification_2026/attachment_manifest.json \
  --requirements opportunities/naspo_sw1045_qualification_2026/requirements.json \
  --owner opportunities/naspo_sw1045_qualification_2026/repo_evidence_candidate.json \
  --receipt opportunities/naspo_sw1045_qualification_2026/current_qualification_receipt.json \
  --trusted-now 2026-09-13T11:15:00Z
```

A green compiler state is **owner review only**. Every authority bit remains false.

## Authority ceiling

No agency/NASPO/prime contact, supplier registration, portal login, representation of past performance, named-person commitment, pricing commitment, certification/signature, proposal submission, spend, contract acceptance, award, cash, or recognized-revenue action is performed or authorized here.
