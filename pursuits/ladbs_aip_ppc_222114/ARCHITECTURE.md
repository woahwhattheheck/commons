# Proposed technical acceptance architecture — not deployed capability

This architecture is a response hypothesis for the LADBS AIP-PPC solicitation. It is deliberately separated from qualification evidence: design quality cannot cure bidder eligibility, references, insurance, forms, staffing or commercial authorization.

## 1. Applicant preflight

Applicant uploads or selects a project package. Intake produces immutable file/page digests, project metadata, schema validation and a completeness inventory. Raw source material remains distinguishable from extracted facts.

## 2. Evidence-bound extraction

OCR/document parsers and domain tools emit claims with page/region references, confidence metadata, extractor/tool version and input digest. Unsupported extraction becomes `NEEDS_REVIEW`, not a silently accepted fact.

## 3. Versioned rule/source graph

Code/rule sources are ingested as versioned authorities with effective windows. Every deterministic rule check returns its rule/source ID and version. AI components may retrieve and explain; they do not rewrite the authoritative rule graph.

## 4. Pre-screen findings

A finding binds: project/input digest, extracted evidence, rule/source version, deterministic tool results, model/tool version, cited references, timestamp and severity. It is a pre-screen candidate, not a permit approval or City determination.

## 5. Clearance candidates

Department/clearance suggestions carry reason codes and sources. The user sees why the clearance may apply and what evidence would change that candidate. Final authority remains with LADBS/other City departments.

## 6. Applicant and staff surfaces

Applicant view prioritizes missing material, explainable findings and source links. Staff view adds QA queues, override/reviewer dispositions, false-positive monitoring, latency/throughput metrics and version drift. Overrides are append-only and attributable.

## 7. City integration API

Proposed API returns structured project/findings/reference objects with stable IDs, pagination, idempotency keys, request correlation, version metadata and explicit status semantics. Exact authentication/schema/rate-limit requirements are deferred to controlling Appendix 3 bytes.

## 8. MCP seam

If the controlling package requires Model Context Protocol, expose only scoped tools/resources over the exact required MCP version and transport. Tool results bind provenance and authority. Existing Commons/TitanMCP work may be reused only after exact requirement-to-evidence matching; this document does not claim acceptance conformance.

## 9. Security/privacy

Fail closed until buyer requirements are recovered. Candidate controls include least privilege, tenant isolation, encryption, explicit retention, secret isolation, audit logs, dependency/SBOM controls, abuse/rate limits, prompt/tool injection boundaries, model-data handling declarations and incident response. None is represented as implemented merely because it is listed here.

## 10. Replay and acceptance

An acceptance harness replays fixed project packets against frozen rule/source/model/tool versions and compares deterministic artifacts. Golden tests include hallucination/citation failure, stale-rule versions, conflicting sources, prompt/tool injection, dimension/extraction uncertainty, missing pages, API schema drift, reviewer override and privacy redaction. Buyer acceptance criteria must come from Appendix 4 / controlling package.
