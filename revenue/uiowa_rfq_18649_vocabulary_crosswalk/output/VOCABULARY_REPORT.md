# RFQ-18649 group and assessment-area vocabulary reconciliation

> **VOCABULARY RECONCILIATION over synthetic RFQ-18649 fixtures. Terms are reported as observed; mappings are declared, never guessed. Nothing here is a University of Iowa finding, and no lane is scored, ranked or certified.**

325 observations across 55 files in 21 lanes. **53 distinct terms**: 26 resolve to a canonical value, **27 need a decision from the lane that uses them.**

## 1. Why this matters

A check written against one lane's spelling silently mis-compares another's. This is not hypothetical: a UIOWA-130 check that said `deployment` where a lane says `deployment_operations` reported that lane as covering 9 of 12 cells when it covers all 12. The check manufactured a gap in another seat's work.

## 2. Terms needing a decision

These are **not** mapped. Each names the lane that must answer.

| Term | Slot | Kind | Rows | Lanes | Question |
| --- | --- | --- | --- | --- | --- |
| `synthetic-registration` | group | **UNRESOLVED_CONCEPT** | 8 | uiowa_rfq_18649_delivery_metrics | Which of ESS/RIS/IAM owns the fictional 'synthetic-registration' service? |
| `Access / IAM` | area | **UNMAPPED** | 2 | uiowa_rfq_18649_workbench | Which canonical area does 'Access / IAM' denote, if any? |
| `Access / IAM / software delivery` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Access / IAM / software delivery' denote, if any? |
| `Access / data governance` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Access / data governance' denote, if any? |
| `Accessibility / procurement / governance` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Accessibility / procurement / governance' denote, if any? |
| `Accessibility / software delivery` | area | **UNMAPPED** | 2 | uiowa_rfq_18649_workbench | Which canonical area does 'Accessibility / software delivery' denote, if any? |
| `Data classification` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Data classification' denote, if any? |
| `Data classification / software delivery` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Data classification / software delivery' denote, if any? |
| `Data use / AI readiness` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Data use / AI readiness' denote, if any? |
| `Deployment / operations` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Deployment / operations' denote, if any? |
| `Deployment / operations / records` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Deployment / operations / records' denote, if any? |
| `Records handling / delivery evidence` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Records handling / delivery evidence' denote, if any? |
| `Records handling / operations` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Records handling / operations' denote, if any? |
| `Records handling / software delivery` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Records handling / software delivery' denote, if any? |
| `Software delivery / deployment` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Software delivery / deployment' denote, if any? |
| `Software delivery / deployment / security` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Software delivery / deployment / security' denote, if any? |
| `Software delivery / governance` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Software delivery / governance' denote, if any? |
| `Software delivery / security` | area | **UNMAPPED** | 1 | uiowa_rfq_18649_workbench | Which canonical area does 'Software delivery / security' denote, if any? |
| `ai_readiness|deployment_operations` | area | **COMPOUND** | 4 | uiowa_rfq_18649_workbench | Should a cell naming several areas count once, or once per area? |
| `ai_readiness|security` | area | **COMPOUND** | 4 | uiowa_rfq_18649_workbench | Should a cell naming several areas count once, or once per area? |
| `ai_readiness|security|deployment_operations` | area | **COMPOUND** | 1 | uiowa_rfq_18649_workbench | Should a cell naming several areas count once, or once per area? |
| `ai_readiness|software_development` | area | **COMPOUND** | 3 | uiowa_rfq_18649_workbench | Should a cell naming several areas count once, or once per area? |
| `operational_reliability` | area | **UNRESOLVED_CONCEPT** | 3 | uiowa_rfq_18649_outcome_measurement | Is operational_reliability intended as the DEP practice area, or as an outcome measured across areas? Joining on it is unsafe until the owning lane answers. |
| `security|deployment_operations` | area | **COMPOUND** | 23 | uiowa_rfq_18649_workbench | Should a cell naming several areas count once, or once per area? |
| `security|software_development` | area | **COMPOUND** | 2 | uiowa_rfq_18649_workbench | Should a cell naming several areas count once, or once per area? |
| `software` | area | **AMBIGUOUS** | 3 | uiowa_rfq_18649_question_cards | Is 'software' here software_development or software_delivery? |
| `software_development|security` | area | **COMPOUND** | 10 | uiowa_rfq_18649_workbench | Should a cell naming several areas count once, or once per area? |

## 3. Declared mappings

`EXACT_VARIANT` is mechanical — same words, different case or separator — and can be accepted without argument. `DECLARED_JUDGMENT` is this package's reading and a reviewer may reject it; the original term is retained either way.

| Term | Slot | → | Kind | Rows | Basis |
| --- | --- | --- | --- | --- | --- |
| `CROSS` | group | `CROSS_GROUP` | SCOPE_VALUE | 12 | names a cross-group scope; not a mis-spelling of a group |
| `ESS` | group | `ESS` | EXACT_VARIANT | 151 | canonical form |
| `ESS-FICTIONAL` | group | `ESS` | DECLARED_JUDGMENT | 2 | origin-qualified spelling of the same fictional group |
| `ESS-SYN` | group | `ESS` | DECLARED_JUDGMENT | 13 | origin-qualified spelling of the same fictional group; declared explicitly because same-looking values from different origins must not join by resemblance |
| `IAM` | group | `IAM` | EXACT_VARIANT | 132 | canonical form |
| `IAM-FICTIONAL` | group | `IAM` | DECLARED_JUDGMENT | 2 | origin-qualified spelling |
| `RIS` | group | `RIS` | EXACT_VARIANT | 106 | canonical form |
| `RIS-FICTIONAL` | group | `RIS` | DECLARED_JUDGMENT | 1 | origin-qualified spelling |
| `Shared` | group | `CROSS_GROUP` | SCOPE_VALUE | 1 | names a shared/cross-group scope |
| `iam-directory` | group | `IAM` | GRANULARITY_MISMATCH | 2 | a service inside the IAM group; rows about one service are not interchangeable with rows about the group |
| `iam-group-service` | group | `IAM` | GRANULARITY_MISMATCH | 1 | a service inside the IAM group; rows about one service are not interchangeable with rows about the group |
| `iam-sso` | group | `IAM` | GRANULARITY_MISMATCH | 1 | a service inside the IAM group; rows about one service are not interchangeable with rows about the group |
| `AI` | area | `AI` | EXACT_VARIANT | 70 | canonical form |
| `AI readiness` | area | `AI` | EXACT_VARIANT | 3 | same words, prose form |
| `DEP` | area | `DEP` | EXACT_VARIANT | 68 | canonical form |
| `Deployment and operations` | area | `DEP` | EXACT_VARIANT | 3 | same words, prose form |
| `SD` | area | `SD` | EXACT_VARIANT | 72 | canonical form |
| `SEC` | area | `SEC` | EXACT_VARIANT | 80 | canonical form |
| `Security` | area | `SEC` | EXACT_VARIANT | 3 | same word, title case |
| `Software development` | area | `SD` | EXACT_VARIANT | 3 | same words, title case |
| `ai_readiness` | area | `AI` | EXACT_VARIANT | 15 | same words, snake case |
| `deployment` | area | `DEP` | DECLARED_JUDGMENT | 4 | the shorter term is read as the deployment half of deployment/operations; a lane using it may or may not intend operations as well |
| `deployment_operations` | area | `DEP` | EXACT_VARIANT | 3 | same words, snake case |
| `security` | area | `SEC` | EXACT_VARIANT | 8 | same word, lower case |
| `software_delivery` | area | `SD` | DECLARED_JUDGMENT | 4 | read as the same area the RFQ calls software development; 'delivery' and 'development' are not identical words and a lane may mean a narrower thing |
| `software_development` | area | `SD` | EXACT_VARIANT | 3 | same words, snake case |

## 4. Terms that resemble each other but do not resolve together

- **`ai…`** (area): `AI`, `AI readiness`, `ai_readiness`, `ai_readiness|deployment_operations`, `ai_readiness|security`, `ai_readiness|security|deployment_operations`, `ai_readiness|software_development` → `AI`, `None`. these terms begin with the same word but do not all resolve to the same canonical value, so a join on the raw column would merge rows that this crosswalk keeps separate.
- **`deployment…`** (area): `Deployment / operations`, `Deployment / operations / records`, `Deployment and operations`, `deployment`, `deployment_operations` → `DEP`, `None`. these terms begin with the same word but do not all resolve to the same canonical value, so a join on the raw column would merge rows that this crosswalk keeps separate.
- **`software…`** (area): `Software delivery / deployment`, `Software delivery / deployment / security`, `Software delivery / governance`, `Software delivery / security`, `Software development`, `software`, `software_delivery`, `software_development`, `software_development|security` → `None`, `SD`. these terms begin with the same word but do not all resolve to the same canonical value, so a join on the raw column would merge rows that this crosswalk keeps separate.

## 4b. Pattern: slash joined prose terms

**16 terms / 18 rows**, all in `uiowa_rfq_18649_workbench`.

These terms use a different taxonomy, not a different spelling of the same one. They name concepts outside the four assessment areas entirely - data classification, records handling, accessibility, procurement, governance - so no canonical assessment area applies.

**Not split.** " / " does not carry one meaning in this column. In "Deployment / operations" it joins two words of a single concept; in "Access / IAM / software delivery" it appears to join separate concepts. Splitting on it would invent an "Access" area and destroy "Deployment and operations". This package does not split on an ambiguous separator.

*Question for that lane:* Is this column the four-area assessment taxonomy under other names, or a separate policy-topic taxonomy that should not be joined to it at all?

## 5. What this package will not do

- **No fuzzy matching of any kind.** An undeclared term is `UNMAPPED`, never assigned to the nearest-looking canonical value.
- **`operational_reliability` is not mapped to `DEP`.** Reliability in operation is an outcome; deployment and operations is a practice area. Equating them would fabricate agreement between lanes that may be measuring different things.
- **Compound cells are not split.** Splitting `ai_readiness|security` into two rows assumes the separator means "and" and double-counts the row.
- **No lane is scored, ranked, corrected or certified.** No file outside this package's own output directory is written.
