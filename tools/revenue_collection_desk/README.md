# Revenue Collection Desk

Internal, deterministic collection-state compiler for sanitized retained evidence.

It keeps these facts separate:

- submitted work is not accepted work;
- accepted work does not prove the proposed compensation was agreed or allocated;
- confirmed compensation entitlement is not paid work;
- a provider/email statement that payment was sent is not bank settlement;
- a hosted token balance or reference valuation is not USD cash;
- a sent collection message is not proof of delivery;
- a hard-bounced route is not a successful contact;
- silence never authorizes another collection message.

## Lifecycle

Financial states:

`WORK_SUBMITTED` → `ACCEPTED_AWAITING_PAYMENT` → optionally
`PAYMENT_ASSERTED_HOLD` → `PAYMENT_AVAILABLE` → `SETTLED_CASH`.

`DISPUTED` and `CLOSED_NO_PAY` are explicit alternatives. Direct settlement from an
accepted/asserted state is allowed only when a retained `SETTLED_CASH` event supplies
the exact settlement currency and amount. The compiler never calculates FX or
token-to-USD value.

Compensation-basis evidence is orthogonal to work acceptance. A receipt-bound
`ENTITLEMENT_CONFIRMED` event must carry `entitlement_instrument` and
`entitlement_amount`; the instrument must exactly match the claim and the amount
must be the same exact decimal value. Its source reference/digest and bound economics
are retained as `entitlement_evidence` and folded into `economics_receipt_sha256`.
That prevents a generic acceptance or unrelated compensation receipt from making a
different claim collectible. Without valid bound evidence, accepted work remains
`VERIFY_ENTITLEMENT`, is counted only in
`accepted_unconfirmed`, and cannot enter the collection route. A proposed quote or
merge by itself is not entitlement evidence. Direct retained payment evidence may
still advance the financial lifecycle without this event.

Collection-route events are orthogonal:

- `COLLECTION_CONTACT_SENT` requires confirmed entitlement plus an explicit `cooldown_until`;
- `DELIVERY_CONFIRMED` records delivery evidence but never changes financial state;
- `DELIVERY_BOUNCED` marks the route dead and yields `ROUTE_REPAIR_REQUIRED`;
- `ROUTE_REPAIRED` clears the dead route;
- `COLLECTION_RELEASED` is the explicit retained-evidence generation that can end
  a prior contact DNR. Mere passage of time never does.

## CLI

From a checkout containing this version, use the included fictional example:

```bash
python -m tools.revenue_collection_desk compile tools/revenue_collection_desk/example.json --pretty
python -m tools.revenue_collection_desk queue tools/revenue_collection_desk/example.json
python -m tools.revenue_collection_desk verify tools/revenue_collection_desk/example.json report.json

python -m unittest -v test_revenue_collection_desk test_revenue_collection_desk_exact test_revenue_collection_desk_rehearsal
python -O -m unittest -v test_revenue_collection_desk test_revenue_collection_desk_exact test_revenue_collection_desk_rehearsal
```

`compile` emits its report to stdout. For `verify`, supply a saved copy of that
report as `report.json`; do not overwrite the ledger. Verification exits 0 for an
exact replay, 1 for a different report, and 2 for invalid input or an I/O error.
`queue` emits Markdown to stdout. No command sends a collection message.

Input is strict JSON: duplicate keys and non-finite constants are rejected; unknown
fields fail closed; amounts are exact positive decimal strings; event timestamps
must be strictly increasing within a claim; source references are opaque bounded
identifiers plus SHA-256 digests, never email bodies or secrets.

The report sorts claims by `claim_id`, so claim-list order does not change the
receipt. Event order is evidence chronology and is intentionally validated rather
than reordered.

## Exact totals and replay

Receivable buckets are summed separately by instrument; supplied settlements are
summed separately by settlement currency. Aggregation derives enough precision
from the finite input coefficients, finest input exponent and term count to retain
every digit and carry. It runs in a fresh private Decimal context. Caller precision,
rounding, exponent bounds, traps and existing flags cannot change the result or its
receipt, and the caller's context is not mutated. Original amount/evidence strings
remain intact; only aggregate display strings lose insignificant trailing zeros.
There is no float conversion, fixed two-place currency rounding or mixed-currency
sum. Valid amounts can contain large integers and at most 18 fractional places.

Older reports produced by a rounded total will correctly fail exact replay under
this version. Recompile the retained ledger; do not edit totals or relabel an old
receipt as a new one. Reports whose old totals were already exact remain identical
when all other source behavior and input evidence are unchanged.

## Fictional operator rehearsal

```bash
python -m tools.revenue_collection_desk.rehearsal
python -m tools.revenue_collection_desk.rehearsal --json
```

Twelve scenarios call this actual compiler at precisions 3, 28 and 80. The readable
view explains acceptance without compensation, bound/mismatched entitlement,
payment holds, token availability, explicit settlement, delivery/silence, bounced
routes, closed unpaid work, disputes and the large-value lost-cent regression.
The JSON view includes every fictional ledger, observed compiler result, replay
check and tampered-report rejection. Failure exits 1 even under `python -O`.
Neither view writes files or contacts any external service.

The source-bound execution record is [EXECUTION.md](EXECUTION.md). All example
records, counterparties, references and digests are fictional. A deterministic
receipt binds the supplied bytes; it does not authenticate a real source or prove
that money moved. `DONE` alone does not mean paid: inspect financial state and the
explicit `settled_cash_by_currency` field.

## Authority

This package performs no network calls and grants no authority to send email/Slack,
submit claims, create invoices, move money, mutate wallets/banks/providers, or
recognize unsettled cash. `AUTHORITY` is hard-false. Customer/public artifacts
should not expose this internal control surface.
