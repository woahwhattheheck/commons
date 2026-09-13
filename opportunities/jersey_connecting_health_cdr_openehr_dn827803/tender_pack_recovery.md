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
4. Build a deterministic inventory of every controlling file/addendum, with stable source IDs, kinds, exact SHA-256 values and portal/version coordinates.
5. Identify which file or deterministic archive is the tender-pack byte object consumed by `qualify.py`, and compute SHA-256 over those exact bytes.
6. Review **all** mandatory requirements, exclusions, evaluation gates, response limits, declarations, deadlines and portal mechanics. Assign each extracted requirement a stable ID and bind its mandatory flag, route/cure semantics, exact buyer source ID + SHA-256 and description SHA-256.
7. Review every capability-evidence item proposed for `PROVEN`. Retain a stable evidence ID, claim/capability ID, `PRIME` or `PARTNER` subject, immutable source SHA-256, HTTPS source reference and SHA-256 of the exact reviewed claim statement.
8. Update `sources.json` only after the bytes exist:
   - `acquired=true`;
   - exact lowercase tender-pack SHA-256;
   - `reviewed=false`, state `TENDER_PACK_ACQUIRED_UNREVIEWED` until full review;
   - after complete review, `reviewed=true`, state `TENDER_PACK_ACQUIRED_REVIEWED`.
9. Recompute SHA-256 of the complete updated `sources.json` bytes.
10. Create a `jersey-dn827803-trusted-qualification/v2` commitment containing:
    - exact source-ledger and tender-pack SHA-256 values;
    - extraction time and `addenda_checked_through` time;
    - buyer-source-bound response deadline and deadline source ID;
    - `complete=true` only after the complete current package was reviewed;
    - canonical buyer-source set + set digest;
    - canonical complete requirement set + set digest; and
    - canonical approved-evidence set + set digest.
11. Normalize that trusted commitment with the same v2 schema and retain its canonical SHA-256 **separately from the file presented to the evaluator**. This separately retained digest is the verifier trust root. Do not recompute the expected root from a newly presented trusted-qualification file during consumption.
12. Run `qualify.py ... --tender-pack ACTUAL_FILE_OR_ARCHIVE --trusted-qualification REVIEWED_TRUST.json --trusted-qualification-sha256 RETAINED_ROOT` so both the actual bytes and the independently retained extraction commitment must match.

The trusted extraction/addenda inventory is current-work evidence, not a permanent certification. The v2 evaluator fails closed once `addenda_checked_through` is more than 24 hours behind trusted current UTC. Refresh the controlling inventory and retain a new reviewed root rather than rolling the evaluation clock backward.

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