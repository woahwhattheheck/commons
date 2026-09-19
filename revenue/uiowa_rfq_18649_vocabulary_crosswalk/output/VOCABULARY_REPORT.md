# RFQ-18649 group and assessment-area vocabulary reconciliation

> **VOCABULARY RECONCILIATION over synthetic RFQ-18649 fixtures. Terms are reported as observed; mappings are declared, never guessed. Nothing here is a University of Iowa finding, and no lane is scored, ranked or certified.**

517 observations across 95 files in 30 lanes. **76 distinct terms**: 29 resolve to a canonical value, **47 need a decision from the lane that uses them.**

## 1. Why this matters

A check written against one lane's spelling silently mis-compares another's. This is not hypothetical: a UIOWA-130 check that said `deployment` where a lane says `deployment_operations` reported that lane as covering 9 of 12 cells when it covers all 12. The check manufactured a gap in another seat's work.

## 2. Terms needing a decision

These are **not** mapped. Each names the lane that must answer.

| Term | Slot | Kind | Rows | Lanes | Question |
| --- | --- | --- | --- | --- | --- |
| `Fictional registration service` | group | **UNMAPPED** | 1 | uiowa_rfq_18649_incident_learning | Which canonical group does 'Fictional registration service' denote, if any? |
| `Fictional sign-in service` | group | **UNMAPPED** | 1 | uiowa_rfq_18649_incident_learning | Which canonical group does 'Fictional sign-in service' denote, if any? |
| `Synthetic Identity Request Router` | group | **UNMAPPED** | 1 | uiowa_rfq_18649_handoff | Which canonical group does 'Synthetic Identity Request Router' denote, if any? |
| `Synthetic Student Self-Service` | group | **UNMAPPED** | 1 | uiowa_rfq_18649_handoff | Which canonical group does 'Synthetic Student Self-Service' denote, if any? |
| `synthetic-registration` | group | **UNRESOLVED_CONCEPT** | 8 | uiowa_rfq_18649_delivery_metrics | Which of ESS/RIS/IAM owns the fictional 'synthetic-registration' service? |
| `AI use and governance` | area | **UNMAPPED** | 4 | uiowa_rfq_18649_exec_summary | Which canonical area does 'AI use and governance' denote, if any? |
| `ALL` | area | **SCOPE_VALUE_AREA** | 2 | uiowa_rfq_18649_qa_refusal_contract |  |
| `Access / IAM` | area | **UNMAPPED** | 2 | uiowa_rfq_18649_workbench | Which canonical area does 'Access / IAM' denote, if any? |
| `Access / IAM / software delivery` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Access / IAM / software delivery' denote, if any? |
| `Access / data governance` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Access / data governance' denote, if any? |
| `Accessibility / procurement / governance` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Accessibility / procurement / governance' denote, if any? |
| `Accessibility / software delivery` | area | **UNMAPPED** | 2 | uiowa_rfq_18649_workbench | Which canonical area does 'Accessibility / software delivery' denote, if any? |
| `Data classification` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Data classification' denote, if any? |
| `Data classification / software delivery` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Data classification / software delivery' denote, if any? |
| `Data readiness` | area | **UNMAPPED** | 6 | uiowa_rfq_18649_exec_summary | Which canonical area does 'Data readiness' denote, if any? |
| `Data use / AI readiness` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Data use / AI readiness' denote, if any? |
| `Deployment / operations` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Deployment / operations' denote, if any? |
| `Deployment / operations / records` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Deployment / operations / records' denote, if any? |
| `ESS:DEP` | area | **CROSS_SLOT_PACKED** | 2 | uiowa_rfq_18649_qa_refusal_contract | Should a packed group:area value be joined as a group, as an area, or as a composite key? |
| `ESS:SD` | area | **CROSS_SLOT_PACKED** | 6 | uiowa_rfq_18649_qa_refusal_contract | Should a packed group:area value be joined as a group, as an area, or as a composite key? |
| `ESS:SEC` | area | **CROSS_SLOT_PACKED** | 2 | uiowa_rfq_18649_qa_refusal_contract | Should a packed group:area value be joined as a group, as an area, or as a composite key? |
| `IAM:AI` | area | **CROSS_SLOT_PACKED** | 1 | uiowa_rfq_18649_qa_refusal_contract | Should a packed group:area value be joined as a group, as an area, or as a composite key? |
| `Incident response` | area | **UNMAPPED** | 3 | uiowa_rfq_18649_exec_summary | Which canonical area does 'Incident response' denote, if any? |
| `RIS:DEP` | area | **CROSS_SLOT_PACKED** | 5 | uiowa_rfq_18649_qa_refusal_contract | Should a packed group:area value be joined as a group, as an area, or as a composite key? |
| `Records handling / delivery evidence` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Records handling / delivery evidence' denote, if any? |
| `Records handling / operations` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Records handling / operations' denote, if any? |
| `Records handling / software delivery` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Records handling / software delivery' denote, if any? |
| `Service delivery` | area | **UNMAPPED** | 2 | uiowa_rfq_18649_exec_summary | Which canonical area does 'Service delivery' denote, if any? |
| `Software delivery / deployment` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Software delivery / deployment' denote, if any? |
| `Software delivery / deployment / security` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Software delivery / deployment / security' denote, if any? |
| `Software delivery / governance` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Software delivery / governance' denote, if any? |
| `Software delivery / security` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Software delivery / security' denote, if any? |
| `access_review` | area | **UNMAPPED** | 2 | uiowa_rfq_18649_readout_deck | Which canonical area does 'access_review' denote, if any? |
| `ai_readiness|deployment_operations` | area | **COMPOUND** | 4 | uiowa_rfq_18649_workbench | Should a cell naming several areas count once, or once per area? |
| `ai_readiness|security` | area | **COMPOUND** | 4 | uiowa_rfq_18649_workbench | Should a cell naming several areas count once, or once per area? |
| `ai_readiness|security|deployment_operations` | area | **COMPOUND** | 1 | uiowa_rfq_18649_workbench | Should a cell naming several areas count once, or once per area? |
| `ai_readiness|software_development` | area | **COMPOUND** | 3 | uiowa_rfq_18649_workbench | Should a cell naming several areas count once, or once per area? |
| `change_management` | area | **UNMAPPED** | 4 | uiowa_rfq_18649_readout_deck | Which canonical area does 'change_management' denote, if any? |
| `delivery` | area | **UNMAPPED** | 5 | uiowa_rfq_18649_prioritization | Which canonical area does 'delivery' denote, if any? |
| `monitoring` | area | **UNMAPPED** | 2 | uiowa_rfq_18649_readout_deck | Which canonical area does 'monitoring' denote, if any? |
| `operational_reliability` | area | **UNRESOLVED_CONCEPT** | 3 | uiowa_rfq_18649_outcome_measurement | Is operational_reliability intended as the DEP practice area, or as an outcome measured across areas? Joining on it is unsafe until the owning lane answers. |
| `quality` | area | **UNMAPPED** | 5 | uiowa_rfq_18649_prioritization | Which canonical area does 'quality' denote, if any? |
| `security|deployment_operations` | area | **COMPOUND** | 23 | uiowa_rfq_18649_workbench | Should a cell naming several areas count once, or once per area? |
| `security|software_development` | area | **COMPOUND** | 2 | uiowa_rfq_18649_workbench | Should a cell naming several areas count once, or once per area? |
| `service_recovery` | area | **UNMAPPED** | 2 | uiowa_rfq_18649_readout_deck | Which canonical area does 'service_recovery' denote, if any? |
| `software` | area | **AMBIGUOUS** | 15 | uiowa_rfq_18649_question_cards, uiowa_rfq_18649_workshare | Is 'software' here software_development or software_delivery? |
| `software_development|security` | area | **COMPOUND** | 10 | uiowa_rfq_18649_workbench | Should a cell naming several areas count once, or once per area? |

## 3. Declared mappings

`EXACT_VARIANT` is mechanical — same words, different case or separator — and can be accepted without argument. `DECLARED_JUDGMENT` is this package's reading and a reviewer may reject it; the original term is retained either way.

| Term | Slot | → | Kind | Rows | Basis |
| --- | --- | --- | --- | --- | --- |
| `ALL` | group | `CROSS_GROUP` | SCOPE_VALUE | 1 | names every group rather than one |
| `CROSS` | group | `CROSS_GROUP` | SCOPE_VALUE | 12 | names a cross-group scope; not a mis-spelling of a group |
| `ESS` | group | `ESS` | EXACT_VARIANT | 319 | canonical form |
| `ESS-FICTIONAL` | group | `ESS` | DECLARED_JUDGMENT | 4 | origin-qualified spelling of the same fictional group |
| `ESS-SYN` | group | `ESS` | DECLARED_JUDGMENT | 13 | origin-qualified spelling of the same fictional group; declared explicitly because same-looking values from different origins must not join by resemblance |
| `IAM` | group | `IAM` | EXACT_VARIANT | 265 | canonical form |
| `IAM-FICTIONAL` | group | `IAM` | DECLARED_JUDGMENT | 4 | origin-qualified spelling |
| `RIS` | group | `RIS` | EXACT_VARIANT | 235 | canonical form |
| `RIS-FICTIONAL` | group | `RIS` | DECLARED_JUDGMENT | 2 | origin-qualified spelling |
| `Shared` | group | `CROSS_GROUP` | SCOPE_VALUE | 1 | names a shared/cross-group scope |
| `iam-directory` | group | `IAM` | GRANULARITY_MISMATCH | 2 | a service inside the IAM group; rows about one service are not interchangeable with rows about the group |
| `iam-group-service` | group | `IAM` | GRANULARITY_MISMATCH | 1 | a service inside the IAM group; rows about one service are not interchangeable with rows about the group |
| `iam-sso` | group | `IAM` | GRANULARITY_MISMATCH | 1 | a service inside the IAM group; rows about one service are not interchangeable with rows about the group |
| `AI` | area | `AI` | EXACT_VARIANT | 125 | canonical form |
| `AI readiness` | area | `AI` | EXACT_VARIANT | 6 | same words, prose form |
| `DEP` | area | `DEP` | EXACT_VARIANT | 112 | canonical form |
| `Deployment and operations` | area | `DEP` | EXACT_VARIANT | 6 | same words, prose form |
| `OPS` | area | `DEP` | DECLARED_JUDGMENT | 3 | read as an abbreviation of operations, i.e. the deployment and operations area; no other lane in the tree uses OPS |
| `SD` | area | `SD` | EXACT_VARIANT | 121 | canonical form |
| `SDLC` | area | `SD` | DECLARED_JUDGMENT | 3 | software development life cycle, read as the software development area; no other lane in the tree uses SDLC |
| `SEC` | area | `SEC` | EXACT_VARIANT | 128 | canonical form |
| `Security` | area | `SEC` | EXACT_VARIANT | 6 | same word, title case |
| `Software development` | area | `SD` | EXACT_VARIANT | 6 | same words, title case |
| `ai_readiness` | area | `AI` | EXACT_VARIANT | 32 | same words, snake case |
| `deployment` | area | `DEP` | DECLARED_JUDGMENT | 20 | the shorter term is read as the deployment half of deployment/operations; a lane using it may or may not intend operations as well |
| `deployment_operations` | area | `DEP` | EXACT_VARIANT | 15 | same words, snake case |
| `security` | area | `SEC` | EXACT_VARIANT | 55 | same word, lower case |
| `software_delivery` | area | `SD` | DECLARED_JUDGMENT | 7 | read as the same area the RFQ calls software development; 'delivery' and 'development' are not identical words and a lane may mean a narrower thing |
| `software_development` | area | `SD` | EXACT_VARIANT | 21 | same words, snake case |

## 4. Terms that resemble each other but do not resolve together

- **`ai…`** (area): `AI`, `AI readiness`, `AI use and governance`, `ai_readiness`, `ai_readiness|deployment_operations`, `ai_readiness|security`, `ai_readiness|security|deployment_operations`, `ai_readiness|software_development` → `AI`, `None`. these terms begin with the same word but do not all resolve to the same canonical value, so a join on the raw column would merge rows that this crosswalk keeps separate.
- **`deployment…`** (area): `Deployment / operations`, `Deployment / operations / records`, `Deployment and operations`, `deployment`, `deployment_operations` → `DEP`, `None`. these terms begin with the same word but do not all resolve to the same canonical value, so a join on the raw column would merge rows that this crosswalk keeps separate.
- **`software…`** (area): `Software delivery / deployment`, `Software delivery / deployment / security`, `Software delivery / governance`, `Software delivery / security`, `Software development`, `software`, `software_delivery`, `software_development`, `software_development|security` → `None`, `SD`. these terms begin with the same word but do not all resolve to the same canonical value, so a join on the raw column would merge rows that this crosswalk keeps separate.

## 4b. Pattern: slash joined prose terms

**16 terms / 18 rows**, all in `uiowa_rfq_18649_workbench`.

These terms use a different taxonomy, not a different spelling of the same one. They name concepts outside the four assessment areas entirely - data classification, records handling, accessibility, procurement, governance - so no canonical assessment area applies.

**Not split.** " / " does not carry one meaning in this column. In "Deployment / operations" it joins two words of a single concept; in "Access / IAM / software delivery" it appears to join separate concepts. Splitting on it would invent an "Access" area and destroy "Deployment and operations". This package does not split on an ambiguous separator.

*Question for that lane:* Is this column the four-area assessment taxonomy under other names, or a separate policy-topic taxonomy that should not be joined to it at all?

## 4c. Key names that do not mean one thing

- **`area`** — the key 'area' carries value sets with no overlap between at least two lanes, so the key name alone does not establish what the column holds.
    - `uiowa_rfq_18649_ai_use_inventory`: `AI`
    - `uiowa_rfq_18649_economics_resource_adapters`: `AI`, `DEP`, `SD`, `SEC`
    - `uiowa_rfq_18649_exec_summary`: `AI use and governance`, `Data readiness`, `Incident response`, `Service delivery`
    - `uiowa_rfq_18649_intake_rehearsal`: `AI`, `DEP`, `SD`, `SEC`
    - `uiowa_rfq_18649_labeling_integrity`: `deployment`, `software_delivery`
    - `uiowa_rfq_18649_milestone_packets`: `deployment`, `software_delivery`
    - `uiowa_rfq_18649_output_agreement`: `AI`, `DEP`, `SD`, `SEC`
    - `uiowa_rfq_18649_prioritization`: `AI`, `DEP`, `SD`, `SEC`
    - `uiowa_rfq_18649_qa_refusal_contract`: `ALL`, `DEP`, `ESS:DEP`, `ESS:SD`, `ESS:SEC`, `IAM:AI`, `RIS:DEP`, `SD`
    - `uiowa_rfq_18649_rating_model`: `deployment_operations`, `security`, `software_development`
    - `uiowa_rfq_18649_readout_deck`: `access_review`, `change_management`, `monitoring`, `service_recovery`
    - `uiowa_rfq_18649_report_structure`: `AI`, `DEP`, `SD`, `SEC`
    - `uiowa_rfq_18649_report_visuals`: `AI`, `OPS`, `SDLC`, `SEC`
    - `uiowa_rfq_18649_synthetic_collection`: `ai_readiness`, `deployment_operations`, `security`, `software_development`
    - `uiowa_rfq_18649_workshare`: `AI`, `DEP`, `SD`, `SEC`
- **`assessment_area`** — the key 'assessment_area' carries value sets with no overlap between at least two lanes, so the key name alone does not establish what the column holds.
    - `uiowa_rfq_18649_outcome_measurement`: `operational_reliability`, `security`, `software_delivery`
    - `uiowa_rfq_18649_question_cards`: `ai_readiness`, `deployment`, `security`, `software`
    - `uiowa_rfq_18649_synthetic_collection`: `ai_readiness`, `deployment_operations`, `security`, `software_development`
    - `uiowa_rfq_18649_workbench`: `Access / IAM`, `Access / IAM / software delivery`, `Access / data governance`, `Accessibility / procurement / governance`, `Accessibility / software delivery`, `Data classification`, `Data classification / software delivery`, `Data use / AI readiness`
- **`group`** — the key 'group' carries value sets with no overlap between at least two lanes, so the key name alone does not establish what the column holds.
    - `uiowa_rfq_18649_ai_opportunity_portfolio`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_ai_use_inventory`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_doc_usability`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_economics_resource_adapters`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_handoff`: `ESS`, `IAM`
    - `uiowa_rfq_18649_intake_rehearsal`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_milestone_packets`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_output_agreement`: `CROSS`, `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_prioritization`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_qa_refusal_contract`: `ALL`, `ESS`, `RIS`
    - `uiowa_rfq_18649_question_cards`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_readout_deck`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_report_structure`: `CROSS`, `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_report_visuals`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_workbench`: `ESS-SYN`
    - `uiowa_rfq_18649_workshare`: `ESS`, `IAM`, `RIS`
- **`service`** — the key 'service' carries value sets with no overlap between at least two lanes, so the key name alone does not establish what the column holds.
    - `uiowa_rfq_18649_build_board`: `ESS`, `IAM`, `RIS`, `Shared`
    - `uiowa_rfq_18649_contractor_transition`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_deadline_continuity`: `RIS`
    - `uiowa_rfq_18649_delivery_metrics`: `synthetic-registration`
    - `uiowa_rfq_18649_handoff`: `Synthetic Identity Request Router`, `Synthetic Student Self-Service`
    - `uiowa_rfq_18649_incident_learning`: `Fictional registration service`, `Fictional sign-in service`
    - `uiowa_rfq_18649_intake_rehearsal`: `iam-directory`, `iam-group-service`, `iam-sso`
    - `uiowa_rfq_18649_labeling_integrity`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_rating_model`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_security_event_review`: `ESS-FICTIONAL`, `IAM-FICTIONAL`, `RIS-FICTIONAL`
    - `uiowa_rfq_18649_synthetic_collection`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_test_data_readiness`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_traceability`: `ESS`, `IAM`, `RIS`
    - `uiowa_rfq_18649_traceability_rehearsal`: `ESS`, `IAM`, `RIS`

## 5. What this package will not do

- **No fuzzy matching of any kind.** An undeclared term is `UNMAPPED`, never assigned to the nearest-looking canonical value.
- **`operational_reliability` is not mapped to `DEP`.** Reliability in operation is an outcome; deployment and operations is a practice area. Equating them would fabricate agreement between lanes that may be measuring different things.
- **Compound cells are not split.** Splitting `ai_readiness|security` into two rows assumes the separator means "and" and double-counts the row.
- **No lane is scored, ranked, corrected or certified.** No file outside this package's own output directory is written.
