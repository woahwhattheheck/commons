# CPCA HCCN Connect evidence inventory

This inventory is deliberately fail-closed. The buyer packet is controlling; repository adjacency is not healthcare qualification.

| Buyer evidence need | Current state | Required proof / next action |
|---|---|---|
| Controlling RFP bytes | **PROVEN** | Buyer-delivered 16-page PDF, SHA-256 `37c61b76500fee4639e1499d7683d4882da294f65d77e5e59c224ada3fc52529` |
| Organization legal name / point of contact | **OWNER_INPUT_REQUIRED** | Supply exact current entity and human contact facts |
| FQHC / look-alike / PCA-HCCN / safety-net primary-care experience | **MISSING_IN_CURRENT_REPO_EVIDENCE** | For every selected domain, bind at least one qualifying engagement to evidence; do not infer from general public-sector work |
| AI emerging-domain comparable engagements | **OWNER_INPUT_REQUIRED** | At least one completed/substantially completed engagement in prior two years plus one additional completed/active/pilot engagement |
| Data Sharing / UDS+ comparable engagements | **OWNER_INPUT_REQUIRED** | Same emerging-domain minimum, plus domain-specific standards evidence |
| Data Management / Value-Based Care comparable engagements | **OWNER_INPUT_REQUIRED** | At least three completed comparable engagements in prior three years per selected domain |
| Technical Assistance evidence | **OWNER_INPUT_REQUIRED** | Individualized assessment / roadmap / implementation / coaching evidence, not product demos |
| Group Training evidence | **OWNER_INPUT_REQUIRED** | Structured curriculum, learning objectives, interactive facilitation and evaluation evidence; webinars alone do not qualify |
| Proposed personnel | **OWNER_INPUT_REQUIRED** | Real people only; roles, credentials/certifications, years, domain qualifications, and comparable-engagement participation |
| Subcontractors | **OWNER_INPUT_REQUIRED** | Disclose all portions performed by third parties and bind their qualifications |
| Regulatory / standards knowledge | **PARTNER_OR_OWNER_EVIDENCE_REQUIRED** | For selected domains: applicable HRSA/UDS/FHIR/Medi-Cal/HEDIS/privacy/security/AI-governance requirements |
| Cultural competency / rural / agricultural-worker delivery | **OWNER_INPUT_REQUIRED** | Bind actual practice/evidence; do not infer from generic DEI language |
| Virtual delivery / California presence | **OWNER_INPUT_REQUIRED** | At least one path must be supportable |
| Concurrent engagement capacity | **OWNER_INPUT_REQUIRED** | Staffing/capacity evidence |
| References | **OWNER_INPUT_REQUIRED** | At least three supportable clients; keep private contact details out of public Git |
| Work samples | **OWNER_INPUT_REQUIRED** | At least one relevant sample for selected domain(s) |
| Rate structure | **OWNER_INPUT_REQUIRED** | Fully loaded owner-approved rates; no generated market-rate commitment |
| Licensing / certifications / insurance / accreditation | **OWNER_REVIEW_REQUIRED** | Determine what is required for selected services and bind actual evidence |
| Engagement Agreement | **FUTURE CONTRACT GATE** | Human legal review only if approved |
| BAA / PHI / PII capability | **OWNER_REVIEW_REQUIRED** | CPCA requires BAA as applicable; do not claim HIPAA/BAA readiness without actual controls/terms |
| Appendix C attestation | **HUMAN_SIGNATURE_REQUIRED** | Authorized human must review licensing, nondiscrimination, conflicts and sign |
| Submission authority | **NOT_AUTHORIZED** | Human owner decides and submits through buyer Smartsheet |

## Current route decision

**HOLD for direct prime submission.** Default-branch Commons searches on 2026-09-14 returned no code hits for `FQHC`, `health center`, or `safety-net`. That does not prove qualifying experience is absent; it means the repository does not currently support asserting it.

The strongest *technical* fit is Objective 5 Artificial Intelligence, especially AI Governance, AI Vendor Evaluation and AI Use Case Education. Those should still remain **HOLD** until the healthcare/safety-net experience gate and emerging-domain comparable-engagement minimum are proven. AI Implementation and Group Training are separate claims and should not be selected merely because adjacent artifacts exist.

If the required safety-net experience cannot be proven directly, the next rational route is a **qualified healthcare/FQHC teaming partner** with verifiable safety-net delivery, client references, and personnel who can satisfy the selected-domain experience standard. Any partner route must be checked against the RFP's applicant/vendor wording before treating it as curative.
