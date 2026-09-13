# AIR AI Workforce Evidence Network RFI — partner-first qualification package

This package converts AIR's September 2026 RFI into an evidence-bound commercial decision, prompt-aligned response draft, and evaluation plan. It deliberately does **not** turn a technology capability into a fictional workforce-delivery track record.

## Current decision

**`PARTNER_REQUIRED` on repository-visible evidence.**

AIR welcomes technology providers and ideas from concept through deployed maturity, but the RFI also asks for respondents with an established track record supporting career readiness/job entry and/or adult upskilling, reskilling, and lifelong learning. The current Commons opportunity record for the Kentucky AI Workforce Readiness procurement already documents the same owner-side gap: the available artifacts did not independently prove an experienced workforce-training prime with the required delivery history/references. The Lawrence Youth AI Workforce Training qualification likewise keeps prime readiness on HOLD pending real workforce-delivery evidence.

That is not a no-bid. It points to a stronger route: pair the auditable AI/evaluation layer with a workforce board, training provider, education organization, employer network, or other delivery organization that truthfully owns the population relationship and track record.

## AIR source truth

The official AIR RFI was released **September 4, 2026** and responses are due **October 2, 2026 at 12:00 PM ET**. The current RFI is information gathering and makes **no award**. AIR may invite a subset of respondents to a later invitation-only RFP and may explore other partnership/future-work opportunities, but neither is guaranteed.

The source contains 12 response prompts. Word-limited prompts are bound in `source_snapshot.json`:

- Organizational Background — 200 words
- AI-Enabled Workforce Innovation — 300
- Workforce Challenge — 200
- Key Learning Questions — 200
- Population(s) of Focus — 100
- Technical Approach, Models, and Data — 300
- Early Results or Evidence — 200
- Responsible AI and Safeguards — 200
- Opportunities for Partnership with AIR — 150

The raw PDF bytes were not acquired by this carrier, so `rfp_pdf_sha256` is intentionally `null`; the package binds the official URL and a canonical extracted-fact snapshot instead of fabricating a digest.

## Product files

- `source_snapshot.json` — official AIR URLs, dates, prompt limits, review criteria, and authority ceiling.
- `requirements.json` — direct/partner/HOLD route contract.
- `owner_inputs.template.json` — private owner facts that must never be inferred from repository prose.
- `preflight.py` — strict compiler/verifier producing `DIRECT_RFI_READY_FOR_OWNER_REVIEW`, `PARTNER_RFI_READY_FOR_OWNER_REVIEW`, `PARTNER_REQUIRED`, or `HOLD`.
- `test_preflight.py` — hostile, route, time, type, replay, and publication tests.
- `evidence_inventory.md` — what Commons supports and what is still missing.
- `response_draft.md` — response-ready structure against AIR's exact prompts, with unsupported claims left explicitly gated.
- `evidence_design.md` — outcomes, comparison designs, instrumentation, privacy/fairness, worker voice, and AIR evaluation role.
- `red_team.md` — claim/maturity/data/evaluator-risk attack pass.

## Recommended concept

**Evidence-Bound AI Career Navigation & Readiness Lab** — a partner-delivered, human-in-the-loop evaluation of AI-assisted career-navigation and readiness support. A workforce partner owns recruitment/service delivery and any participant relationship; the technology layer contributes bounded decision support, provenance, reproducible model/version receipts, contradiction/replay checks, and evaluator-facing telemetry.

The concept intentionally avoids autonomous job applications, applicant ranking, eligibility determination, benefit decisions, or unsupported claims of employment impact.

## Running the gate

Copy the owner template outside the repo, fill it only with supportable facts, and run:

```bash
python3 opportunities/air_ai_workforce_rfi_2026/preflight.py compile \
  --source opportunities/air_ai_workforce_rfi_2026/source_snapshot.json \
  --owner /private/air-owner-inputs.json \
  --trusted-now 2026-09-13T11:00:00Z
```

`PARTNER_REQUIRED` means the concept can keep moving but a track-record-bearing workforce partner is still an explicit commercial prerequisite. A readiness state is **owner review only**; it is never submission authority.

## Authority ceiling

No AIR/partner contact, Submittable submission, representation of prior workforce outcomes, participant-data access, data-sharing commitment, pricing, signature, contract, spend, award, cash, or recognized-revenue action is performed or authorized by this package.
