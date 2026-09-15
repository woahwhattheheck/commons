# Commercial Waste Container Route & Service Exception Operations Desk

A local-first operations desk for regional commercial waste/container haulers that run recurring scheduled service across multiple customer sites.

**Commercial hypothesis:** $3,500 setup + $399/month. This is an offer hypothesis, not buyer acceptance or booked revenue. The software does not send outreach, dispatch vehicles, call providers, or mutate payments.

## What it does

- imports owner-authored customer → site → container → recurring plan data;
- generates a deterministic daily route from weekday plans;
- tracks each stop as `PENDING`, `SERVICE_CONFIRMED`, `EXCEPTION_OPEN`, `RESOLVED_NO_CHARGE`, or `RESOLVED_BILLABLE`;
- requires skipped/blocked service exceptions to be resolved before invoice drafting;
- computes money only as integer minor units;
- isolates invoice drafts by customer and period;
- records immutable SQLite event receipts;
- makes mutating commands idempotent by operation key: identical retry returns the prior result, changed input under a used key fails;
- survives process restart and serializes concurrent writers with `BEGIN IMMEDIATE`;
- exports deterministic JSON, CSV, and Markdown route views.

It intentionally does **not** choose routes, navigate vehicles, make compliance decisions, send messages, charge cards, or infer that a customer accepted the commercial offer.

## Quick proof

```bash
cd revenue/hive/commercial-waste-route-operations
python test_desk.py
python demo.py
```

The synthetic demo creates two customers / three sites, records one blocked-access exception, proves the premature invoice is blocked, resolves it as no-charge, and then produces separate ACME and BETA invoice drafts.

## CLI

Initialize:

```bash
python desk.py --db ./desk.sqlite3 init \
  --manifest ./sample_manifest.json \
  --op-key manifest-2026-09-14
```

Generate the Monday route:

```bash
python desk.py --db ./desk.sqlite3 route \
  --date 2026-09-14 \
  --op-key route-2026-09-14
```

Record service or an exception:

```bash
python desk.py --db ./desk.sqlite3 record \
  --stop-id 'stop:2026-09-14:PLAN-ACME-DOWNTOWN' \
  --outcome SERVICED \
  --op-key stop-acme-downtown-2026-09-14

python desk.py --db ./desk.sqlite3 record \
  --stop-id 'stop:2026-09-14:PLAN-ACME-MARKET' \
  --outcome SKIPPED \
  --exception-code BLOCKED_ACCESS \
  --op-key stop-acme-market-2026-09-14
```

Resolve an exception:

```bash
python desk.py --db ./desk.sqlite3 resolve \
  --stop-id 'stop:2026-09-14:PLAN-ACME-MARKET' \
  --resolution NO_SERVICE_NO_CHARGE \
  --op-key resolve-acme-market-2026-09-14
```

Create an invoice **draft** only after all routed service states for that customer/period are settled:

```bash
python desk.py --db ./desk.sqlite3 invoice \
  --customer-id ACME \
  --period-start 2026-09-14 \
  --period-end 2026-09-14 \
  --op-key invoice-acme-2026-09-14
```

Export:

```bash
python desk.py --db ./desk.sqlite3 export-route --date 2026-09-14 --format json
python desk.py --db ./desk.sqlite3 export-route --date 2026-09-14 --format csv
python desk.py --db ./desk.sqlite3 export-route --date 2026-09-14 --format markdown
python desk.py --db ./desk.sqlite3 events
```

A one-customer synthetic manifest is included as `sample_manifest.json`.

## Manifest shape

```json
{
  "customers": [
    {
      "id": "ACME",
      "name": "Acme Coffee Group",
      "currency": "USD",
      "sites": [
        {
          "id": "ACME-DOWNTOWN",
          "name": "Downtown Cafe",
          "containers": [
            {
              "id": "ACME-DOWNTOWN-8YD",
              "label": "Rear 8yd",
              "container_type": "front-load 8yd",
              "plans": [
                {
                  "id": "PLAN-ACME-DOWNTOWN",
                  "weekday": 0,
                  "service_code": "RECURRENT_PICKUP",
                  "price_minor": 12900
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

`weekday` is Python's weekday convention (`0` Monday … `6` Sunday). `price_minor` is a non-negative integer such as cents for USD.

## Operational invariants

1. **No premature billing.** Any `PENDING` or `EXCEPTION_OPEN` stop for the customer and invoice period blocks the draft.
2. **No float money.** Plan prices and invoice totals are integer minor units.
3. **One operation key, one input.** Exact retry is stable; changed input with the same key raises `OperationConflict`.
4. **Terminal-stop race safety.** The SQLite writer transaction checks current stop state before transition; concurrent terminal attempts yield one winner.
5. **Immutable event rows.** SQLite triggers reject event update/delete.
6. **No external side effects.** Provider calls, outreach, vehicle dispatch/navigation, and payment mutation are outside this product.

## Product boundary

This is operations software, not a hauling, routing, regulatory, safety, or environmental decision engine. Operators remain responsible for real-world service facts, dispatch/navigation, applicable rules, and billing approval. Invoice output is explicitly a **draft**; it does not charge or send anything.
