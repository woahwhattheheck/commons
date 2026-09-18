# Tender-pack recovery and exact-byte binding

## Known public route

- Buyer: Government / States of Jersey
- Procurement: `Connecting Health - Clinical Data Repository (CDR) and openEHR`
- Reference: `DN827803`
- Public ProContract window: 28 Aug 2026 to 29 Sep 2026 23:30 (confirm timezone and final deadline from controlling tender pack)

The public listing and mirrors expose useful scope, but this carrier does **not** contain the controlling tender documents.

## Authorized recovery procedure

An operator who already has authority to access the procurement portal should:

1. Open the exact `DN827803` opportunity without creating a new supplier account unless separately authorized.
2. Download every current tender document, schedule, response workbook/form, contract, security schedule, architecture appendix, pricing sheet and amendment.
3. Preserve each filename and byte sequence exactly and record portal version/timestamp metadata where shown.
4. Identify which file or archive is controlling; if multiple files collectively control the response, archive them deterministically and hash that archive.
5. Compute SHA-256 over the exact controlling bytes.
6. Review all mandatory requirements, exclusions, evaluation gates, response limits, declarations, deadlines and portal mechanics.
7. Update `sources.json` only after the bytes exist:
   - `acquired=true`;
   - exact lowercase SHA-256;
   - `reviewed=false`, state `TENDER_PACK_ACQUIRED_UNREVIEWED` until full review;
   - after complete review, `reviewed=true`, state `TENDER_PACK_ACQUIRED_REVIEWED`.
8. Recompute SHA-256 of the complete updated `sources.json` bytes and bind it into the manifest.
9. Run `qualify.py ... --tender-pack ACTUAL_FILE_OR_ARCHIVE` so the actual bytes must match the declared digest.

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
- exact submission deadline/timezone and portal actions.

## Stop conditions

Stop instead of improvising if access requires new account registration, acceptance of supplier terms, a declaration, a clarification message, a live submission action, or a representation on behalf of Token Junkie Labs. Those actions require separate authority.
