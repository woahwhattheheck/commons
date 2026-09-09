# Fleetline — rental operations workspace

A runnable first version of Hive demand `bm-hive-20260908-036` for operators
who already own and manage a small car or equipment fleet. It is working
booking software, not a hosted rental marketplace or payment service.

## Run in the approved execution environment

Python 3.10 or later and its standard library are enough for the product.
Use the existing private cloud workspace; this delivery does not provision
infrastructure or require work on the owner's computer.

```sh
cd revenue/hive/rental-operations
python server.py --db /path/to/private/fleet.sqlite --port 8086
```

Open `http://127.0.0.1:8086` in that environment's browser. The service binds
only to loopback and serves its own page and JavaScript. The default database
is `~/.fleetline/fleet.sqlite`, outside the source directory. Keep the database
and exports private. This first version is a single-workspace desk, not a
public multi-tenant service. It contains no external integrations, telemetry,
credentials, automated messages, or payment processing.

## Complete operator workflow

Add each physical asset separately, with an hourly or 24-hour rate and a
minimum number of charge units. Enter a customer booking or maintenance hold,
check availability, and save. The date-filtered schedule shows current status,
quote and revision. Edit reserved records, cancel them to release availability,
or record partial and completed handover/return checklists. Generate and copy
a current customer-message draft, print the schedule, and export the full
workspace including its audit history. Drafts are never sent by this app.

A synthetic example at $75.25 per started 24-hour day costs $75.25 for exactly
24 hours and $150.50 for 24 hours plus one microsecond. Rates and totals are
stored as integer cents. Quotes exclude taxes, deposits, delivery and other
charges; no payment or legal rental agreement is implied.

## Scheduling and data behavior

* Each asset has capacity one. Booking and maintenance intervals use the same
  atomic SQLite overlap check. End times are exclusive, so adjacent intervals
  are allowed. A maintenance hold cannot silently displace a booking.
* Concurrent writers cannot reserve the same interval twice. Record revisions
  prevent stale edits from overwriting a newer value. Repeated API requests
  with the same operation ID and exact command return the original result;
  reusing that ID with changed content returns a conflict. The browser retains
  an unchanged retry ID while its page remains open. After an ambiguous result
  or page reload, refresh the schedule before entering a replacement request.
* Existing bookings retain their original rate/minimum snapshot when an asset's
  rate changes. Rescheduling recalculates duration using that original rate.
  A different asset or booking kind requires cancellation and a new record.
* A completed handover requires the checklist items and allows only one physical
  handover per asset at a time. Return it before handing it over on another
  booking. A returned booking keeps its original reserved interval; an overdue
  physical return does not automatically extend the calendar interval. Review
  actual handover state before promising pickup. Returned/out bookings remain
  in the record; only reserved bookings/holds can be rescheduled or cancelled.
* Times are stored as UTC microseconds. API times need an explicit offset or
  `Z`, with no more than six fractional digits. The editor uses the browser's
  device timezone and the schedule displays the offset. Nonexistent local
  clock-change times are rejected. For the second occurrence of a repeated
  local hour, use the API with its explicit offset. Unchanged editor times
  preserve the original timestamp, including its fractional precision.
* Complete JSON exports contain assets, reservations, operation results and an
  append-only audit history. The export is a portable data record, not a
  one-click restore feature. Back up the SQLite file using SQLite's backup
  facility before replacing or moving a live workspace.

## API

`GET /api/state` returns current records. `GET /api/availability?start=...&end=...`
returns per-asset availability and quotes. `GET /api/message?id=...` creates an
unsent draft, and `GET /api/export` downloads the workspace.

`POST /api/command`, with `Content-Type: application/json`, accepts:

```json
{"operation_id":"your-stable-request-id","command":{"action":"save_asset","id":null,"expected_revision":0,"name":"Example lift","unit":"day","rate":"75.25","minimum_units":1,"notes":"Synthetic example"}}
```

Other command actions are `save_reservation`, `cancel`, and `checklist`.
The browser controller and tests show complete request shapes. Reads never
change the database. Writes, their audit event and retry result commit in one
transaction. Malformed or conflicting commands leave existing rows unchanged.

## Executed checks

```sh
PYTHONWARNINGS=error::ResourceWarning python -m unittest -v test_fleet.py
node --check app.js
# Optional development check; uses an existing Playwright + Chromium installation:
python test_browser.py
```

The 35 SQLite/HTTP tests cover real concurrent writers, unchanged retry after
reopening the database, maintenance blocking, interval boundaries, exact rate
arithmetic, timestamp precision, stale revisions, immutable quote snapshots,
handover/return constraints, exports and HTTP input handling.

The browser script exercised 17 checks with the actual UI, a real HTTP server
and SQLite: create asset, quote/book, reject overlap, maintenance availability,
handover/return, current draft, rate change, date filter, downloaded export,
390px layout, print view and server restart. In this cloud run native local-page
navigation was blocked, so it used an embedded DOM with a real-HTTP fetch bridge.
That establishes those rendered controls and backend operations, not native
origin/CSP/network loading, a public deployment, or customer acceptance. The
script reports its mode explicitly and preserves the distinction.

Only fictitious customer data was used. No customer, sale, payment, hosted
availability, live rental booking or outbound delivery is claimed.
## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../../agent-rescue.html)
- [$199 dealer diagnostic](../../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../../plant-downtime-handoff.html)

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
