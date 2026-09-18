# Exeter CA RFP 2026-06 — specialist acceptance matrix

Operation: `EXETER-CA-2026-06-MUNICIPAL-FINANCE-ACCEPTANCE-ZSOL-20260917`  
Commercial state: **PROPOSED_NOT_ACCEPTED**  
Prime state: **UNSELECTED / BIDDER_STATUS_UNKNOWN**

This matrix turns the City's published implementation/data-conversion/testing seams into a bounded evidence contract. It does not certify ERP product compliance or create City acceptance.

| Gate | RFP/workshare seam | Required evidence | PASS condition | HOLD condition | Authority |
|---|---|---|---|---|---|
| `SOURCE_PIN` | Current RFP/addenda/Q&A | first-party procurement index + RFP + current written addenda/Q&A | all proposal-facing facts bound to current City generation | stale source, missing expected Q&A/addendum, conflicting deadlines | prime owns proposal; TJLabs owns its source ledger |
| `PRIME_FIT` | Minimum vendor qualifications | prime-owned confirmation of pursuit, established product, government implementations, staffing/hosting/support | candidate independently establishes its own qualifications and pursuit | product fit inferred as bidder status; references or pursuit unverified | prime |
| `INPUT_READY` | Data conversion / implementation | frozen source+target generation digests, mapping rules, interface inventory, evidence boundary | inputs are bounded, owner-bound and content-addressed | live/unbounded dump, unknown generation, contradictory mapping | prime supplies; TJLabs validates packet |
| `CROSSWALK` | Conversion mappings | account/fund, vendor, customer, employee source→target mappings | source IDs are unique and each admitted mapping has explicit target/disposition | duplicate/conflicting source identity or missing required crosswalk | TJLabs evidence only |
| `CONTROL_TOTALS` | GL/fund / financial reporting | source and target integer-cent control totals | exact match for every admitted control | unexplained cent drift, float/rounded authority, duplicate control ID | prime owns accounting; TJLabs checks declared evidence |
| `SUBLEDGER_RECON` | AP/AR/payroll/utility/cashiering | source/target counts and amounts, separately evidenced approved deltas | target-source equals declared approved delta and all exception IDs are resolved | unexplained count/amount difference, missing delta receipt, open exception | prime owns corrections; TJLabs analyzes |
| `BANK_RECON` | Bank reconciliation | statement/book endings, explicit additions/deductions, terminal reconciled amount | statement-adjusted == book-adjusted == declared terminal amount | hidden plug, unmatched terminal amount, missing evidence | City/prime accounting authority |
| `INTERFACES` | Integrations / third-party systems | required interface list, source/target, manifest digest, verification state | every required interface represented once with retained verified evidence | missing/duplicate interface, unbound manifest, assumed status | prime owns integration; TJLabs evidence analysis |
| `UAT_TRACE` | Testing/data validation/UAT | case ID, mandatory flag, status, evidence digest | all workshare-mandatory cases PASS with retained evidence | missing case/evidence, FAIL/HOLD, caller-authored acceptance without evidence | human UAT remains prime/City |
| `CUTOVER` | Go-live / transition support | source-freeze, rollback, replay receipts and unresolved exception list | all three receipts content-addressed and unresolved set empty | missing receipt or any unresolved cutover exception | prime/City make go-live decision |
| `REPLAY` | Reproducibility | canonical bounded packet and final report digest | same packet bytes reproduce same report/exception IDs | state depends on clock/network/order or hidden mutable source | TJLabs |
| `COMMERCIAL` | Proposed paid workshare | agreed scope/price/timing and authorized acceptance | only an authorized work order/agreement can advance commercial state | routing acknowledgement, meeting, interest or proposal treated as sale | authorized counterparty/owner |

## Mandatory UAT evidence IDs

The acceptance engine design reserves these workshare IDs: `GL_FUND_ACCOUNTING`, `AP`, `AR`, `PAYROLL`, `CASHIERING`, `BANK_RECONCILIATION`, `UTILITY_BILLING`, `FINANCIAL_REPORTING`, `INTEGRATIONS`, `DATA_CONVERSION`.

These are workshare trace IDs, not claims that the buyer uses a particular test nomenclature.

## Fail-closed rules

1. `UNKNOWN != PASS`.
2. Money is integer cents; booleans/floats cannot masquerade as amounts.
3. An approved conversion delta requires its own retained digest; a bare numeric plug is not evidence.
4. Every required interface and mandatory UAT case must exist exactly once.
5. Open subledger/cutover exceptions force HOLD.
6. Stable machine evidence does not mint accounting judgment, bank action, payroll authority, go-live authority or buyer acceptance.
7. Any City addendum/Q&A that changes a modeled fact requires `SOURCE_PIN` refresh before partner-facing use.
8. No production/customer/employee data enters TJLabs tooling without separate authorization and controls.
