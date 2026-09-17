# USAC IT-26-139 — Artificial Intelligence Consulting Services

Original pursuit/source/product/finalizer: **Zeta / GPT-5.6 Sol**  
Original operation: `USAC-IT-26-139-AI-CONSULTING-ZETA-20260913` / issue #14263 / PR #14281  
Bridge recovery: **Z-Sol-61 (`ZS61`) / GPT-5.6 Sol**  
Raw-byte helper/source recovery credit: **Z-CeriumSignal-0932-P5N7 (`ZCSG-P5N7`)**  
Current stale-recovery/source-generation finalizer: **Swarm Z / Sol-17 / GPT-5.6 Sol**

The pursuit remains behind the shared, repo-pinned `revenue.pursuit_evidence_bridge`. Runtime booleans, caller clocks, or caller-supplied trust roots cannot mint PRIME/TEAM readiness.

## Current posture

**HOLD. No external action is authorized.**

The checked-in binding `usac-it-26-139-main-v1` pins:

- canonical JSON root of `source_ledger.json`: `4f11bdd08f9244fce03546458f8bcb8f6aff456beb7fe43b8d0bc1596089f72c`;
- canonical JSON root of `submission_manifest.json`: `ce47b0d480532ef8b69274899b874a8dc32cabecca8b4e464d799f22325e15d0`;
- proposal deadline `2026-09-30T15:00:00Z`;
- exactly one static source hold: `CURRENT_BUYER_PAGE_GENERATION_NOT_RETAINED`; and
- no bidder-vault roots yet.

Four controlling buyer artifacts are now retained byte-for-byte from authenticated GitHub Actions artifact `10457019683` (archive SHA-256 `927631e36052b358cd168479172e0dcb4f2722d68c1f0b92a220fa2d940a0374`):

- RFP: `fc278ff4c8ab5fff06b38e4d463b2cc119a2a5c27b7a527ba89ccc40a40decbe`;
- Attachment 1 Bid Sheet: `836f443922a2ea41d6b3804dd3ec80d7854149368edf617a7eab7a31349ff479`;
- Attachment 2 Confidentiality Agreement: `c9471803056957b73d396f6379dcdaf4facd41a7bd90cb75ccc42e8f5a23370b`;
- Questions & Answers: `3682d0351e322ac1e9e2f277dfed4dfed75b01ffaf34e554b7d5c259a07852bb`.

The Bid Sheet was inspected inertly as OOXML: one sheet (`Tab 1 - Summary`), `A1:E26`, 20 non-empty cells, zero formulas. It records 120-day bid-sheet validity and a four-month firm-fixed-price structure. This is source evidence only; it does not establish an approved price or signature authority.

The first-party procurement page was rechecked on 2026-09-17 and still exposed the same four artifacts, with no additional notice link observed. Its **current HTML generation has not yet been retained byte-for-byte**, so that source hold remains deliberately open. A disposable evidence helper may close it only after a successful retained generation is harvested and reviewed.

## Current gate

From repository root:

```bash
python -m opportunities.usac_it_26_139_ai_consulting.qualify
```

Exit status is `0` only for `OPPORTUNITY_EVIDENCE_READY`, `2` for a valid current `HOLD`, and `3` for malformed/tampered input or I/O failure. An optional `--vault PATH` is accepted only after exact bidder-vault roots have been independently retained in the repo binding. While those roots are null, runtime vault bytes are rejected rather than self-authorized.

The wrapper exposes no caller `as_of`, deadline, expected source root, expected manifest root, binding registry, PRIME/TEAM switch, or self-asserted readiness booleans.

## Evidence still required

Before any readiness claim, retain and review the current first-party USAC procurement-page generation so later notices/addenda cannot be silently missed. Separately, independently retained bidder-vault evidence must establish the real organization/legal entity, UEI/SAM status, authorized signer, legal/NDA/insurance/conflict posture, named personnel, reference/engagement evidence, team commitments, proposal artifacts, and owner-approved prices required by the manifest.

Only a reviewed repository change may pin those exact roots. Runtime input cannot mint them.

## Substantive package retained from Zeta

The existing technical response remains a drafting asset covering the buyer-shaped AI consulting scope. `requirements.json`, `technical_response.md`, `source_ledger.json`, and `submission_manifest.json` are source/drafting evidence, not proof of legal entity, SAM status, signer authority, references, personnel commitments, NDA execution, final price, or submission authority.

## Authority ceiling

Authorized here: internal source/evidence recovery, drafting, qualification code/tests/docs/CI, GitHub/Slack coordination, review, and guarded merge.

Not authorized here: buyer email; Procurement@usac.org or Noor Jalal contact; USAC portal/account mutation; SAM/UEI/registration changes; NDA execution; signature/certification; reference outreach; staffing/team commitments; final price; proposal submission; contract acceptance; spend; payment mutation; award/payment/revenue claims.

Every action-authority bit emitted by the bridge and `external_submission_authorized` remain false.
