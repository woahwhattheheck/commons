# Architecture and evidence matrix

Public notice descriptions are not the tender pack. This matrix separates what is publicly visible from evidence that must exist before a truthful bid posture can be recommended.

| Area | Public signal | Evidence required before `PROVEN` | Current state |
|---|---|---|---|
| Clinical Data Repository | Centralised CDR is the core requirement | Named production product/platform, architecture, reference deployment, operating model | UNKNOWN |
| openEHR | Platform must be compliant with openEHR standards and architecture | openEHR version/conformance statement, archetype/template governance, CDR APIs, validation evidence, production references | UNKNOWN |
| Real-time clinical data | Real-time access to clinical information | Ingestion/event architecture, latency/SLO evidence, ordering/idempotency, downtime/recovery behaviour | UNKNOWN |
| Interoperability | Cross health/care-system interoperability | Interface catalogue, FHIR/HL7/openEHR/other standards as buyer requires, conformance and failure testing | UNKNOWN |
| Existing-estate integration | Integrate with Jersey government and healthcare technology environments | Actual target-system inventory from tender pack, connector ownership, deployment evidence | TENDER_PACK_REQUIRED |
| Identity / terminology | Implicit in safe cross-system clinical data | Patient/subject identity, terminology/code-system governance, matching/mastering and provenance controls | UNKNOWN |
| Portability / supplier independence | Explicit public outcome | Open interfaces/formats, data export/exit method, archetype/template ownership, no-lock-in evidence | UNKNOWN |
| Analytics / digital capability | Future analytics/digital use is explicit | Governed read/access patterns, analytical replicas/queries, workload isolation, lineage | UNKNOWN |
| Migration | Centralised platform delivery implies transition, but details are not public | Historical scope, migration method, reconciliation, coexistence/cutover/rollback, archival | TENDER_PACK_REQUIRED |
| Security / privacy | Exact schedules not public | Buyer security/privacy/hosting/residency/IAM/incident requirements and inspectable evidence | TENDER_PACK_REQUIRED |
| Clinical safety | Exact buyer safety regime not public | Clinical-safety governance, hazards, accountable roles, release/incident evidence as required | TENDER_PACK_REQUIRED |
| Availability / resilience | Real-time clinical access implies high operational importance | Buyer SLO/RTO/RPO, HA/DR architecture, exercises, observability and failure receipts | TENDER_PACK_REQUIRED |
| Operations / support | Five-year operating horizon | Support model, SLAs, escalation, patch/change, capacity, service continuity, knowledge transfer | UNKNOWN |
| Commercial / legal | Tender is live; terms not captured | Pricing schema, liabilities, IP/data ownership, exit, insurance, declarations, contract schedules | TENDER_PACK_REQUIRED |
| Evaluation / submission | Not recovered | Exact mandatory gates, scoring, field limits, attachments, deadline/timezone, portal mechanics | TENDER_PACK_NOT_ACQUIRED |

## Evidence rules

1. A prototype, generic data platform, FHIR library or agent system is not proof of a production openEHR clinical repository.
2. `PROVEN` requires a reviewer-inspectable evidence pointer. Self-authored assertions are not past-performance evidence.
3. Clinical-safety, security and regulatory claims are never inferred from software engineering capability.
4. A bounded specialist route may be viable only if a qualified prime owns the clinical/product/commercial gaps and the tender permits that structure.
5. Tender-controlled fields remain unknown until the actual controlling bytes are recovered, hashed and reviewed.
