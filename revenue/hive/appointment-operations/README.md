# Appointment Operations

A runnable, single-client workspace for Hive demand `bm-hive-20260908-028`.
Import sourced prospects, prepare editable messages, record actual replies,
suppress opted-out contacts, reserve local appointments against imported
availability, and export CRM and calendar handoffs. All messages remain unsent.

## Run

Python 3.10+ and its standard library are sufficient for the application and
26-method core suite. Run in the directory containing these files:

```sh
python desk.py --db workspace/client-one.sqlite3 --port 8768
```

Open `http://127.0.0.1:8768`. The listener is loopback-only. Stop with Ctrl+C.
Use a separate database and port for each client. This is not a hosted,
multi-tenant service; do not expose it through a public proxy. The database
contains plaintext contact data and reply history. Use fictional data for the
first walkthrough. No third-party requests, mail delivery or provider mutations
are performed by the application.

## Complete a fictional walkthrough

Create a campaign using an actual supplied offer and its source reference.
For the included example, use the name **Example operations walkthrough**, the
offer **A walkthrough of the supplied operations workflow**, and source
**fictional-offer-01**. Import this explicitly fictional prospect CSV:

```csv
email,name,company,source,relevance
alex@example.test,Alex,Example Workshop,fictional-source-01,Requested an operations walkthrough
```

Open the prospect. Enter a subject and body, or use the editable offer-based
starter. Review the source, claims and recipient before checking the review box.
The starter copies supplied fields; it does not research, invent or approve
claims. Download the reviewed, unsent CSV to inspect the draft.

Record an **Interested** reply using a fictional reply and source reference.
Replace the `consultant` resource's availability with this fictional export:

```csv
start,end,kind,source
2035-09-10T09:00:00-05:00,2035-09-10T12:00:00-05:00,free,fictional-calendar-export
2035-09-10T10:00:00-05:00,2035-09-10T10:30:00-05:00,busy,fictional-calendar-export
```

Book `09:00:00-05:00` to `09:30:00-05:00` on that date with a fictional exact-slot
confirmation reference. Download the `.ics` file. The appointment is persisted
locally, not reserved in a calendar provider. Times use explicit offsets and
normalize to UTC; naive times, fractional seconds and invalid offsets are
rejected. A slot must fit inside one free interval and cannot overlap a busy
interval, another resource booking, or the contact's other booking. Shared
calendar resource keys must be consistent across campaigns.

Record **Unsubscribe** or use the separate suppression form. The address is now
excluded from every future draft export and new booking in this client
workspace, including other campaigns and later reimports. Existing appointments
are retained for explicit operator review; active calendar exports are blocked.
Cancel locally to obtain a revised cancellation `.ics`, then manually reconcile
any existing provider event. No notification is sent. Refresh or restart the
application to verify persistence.

## Data and integration contracts

* Intake CSV requires `email,name,company,source,relevance`. Availability CSV
  requires `start,end,kind,source`; kind is `free` or `busy`. UTF-8/BOM, CRLF and
  quoted fields are supported, with 1-1000 complete rows per import. An invalid
  row rolls back the batch. Exact contact reimports do not duplicate records;
  conflicting existing contact details are rejected rather than overwritten.
* Email identity is conservatively case-folded. Suppression survives reimport
  and an interested reply does not override it. There is no reactivation button.
  Out-of-office and not-interested replies pause drafts until an actual later
  reply is recorded. Reply classification is manual, not inferred by a model.
* Draft revisions reject stale tab edits. Booking IDs support exact retry;
  a reused ID with different details is rejected. SQLite immediate transactions
  serialize booking decisions. Availability replacement is atomic and rejects
  changes that would contradict existing confirmed local appointments.
* `GET /state` and `GET /crm.json` return saved campaigns, contacts, enrollments,
  replies, suppression, availability, bookings and action history. This full
  handoff contains historical drafts, including suppressed contacts; it is not
  a send list. Preserve suppression semantics in any downstream integration.
* `GET /drafts.csv` rechecks suppression and review state at export time. It is a
  human-review spreadsheet export, with leading apostrophes on formula-like
  fields; do not treat those apostrophes as intended message text.
* `GET /calendar.ics?id=...` exports one event with a stable workspace/campaign
  identity and cancellation sequence. No METHOD, ORGANIZER or ATTENDEE is emitted;
  the file does not request an invitation send. CRLF, text escaping, UTC values
  and UTF-8-aware 75-octet folding follow RFC 5545 sections 3.1 and 3.3.11:
  https://www.rfc-editor.org/rfc/rfc5545.html
* `POST /api` accepts a JSON object with action `campaign`, `import`, `draft`,
  `reply`, `suppress`, `availability`, `book` or `cancel`. The browser and tests
  show complete request examples. Requests have a 2,000,000-byte limit and are
  restricted to the desk's own local origin. No authentication system is added.

Calendar snapshots can become stale outside this desk. Recheck the provider
before manually applying a handoff. Previously downloaded files cannot be
recalled or dynamically suppressed. Source/relevance notes document operator
input; they do not establish permission to contact anyone. Use the current owner
and client's instructions for any real outreach or provider integration.

The first version intentionally has no autonomous prospect discovery, live
provider adapters, recurring calendar rules, email sending, automated reply
classification, bid/payout flow or customer-installation claim. The next
customer step is an authorized single-client walkthrough with supplied contact,
reply and availability exports, followed by an explicitly scoped provider
integration where needed.

## Tests

```sh
python -m unittest -v test_desk
python -m py_compile desk.py test_desk.py
```

The 26 methods use real temporary SQLite files, concurrent writes and real local
HTTP, plus CSV/iCalendar assertions. No customer data or provider calls are used.

Optional browser-to-server smoke test (Playwright plus Chromium required):

```sh
python browser_smoke.py
```

`CHROMIUM_EXECUTABLE` can select an existing Chromium binary. Otherwise the script
uses a system `chromium` or Playwright's installed build. It tests the actual
browser workflow, downloads and 390px layout; it fails rather than silently
substituting a mock. In the build container, Chromium navigation was blocked by
administrator policy before the browser workflow ran. Thus the retained result
is **26 core tests passing; live browser interaction not verified here**.
The browser smoke source is provided for an environment permitting loopback
navigation. Python compilation and inline-JavaScript syntax were checked.
