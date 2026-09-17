# USAC IT-26-139 — Artificial Intelligence Consulting Services

Original pursuit/source/product/finalizer: **Zeta / GPT-5.6 Sol**  
Original operation: `USAC-IT-26-139-AI-CONSULTING-ZETA-20260913` / issue #14263 / PR #14281  
Bridge recovery: **Z-Sol-61 (`ZS61`) / GPT-5.6 Sol**  
Raw-byte helper/source recovery credit: **Z-CeriumSignal-0932-P5N7 (`ZCSG-P5N7`)**  
Stale source-generation recovery: **Swarm Z / Sol-17 / GPT-5.6 Sol**  
Custody-truth RED closure/finalization: **Sol-Z / GPT-5.6 Sol**

The pursuit remains behind the shared, repo-pinned `revenue.pursuit_evidence_bridge`. Runtime booleans, caller clocks, recovered hash strings, or caller-supplied trust roots cannot mint PRIME/TEAM readiness.

## Current posture

**HOLD. No external action is authorized.**

The checked-in binding `usac-it-26-139-main-v1` pins:

- canonical JSON root of `source_ledger.json`: `3ee53d7c81fcae9a4024720c237e6bd4a7196144c986842401636b31f6f00cc6`;
- canonical JSON root of `submission_manifest.json`: `41af16186712ea6ee612b4ad4932fd0e66d4cba3597ce1a10839de176c221e5e`;
- proposal deadline `2026-09-30T15:00:00Z`;
- static source holds for the current buyer-page generation plus the RFP, Bid Sheet, Confidentiality Agreement, and Q&A bytes; and
- no bidder-vault roots yet.

## Recovered hashes are evidence, not custody

An authenticated GitHub Actions recovery artifact (`10457019683`, archive SHA-256 `927631e36052b358cd168479172e0dcb4f2722d68c1f0b92a220fa2d940a0374`) previously yielded these exact observed hashes:

- RFP: `fc278ff4c8ab5fff06b38e4d463b2cc119a2a5c27b7a527ba89ccc40a40decbe`;
- Attachment 1 Bid Sheet: `836f443922a2ea41d6b3804dd3ec80d7854149368edf617a7eab7a31349ff479`;
- Attachment 2 Confidentiality Agreement: `c9471803056957b73d396f6379dcdaf4facd41a7bd90cb75ccc42e8f5a23370b`;
- Questions & Answers: `3682d0351e322ac1e9e2f277dfed4dfed75b01ffaf34e554b7d5c259a07852bb`.

Those hashes remain useful provenance, but the bridge does **not** possess or digest the four artifact members. Accordingly all four ledger rows remain `byte_custody=false` and all four byte-custody HOLDs remain machine-enforced. A hash observed once from an out-of-band artifact is not equivalent to durable repo-pinned bytes or a bridge-verifiable custody manifest.

The pinned source generation is timestamped `2026-09-16T16:14:43Z`. An independent Sep-17 review externally observed the same buyer-page link set, but that later observation is deliberately **not** represented as part of this pinned generation and clears no hold. The current first-party page generation itself remains unretained, so later notices/addenda cannot be declared current from this package.

The Bid Sheet was also inspected inertly during recovery as OOXML (one sheet `Tab 1 - Summary`, `A1:E26`, 20 non-empty cells, zero formulas; 120-day validity and a four-month firm-fixed-price structure visible). That is drafting/source evidence only; it does not establish an approved price, signature authority, or durable byte custody.

## Current gate

From repository root:

```bash
python -m opportunities.usac_it_26_139_ai_consulting.qualify
```

Exit status is `0` only for `OPPORTUNITY_EVIDENCE_READY`, `2` for a valid current `HOLD`, and `3` for malformed/tampered input or I/O failure. An optional `--vault PATH` is accepted only after exact bidder-vault roots have been independently retained in the repo binding. While those roots are null, runtime vault bytes are rejected rather than self-authorized.

The wrapper exposes no caller `as_of`, deadline, expected source root, expected manifest root, binding registry, PRIME/TEAM switch, or self-asserted readiness booleans.

## Evidence still required

A later reviewed source generation must durably retain and bridge-bind the current first-party USAC procurement page generation plus the controlling RFP, Bid Sheet, Confidentiality Agreement, and Q&A bytes (or a mechanically equivalent durable member manifest that the bridge actually verifies) before the corresponding source holds can be removed.

Separately, independently retained bidder-vault evidence must establish the real organization/legal entity, UEI/SAM status, authorized signer, legal/NDA/insurance/conflict posture, named personnel, reference/engagement evidence, team commitments, proposal artifacts, and owner-approved prices required by the manifest.

Only a reviewed repository change may pin those exact roots. Runtime input cannot mint them.

## Substantive package retained from Zeta

The existing technical response remains a drafting asset covering the buyer-shaped AI consulting scope. `requirements.json`, `technical_response.md`, `source_ledger.json`, and `submission_manifest.json` are source/drafting evidence, not proof of legal entity, SAM status, signer authority, references, personnel commitments, NDA execution, final price, or submission authority.

## Authority ceiling

Authorized here: internal source/evidence recovery, drafting, qualification code/tests/docs/CI, GitHub/Slack coordination, review, and guarded merge.

Not authorized here: buyer email; Procurement@usac.org or Noor Jalal contact; USAC portal/account mutation; SAM/UEI/registration changes; NDA execution; signature/certification; reference outreach; staffing/team commitments; final price; proposal submission; contract acceptance; spend; payment mutation; award/payment/revenue claims.

Every action-authority bit emitted by the bridge and `external_submission_authorized` remain false.
