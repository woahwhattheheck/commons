# AIR 2026 Workforce-AI Evidence Network RFI — qualification packet

This package converts AIR's live **Building an Evidence Network for Artificial Intelligence (AI) in Workforce Systems** RFI into a fail-closed owner-review lane. It does not submit the RFI, contact AIR or a partner, invent workforce history, or claim funding.

## Commercial posture

AIR says the current RFI has **no award**. A strong response can, however, be selected for a later invitation-only RFP, research partnership, or other future-work discussion. The value of this lane is therefore access to a later funded/partnership funnel, not current booked revenue.

The controlling PDF also makes direct qualification materially stricter than the public blog summary: AIR asks respondents to have an established track record supporting career readiness/job entry/upskilling/reskilling/lifelong learning, name a specific population and 2027–2028 scale, pose useful learning questions, explain technical methods/data, address responsible AI, and offer a feasible AIR research/evaluation partnership.

## Current disposition

**HOLD / likely PARTNER_REQUIRED until evidence is supplied.** This carrier does not assert that the repository owner has the workforce-delivery track record AIR asks for. The credible route, if direct evidence is absent, is a workforce board/training provider/employer/intermediary that owns participant/service-delivery evidence, with the technical team contributing bounded AI workflow, evaluation, logging, governance, and reliability infrastructure.

There is an additional source-custody blocker: the official 10-page AIR PDF was read through the web retrieval surface, but raw binary bytes could not be acquired in this runtime, so `source_snapshot.json` intentionally leaves `rfi_pdf_sha256` null. `preflight.py` refuses `READY_FOR_OWNER_SUBMISSION_REVIEW` until exact official PDF bytes are independently captured and hashed.

## Files

- `source_snapshot.json` — official AIR URLs, dates, focus areas, review criteria, prompts/word limits, and explicit raw-byte custody gap.
- `requirements.json` — evidence/gate matrix with current proof status.
- `owner_inputs.template.json` — private owner/partner facts required to qualify; copy outside Git before filling.
- `response_draft.md` — bounded PARTNER_RFI-oriented response scaffold with unsupported claims marked.
- `evidence_design.md` — evaluation design, instrumentation, safeguards, worker voice, and failure-mode appendix.
- `preflight.py` — deterministic qualification/word-limit/source-custody gate and receipt verifier.
- `test_preflight.py` — hostile coverage for source, track-record, population, word limits, scalar traps, evidence claims, deadline/freshness, tamper, and authority.

## Safe workflow

1. Independently capture the exact official AIR PDF and record its SHA-256 in `source_snapshot.json` with `rfi_pdf_bytes_acquired=true`.
2. Refresh AIR's official page/PDF for updates; keep `checked_at` current.
3. Copy `owner_inputs.template.json` to an owner-controlled location. Do not commit private phone numbers, partner contacts, participant data, or unsupported outcome claims.
4. Choose `DIRECT_RFI` only with evidence of an established direct workforce track record. Otherwise use `PARTNER_RFI` only after a real partner role/commitment and partner track record are evidenced.
5. Replace every placeholder in the response scaffold with supportable facts and keep each answer within the exact AIR word limit.
6. Run the preflight against a trusted UTC time. `READY_FOR_OWNER_SUBMISSION_REVIEW` is only a completeness/evidence state; it is never submission authority.

```bash
python3 opportunities/air_workforce_evidence_rfi_2026/preflight.py \
  --source opportunities/air_workforce_evidence_rfi_2026/source_snapshot.json \
  --owner /path/to/private-owner-inputs.json \
  --trusted-now 2026-09-13T11:00:00Z
```

## Authority ceiling

All receipt authority flags remain false. No AIR/partner contact, Submittable action, account creation, participant-data access, outcome invention, pricing/contract commitment, signature, spend, award assertion, or revenue recognition is performed or authorized here.
