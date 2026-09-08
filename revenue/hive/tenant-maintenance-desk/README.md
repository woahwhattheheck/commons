# Tenant desk

A runnable, shared maintenance workspace for small property managers. Residents or operators can record a repair with photos; the operator assigns an appointment, replaces an unavailable vendor, and records the resolution. The tenant-status view shows the current appointment and the complete change history rather than a stale confirmation.

Implements Hive demand `bm-hive-20260908-014`. Built by ASTRA-HEMLOCK in a cloud workspace. Existing Hive products and shared host code are unchanged.

## Run the workspace

Python 3.10 or later is the only runtime dependency. Run in the chosen cloud runtime; keep its data directory outside the source checkout.

```sh
cd revenue/hive/tenant-maintenance-desk
python server.py --db /path/to/runtime-data/tenant-desk.sqlite --port 8089 --demo
```

Open `http://127.0.0.1:8089` in that runtime. `--host` configures the listening interface; the default is loopback. `--demo` adds explicitly fictional records and is repeat-safe. Omit it for an empty database. Restarting with the same database preserves requests, original photo bytes, vendors, appointments, and history.

This is a **shared workspace**, not a private multi-tenant portal. The tenant-status view is a presentation view, not an isolation boundary. No sign-up, service keys, or external accounts are required. Keep personal tenant information out of public demos, public repositories, and public deployments. No customer database is included in this source package.

## Complete a repair

In **Properties & vendors**, add a property and its FAQ/contact instructions, then add vendors and their trades. In **Maintenance queue**, create a request, choose its priority, and optionally attach up to three original PNG/JPEG/WebP photos (2 MiB each). The priority queue puts emergency flags and urgent requests first, with closed requests separate.

Select a request and schedule an available vendor. The browser displays local appointment times; the database stores normalized UTC instants. Adjacent appointments are allowed, but overlapping active appointments for the same vendor are rejected. A failed replacement leaves the existing appointment intact.

Mark an assigned vendor unavailable. Each affected appointment is cancelled and its request enters **Needs replacement**. The tenant view immediately reflects that saved state on refresh; it does not keep displaying the cancelled appointment as current. Choose another available vendor and save the replacement. Closing the request records the resolution and completes its active appointment. Reopening preserves the prior history.

**Open tenant status** creates a fragment link to the selected request. That view includes property information, the current appointment or replacement-needed message, original-photo download links, and closure/history. Nothing sends email or SMS; the operator uses their existing communications process to share an update. Refresh reads the latest saved records; there is no background polling or external dispatch.

For immediate danger, contact local emergency services or the property's emergency contact. An emergency flag here prioritizes the queue; this application is not monitored emergency dispatch.

## Persistence and integration

Every command runs inside one `BEGIN IMMEDIATE` SQLite transaction. Successful operation IDs and command digests are stored with the original response, so a retry does not create a second request or appointment. Reusing an operation ID with a different payload returns a conflict. The browser preserves its operation ID when a request fails before a successful response, within that page session.

Request edits require the current integer version. Stale versions return HTTP 409 without replacing current data. Vendor unavailability cancels active appointments and advances affected request versions in the same transaction. Original photos are database blobs, so failed intake does not leave orphan files. Photo handling checks file signatures and size; it does not perform image decoding, image-quality review, or malware scanning.

`GET /api/state` returns properties, vendors, and request details, including the current appointment, history, and photo metadata. `GET /api/photo/<id>` downloads the exact stored image bytes. `GET /api/export` exports the queue and metadata as JSON; **it is not a restorable backup and does not contain photo bytes or the retry journal**. Preserve the SQLite database using the runtime's consistent SQLite backup process; do not copy only the database file while ignoring its active WAL.

`POST /api/command` accepts UTF-8 JSON in this envelope:

```json
{
  "operation_id": "a-stable-id-for-this-specific-attempt",
  "command": {
    "type": "request",
    "property_id": "an-existing-property-id",
    "unit": "2B",
    "description": "Kitchen tap drips after closing.",
    "urgency": "routine",
    "photos": []
  }
}
```

Command types and fields:

| Type | Fields besides `type` |
| --- | --- |
| `property` | `name`, optional `faq` |
| `faq` | `property_id`, `faq` |
| `vendor` | `name`, `trade` |
| `vendor_availability` | `vendor_id`, boolean `available` |
| `request` | `property_id`, `unit`, `description`, optional `urgency`, optional `photos` |
| `schedule` | `request_id`, `version`, `vendor_id`, timezone-aware `start`/`end`, optional `reason` |
| `close` | `request_id`, `version`, nonempty `closure` |
| `reopen` | `request_id`, `version`, nonempty `reason` |

Each photo object contains `name` and raw image bytes encoded in `base64`. The HTTP body limit is 9 MiB. JSON duplicate keys, non-finite numbers, malformed shapes, and unsupported photo signatures receive explicit errors. Errors use `{"error":"..."}` with 400 for invalid input, 404 for missing records, 409 for stale/conflicting changes, 413 for oversized HTTP bodies, and 415 for unsupported content types. A missing foreign-key reference during intake returns 409.

## Validation

```sh
python -m unittest -v test_desk.py
node --check app.js
```

The dependency-free suite passes **28 tests**, including real temporary SQLite databases, exact photo persistence/download, reopen/restart, concurrent retry and booking races, stale versions, rollback on malformed multi-photo intake, and actual loopback HTTP endpoints.

Browser checks require Playwright and Chromium. They use the real application JavaScript and actual database/HTTP implementation, not substituted business logic:

```sh
python browser_check.py -v
```

`CHROMIUM_PATH` selects a system Chromium executable. `SHOT_DIR` optionally saves screenshots. In this delivery's cloud container, direct Chromium navigation returned `ERR_BLOCKED_BY_ADMINISTRATOR`; it is **not claimed validated**. The separate offline DOM-to-HTTP bridge mode passes **4 checks** at 1280 px and 390 px widths: the full customer workflow and literal-text rendering on each. This mode leaves browser policy unchanged, renders the actual source HTML/JavaScript, and forwards fetch calls to the real loopback server. It does not establish direct browser network/download transport or a deployed public URL.

```sh
BROWSER_HTTP_BRIDGE=1 CHROMIUM_PATH=/usr/bin/chromium \
  SHOT_DIR=/path/to/screenshots python browser_check.py -v
```

In bridge mode, photo link rendering and original HTTP bytes are checked separately. Screenshots were visually inspected; queue and tenant views fit both measured viewport widths without horizontal overflow. No repository-wide battery result is implied.

## Customer handoff

The proposed offer in the source demand is $500 setup plus $99/month for an initial property portfolio. This is a proposed service price, not booked revenue or a customer commitment. The next customer step is an operator walkthrough with fictional records, followed by property/vendor setup and an agreed operating/communications process in the customer's chosen runtime. No hosting, payment, outreach, or provider account was provisioned by this contribution.

Demand thread: https://tokenjunkielabs.slack.com/archives/C0BV6G7Q3L7/p1788849792368269

The HTTP adapter composes the existing Hive Fleetline transport pattern (`revenue/hive/rental-operations/server.py`, blob `62044e5e231c0e3f66a8bfeb52f5fef1dfbdb7c0`). Its files and business logic are unchanged. This package adds only its own directory and a publication receipt.
