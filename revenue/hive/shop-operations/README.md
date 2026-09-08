# Shop Operations Desk

A runnable local merchant workspace for Hive demand `bm-hive-20260908-032`.
Prepare source-linked catalog listings, allocate customer orders and creator
samples from the same stock, record shipment handoffs, inspect partial returns,
and export the resulting inventory and order records. Python standard library
only for the application; SQLite stores the work across restarts.

This is a working import/export operations desk, **not a connected TikTok Shop
app**. It does not publish a marketplace listing, send a creator/customer message,
ship a parcel, collect payment, issue a refund, or update remote stock. Those
operations remain in the merchant's existing tools. No merchant, provider
installation, actual order, or revenue is claimed by the supplied fixtures.

## Run

Requires Python 3.10 or later. From this directory:

```sh
python shop_ops.py --db ./workspace.sqlite3 serve
```

Open `http://127.0.0.1:8765`. The database is created if absent; restart with the
same `--db` path to continue the workspace. `--port` and `--host` are available
on `serve`. Anyone able to reach the server can read and change this workspace;
there is no login or merchant isolation. This is one merchant workspace, not a
hosted multi-tenant service. Keep real customer data out of public repositories.

The dashboard supports catalog import, product editing, receipts, multi-line
orders, sample allocations, cancellation, fulfillment, partial returns, listing
and inventory export, and a movement history. Product source links and copy are
operator-supplied. Unknown attributes stay explicit, rather than generated facts.
A ready/listed record requires description text and cleared uncertainty notes;
this is a completeness check, not independent verification of product claims.

## Complete a workflow

1. Add a product with its SKU, factual listing copy, merchant/specification source,
   price in minor currency units (for example, 2400 USD = $24.00), and listing
   record. `listed` means the operator recorded that state, not that an API
   confirmed a listing. Product SKUs are immutable; use Edit to change metadata.
2. Receive units against a delivery reference. Each `(reference, SKU)` is unique;
   separate actual deliveries need separate references. The same reference can
   cover multiple SKUs. Corrections to an already-posted receipt are not an
   implemented operation; do not enter a duplicate receipt as a correction.
3. Reserve an order using a unique external order ID and one `SKU,quantity` per
   line. Choose Creator sample to allocate samples with the identical stock
   accounting. Recipient fields are references, not a messaging integration.
4. After physical handoff, enter the shipment/handoff reference and record
   fulfillment. Cancellation releases a reserved allocation. A fulfilled order
   cannot be cancelled in this desk; record returned units instead.
5. After inspecting a return, record its unique return-line ID, fulfilled order,
   SKU, quantity and explicit restock/non-restock outcome. Partial returns can
   be recorded separately. Use separate return-line IDs for separate SKUs.
6. Export inventory/listing CSV and order/line CSV for the merchant's existing
   workflow. These are this desk's schemas, not advertised as official TikTok
   import templates. A merchant-specific mapping and a real installation are
   the next integration work, not completed here.

The test example receives 10 units, fulfills four, restocks two returned units,
records one damaged return without restocking, and fulfills one creator sample.
The result is **seven on hand, zero reserved, seven available**, reconciled from
the actual movement rows. All names and source URLs in examples are fictitious.

## Catalog import and command API

A catalog file is a JSON array of metadata objects, or an object containing
`products`. New SKUs use `version: 0`; existing SKUs use the version exported in
`GET /api/state`. Import applies every row in one transaction or none. Duplicate
SKUs within one import are rejected. Stock fields in metadata imports are not
applied; receipt/reservation/fulfillment/return operations own quantities.

`sample_catalog.json` is an explicitly synthetic import suitable for trying the
UI on a new database. `example.invalid` links are placeholders, not live catalog
sources or endorsements.

Each mutation is `POST /api/command` with a JSON body:

```json
{
  "key": "merchant-receipt-20260908-001",
  "action": "receive",
  "data": {"sku": "BAG-01", "quantity": 10, "reference": "delivery-001"}
}
```

Supported commands and payloads:

| Action | Data |
| --- | --- |
| `product` | One product metadata object, including expected `version` |
| `catalog` | `products`: nonempty list of product metadata objects |
| `receive` | `sku`, positive integer `quantity`, unique receipt `reference` per SKU |
| `order` | unique `id`, `kind` (`sale` or `sample`), `recipient_ref`, `lines` of `sku` and `quantity` |
| `fulfill` | order `id`, nonempty `shipment_ref` |
| `cancel` | reserved order `id` |
| `return` | unique return-line `id`, `order_id`, `sku`, `quantity`, explicit boolean `restock`, optional `note` |

Command keys are durable in SQLite. **Retry the identical key and payload after
an uncertain response.** It returns the original result even after a restart;
reusing a key with different data is a conflict. Successful receipt references,
order IDs and return IDs cannot be inserted again under a new key. Repeated
fulfill/cancel of an already-matching state does not move stock again. The UI
keeps an uncertain request and its key in the current tab for exact retry; it
does not persist that pending browser request across tab closure. Use the state
view and the integration's retained request key to reconcile after closure.

For command-line operation, save one complete command object to a file:

```sh
python shop_ops.py --db ./workspace.sqlite3 apply command.json
python shop_ops.py --db ./workspace.sqlite3 export > operational-snapshot.json
```

`GET /export/{table}.csv` exports `products`, `orders`, `lines`, `returns`,
`return_lines`, `receipts`, or `movements`. CSV prefixes formula-like text with
an apostrophe for spreadsheet handoff; JSON retains raw strings. JSON snapshots
are operational exports, not full database backups: the idempotency table is
not included. For a full backup, stop the server and copy the SQLite database
with any remaining WAL/SHM sidecars as a unit, or use SQLite's online backup API.
Do not restore a JSON export expecting original retry history to be present.

## Accounting and concurrency

`available = on_hand - reserved`. Reservations increase reserved only;
fulfillment decreases both on-hand and reserved; cancellation decreases reserved
only; inspected restock increases on-hand. Non-restock returns are retained in
the return tables without entering sellable stock. Samples use the same rules.
Order lines retain the price/currency at reservation, not the latest catalog
price. No exchange conversion, tax, shipping charge, refund or payment ledger is
computed.

All mutations use `BEGIN IMMEDIATE`, foreign keys, inventory consistency checks,
and a durable operation/result table in the same transaction. Multi-SKU orders
and catalog imports roll back together. Product metadata updates require the
current version; stock movements also advance that version, so stale editors
must reload rather than replace fresh data. Snapshots read one transaction.
Quantities and minor-unit prices are integers from zero through 1,000,000,000;
individual movement and order quantities must be positive. JSON bodies are
bounded to 2 MB. Network binding and SQLite storage remain operator choices.

## Executed validation

```sh
PYTHONWARNINGS=error::ResourceWarning python -B -m unittest -v test_shop_ops
```

The delivered runtime passed 27 methods on Python 3.13.5 in the provided cloud
container. These use real temporary SQLite files, threads, local HTTP requests
and CLI subprocesses, including 12 concurrent reservations for five units,
20 identical receipt retries, concurrent return caps, malformed data, partial
returns, import rollback, replay after restart, and ledger reconstruction.

An optional browser-control suite needs Playwright and installed Chromium:

```sh
CHROMIUM_PATH=/usr/bin/chromium python -B -m unittest -v test_browser
```

Eight methods passed against actual Chromium DOM and File objects with **explicit
fetch and UUID test adapters**. These exercise form typing, multi-line samples,
exact retry payloads, conflict handling, return inspection, literal text,
editing versions, mobile overflow, catalog files and fulfillment controls. The
suite skips when the optional browser dependencies are absent. Native Chromium
navigation to the running loopback server returned
`net::ERR_BLOCKED_BY_ADMINISTRATOR` in this environment; native browser-to-HTTP
end-to-end acceptance is **not** claimed. Separate real HTTP tests are green.

The browser suite found and covered the retry button's hidden-state styling;
`[hidden]` now retains priority over the general button display rule. No hosted
CI success, deployed site, remote integration or whole-repository test result is
claimed by these local results.
