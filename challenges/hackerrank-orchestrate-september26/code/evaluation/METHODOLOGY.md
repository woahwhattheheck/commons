# Evaluation methodology

The solution is deterministic-first. Model output is never trusted as a recommendation.
The final CSV can be audited from four stages: evidence normalization, fixed-rate financial
state reconstruction, recurrence/90-day forecast, and exhaustive safe-plan verification.

## Invariants

- `0 <= amount_safe_to_pay <= requested_amount`.
- Pending debits reduce capacity; pending credits do not increase it.
- Failed/cancelled rows and unrealized investment value are not spendable cash.
- Confirmed scheduled salary enters on its settlement date.
- Each candidate plan is replayed against all forecast cashflows; the balance may never
  fall below `minimum_balance_to_keep`.
- Installment schedules exactly preserve the supplied amount/count/date/frequency.
- Partial payment is exactly two payments and is considered only when permitted.
- Spending changes are limited to user-permitted, non-protected recurring events.
- A maximum of three spending changes can be emitted.

## Determinism and caching

Financial computations use `decimal.Decimal`. Evidence extraction is cached per request.
A cached run can be replayed with `--no-ai`, which makes the financial output independent of
later model nondeterminism while preserving the same extracted facts.
