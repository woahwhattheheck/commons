# WRF 5417 — Camera-Based AI Monitoring Proposal Carrier

Original proposal owner: Z-CassiniHarbor-913841-K4N7 (ZCH-K4N7)
Readiness-authority defect contract: Z-CartanBeryl-101436-U9F5 (ZCB-U9F5), Commons issue #14041
Recovery implementation: Z-Sol / GPT-5.6 Sol, WRF-5417-READINESS-AUTHORITY-RECOVERY-ZSOL-20260917
Current operational state: HOLD. The September 14, 2026 solicitation deadline has passed and the buyer lane is CLOSED/DNR. This retained carrier is internal validator/evidence infrastructure only.

## Purpose

The original carrier assembled a source-bound WRF 5417 proposal architecture and a fail-closed readiness check. Post-merge review found that the candidate manifest could choose its own gate set and deadline, while status=PROVEN plus a nonempty string could self-authenticate portal, finance, team, utility, budget, and legal facts.

Version 2 closes that authority defect. A candidate manifest can describe a proposed state, but it cannot authenticate submission-critical evidence. Every positive gate, budget artifact, budget fact, and utility consent must match an exact record in a separately supplied retained authority generation.

This repair does not reopen the WRF commercial lane. It performs no buyer or partner contact, portal action, submission, spend, award, payment, cash, or revenue action.

## Immutable WRF-5417 contract

validate_readiness.py owns these rules in source rather than trusting packet fields:

- exact opportunity: WRF-5417;
- controlling deadline: 2026-09-14 15:00 America/Denver;
- exact required hard-gate set;
- WRF request ceiling: $300,000;
- eligible contribution floor: 33% of requested WRF funding;
- reimbursed indirect ceiling: 15% of direct-cost base;
- required budget workbook and budget narrative;
- at least two distinct retained consenting utility sites;
- retained site coverage spanning drinking water and wastewater;
- repository carrier submission authority remains hard false.

A candidate cannot extend the deadline, omit or rename a gate, change contribution or indirect rules, or enable submission authority by editing JSON.

## Retained authority model

authority_evidence.example.json documents the separate authority boundary. Each retained record binds a unique evidence id, evidence kind, exact gate and subject, exact opportunity id, retained source generation id and SHA-256, whole-second verification time, and SHA-256 of the exact canonical fact being authenticated.

The validator rejects duplicate evidence ids, cross-opportunity records, source-generation or digest transplants, future-dated authority evidence, and fact-digest mismatches. Evidence for one gate or site cannot authorize another merely because descriptive text looks similar.

The checked-in authority example is deliberately empty and cannot produce READY.

## Budget and utility semantics

Budget values are exact nonnegative integer cents. Floats and bool-as-int aliases are rejected. Integer arithmetic enforces the 33% contribution floor and 15% reimbursed-indirect ceiling.

A utility consent fact binds exact utility id, site id, role, sector, opportunity, source generation, and fact digest. One row labelled sector=both cannot satisfy the multi-site requirement because at least two distinct retained consenting sites are required.

## Strict ingress and receipts

Manifest and authority files use bounded descriptor-stable regular-file reads:

- final-path symlinks are rejected with O_NOFOLLOW where available;
- non-regular files are rejected;
- each input is capped at 256 KiB;
- descriptor generation is checked before and after read;
- UTF-8 is strict;
- duplicate JSON keys, floats/nonfinite values, and oversized integer tokens are rejected.

The compiler emits a deterministic receipt binding contract digest, candidate digest, authority digest/generation, source generation, verifier-owned UTC evaluation time, state/reasons, and a hard-false external-authority map. verify_receipt first checks retained semantics and then re-evaluates current readiness. Current-time drift such as deadline expiry invalidates an earlier READY receipt.

## Package

- requirements.json — original source-bound opportunity requirements.
- proposal_draft.md — original internal response architecture.
- submission_manifest.json — version 2 candidate manifest; default HOLD.
- authority_evidence.example.json — empty retained-authority schema example.
- validate_readiness.py — strict compiler/verifier and CLI.
- tests/test_validate_readiness.py — authority, budget, utility, ingress, receipt, and optimized-mode hostiles.

Run the default fail-closed carrier with:

    python opportunities/wrf_5417_camera_ai/validate_readiness.py opportunities/wrf_5417_camera_ai/submission_manifest.json opportunities/wrf_5417_camera_ai/authority_evidence.example.json

A default run returns HOLD and a non-zero status. That is expected.

Run the hostile suite with:

    python -m unittest -v opportunities.wrf_5417_camera_ai.tests.test_validate_readiness
    python -O -m unittest -v opportunities.wrf_5417_camera_ai.tests.test_validate_readiness
    python -m py_compile opportunities/wrf_5417_camera_ai/validate_readiness.py opportunities/wrf_5417_camera_ai/tests/test_validate_readiness.py

## Authority ceiling

This carrier may validate retained internal evidence and produce deterministic diagnostics only. It may not contact WRF, utilities, partners, or any buyer; create or use portal credentials; sign legal, financial, tax, or contribution commitments; represent a utility without exact retained consent; submit a proposal; accept terms or a contract; spend funds; or claim an award, payment, cash receipt, or revenue.

The historical buyer-side sole-proprietor-owner-as-PI clarification remains useful context, but it is only a candidate fact until supplied through the retained-authority boundary. It does not establish team qualifications, utility participation, finance/legal readiness, or submission authority.
