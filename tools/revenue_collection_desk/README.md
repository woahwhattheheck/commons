# Revenue Collection Desk

Offline, stdlib-only control plane for **sanitized retained evidence** about money owed to the Commons. It separates work acceptance, payment assertions, hosted availability, and exact settlement so the swarm does not count assertions as cash or spam a counterparty after silence.

## Authority boundary

This package does not send email or Slack, submit claims, create invoices, access providers, touch wallets/banks, move money, perform FX/token conversion, or decide accounting revenue. `COLLECTION_ELIGIBLE` means only that retained evidence includes an unexpired explicit collection release and the local DNR/route rules allow a human-controlled next step. It is not send authorization outside that evidence context.

## Source contract

`source/v1` contains an `as_of` UTC timestamp and claims with immutable `claim_id`, `counterparty_id`, `work_ref`, `instrument`, exact decimal-string `amount`, optional `reference_value_usd`, and retained evidence events. Opaque refs only: do not paste emails, secrets, wallet keys, bank details, or message bodies.

Financial states are ordered evidence, never inferred from route delivery:

`WORK_SUBMITTED -> ACCEPTED_AWAITING_PAYMENT -> PAYMENT_ASSERTED_HOLD -> PAYMENT_AVAILABLE -> SETTLED_CASH`

`DISPUTED` and `CLOSED_NO_PAY` are explicit alternatives. Every financial event repeats the exact claim economics; conflicts fail closed. A `SETTLED_CASH` event requires an opaque settlement reference. Totals are emitted **per instrument only**. Reference USD valuations are metadata and never enter cash totals.

Collection evidence is orthogonal. A release has an explicit validity window. A delivered contact can carry a DNR timestamp. Silence after a delivered contact stays `WAIT_REPLY` until a *newer* explicit release exists. `BOUNCED` or `DEAD` delivery becomes `ROUTE_REPAIR_REQUIRED`; repair alone does not authorize contact.

## Next actions

The compiler emits only: `WAIT_HOLD`, `WAIT_REPLY`, `VERIFY_AVAILABLE`, `VERIFY_SETTLEMENT`, `COLLECTION_ELIGIBLE`, `ROUTE_REPAIR_REQUIRED`, `DONE`, or `HOLD_CONFLICT`.

## Run

From repository root:

```bash
python -m py_compile tools/revenue_collection_desk/*.py tests/test_revenue_collection_desk.py
python -m unittest -v tests.test_revenue_collection_desk
python -O -m unittest -v tests.test_revenue_collection_desk

python -m tools.revenue_collection_desk.cli compile \
  tools/revenue_collection_desk/example.synthetic.json /tmp/revenue-collection-demo
python -m tools.revenue_collection_desk.cli verify \
  tools/revenue_collection_desk/example.synthetic.json /tmp/revenue-collection-demo
```

Compile creates a new directory only: `report.json`, `queue.md`, and `receipt.json`. Verification recompiles all artifacts exactly. Existing destinations are refused; verifier inputs must be ordinary non-symlink files. JSON duplicate keys, numeric fractions/non-finite numbers, event duplicates, future evidence, conflicting economics, and illegal financial transitions fail closed.

The synthetic example intentionally includes a USD accepted claim with explicit collection release and an RTC payment assertion still in hold. Its `$75.00` RTC reference valuation never creates a USD cash row.
