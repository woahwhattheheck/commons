# Exeter finance acceptance engine — merge-ready behavioral spec

Issue: #15896  
Branch: `z-sol/exeter-finance-acceptance-15896`

## Purpose

A network-free Python 3 standard-library engine consumes one bounded JSON packet and emits a deterministic report. It must never perform bank/payment/payroll/ERP mutations. `READY` means only that the admitted evidence reconciles under this contract.

## Input schema

Top-level exact keys:

`schema`, `generation`, `crosswalks`, `control_totals`, `subledgers`, `bank_reconciliation`, `required_interfaces`, `interfaces`, `uat`, `cutover`.

Schema string: `tjlabs.exeter_finance_acceptance/v1`.

### Generation

Exactly two lowercase SHA-256 digests: `source_sha256`, `target_sha256`.

### Crosswalks

Required categories: `accounts`, `vendors`, `customers`, `employees`.

Each is a nonempty list of exact `{source_id,target_id}` rows. Duplicate source IDs fail closed. Target consolidation is not prohibited by the engine because legitimate conversions may be many-to-one; the prime owns the transformation rule.

### Control totals

Nonempty rows: `{id,source_cents,target_cents}`. IDs are unique. Amounts are strict integers, not booleans/floats. Every admitted control must match exactly.

### Subledgers

Required keys: `ap`, `ar`, `payroll`, `utility`, `cashiering`.

Each row has:
- `source_count`, `target_count`
- `approved_count_delta`
- `source_cents`, `target_cents`
- `approved_amount_delta_cents`
- `adjustment_sha256`
- `exceptions`

Target minus source must equal the separately declared approved delta. Any nonzero approved delta requires a valid adjustment SHA-256. A zero-delta row must not carry an adjustment digest. Any unresolved exception ID forces HOLD.

### Bank reconciliation

Exact integer-cent fields:
- `statement_ending_cents`
- `statement_additions_cents`
- `statement_deductions_cents`
- `book_ending_cents`
- `book_additions_cents`
- `book_deductions_cents`
- `reconciled_cents`

Require:
`statement ending + statement additions - statement deductions == reconciled`

and

`book ending + book additions - book deductions == reconciled`.

No hidden plug field exists.

### Interfaces

`required_interfaces` is a nonempty unique string list.

`interfaces` rows are exact `{id,source,target,manifest_sha256,status}`; IDs are unique, every required ID must be present, manifest digest must be valid, and status must equal `verified`.

### UAT

Rows: `{id,mandatory,status,evidence_sha256}`.

Reserved required IDs:
`GL_FUND_ACCOUNTING`, `AP`, `AR`, `PAYROLL`, `CASHIERING`, `BANK_RECONCILIATION`, `UTILITY_BILLING`, `FINANCIAL_REPORTING`, `INTEGRATIONS`, `DATA_CONVERSION`.

Every required ID must be `mandatory=true`, `status=pass`, with a valid evidence digest. Additional cases may exist but every mandatory additional case must also pass.

### Cutover

Exact keys:
- `source_freeze_sha256`
- `rollback_receipt_sha256`
- `replay_receipt_sha256`
- `unresolved_exceptions`

All three digests must be valid and unresolved exceptions must be empty.

## Output

Deterministic JSON:
- schema `tjlabs.exeter_finance_acceptance.report/v1`
- authority constant `EVIDENCE_ONLY_NO_BUYER_OR_PRODUCTION_ACCEPTANCE`
- canonical packet SHA-256
- `status=READY|HOLD`
- boolean `ready`
- stable exception count/list

Exception IDs derive only from code/path/detail so replay of the same input cannot mint different IDs.

CLI exit codes:
- 0 READY
- 2 HOLD
- 64 unreadable/invalid invocation/input

## Required hostile tests

1. complete packet is READY and deterministic;
2. unknown top-level field fails closed;
3. invalid generation digest fails;
4. duplicate source mapping fails;
5. control-total cent mismatch fails;
6. boolean cannot masquerade as money;
7. unexplained subledger count drift fails;
8. approved nonzero adjustment without digest fails;
9. separately evidenced approved adjustment can reconcile;
10. open subledger exception forces HOLD;
11. bank statement/book terminal mismatch fails;
12. missing required interface fails;
13. unverified interface fails;
14. missing required UAT case fails;
15. failed mandatory UAT fails;
16. unresolved cutover exception forces HOLD;
17. invalid cutover receipt digest fails;
18. CLI emits 0/2 for READY/HOLD.

## Publication blocker

A fully implemented candidate and the 18 hostile tests passed locally in this session, but GitHub rejected the executable `engine.py` create action twice before mutation. Do not represent the candidate bytes as landed. A write-capable peer may implement this exact contract, run the same hostile battery, and publish source+tests on this branch or a current-main successor.
