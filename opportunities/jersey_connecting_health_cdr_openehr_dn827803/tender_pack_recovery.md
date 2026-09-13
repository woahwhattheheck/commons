# Tender-pack recovery and exact-byte authority retention

## Known public route

- Buyer: Government / States of Jersey
- Procurement: `Connecting Health - Clinical Data Repository (CDR) and openEHR`
- Reference: `DN827803`
- Public ProContract window: 28 Aug 2026 to 29 Sep 2026 23:30 (the future READY path must bind the controlling buyer-pack deadline, not merely this public listing)

The public listing and mirrors expose useful scope, but this carrier does **not** contain the controlling tender documents. Current state is therefore `HOLD_TENDER_PACK_REQUIRED`.

## Authorized recovery procedure

An operator who already has authority to access the procurement portal should:

1. Open the exact `DN827803` opportunity without creating a new supplier account unless separately authorized.
2. Download every current tender document, schedule, response workbook/form, contract, security schedule, architecture appendix, pricing sheet and amendment/addendum.
3. Preserve each filename and byte sequence exactly and record portal version/timestamp metadata where shown.
4. Build one deterministic controlling tender-pack archive and compute its lowercase SHA-256.
5. Produce a complete extraction with:
   - every tender/addendum/schedule/form in the inventory, each with stable ID, kind, exact source coordinate and SHA-256;
   - the buyer-controlled response deadline, exact deadline source ID/coordinate and committed deadline text digest;
   - every mandatory requirement with stable ID, source ID/coordinate/digest, category, mandatory bit, applicable route set, cure semantics, shared-evidence semantics, raw requirement-text digest, description and description digest;
   - exact inventory/requirement counts and deterministic set digests;
   - `inventory_complete=true` and `mandatory_requirements_complete=true` only after independent completeness review.
6. Build a separate evidence bundle. Each immutable evidence source gets a source ID, exact coordinate and SHA-256. Each claim record binds:
   - subject/entity;
   - exact requirement ID(s);
   - category;
   - evidence source ID/digest/coordinate;
   - claim text digest;
   - explicit reuse semantics;
   - a deterministic binding digest over those fields.
7. Update `sources.json` only after the controlling bytes exist:
   - refresh `checked_at` from the source review;
   - bind the controlling buyer deadline;
   - `acquired=true`;
   - exact tender-pack SHA-256;
   - `reviewed=false`, state `TENDER_PACK_ACQUIRED_UNREVIEWED` until full review;
   - after complete review, `reviewed=true`, state `TENDER_PACK_ACQUIRED_REVIEWED`.
8. **Independently retain** the consumption boundary in `trusted_root.json` only after reviewing the exact artifacts above. Bind:
   - the exact raw `sources.json` SHA-256;
   - source check time and buyer deadline;
   - exact tender-pack SHA-256;
   - exact extraction-file SHA-256;
   - exact evidence-bundle SHA-256;
   - root retention time and current-source freshness limit.
   The production CLI has no `--trusted-root` override; a caller-presented source/extraction/evidence packet cannot replace this retained commitment.
9. Run `qualify.py` with the actual pack, extraction and evidence bytes. A changed source ledger, omitted/later addendum gate, changed route/cure/mandatory/category/description semantics, changed evidence, stale source, or deadline extension requires a new independently reviewed root rather than caller-side recomputation.

## Extract before any commercial recommendation

- mandatory eligibility and supplier geography;
- single-supplier vs consortium/partner rules and named-party requirements;
- openEHR versions, conformance, archetype/template governance and API expectations;
- CDR data model, persistence, query and lifecycle requirements;
- real-time ingestion/access latency, throughput and resilience requirements;
- FHIR/HL7/other interface standards and exact target systems;
- patient identity, terminology, provenance and consent/access-control requirements;
- data residency, hosting, IAM, cyber, audit and incident requirements;
- clinical-safety/regulatory requirements and accountable roles;
- migration history/volumes, reconciliation, coexistence, cutover and archive requirements;
- availability/SLA/RTO/RPO/DR/observability expectations;
- analytics platform/interface expectations and workload separation;
- implementation milestones, training, support and transition/exit requirements;
- scoring, mandatory/pass-fail gates, attachments and word/character limits;
- commercial/pricing schedule, liabilities, insurance, IP/data ownership, indexation and exit;
- exact submission deadline/timezone, amendment history, and portal actions.

## Stop conditions

Stop instead of improvising if access requires new account registration, acceptance of supplier terms, a declaration, a clarification message, a live submission action, or a representation on behalf of Token Junkie Labs. Those actions require separate authority.
