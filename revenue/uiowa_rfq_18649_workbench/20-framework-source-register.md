# UIOWA-020 — Primary framework source and version register

**Purpose.** This register supports the University of Iowa RFQ 18649 assessment design. It records the primary framework versions used by `20-framework-crosswalk.csv` and the boundaries on how they may be interpreted.

**Accessed:** 2026-09-19

## Canonical baselines

| Framework | Version used | Publication | Primary source | Status for this assessment | Revalidation rule |
|---|---|---|---|---|---|
| NIST Secure Software Development Framework (SSDF) | v1.1, NIST SP 800-218 | 2022-02-03 | https://csrc.nist.gov/pubs/sp/800/218/final and https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-218.pdf | Current **final** SSDF baseline used here. The crosswalk cites SSDF practice identifiers (PO, PS, PW, RV). | Check the CSRC publication page at kickoff and before the final report for revisions or superseding publications. |
| NIST Cybersecurity Framework (CSF) | 2.0, NIST CSWP 29 | 2024-02-26 | https://csrc.nist.gov/pubs/cswp/29/the-nist-cybersecurity-framework-csf-20/final and https://nvlpubs.nist.gov/nistpubs/CSWP/NIST.CSWP.29.pdf | Current published CSF baseline used here. The crosswalk uses Core Functions/Categories plus the Profile and Tier concepts. | Check the CSRC publication page at kickoff and before the final report. |
| NIST AI Risk Management Framework (AI RMF) | 1.0, NIST AI 100-1 | 2023-01-26 | https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10 and https://nvlpubs.nist.gov/nistpubs/ai/nist.ai.100-1.pdf | Current released AI RMF baseline used here. NIST's AI RMF site states that AI RMF 1.0 is being revised in 2026; therefore the framework must be revalidated before delivery. | Recheck https://www.nist.gov/itl/ai-risk-management-framework at kickoff and before any final deliverable. If a successor is released, record both the version used for evidence collection and any transition impact. |

## Version watch and conditional supplements

| Publication | Status checked 2026-09-19 | Use in this assessment |
|---|---|---|
| NIST SP 800-218 Rev. 1 / SSDF v1.2 | **Initial Public Draft**, released 2025-12-17; comment period closed 2026-01-30. https://csrc.nist.gov/pubs/sp/800/218/r1/ipd | Monitor for finalization. Do **not** silently substitute the draft for the final v1.1 baseline. If a final successor appears during delivery, document the transition impact explicitly. |
| NIST SP 800-218A, Secure Software Development Practices for Generative AI and Dual-Use Foundation Models | **Final**, released 2024-07-26. https://csrc.nist.gov/pubs/sp/800/218/a/final | Conditional supplement only when the assessed activity includes GenAI or dual-use foundation-model development within the profile's scope. It does not establish that Iowa performs such development. |
| NIST AI 600-1, Generative AI Profile | **Final**, released 2024-07-26. https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence | Conditional supplement only when discovery confirms an in-scope generative-AI use case; not a universal AI-readiness baseline. |

## Interpretation boundaries

1. **Framework text is reference vocabulary, not observed Iowa practice.** A NIST outcome or practice identifier is a prompt for interviews, artifact requests, and evidence interpretation. It does not show that the University, AIS, ESS, RIS, or IAM implements that practice.
2. **No certification claim.** None of these mappings asserts NIST certification, conformance, compliance, accreditation, or endorsement.
3. **No invented maturity scale.** CSF Tiers describe characteristics of cybersecurity risk governance and management. This assessment will not turn them into a numeric maturity score, percentile, or league table.
4. **No procurement recommendation.** Framework references may surface dependency, platform, supplier, or third-party risk questions. They do not recommend a vendor or product.
5. **Version matters.** Findings and recommendations must name the exact framework version used. If NIST releases a successor during the engagement, the team will record the change rather than silently rewriting the baseline.
6. **Primary-source hierarchy.** The linked NIST publication pages and PDFs are authoritative for this crosswalk. Secondary explainers may help analysts navigate a topic but must not replace the primary citation in a finding.
7. **Scope remains the RFQ.** The framework material is adapted only to software development, security, deployment/operations, and AI readiness for the systems and teams actually in scope. It does not expand the engagement into a general enterprise compliance audit.

## Locator convention

- **SSDF:** practice identifiers such as `PO.1`, `PS.1`, `PW.7`, and `RV.3`.
- **CSF 2.0:** Core Category identifiers such as `GV.RM`, `ID.AM`, `PR.AA`, `DE.CM`, `RS.MA`, and `RC.RP`, plus `§3.1` Organizational Profiles and `§3.2` CSF Tiers.
- **AI RMF 1.0:** Core subcategory identifiers such as `GOVERN 1.6`, `MAP 3.5`, `MEASURE 2.10`, and `MANAGE 2.4`.

The locator is intended to make every crosswalk row auditable against the primary publication rather than relying on a paraphrase alone.
