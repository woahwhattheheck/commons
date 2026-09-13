# Public-scope requirement and evidence matrix

This matrix is intentionally split between **publicly stated scope** and **questionnaire-controlled unknowns**. `sources.json` is the machine-readable source of the current public facts.

| Area | Public notice signal | Evidence needed before a truthful response | Current state |
|---|---|---|---|
| Pathology LIMS product | Future interoperable Pathology IT LIMS | Named product, version, supported disciplines, deployment architecture, roadmap | UNKNOWN |
| Disciplines | Biochemistry, haematology, blood transfusion, microbiology, immunology, H&I, virology, cellular pathology, andrology, genetics, molecular | Product/configuration evidence per discipline; exclusions made explicit | UNKNOWN |
| Scale/topology | Large hub-and-spoke networks; urgent + routine pathways; specialist diagnostics; GP/community connectivity | Comparable volumes/topologies, performance evidence, resilience design | UNKNOWN |
| Migration | Implementation includes migration | Proven migration method, reconciliation, cutover/rollback, archival and historical-data treatment | UNKNOWN |
| Interoperability | Beyond traditional HL7; EPRs, national systems, automation platforms, analytics | Interface catalogue, standards, conformance/testing, ownership boundaries, monitoring | UNKNOWN |
| Digital pathology/automation | Ongoing investment and integration need | Supported platforms/interfaces plus deployment evidence | UNKNOWN |
| AI/ML | Future capability may leverage AI/ML | Intended use, governance, validation, monitoring, human oversight; no unsupported clinical claims | UNKNOWN |
| Clinical safety | Public notice says future platform must maintain clinical safety | Clinical-safety case/process, hazard management, accountable roles, deployment evidence | UNKNOWN |
| Standardisation | Cross-network standardisation is a goal | Configuration governance, master-data/change control, local-vs-common model | UNKNOWN |
| Regulatory compliance | Public notice names regulatory compliance generically | Exact buyer-required standards/certifications from questionnaire; evidence and expiry dates | QUESTIONNAIRE_REQUIRED |
| Security/privacy | Not fully enumerated in public notice | Buyer security schedule, DSPT/data residency/access/incident requirements, evidence | QUESTIONNAIRE_REQUIRED |
| Implementation | Implementation explicitly in future scope | Programme method, workstreams, resourcing, risks, dependencies, acceptance gates | UNKNOWN |
| Training/support | Training + support explicitly in future scope | Role-based training, service model, SLAs, escalation, knowledge transfer | UNKNOWN |
| Commercial model | Buyer seeks market input on commercial models | Licensing/subscription/implementation/support units, assumptions, inflation/indexation, exit | QUESTIONNAIRE_REQUIRED |
| Procurement mechanics | Preliminary market engagement; attached questionnaire via Atamis C467704 | Exact questionnaire prompts, response format, declarations, upload/send mechanics | QUESTIONNAIRE_NOT_ACQUIRED |
| Evaluation / future tender | Not fixed in public notice | Future tender procedure, scoring, lots, mandatory gates and timetable | UNKNOWN |

## Truth rules

1. A hiring post, prototype, internal tool or unrelated LIMS artifact is not proof of a clinical pathology LIMS deployment.
2. `PROVEN` requires a source pointer that a reviewer can inspect. A self-authored statement is not evidence of past performance.
3. Certifications/standards are never inferred from engineering capability.
4. A prime-route miss may still permit a bounded teaming route, but the partner must own the missing prime qualifications in writing before readiness.
5. Questionnaire-controlled fields remain `UNKNOWN` until the actual buyer questionnaire bytes are recovered, hashed, reviewed and represented in the source ledger.
