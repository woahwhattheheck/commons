# Commercial Laundry Route & Linen Custody Operations Desk

Owner-authorized working-product lane for **Commons #14558**. Original product/spec/commercial credit remains **Z-Sol-22 / GPT-5.6 Sol**; recovery lineage includes **Z-IronWeave-1823-R7K5** and the 2026-09-17 Z-Sol recovery take. This carrier implements and finalizes the abandoned source lane without changing the original economics or authority ceiling.

## Buyer and commercial hypothesis

Independent commercial laundry / linen operators serving recurring multi-site business accounts.

- proposed setup: **$4,500**
- proposed ongoing service: **$499/month**
- state: **`PROPOSED_NOT_ACCEPTED`** until a customer actually accepts it

No acceptance, booked/earned revenue, receivable, savings, payment, or cash is implied by this repository.

## What the desk does

`laundry_desk.py` is a standard-library-only SQLite operations desk with:

- owner-authored customers, sites, dated service agreements, item-level exact-cent pricing;
- dated recurring service plans and a deterministic daily route manifest;
- pickup container custody and item counts;
- plant-processing good/damaged counts;
- delivery container custody and item counts; pickup/delivery container-set discontinuities become explicit custody exceptions;
- explicit `PROCESS_COUNT_MISMATCH`, `DAMAGE`, `DELIVERY_COUNT_MISMATCH`, `CUSTODY_MISSING`, and `CUSTODY_UNEXPECTED` exceptions;
- invoice-readiness blocking until every exception is explicitly resolved by an operator;
- exact-cent, integer-only invoice **DRAFTS**;
- operation-key idempotency: exact replay is a no-op; changed-content reuse fails closed;
- immutable event history enforced by SQLite triggers;
- restart safety plus transaction/unique-key fences for competing terminal actions;
- deterministic route and customer JSON/CSV/Markdown renderers; customer CSV neutralizes formula-leading owner text at projection time and Markdown renders owner labels literally;
- bounded deterministic generated IDs: readable derived IDs when they fit, SHA-256-bound IDs when a valid component tuple would exceed the public 255-character grammar;
- integrity verification binding operations to event payload digests.

### Authority ceiling

All outputs keep these authorities false:

- customer messaging;
- route/navigation/provider calls;
- accounting mutation;
- payment mutation;
- deployment;
- revenue assertion;
- sanitation certification;
- laundering-quality inference.

This desk records owner-supplied operational evidence. It does **not** infer cleaning quality, certify hygiene, contact customers/providers, optimize navigation, post invoices to accounting systems, charge funds, or claim revenue.

## State machine

A route stop moves monotonically:

`MANIFESTED -> PICKED_UP -> PROCESSED -> DELIVERED -> INVOICE_DRAFTED`

Exact retries with the same operation key and canonical payload return the stored result without appending a new event. A reused key with changed content raises `IdempotencyConflict`. Separate operation keys racing a terminal transition are serialized under `BEGIN IMMEDIATE`; after one commits, the other sees a non-admissible state and fails closed.

Processing accounts for pickup quantity as `processed + damaged`. Any mismatch creates an exception; any non-zero damage creates an explicit damage exception. Delivery compares delivered quantity to processed-good quantity **and** reconciles the exact pickup/delivery container sets. Missing or unexpected container custody opens deterministic exceptions. Legitimate repack/transfer therefore requires an explicit operator resolution record before invoicing rather than being silently accepted. Invoice drafting requires `DELIVERED`, zero open exceptions, and exactly one dated price authority for every delivered item.

## Synthetic two-account demo

```bash
cd revenue/hive/commercial-laundry-operations
python demo.py
```

The demo creates two recurring accounts on one Monday route. Account A runs cleanly to invoice DRAFT. Account B deliberately produces damage, demonstrates invoice blocking, records explicit operator resolution, then drafts its invoice. It reopens the SQLite file in a fresh `LaundryDesk` instance and verifies event/operation integrity plus deterministic export hashes.

## Tests

```bash
cd revenue/hive/commercial-laundry-operations
python -m unittest -v test_laundry_desk.py
python -O -m unittest -v test_laundry_desk.py
```

The hostile suite covers deterministic two-account route creation, exact replay, changed-content reuse, processing shortage, damage, delivery mismatch, custody discontinuity/restart/resolution, integer-cent validation, overlapping pricing authority, maximum accepted identifier lifecycles, resolvable near-bound exceptions, restart/export stability, projection-only CSV formula neutralization, Markdown literal safety/determinism, hard-false authorities, immutable event history, event/operation integrity, concurrent delivery terminal races, duplicate exception resolution, duplicate invoice terminal actions, create-exclusive file export, and the end-to-end demo.

## Read-only CLI / exports

```bash
python cli.py /path/to/desk.sqlite3 integrity
python cli.py /path/to/desk.sqlite3 route-snapshot 'route:2026-09-21:route-louisville'
python cli.py /path/to/desk.sqlite3 customer-snapshot cust-alpha
python cli.py /path/to/desk.sqlite3 export-route 'route:2026-09-21:route-louisville' ./handoff
python cli.py /path/to/desk.sqlite3 export-customer cust-alpha ./handoff-customer
```

Export writes are create-exclusive (`open(..., "x")`) and refuse a symlink export directory; rerunning against an existing handoff fails rather than overwriting evidence.
