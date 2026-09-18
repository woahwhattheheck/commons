# Revenue Collection Desk

Internal, deterministic collection-state compiler for sanitized retained evidence.

It keeps these facts separate:

- submitted work is not accepted work;
- accepted work is not paid work;
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

Collection-route events are orthogonal:

- `COLLECTION_CONTACT_SENT` requires an explicit `cooldown_until`;
- `DELIVERY_CONFIRMED` records delivery evidence but never changes financial state;
- `DELIVERY_BOUNCED` marks the route dead and yields `ROUTE_REPAIR_REQUIRED`;
- `ROUTE_REPAIRED` clears the dead route;
- `COLLECTION_RELEASED` is the explicit retained-evidence generation that can end
  a prior contact DNR. Mere passage of time never does.

## CLI

```bash
python -m tools.revenue_collection_desk compile examples/collections.json --pretty
python -m tools.revenue_collection_desk queue examples/collections.json
python -m tools.revenue_collection_desk verify examples/collections.json report.json

python -m unittest -v test_revenue_collection_desk.py
python -O -m unittest -v test_revenue_collection_desk.py
python -m py_compile tools/revenue_collection_desk/*.py test_revenue_collection_desk.py
```

Input is strict JSON: duplicate keys and non-finite constants are rejected; unknown
fields fail closed; amounts are exact positive decimal strings; event timestamps
must be strictly increasing within a claim and cannot be later than ledger `as_of`; source references are opaque bounded
identifiers plus SHA-256 digests, never email bodies or secrets.

The report sorts claims by `claim_id`, so claim-list order does not change the
receipt. Event order is evidence chronology and is intentionally validated rather
than reordered.

## Authority

This package performs no network calls and grants no authority to send email/Slack,
submit claims, create invoices, move money, mutate wallets/banks/providers, or
recognize unsettled cash. `AUTHORITY` is hard-false. Customer/public artifacts
should not expose this internal control surface.
