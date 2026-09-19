# Does UNKNOWN survive the delivery chain?

A read-only screen over the landed RFQ-18649 lanes. It asks one question: when a lane records that nobody estimated something, does that stay recorded everywhere the same identifier appears?

Scanned: `/home/user/commons/revenue`

- Tree digest before: `sha256:1fa495b0c532d3dc348ac8d04fffe407e1740827ce809b1bb929f549b6ec695d`
- Tree digest after:  `sha256:1fa495b0c532d3dc348ac8d04fffe407e1740827ce809b1bb929f549b6ec695d`
- **Tree unchanged by this scan: True**

## What was found

| | |
|---|---:|
| Claims extracted | 6,221 |
| Distinct identifiers | 136 |
| Identifiers appearing in more than one lane | **29** |
| Distinct field names | 222 |
| Field names appearing in more than one lane | **36** |
| Identifier+field pairs actually comparable | 120 |

- `UNKNOWN_BECAME_ZERO`: **0**
- `UNKNOWN_HARDENED`: **0**
- `CONSISTENT` (all lanes agree it is unknown): 4

## The alignment gap

36 of 222 field names appear in more than one lane. The remaining 186 are used by exactly one lane, so no cross-lane check of those values is possible at all -- not because they agree, but because nothing can be compared to them.

**This is the headline result, not a caveat.** Lanes share identifiers but not a field vocabulary, so most values in the delivery kit cannot be cross-checked by any automated consumer. Where nothing can be compared, silence is not agreement.

Field names that do appear in more than one lane:

| field | lanes |
|---|---|
| `area` | uiowa_rfq_18649_ai_use_inventory, uiowa_rfq_18649_economics_resource_adapters, uiowa_rfq_18649_intake_rehearsal, uiowa_rfq_18649_milestone_packets, uiowa_rfq_18649_output_agreement, uiowa_rfq_18649_prioritization, uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `basis` | uiowa_rfq_18649_ai_opportunity_portfolio, uiowa_rfq_18649_economics_resource_adapters, uiowa_rfq_18649_scope_change |
| `business_verified_at` | uiowa_rfq_18649_recovery_evidence, uiowa_rfq_18649_release_recovery_case |
| `captured_at` | uiowa_rfq_18649_ai_use_inventory, uiowa_rfq_18649_release_recovery_case, uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `claim` | uiowa_rfq_18649_intake_rehearsal, uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `completeness_basis` | uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `confidence` | uiowa_rfq_18649_economics_resource_adapters, uiowa_rfq_18649_output_agreement, uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `conflict_group` | uiowa_rfq_18649_intake_rehearsal, uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `corroboration` | uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `directness` | uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `disruption_at` | uiowa_rfq_18649_recovery_evidence, uiowa_rfq_18649_release_recovery_case |
| `enumerator_authority` | uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `evidence_refs` | uiowa_rfq_18649_ai_use_inventory, uiowa_rfq_18649_report_structure |
| `evidence_state` | uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `finding_refs` | uiowa_rfq_18649_output_agreement, uiowa_rfq_18649_report_structure |
| `follow_up` | uiowa_rfq_18649_intake_rehearsal, uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `group` | uiowa_rfq_18649_ai_opportunity_portfolio, uiowa_rfq_18649_ai_use_inventory, uiowa_rfq_18649_economics_resource_adapters, uiowa_rfq_18649_intake_rehearsal, uiowa_rfq_18649_milestone_packets, uiowa_rfq_18649_output_agreement, uiowa_rfq_18649_prioritization, uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `horizon` | uiowa_rfq_18649_output_agreement, uiowa_rfq_18649_report_structure |
| `last_successful_at` | uiowa_rfq_18649_recovery_evidence, uiowa_rfq_18649_release_recovery_case |
| `locator` | uiowa_rfq_18649_intake_rehearsal, uiowa_rfq_18649_release_recovery_case |
| `notes` | uiowa_rfq_18649_ai_use_inventory, uiowa_rfq_18649_economics_resource_adapters, uiowa_rfq_18649_prioritization, uiowa_rfq_18649_scope_change |
| `rank_position` | uiowa_rfq_18649_ai_opportunity_portfolio, uiowa_rfq_18649_prioritization |
| `recency` | uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `representativeness` | uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `represented_period` | uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `resource_note` | uiowa_rfq_18649_output_agreement, uiowa_rfq_18649_report_structure |
| `restore_completed_at` | uiowa_rfq_18649_recovery_evidence, uiowa_rfq_18649_release_recovery_case |
| `restored_data_as_of` | uiowa_rfq_18649_recovery_evidence, uiowa_rfq_18649_release_recovery_case |
| `scope_limit` | uiowa_rfq_18649_intake_rehearsal, uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `source_ref` | uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `source_type` | uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `statement` | uiowa_rfq_18649_output_agreement, uiowa_rfq_18649_report_structure |
| `status` | uiowa_rfq_18649_output_agreement, uiowa_rfq_18649_prioritization, uiowa_rfq_18649_report_structure, uiowa_rfq_18649_scope_change |
| `title` | uiowa_rfq_18649_ai_opportunity_portfolio, uiowa_rfq_18649_economics_resource_adapters, uiowa_rfq_18649_prioritization, uiowa_rfq_18649_scope_change |
| `universe_definition` | uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare |
| `verified_at` | uiowa_rfq_18649_recovery_evidence, uiowa_rfq_18649_release_recovery_case |

## How the tree spells "nobody estimated this"

| spelling | family | lanes using it |
|---|---|---:|
| `NEEDS_ESTIMATE` | UNKNOWN | 1 |
| `NONE` | UNKNOWN | 2 |
| `NOT QUOTED` | UNKNOWN | 1 |
| `NOT_RANKED` | UNKNOWN | 1 |
| `NO_RESOURCING_DATA` | UNKNOWN | 1 |
| `None` | UNKNOWN | 1 |
| `PARTIAL` | INCOMPLETE | 3 |
| `POPULATION_UNKNOWN` | UNKNOWN | 2 |
| `UNKNOWN` | UNKNOWN | 9 |
| `UNRESOLVED` | INCOMPLETE | 3 |
| `none` | UNKNOWN | 2 |
| `null` | UNKNOWN | 5 |

12 distinct spellings. Every one is a reasonable choice in its own lane. Together they are the reason a downstream consumer cannot tell that two lanes are saying the same thing.

`UNKNOWN` family = nobody supplied a value. `INCOMPLETE` family = somebody looked and the answer is not settled. This screen keeps them apart, because merging them would be the same conflation it exists to detect.

### Fields that spell it more than one way

- **`benefit`** — `UNKNOWN` (uiowa_rfq_18649_prioritization); `null` (uiowa_rfq_18649_prioritization)
- **`complexity`** — `UNKNOWN` (uiowa_rfq_18649_prioritization); `null` (uiowa_rfq_18649_prioritization)
- **`fee`** — `NOT QUOTED` (uiowa_rfq_18649_scope_change); `UNKNOWN` (uiowa_rfq_18649_scope_change)
- **`notes`** — `None` (uiowa_rfq_18649_prioritization); `null` (uiowa_rfq_18649_prioritization)
- **`one_time_cash_state`** — `PARTIAL` (uiowa_rfq_18649_economics_resource_adapters); `UNKNOWN` (uiowa_rfq_18649_economics_resource_adapters)
- **`priority_score`** — `UNKNOWN` (uiowa_rfq_18649_prioritization); `null` (uiowa_rfq_18649_prioritization)
- **`rank`** — `NOT_RANKED` (uiowa_rfq_18649_prioritization); `UNKNOWN` (uiowa_rfq_18649_ai_opportunity_portfolio); `null` (uiowa_rfq_18649_prioritization)
- **`recurring_cash_yr_state`** — `PARTIAL` (uiowa_rfq_18649_economics_resource_adapters); `UNKNOWN` (uiowa_rfq_18649_economics_resource_adapters)
- **`released_capacity_hours_yr_state`** — `PARTIAL` (uiowa_rfq_18649_economics_resource_adapters); `UNKNOWN` (uiowa_rfq_18649_economics_resource_adapters)
- **`representativeness`** — `POPULATION_UNKNOWN` (uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare); `UNKNOWN` (uiowa_rfq_18649_report_structure, uiowa_rfq_18649_workshare)
- **`resourcing_state`** — `NO_RESOURCING_DATA` (uiowa_rfq_18649_economics_resource_adapters); `PARTIAL` (uiowa_rfq_18649_economics_resource_adapters)
- **`status`** — `NEEDS_ESTIMATE` (uiowa_rfq_18649_prioritization); `PARTIAL` (uiowa_rfq_18649_output_agreement, uiowa_rfq_18649_report_structure); `UNKNOWN` (uiowa_rfq_18649_output_agreement, uiowa_rfq_18649_report_structure)

## Findings

### `CONSISTENT` — FND-SYN-ESS-AI-001 · `status`

every lane that speaks to this field records an unsettled value, in the same family: INCOMPLETE.

| side | lane | value | files | example |
|---|---|---|---:|---|
| unsettled | uiowa_rfq_18649_output_agreement | `PARTIAL` | 11 | `uiowa_rfq_18649_output_agreement/fixtures/consistent/matrix.csv` (row 5) |
| unsettled | uiowa_rfq_18649_report_structure | `PARTIAL` | 1 | `uiowa_rfq_18649_report_structure/fixtures/synthetic_finding_matrix.csv` (row 5) |

*Resolution:* Nothing to resolve: no lane claims a settled value here. Listed so the comparison that was actually performed is visible, rather than only its failures.

### `CONSISTENT` — FND-SYN-ESS-SEC-001 · `status`

every lane that speaks to this field records an unsettled value, in the same family: INCOMPLETE.

| side | lane | value | files | example |
|---|---|---|---:|---|
| unsettled | uiowa_rfq_18649_output_agreement | `PARTIAL` | 11 | `uiowa_rfq_18649_output_agreement/fixtures/consistent/matrix.csv` (row 3) |
| unsettled | uiowa_rfq_18649_report_structure | `PARTIAL` | 1 | `uiowa_rfq_18649_report_structure/fixtures/synthetic_finding_matrix.csv` (row 3) |

*Resolution:* Nothing to resolve: no lane claims a settled value here. Listed so the comparison that was actually performed is visible, rather than only its failures.

### `CONSISTENT` — FND-SYN-IAM-DEP-001 · `confidence`

every lane that speaks to this field records an unsettled value, in the same family: INCOMPLETE.

| side | lane | value | files | example |
|---|---|---|---:|---|
| unsettled | uiowa_rfq_18649_output_agreement | `UNRESOLVED` | 11 | `uiowa_rfq_18649_output_agreement/fixtures/consistent/matrix.csv` (row 11) |
| unsettled | uiowa_rfq_18649_report_structure | `UNRESOLVED` | 1 | `uiowa_rfq_18649_report_structure/fixtures/synthetic_finding_matrix.csv` (row 11) |

*Resolution:* Nothing to resolve: no lane claims a settled value here. Listed so the comparison that was actually performed is visible, rather than only its failures.

### `CONSISTENT` — FND-SYN-RIS-SD-001 · `status`

every lane that speaks to this field records an unsettled value, in the same family: INCOMPLETE.

| side | lane | value | files | example |
|---|---|---|---:|---|
| unsettled | uiowa_rfq_18649_output_agreement | `PARTIAL` | 11 | `uiowa_rfq_18649_output_agreement/fixtures/consistent/matrix.csv` (row 6) |
| unsettled | uiowa_rfq_18649_report_structure | `PARTIAL` | 1 | `uiowa_rfq_18649_report_structure/fixtures/synthetic_finding_matrix.csv` (row 6) |

*Resolution:* Nothing to resolve: no lane claims a settled value here. Listed so the comparison that was actually performed is visible, rather than only its failures.

## Set aside: one lane's own variants

3 pair(s) where a lane records a value for an identifier and field that the **same lane** records as unknown elsewhere in its own files. That is a lane's copies differing from each other, which is exactly what a checker's deliberately-broken fixtures look like from outside. These are **not** counted as propagation failures — treating another seat's passing negative tests as defects in the delivery kit would be manufacturing findings. They are listed so the screen is not silently filtering its own results.

| identifier | field | lane(s) | negative-fixture paths |
|---|---|---|---:|
| FND-SYN-IAM-AI-001 | `status` | uiowa_rfq_18649_output_agreement | 1 |
| FND-SYN-RIS-SEC-001 | `status` | uiowa_rfq_18649_output_agreement | 1 |
| REC-SYN-IAM-AI-001 | `horizon` | uiowa_rfq_18649_output_agreement | 1 |

The rule that sets these aside is **structural** — the same lane holds both sides — not a directory-name guess. The path column is reported only as corroborating context; a convention like `fixtures/mismatched/` is a habit, not a guarantee.

## Declared field equivalences

Alignments below were **asserted by a person**, not inferred. Nothing else was aligned by anything but an exact name match.

- **rank_position** — `uiowa_rfq_18649_prioritization.rank`, `uiowa_rfq_18649_ai_opportunity_portfolio.rank`
  - asserted by: OP5-CINDER, from reading both lanes' data dictionaries
  - basis: Both fields hold the item's position in a priority ordering, and both use a distinct marker rather than a number when the item is not ranked. uiowa_rfq_18649_prioritization/DATA_DICTIONARY.md defines 'rank' as null/NOT_RANKED when unranked; the opportunity portfolio's 'rank' is the same concept. The equivalence is asserted on the documented meaning, not on the shared name.

## What this screen cannot tell you

- A clean result means this screen found no disagreement in the fields it could align. It is NOT a statement that the artifacts agree.
- Fields are aligned by exact name or by a declared crosswalk entry. No similarity matching is performed, so genuinely equivalent fields with different names are invisible to this screen unless somebody declares the equivalence.
- Only JSON and CSV are read. Values stated in Markdown prose are not compared.
- The screen cannot tell a legitimate later estimate from a value that was never sourced, and does not try.
- No lane, artifact or author is scored, rated, graded or marked compliant by this output.

---

Produced offline by `scan_unknowns.py` (Python standard library only), read-only. This output is a screen result, not an assessment, not a finding about the University of Iowa, and not a judgement of any lane or any author.
