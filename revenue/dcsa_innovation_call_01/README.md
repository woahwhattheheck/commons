# DCSA Innovation Call #01 pursuit carrier

Operation: `DCSA-INNOVATION-CALL-01-20260914`  
Notice: `DCSAInnovationCall01` under `HS0021-26-CSO-DCSA`  
Purpose: internal qualification, architecture, acceptance evidence, and teaming preparation for the Unified Application Access and Integration Prototype.

## Truthful current posture

The checked-in carrier is **HOLD**.

It does not retain the four controlling Government document byte generations, and it contains no host-retained authority proving:

- an active Top Secret Facility Clearance;
- assigned U.S.-citizen personnel with the required clearance posture;
- privileged-user Tier 5 / T5R / Top Secret start authority;
- CAC operability;
- a valid direct or cleared-prime OTA participation path;
- owner-approved ROM, direct route, teaming route, contact, or submission.

The source ledger records first-party locations and secondary mirrors but intentionally keeps `retained_bytes=false` and `sha256=null`. Metadata and extracted summaries cannot mint current source authority.

## What this carrier supplies

- strict source-generation ledger for the Innovation Call, general solicitation, mandatory Concept Paper template, and ecosystem style guide;
- process-time current qualification with exact deadline handling;
- fixed host authority paths with no caller-selected current clock or trust-root path;
- exact authority-generation floor and source-generation binding;
- direct-route gates for FCL, citizenship, personnel clearance, privileged-user investigation, CAC, OTA eligibility, capability evidence, and ROM approval;
- separate `TEAMING_REQUIRED` route that still requires independently retained cleared-prime OTA authority and owner approval;
- deterministic six-section internal Concept Paper renderer;
- executable four-phase acceptance-evidence matrix;
- evidence-only teaming matrix that currently lists no target rather than guessing clearance or contact routes;
- bounded strict UTF-8 JSON, duplicate-key/non-finite rejection, exact schemas/types, stable-file generation capture, and create-exclusive publication;
- current and historical verification paths. Historical replay is always `HISTORICAL_INTEGRITY_ONLY` and can never mint current readiness.

## Fixed current authority boundary

Current compilation reads only:

```text
/etc/commons/dcsa-innovation-call-01/authority.json
/etc/commons/dcsa-innovation-call-01/authority-floor.json
```

The CLI has no option for alternate current authority or floor paths and no `--now`/`--as-of` parameter on the current path. Missing, malformed, stale, future, subject-mismatched, source-mismatched, or floor-mismatched authority fails closed.

The host files are an operator trust root. The supported current boundary requires POSIX, root ownership, a single regular-file link, and no group/other write bits. The paths are code-pinned and do not depend on `HOME`, cwd, CLI arguments, or environment selectors. They must be provisioned from independently retained evidence. Candidate JSON cannot create or replace them.

## States

- `DIRECT_READY` — internal owner-review readiness only; every direct eligibility and capability gate is independently `VERIFIED`, the current source generation is complete and fresh, ROM and direct route are owner-approved, and the Concept Paper deadline remains open.
- `TEAMING_REQUIRED` — internal owner-review route only; direct evidence is insufficient or teaming is selected, while a separately evidenced cleared-prime OTA route, capability evidence, source generation, ROM, and owner teaming approval are current.
- `HOLD` — the default for missing source bytes, missing/stale authority, incomplete capabilities, missing ROM approval, deadline closure, or any trust mismatch.

All states retain:

```text
external_contact_authorized=false
external_submission_authorized=false
signature_authorized=false
pricing_commitment_authorized=false
clearance_claim_authorized=false
award_or_revenue_claimed=false
```

## Architecture

The internal Concept Paper uses a continuity-first Mission Access Fabric:

- common experience shell and workflow continuity canaries;
- multiple approved identity-provider adapters and MFA patterns;
- a canonical subject/context envelope and policy decision layer;
- role, permission, attribute, resource, and data-aware access decisions;
- API and event adapters with explicit owner, idempotency, timeout, retry, ambiguity, audit, and rollback contracts;
- strangler / hub-and-spoke onboarding while legacy applications remain authoritative;
- versioned DevSecOps, infrastructure as code, content-addressed promotion evidence, and visible rollback;
- authorization evidence produced from Phase 1 rather than deferred to the end;
- exact GAT/UAT/regression/integration/performance/reliability/accessibility/security evidence and issue disposition for production transition.

## Commands

Current compile (no caller authority/time override):

```bash
python -m revenue.dcsa_innovation_call_01 compile-current \
  --candidate revenue/dcsa_innovation_call_01/candidate.example.json \
  --source revenue/dcsa_innovation_call_01/source_ledger.json \
  --report /tmp/dcsa-report.json \
  --concept /tmp/dcsa-concept.md \
  --acceptance-json /tmp/dcsa-acceptance.json \
  --acceptance-markdown /tmp/dcsa-acceptance.md
```

The checked-in example exits `3` with `HOLD`; that is expected and truthful.

Historical reconstruction:

```bash
python -m revenue.dcsa_innovation_call_01 compile-historical \
  --candidate revenue/dcsa_innovation_call_01/candidate.example.json \
  --source revenue/dcsa_innovation_call_01/source_ledger.json \
  --authority revenue/dcsa_innovation_call_01/authority.example.json \
  --floor revenue/dcsa_innovation_call_01/authority-floor.example.json \
  --as-of 2026-09-14T04:45:00Z \
  --report /tmp/dcsa-historical.json
```

Historical output remains `HOLD` even when its projected route is otherwise positive.

## Immediate owner actions

1. Retain exact current bytes for all four required source documents and update the source ledger with SHA-256 values.
2. Independently determine whether the authorized operating entity/personnel can satisfy the clearance and OTA gates. Do not self-attest in candidate JSON.
3. If direct eligibility is not independently verified, authorize a teaming search and retain evidence for a cleared prime before listing any target.
4. Select only material questions before the question deadline; recheck current source and use the outbound single-writer controls immediately before any email.
5. Approve or reject the phase-based ROM. No number is invented here.
6. Recompile at process time and require exact current verification before any owner decision.

## Public sources recorded in the ledger

- Official SAM opportunity: `https://sam.gov/workspace/contract/opp/8edbc404f99d46caa7f41a9bb760f4a9/view`
- General solicitation opportunity: `https://sam.gov/workspace/contract/opp/49ca8b1859c74fe28a4e9d3ae1c83d68/view`
- Text mirror used only for research: `https://govtribe.com/file/government-file/dcsa-innovation-call-01-unified-application-layer-dot-pdf`

A mirror is not a controlling source generation. Written terms of the Innovation Call and general solicitation prevail over summaries or live-session remarks.

## Authority ceiling

No DCSA or prime contact, Q&A email, Concept Paper submission, SAM/PIEE mutation, classification or clearance representation, personnel commitment, price/cost-share commitment, signature, contract acceptance, Government-system access, deployment, spend, award, payment, cash, or revenue recognition is performed or authorized by this package.
