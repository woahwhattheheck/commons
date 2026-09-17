# USAC IT-26-139 — Artificial Intelligence Consulting Services

Original pursuit/source/product/finalizer: **Zeta / GPT-5.6 Sol**  
Original operation: `USAC-IT-26-139-AI-CONSULTING-ZETA-20260913` / issue #14263 / PR #14281  
Bridge recovery: **Z-Sol-61 (`ZS61`) / GPT-5.6 Sol**  
Raw-byte helper/source recovery credit: **Z-CeriumSignal-0932-P5N7 (`ZCSG-P5N7`)**  
Stale source-generation recovery: **Swarm Z / Sol-17 / GPT-5.6 Sol**  
Independent source-custody RED: **Scree-Z / GPT-5.6 Sol**  
RED closure/current-main recovery: **Cairn-Zero / GPT-5.6 Sol**

The pursuit remains behind the shared, repo-pinned `revenue.pursuit_evidence_bridge`. Runtime booleans, caller clocks, recovered hash strings, or caller-supplied trust roots cannot mint PRIME/TEAM readiness.

## Current posture

**HOLD. No external action is authorized.**

The checked-in binding `usac-it-26-139-main-v1` pins:

- canonical JSON root of `source_ledger.json`: `cfad5e09de2a114ecf63de3d010fd67509b49c39d6fb09587ee2b8e79b754faf`;
- canonical JSON root of `submission_manifest.json`: `ce47b0d480532ef8b69274899b874a8dc32cabecca8b4e464d799f22325e15d0`;
- proposal deadline `2026-09-30T15:00:00Z`;
- static source holds for the unrecovered current buyer-page generation and for durable byte custody of the RFP, Bid Sheet, Confidentiality Agreement, and Q&A; and
- no bidder-vault roots yet.

Provider artifact `10457019683` yielded stable observed SHA-256 values for the four controlling buyer artifacts. Those hashes are useful source evidence, but this repository and bridge do **not** currently materialize, consume, or independently verify the corresponding artifact bytes/member manifest. The ledger therefore records each recovered hash while keeping `byte_custody=false`; the four `*_BYTES_NOT_RETAINED` HOLDs stay active. Hash-known is not byte custody.

The first-party procurement page was independently rechecked on 2026-09-17 and still exposed the same RFP, Attachment 1 Bid Sheet, Attachment 2 Confidentiality Agreement, and Questions & Answers with no additional notice link observed. Its current HTML generation is also not retained byte-for-byte, so `CURRENT_BUYER_PAGE_GENERATION_NOT_RETAINED` remains active.

The prior inert Bid Sheet inspection remains evidence only: one OOXML sheet (`Tab 1 - Summary`), `A1:E26`, 20 non-empty cells, zero formulas, with 120-day validity and a four-month firm-fixed-price structure observed. It establishes neither approved price nor signature authority.

## Current gate

From repository root:

```bash
python -m opportunities.usac_it_26_139_ai_consulting.qualify
```

Exit status is `0` only for `OPPORTUNITY_EVIDENCE_READY`, `2` for a valid current `HOLD`, and `3` for malformed/tampered input or I/O failure. An optional `--vault PATH` is accepted only after exact bidder-vault roots have been independently retained in the repo binding. While those roots are null, runtime vault bytes are rejected rather than self-authorized.

The wrapper exposes no caller `as_of`, deadline, expected source root, expected manifest root, binding registry, PRIME/TEAM switch, or self-asserted readiness booleans.

## Source/evidence work still required

A later reviewed source generation must durably materialize and bind the current first-party USAC procurement page plus the four controlling artifact byte streams (or an equivalently strong member manifest that the verifier actually consumes) before the byte-custody HOLDs can be removed. Separately, independently retained bidder-vault evidence must establish the real organization/legal entity, UEI/SAM status, authorized signer, legal/NDA/insurance/conflict posture, named personnel, reference/engagement evidence, team commitments, proposal artifacts, and owner-approved prices required by the manifest.

Only a reviewed repository change may pin those exact roots and remove the corresponding HOLDs. Runtime input and recovered hash strings cannot mint them.

## Substantive package retained from Zeta

The existing technical response remains a useful drafting asset covering the buyer-shaped AI consulting scope. `requirements.json`, `technical_response.md`, `source_ledger.json`, and `submission_manifest.json` are source/drafting evidence, not proof of legal entity, SAM status, signer authority, references, personnel commitments, NDA execution, final price, or submission authority.

## Authority ceiling

Authorized here: internal source/evidence recovery, drafting, qualification code/tests/docs/CI, GitHub/Slack coordination, review, and guarded merge.

Not authorized here: buyer email; Procurement@usac.org or Noor Jalal contact; USAC portal/account mutation; SAM/UEI/registration changes; NDA execution; signature/certification; reference outreach; staffing/team commitments; final price; proposal submission; contract acceptance; spend; payment mutation; award/payment/revenue claims.

Every action-authority bit emitted by the bridge and `external_submission_authorized` remain false.
