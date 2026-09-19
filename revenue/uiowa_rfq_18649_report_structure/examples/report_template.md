# University of Iowa RFQ 18649 - Assessment Report

**Status:** `<DRAFT | FINAL>`  
**Prepared by:** `<assessment team>`  
**Reporting period:** `<start>` to `<end>`  
**Report structure:** `uiowa-rfq-18649-report-structure-v1`

> **EDITABLE TEMPLATE.** Replace every `<...>` placeholder. Do not delete a section to hide a gap: a section with nothing to report says so and cites the open question instead. Missing evidence stays `UNKNOWN` - it never becomes a zero, a pass, or a maturity score.

## Scope boundary

This assessment describes current practice against reference frameworks used as interview and artifact prompts. It is not a formal audit and issues no compliance determination, certification or attestation. It assesses organizational practice; no statement rates, ranks or evaluates a named individual. It describes capabilities the University may need; no vendor selection or product purchase is recommended.

- **Out of scope - Formal audit or compliance opinion.** This engagement produces an assessment of current practice against reference frameworks used as prompts. It does not issue an audit opinion, a compliance determination, a certification, or an attestation.
- **Out of scope - Employee or individual performance evaluation.** Findings describe organizational practice, systems and process. No statement rates, ranks or evaluates a named person or role holder.
- **Out of scope - Vendor or product procurement recommendation.** Recommendations describe capabilities and decisions the University would need to make. Selecting, endorsing or pricing a specific product or vendor is outside this engagement.

---

## 1. Executive Summary

*Audience: leadership. Covers: RFQ-E01.*

**Purpose.** Answer, in one page, what was assessed, what holds up, what does not, and what is proposed next.

**Inputs this section requires**

| dataset | fields consumed | why |
|---|---|---|
| finding_matrix | `finding_id`, `group`, `area`, `status`, `confidence` | Every summary statement names the finding_id it rests on. |
| recommendation_register | `recommendation_id`, `statement`, `horizon`, `finding_refs` | Proposed next steps, each already linked to findings. |
| theme_register | `theme_id`, `statement`, `finding_refs` | The small number of patterns leadership needs before the detail. |

**Traceability rule.** Every sentence that asserts a condition carries at least one finding_id or theme_id.

**Missing-evidence rule.** Areas with status UNKNOWN are named here as unassessed, never omitted to make coverage look complete.

**Write this section by answering:**

- What did we actually look at, and over what window?
- Which two or three conditions most affect delivery and risk?
- What is proposed in the first 90 days, and what does it depend on?
- What could we not determine, and what would settle it?

> `<section content here>`

---

## 2. Engagement Scope and Assessment Areas

*Audience: all. Covers: RFQ-E02.*

**Purpose.** State exactly which groups, services and assessment areas were in scope, and which were not.

**Inputs this section requires**

| dataset | fields consumed | why |
|---|---|---|
| service_responsibility | `scope`, `public_responsibility`, `visible_interfaces`, `source_ids` | Scope statements grounded in the documented responsibilities of each group. |
| finding_matrix | `group`, `area`, `status` | The assessed cell set; anything outside it is declared out of scope. |

**Traceability rule.** Each in-scope service traces to a source_ids entry confirming the responsibility boundary.

**Missing-evidence rule.** A service in scope but not reached is listed as in-scope/not-assessed, not quietly dropped.

**Write this section by answering:**

- Which applications and shared platforms are in scope for each group?
- Which assessment areas were covered for each group?
- What was explicitly excluded, and why?

> `<section content here>`

---

## 3. Methodology

*Audience: all. Covers: RFQ-E03.*

**Purpose.** Describe how evidence was gathered and how findings were formed, so a reader can judge the work.

**Inputs this section requires**

| dataset | fields consumed | why |
|---|---|---|
| framework_crosswalk | `framework`, `version`, `locator`, `proposed_assessment_use`, `adaptation_limit` | Frameworks used as interview and artifact prompts, with each one's stated adaptation limit. |
| evidence_register | `source_type`, `captured_at`, `represented_period` | The actual source mix and collection window, reported rather than asserted. |

**Traceability rule.** Every framework reference cites framework + version + locator.

**Missing-evidence rule.** Where a planned collection step did not happen, the method section says so.

**Write this section by answering:**

- What was collected, from whom, over what period?
- How were interview statements separated from artifact evidence?
- How were framework references used as prompts rather than as criteria?
- What is the declared freshness window for volatile evidence?

> `<section content here>`

---

## 4. Evidence Standard, Confidence and Limitations

*Audience: all. Covers: RFQ-E04.*

**Purpose.** Define the confidence vocabulary and the limits of what this engagement can support.

**Inputs this section requires**

| dataset | fields consumed | why |
|---|---|---|
| evidence_register | `directness`, `recency`, `representativeness`, `corroboration`, `evidence_state`, `confidence`, `scope_limit` | The five confidence dimensions, reported separately and never averaged. |

**Traceability rule.** Each confidence class shown here matches the definition in the evidence method the register was built against.

**Missing-evidence rule.** NOT_EVIDENCED and UNRESOLVED are defined as distinct from a negative finding.

**Write this section by answering:**

- What does each confidence class mean in this report?
- Which limits apply to the whole engagement rather than a single finding?
- Where did contradictory evidence remain unresolved?

> `<section content here>`

---

## 5. Peer and Published-Practice Context

*Audience: leadership. Covers: RFQ-E05.*

**Purpose.** Offer external reference points that help interpret current practice, with comparability stated.

**Inputs this section requires**

| dataset | fields consumed | why |
|---|---|---|
| peer_context_table | `peer`, `service_or_context`, `metric_or_measure`, `value`, `period_or_window`, `denominator_or_scope`, `measure_class`, `comparison_status`, `comparability_notes`, `source_url`, `accessed_date` | Each peer reference carries its own comparability status and the denominator it was measured against. |

**Traceability rule.** Every peer row displays comparison_status and comparability_notes next to the value.

**Missing-evidence rule.** A published process target is labeled as intent, not as attained performance.

**Write this section by answering:**

- What do comparable institutions publish about this practice?
- What would have to be normalized before these numbers could be compared?
- Which references are context only and cannot support a comparison?

> `<section content here>`

---

## 6. Current-State Matrix

*Audience: all. Covers: RFQ-E06.*

**Purpose.** Show all twelve group-by-area cells at once, including the ones that were not assessed.

**Inputs this section requires**

| dataset | fields consumed | why |
|---|---|---|
| finding_matrix | `finding_id`, `group`, `area`, `status`, `confidence`, `statement`, `scope_limit` | The matrix itself; one row per assessed cell. |

**Traceability rule.** Each populated cell shows its finding_id.

**Missing-evidence rule.** A cell with status UNKNOWN renders as UNKNOWN - not assessed, is visually distinct from a weak result, and is excluded from every count of assessed cells.

**Write this section by answering:**

- Which cells are supported, partial, in conflict, or unassessed?
- Where does the evidence disagree with itself?

> `<section content here>`

---

## 7.1. Group Findings - Enterprise Systems and Services (ESS)

*Audience: practitioner. Covers: RFQ-E06.*

**Purpose.** Narrative findings for ESS across the four assessment areas.

**Inputs this section requires**

| dataset | fields consumed | why |
|---|---|---|
| finding_matrix | `finding_id`, `group`, `area`, `status`, `confidence`, `statement`, `scope_limit`, `follow_up_question` | The ESS rows of the matrix. |
| evidence_register | `evidence_id`, `observation_id`, `finding_id`, `claim`, `scope_limit`, `source_ref` | The observations behind each ESS finding. |

**Traceability rule.** Every narrative claim names its finding_id; every finding names its supporting evidence_ids.

**Missing-evidence rule.** Where ESS evidence covers one service only, the narrative says so instead of generalizing to the group.

**Write this section by answering:**

- What holds up across ESS, and on what evidence?
- Where is the evidence single-service rather than group-wide?
- What follow-up would resolve each partial or conflicting cell?

> `<section content here>`

---

## 7.2. Group Findings - Research Information Systems (RIS)

*Audience: practitioner. Covers: RFQ-E06.*

**Purpose.** Narrative findings for RIS across the four assessment areas.

**Inputs this section requires**

| dataset | fields consumed | why |
|---|---|---|
| finding_matrix | `finding_id`, `group`, `area`, `status`, `confidence`, `statement`, `scope_limit`, `follow_up_question` | The RIS rows of the matrix. |
| evidence_register | `evidence_id`, `observation_id`, `finding_id`, `claim`, `scope_limit`, `source_ref` | The observations behind each RIS finding. |

**Traceability rule.** Every narrative claim names its finding_id; every finding names its supporting evidence_ids.

**Missing-evidence rule.** A policy that documents intent is not reported as demonstrated implementation.

**Write this section by answering:**

- What holds up across RIS, and on what evidence?
- Which RIS claims rest on policy intent rather than observed practice?

> `<section content here>`

---

## 7.3. Group Findings - Identity and Access Management (IAM)

*Audience: practitioner. Covers: RFQ-E06.*

**Purpose.** Narrative findings for IAM across the four assessment areas.

**Inputs this section requires**

| dataset | fields consumed | why |
|---|---|---|
| finding_matrix | `finding_id`, `group`, `area`, `status`, `confidence`, `statement`, `scope_limit`, `follow_up_question` | The IAM rows of the matrix. |
| evidence_register | `evidence_id`, `observation_id`, `finding_id`, `claim`, `scope_limit`, `source_ref` | The observations behind each IAM finding. |

**Traceability rule.** Every narrative claim names its finding_id; every finding names its supporting evidence_ids.

**Missing-evidence rule.** An absent access-review record is reported as no evidence observed, not as a failed control.

**Write this section by answering:**

- What holds up across IAM, and on what evidence?
- Where is an absence of records being read as an absence of practice?

> `<section content here>`

---

## 8. Cross-Cutting Themes

*Audience: leadership. Covers: RFQ-E07.*

**Purpose.** Name the patterns that span groups or areas without erasing the findings underneath them.

**Inputs this section requires**

| dataset | fields consumed | why |
|---|---|---|
| theme_register | `theme_id`, `statement`, `finding_refs`, `groups_spanned`, `areas_spanned`, `counter_evidence`, `scope_limit` | Each theme cites the exact findings it spans and any evidence that cuts against it. |
| finding_matrix | `finding_id`, `group`, `area`, `status` | Used to confirm every cited finding exists and that the span claim matches the matrix. |

**Traceability rule.** A theme cites at least two finding_ids from at least two distinct groups or areas.

**Missing-evidence rule.** A theme that would require an unassessed cell to hold is stated with that gap named.

**Write this section by answering:**

- Which conditions recur across groups rather than being local?
- What evidence cuts against each theme?
- Which findings does this theme deliberately not cover?

> `<section content here>`

---

## 9. Recommendations by Group and Department

*Audience: leadership. Covers: RFQ-E08.*

**Purpose.** Proposed actions addressed to a named owner group, each tied to the findings that motivate it.

**Inputs this section requires**

| dataset | fields consumed | why |
|---|---|---|
| recommendation_register | `recommendation_id`, `group`, `area`, `finding_refs`, `statement`, `rationale`, `resource_note`, `dependency` | The recommendation records, each carrying its own finding links and resource note. |
| finding_matrix | `finding_id`, `status`, `confidence` | Used to show the strength of the evidence a recommendation rests on. |

**Traceability rule.** Every recommendation cites at least one finding_id and does not inherit that finding's confidence automatically.

**Missing-evidence rule.** A recommendation motivated by an unresolved question is labeled as investigate-first rather than implement.

**Write this section by answering:**

- What should this group do, and which finding motivates it?
- What capability is needed - stated as a capability, not a product?
- What does this action depend on before it can start?

> `<section content here>`

---

## 10. Prioritization and Phasing

*Audience: leadership. Covers: RFQ-E09.*

**Purpose.** Sequence the recommendations across the 0-90 / 90-180 / 180+ horizons with the assumptions visible.

**Inputs this section requires**

| dataset | fields consumed | why |
|---|---|---|
| recommendation_register | `recommendation_id`, `horizon`, `dependency`, `resource_note`, `finding_refs` | Horizon and dependency per recommendation, with the resource assumption shown rather than computed away. |

**Traceability rule.** Every phased item links back to a recommendation_id, and no item appears in a phase earlier than its dependency.

**Missing-evidence rule.** A recommendation with horizon UNKNOWN is listed in an unsequenced bucket with the missing input named, never defaulted into 180+.

**Write this section by answering:**

- What must happen first because something else depends on it?
- Which items are sequenced by evidence rather than by preference?
- Which estimates are missing, and what would supply them?

> `<section content here>`

---

## A. Appendix A - Supporting Evidence

*Audience: practitioner. Covers: RFQ-E10.*

**Purpose.** The evidence items behind every finding, so a reviewer can re-open any source.

**Inputs this section requires**

| dataset | fields consumed | why |
|---|---|---|
| evidence_register | `evidence_id`, `observation_id`, `finding_id`, `group`, `area`, `source_type`, `source_ref`, `captured_at`, `represented_period`, `claim`, `scope_limit`, `directness`, `recency`, `representativeness`, `corroboration`, `evidence_state`, `confidence`, `follow_up` | The full register, unabridged, so nothing in the body rests on an item that is not listed here. |
| sdlc_evidence_worksheet | `change_id`, `group`, `stage_name`, `status`, `evidence_ref`, `evidence_semantics`, `gap_or_conflict` | Per-change delivery traces where a finding rests on observed change activity. |

**Traceability rule.** Every finding_id cited anywhere in the body appears in this appendix with at least one evidence item.

**Missing-evidence rule.** An evidence item whose represented_period could not be established keeps recency UNKNOWN rather than being assumed current.

**Write this section by answering:**

- What exactly did we see, and what does it establish?
- What is the scope limit of each source?

> `<section content here>`

---

## B. Appendix B - Source and Version Register

*Audience: practitioner. Covers: RFQ-E11.*

**Purpose.** Pin every external framework and published source to the version actually used.

**Inputs this section requires**

| dataset | fields consumed | why |
|---|---|---|
| source_version_register | `framework`, `publication`, `identifier`, `publication_date`, `version_treatment`, `official_source` | The frozen framework versions and how each was treated. |
| policy_context_register | `source_id`, `issuer`, `title`, `policy_or_section`, `version_or_review_date`, `source_url`, `applicability_caveat`, `accessed_date` | Policy sources with their applicability caveats intact. |

**Traceability rule.** Every external citation in the body resolves to a row here with a version or review date.

**Missing-evidence rule.** A draft revision is recorded as a horizon-scan item and is never cited as current practice.

**Write this section by answering:**

- Which version of each framework was used?
- Which sources were accessed on which date?

> `<section content here>`

---

## C. Appendix C - Open Questions and Unresolved Inputs

*Audience: all. Covers: RFQ-E12.*

**Purpose.** Carry forward everything that stayed UNKNOWN, and say what would resolve it.

**Inputs this section requires**

| dataset | fields consumed | why |
|---|---|---|
| finding_matrix | `finding_id`, `group`, `area`, `status`, `follow_up_question` | Every cell that is UNKNOWN, PARTIAL or CONFLICT, with the question that would resolve it. |
| evidence_register | `evidence_id`, `evidence_state`, `confidence`, `follow_up` | Evidence items left UNRESOLVED or NOT_EVIDENCED, with their follow-up. |

**Traceability rule.** Every UNKNOWN, PARTIAL or CONFLICT cell in the matrix appears here exactly once.

**Missing-evidence rule.** This section is the reason an absent input never has to become a zero anywhere else in the report.

**Write this section by answering:**

- What could we not determine?
- What specific artifact or access would resolve it?
- Who owns supplying it?

> `<section content here>`

---
