# Normalized input contract, version 1

The executable validator in `cashiering_lab/core.py` is authoritative for accepted shapes. `examples/clean.json` is a complete specimen. No optional unknown keys are ignored. Explicit `null` represents missing evidence where documented; omitting a required field is a structural error.

## Document

`schema` is `cashiering-acceptance/1`. `case_id` is a stable ASCII identifier. `period.start` and `period.end` are offset-aware timestamps; the interval is half-open. `currency_scale` explicitly maps three-letter uppercase currency labels to an integer scale between zero and four. The engine does not check whether a label/scale pair is authoritative. `variance_reason_threshold_minor` is a nonnegative integer, applied independently in each batch/deposit's units, with a strictly-greater-than comparison.

`batches` must be nonempty. `transactions` and `deposits` can be empty. Zero-transaction batches still need a supplied drawer count and a declared zero activity total to compare. Cash retained from opening float can be deposited, so a zero-transaction batch is not assumed to have zero cash available for deposit.

## Scope and identifiers

Every batch and deposit carries exactly these scope fields: `agency`, `business_unit`, `department`, `location`, `bank_account`, and `currency`. A consolidated deposit must match all six, not just currency. Refunds/reversals use the scope of their containing batch and must match the original receipt's batch scope. This conservative equality rule is not a representation of State policy; more flexible authorized scope mappings need a separately reviewed adapter.

Identifiers use `[A-Za-z0-9][A-Za-z0-9._:-]{0,79}`. They are opaque, not routing numbers, account credentials, card numbers, or real personal identifiers. Generic strings are limited to 240 characters and exclude control characters and unpaired Unicode surrogates. These syntactic rules do not authenticate identity or detect all sensitive data.

## Money

Every amount is a signed integer in the associated currency's minor units, with absolute per-field bound 10^15. Booleans and floating-point numbers are not money. Cash-count and float fields are nonnegative; refund/reversal components are nonpositive and their total must be negative. Totals use Python integers; downstream consumers must not coerce arbitrarily large integer totals to lossy floating point.

The engine receives, rather than decides, original amounts, rounding adjustments, fees, tax treatment, tender choices, account codes, and accounting policy. Amounts in allocations must sum to collected, including any policy-defined handling of rounding. It does not generate accounting allocations from percentages or determine which accounts are permissible.

## Batches

Fields: `id`, six scope fields, `cashier`, `opened_at`, `closed_at`, `opening_cash_minor`, `counted_cash_minor`, `retained_cash_minor`, `declared_total_minor`, and `variance_reason`.

Open and close must fall within the document period, with open strictly earlier than close. Transaction timestamps are tested against `[opened_at, closed_at)`. The close timestamp is an operator declaration; no source lifecycle event or current-time proof is inferred. `counted_cash_minor` and `declared_total_minor` may be null, generating missing-evidence findings. `variance_reason` may be null; a nonempty reason explains but does not authorize or erase a discrepancy.

A batch must have a counted drawer value even when cash activity is zero. Use an explicit zero for a genuinely zero/no-cash drawer, not null. The source adapter/operator is responsible for supplying a meaningful drawer model. Cash available for deposit is counted less retained, not transaction cash less theoretical float. Negative availability remains a finding, not an automatic funding transaction.

## Transactions

Fields: `id`, `batch_id`, `kind`, `timestamp`, `original_id`, `original_minor`, `rounding_minor`, `collected_minor`, `tenders`, `allocations`, and `evidence_ref`.

Kinds are `RECEIPT`, `REFUND`, `REVERSAL`. A receipt's original reference is null. A linked original must be a retained receipt, in scope, and strictly earlier in time. Same-instant linked reversals need upstream sequencing evidence and are outside this version; lexical ID order is not treated as business chronology.

Each tender component contains only `type` and `amount_minor`. Supported normalized types are `CASH`, `CHECK`, `CARD`, `ACH`, and `OTHER`. These are reporting categories, not payment capabilities. Each accounting component contains `account_id` and `amount_minor`. Types/accounts are unique within their collection; zero components are permitted but do not conceal opposite-sign components. At most 100 tender and 100 allocation components are accepted per transaction.

For partial refunds, cumulative amounts returned are bounded per original total, unrounded original amount, tender, and account. Cumulative returned rounding lies between zero and the signed original adjustment. The original's precise rounding policy is not reconstructed. A full reversal must exactly negate the original's component dictionaries, original amount, rounding, and collected amount; it is rejected after any earlier linked return.

Evidence references are unique among transactions as a conservative duplicate-row check. They are operator-declared references only. Split provider rows, a common source row carrying several events, or other remittance encodings need normalization before ingestion, with documented lineage rather than reminted fake evidence IDs.

## Deposits

Fields: `id`, six scope fields, `tender`, `batch_ids`, `observed_minor`, `variance_reason`, and `evidence_ref`.

`batch_ids` is a nonempty, duplicate-free list of known batches. Each complete batch/tender is assigned at most once across deposits. A deposit can consolidate batches only in the exact same six-field scope. Partial deposits, transfers between deposits, multiple bank accounts within one batch, and ambiguous overlaps require a different normalized model; they are not guessed.

Cash expected amounts use counted-minus-retained cash. For all other tenders, expectation is recorded signed tender activity, not a processor's fee-netted or timing-adjusted statement. Negative noncash amounts represent an explicitly normalized net outgoing flow, not a collection success. A real settlement bridge must explicitly reconcile gross/net, fee, cutoff, value-date, and return behavior before applying these fields.

`observed_minor` may be null; this produces a missing-evidence finding and no numerical variance. Reused declared deposit evidence references are flagged independently of batch assignment reuse. No bank statement or source file is automatically downloaded or authenticated.

## Error classes

Structural ambiguity returns `InputError` and prevents a usable report. Economic inconsistency is retained as a finding while original supplied rows remain visible. A malformed input and an inconsistent but readable input are therefore distinguishable. The valid clean status means only that this engine found no exceptions within its documented model; it does not imply source completeness or production readiness.

### Timestamp profile

Dates/times require uppercase `T` and `Z` or an explicit `±HH:MM` offset, mandatory seconds, and at most six fractional digits. Numeric offset hours must be 00–23 and minutes 00–59; overflowing values are rejected rather than normalized. Leap seconds, timezone-name annotations, lowercase separators, and longer fractional precision are not supported. This is a declared subset, not a claim to implement the complete RFC 3339/RFC 9557 formats. The engine compares UTC instants, not local business-calendar labels.
