# Proposed OSIP operations-support workshare

Status: internal design; no implementation, engagement, qualification, or award claimed. Operation: `RI-OSIP-TEAMING-DOSSIER-IMPLEMENTATION-ZSOL-20260917`. Original opportunity and teaming work: **Sol17 / ZSol**; recovery and expansion: **ZZ-Keystone-43CF**. Source review: September 19, 2026.

The proposed package turns a prime's approved data extracts into reproducible reconciliation results, reviewable exceptions, and reporting workpapers. It operates on copies. Investment management, custody, money movement, participant transaction execution, accounting policy, and final publication remain with the appointed responsible parties. This workshare does not establish our eligibility to serve as prime.

## Placement within the procurement

The six scope groups are in Section III on printed pp.4-5 of the [official OSIP RFP](https://treasury.ri.gov/media/2171/download?language=en#page=4). The following is our proposed allocation, not an interpretation granting us authority.

| RFP group | Proposed supporting deliverable | Responsible party retains |
| --- | --- | --- |
| 1: Portfolio management | Index the prime's supplied portfolio and performance files for report traceability. | Security selection, valuation policy, investment decisions, execution. |
| 2: Accounting and records | Participant roll-forwards, source-to-total reconciliations, draft reporting extracts. | Official books, earnings posting, accounting judgments. |
| 3: Transaction administration | Compare recorded events with confirmations and settlement extracts. | Contributions, withdrawals, account changes, correction posting. |
| 4: Audit/custody coordination | Evidence index, reconciliation workpapers, request/response register. | Custody, auditor appointment, audit procedures and opinions. |
| 5: Participant service | Draft statement checks and clearly labeled issue summaries for the prime. | Participant support, distribution, official communications. |
| 6: Technology and continuity | Reproducible reruns, restore exercise, operational runbook and handoff. | Production operations and the engagement's service commitments. |

The RFP requests intended subcontractor details in III.H.5 (p.8) and reporting methods in III.M (p.10). Prime confirmation is needed before presenting this proposed allocation as part of a bid. [RFP pp.8 and 10](https://treasury.ri.gov/media/2171/download?language=en#page=8).

## Inputs and data handling

| Input supplied by prime | Required meaning | Receipt and quality evidence |
| --- | --- | --- |
| Participant account roster and opening/closing ledger extracts | Stable account identifier, status, period, balance basis, currency, decimal precision. | Source version, period boundaries, row count, unique-key count. |
| Contributions, withdrawals, earnings, fees and adjustments | Event ID, account ID, amount, sign convention, effective/posted/settlement dates, reversal references. | Original rows retained; exact replay and conflicting duplicate counts separated. |
| Master-ledger, bank/custodian and confirmation extracts | Source-specific identifiers and timing basis; pending items identified. | Independent control totals and explicit mapping to each source. |
| Earnings allocation specification and reference output | Prime-approved formula, eligibility dates, rate basis, rounding and residual treatment. | Versioned specification and known-answer cases. |
| Reporting calendar, templates and chart of accounts | Fiscal period, reporting categories, correction process and release owner. | Field dictionary and accountable owner for every mapping. |

Use synthetic data for development and acceptance preparation. Any later production work takes place in the prime's agreed private environment using the least data needed for the task. Keep identifying crosswalks separate from working account codes. No participant information, account credentials, banking instructions, or production extracts belong in this dossier, public repositories, Slack posts, or demonstration files.

Record permitted delivery methods, storage location, retention, return/deletion obligations, incident contacts, and backup handling with the prime before production data is provided. These are proposed engagement terms, not claims about controls already deployed. Preserve original input bytes and provenance; never overwrite an extract to make a reconciliation balance.

## Deterministic reconciliation method

1. Freeze the input set. Produce a manifest containing file digest, source, period, receipt time and schema version. Record timezone and cutoff conventions explicitly; preserve all date fields.
2. Validate schema, identifiers, currency and decimal scale. Missing files, incomplete periods or malformed rows produce an incomplete result with named exceptions; absent data never becomes zero.
3. Normalize into a derived event table while retaining row-level source references. An exact replay may be excluded from calculations once, with its raw row preserved. Reused IDs carrying different values are conflicts, not duplicates to discard.
4. For each participant, recompute closing balance from opening balance plus signed, eligible posted events. Match reversals to their original events. Apply fees or adjustments only when present in the approved source; never invent balancing entries. Keep settled and pending views separate.
5. Compare the recomputed close with the official participant close. Separately reconcile participant totals to the applicable master-ledger control accounts, and master-ledger cash movements to bank/custodian evidence. Do not equate participant liabilities with an investment-asset total without the prime's documented bridge.
6. Reperform earnings arithmetic only against the prime's supplied formula. Explain rounding residuals separately; a configured tolerance is not permission to hide an unexplained difference.
7. Emit exceptions, totals and workpapers. Repeating the same input hashes and rule version must reproduce identical substantive outputs; runtime timestamps belong in the execution receipt, outside canonical output hashes.

See [WORKED_RECONCILIATION.md](WORKED_RECONCILIATION.md) for the separately labeled fictional example. It illustrates the method and is not evidence of an OSIP production deployment.

## Exceptions and review trail

Each exception records period, participant code, rule ID, source references, observed/expected values, exact delta, rule version, input hashes and reviewer disposition. A logical exception key remains stable across reruns; changed inputs create a new version rather than erase history.

Proposed rules: missing source; incomplete period; unknown account; conflicting event ID; unmatched reversal; unmatched confirmation; late or differently dated posting; participant closing mismatch; master-control mismatch; unexplained earnings residual; unmapped reporting category. Define severity and response ownership with the prime. Resolutions are documented explanations or prime-issued corrected source versions. The package creates no ledger writeback, payment file, bank instruction or transaction command.

## Reporting and audit package

Proposed outputs are an input manifest, mapping dictionary, participant roll-forward CSV, control-total workbook or CSV, exception register, report-field lineage, and a human-readable completion receipt. Every reported total traces to source rows and the applied rule version. Each output distinguishes incomplete, reconciled, and reconciled-with-explained-items states.

The statutory support map covers individual account activity and monthly status, then fiscal-year pool activity including deposits, earnings, investment movements and administrative expenses. Treasury remains the statutory reporting party. This mapping follows [R.I. Gen. Laws §35-10.2-9](https://webserver.rilegislature.gov/Statutes/TITLE35/35-10.2/35-10.2-9.htm); the prime and Treasury determine the final reporting presentation.

Prepare auditor-request workpapers with source inventories, selections, reconciliations and version history. Independent auditors decide sufficiency and findings. No generated workpaper is labeled an audit opinion or a certification of statutory compliance.

## Proposed implementation and acceptance

| Stage | Deliverable | Acceptance evidence to agree with prime |
| --- | --- | --- |
| Mapping | Input dictionary, source/control map, unresolved-questions register. | Every field and balance basis mapped or explicitly unresolved. |
| Synthetic build | Parser, normalization specification and reconciliation rules. | Exact decimals; replay stability; seeded missing, duplicate, reversal, timing and mismatch cases classified as expected. |
| Parallel review | Side-by-side results on an agreed historical period in the prime's environment. | Complete source coverage; every difference explained or left visibly open; no production writes. |
| Reporting | Participant and aggregate draft extracts with field lineage. | Each total ties to accepted workpapers; no cross-participant attribution errors. |
| Recovery | Restore and rerun from preserved inputs and versioned rules. | Reproduced canonical hashes; measured recovery time recorded against an agreed target. |
| Handoff | Runbook, issue ownership, retained evidence and version inventory. | Prime operator completes a witnessed rerun and documents acceptance or outstanding items. |

No duration, capacity, service level, price or test result is asserted here. Agree those values after receiving representative data shapes and the prime's required operating windows.

## Decision log to maintain

| Decision | Current position | Next evidence / owner |
| --- | --- | --- |
| Prime relationship | Unconfirmed; subcontracting concept only. | Prospective prime's bid lead confirms role and disclosure treatment. |
| Account and settlement basis | Unresolved. | Prime operations/accounting owners supply field definitions. |
| Earnings and rounding | Use only supplied, versioned rules. | Prime accounting owner supplies expected examples. |
| Exception tolerance | No implicit tolerance or balancing entry. | Prime defines documented thresholds and escalation responsibility. |
| Reporting and publication | Draft outputs reviewed by designated responsible parties. | Prime/Treasury establish templates, deadlines and recipients. |
| Production data and continuity | Synthetic preparation only at this stage. | Prime agrees handling, retention, recovery targets and operating environment. |

For each decision, retain an ID, date, owner, options considered, selected value, rationale, evidence reference and superseded version.
