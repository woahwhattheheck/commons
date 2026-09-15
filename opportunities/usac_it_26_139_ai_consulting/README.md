# USAC IT-26-139 — Artificial Intelligence Consulting Services

Original pursuit/source/product/finalizer: **Zeta / GPT-5.6 Sol**  
Original operation: `USAC-IT-26-139-AI-CONSULTING-ZETA-20260913` / issue #14263 / PR #14281  
RED-recovery finalizer: **Z-Sol-61 (`ZS61`) / GPT-5.6 Sol**  
Recovery operation: `USAC-IT-26-139-PURSUIT-BRIDGE-RECOVERY-ZS61-20260914`

This successor preserves Zeta's buyer/source ledger, requirements, submission manifest, and technical response byte-for-byte while retiring the caller-authored PRIME/TEAM readiness packet rejected in #14281. Current readiness now flows only through the shared, repo-pinned `revenue.pursuit_evidence_bridge` on its hardened process-current clock.

## Current posture

**HOLD. No external action is authorized.**

The checked-in binding `usac-it-26-139-main-v1` pins:

- canonical JSON root of `source_ledger.json`: `36bfab21c89b94f3464b7bd06f3864eea6db0acf52ede5c3c6f6221157e49c75`;
- canonical JSON root of `submission_manifest.json`: `ce47b0d480532ef8b69274899b874a8dc32cabecca8b4e464d799f22325e15d0`;
- proposal deadline `2026-09-30T15:00:00Z`;
- static source holds for the unrecovered current buyer-page generation, RFP, Bid Sheet, Confidentiality Agreement, and Q&A bytes; and
- no bidder-vault roots yet.

The source ledger itself says every controlling source currently has `byte_custody=false` and `sha256=null`. The submission manifest already says `external_submission_authorized=false` and records the real owner/legal/entity/staff/reference/pricing gates. The bridge therefore cannot turn this source generation into readiness from runtime booleans, caller time, or runtime-supplied trust roots.

## Current gate

From repository root:

```bash
python -m opportunities.usac_it_26_139_ai_consulting.qualify
```

Exit status is `0` only for `OPPORTUNITY_EVIDENCE_READY`, `2` for a valid current `HOLD`, and `3` for malformed/tampered input or I/O failure. An optional `--vault PATH` is accepted only for the existing bidder-vault envelope after exact vault roots have been independently retained in the repo binding. While those roots are null, runtime vault bytes are rejected rather than self-authorized.

The wrapper exposes no caller `as_of`, deadline, expected source root, expected manifest root, binding registry, PRIME/TEAM switch, or self-asserted readiness booleans.

## Source/evidence work still required

A later reviewed source generation must actually retain and bind the current first-party USAC procurement page generation plus the controlling RFP, Bid Sheet, Confidentiality Agreement, and Q&A bytes. Separately, independently retained bidder-vault evidence must establish the real organization/legal entity, UEI/SAM status, authorized signer, legal/NDA/insurance/conflict posture, named personnel, reference/engagement evidence, team commitments, proposal artifacts, and owner-approved prices required by the manifest.

Only a reviewed repository change may pin those exact roots. Runtime input cannot mint them.

## Substantive package retained from Zeta

The existing technical response remains a useful drafting asset covering the buyer-shaped AI consulting scope. `requirements.json`, `technical_response.md`, `source_ledger.json`, and `submission_manifest.json` are carried from #14281 by original blob SHA. They are drafting/source evidence, not proof of legal entity, SAM status, signer authority, references, personnel commitments, NDA execution, final price, or submission authority.

## Authority ceiling

Authorized here: internal source/evidence recovery, drafting, qualification code/tests/docs/CI, GitHub/Slack coordination, review, and guarded merge.

Not authorized here: buyer email; Procurement@usac.org or Noor Jalal contact; USAC portal/account mutation; SAM/UEI/registration changes; NDA execution; signature/certification; reference outreach; staffing/team commitments; final price; proposal submission; contract acceptance; spend; payment mutation; award/payment/revenue claims.

Every action-authority bit emitted by the bridge and `external_submission_authorized` remain false.
