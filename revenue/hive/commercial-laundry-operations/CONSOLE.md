# Run the laundry shift from a local browser

The console is an operator interface to the existing SQLite engine and
`operate.py`, not another ledger. It adds customer/site/price/plan forms, daily
route forms, visible counts and exceptions, draft-only invoices, and native
route/customer downloads. It does not send messages, issue invoices, process
payments, infer cleaning quality, or provide a hosted service.

## Start one private workspace

Use Python 3.11 or later and a modern JavaScript-enabled browser. Run from this
product directory. The parent directory must already exist and be owned by the
operator. For a deliberately new workspace:

```sh
python -B operator_console.py /private/laundry/shift.sqlite3 --init
```

`--init` invokes the existing exclusive initializer. It will not overwrite an
existing file. To reopen an existing supported database, omit `--init`:

```sh
python -B operator_console.py /private/laundry/shift.sqlite3
```

Open the **private address printed in the terminal**. The server selects a free
loopback port; `--port 8765` can request a specific one. Binding is always
`127.0.0.1`, never a LAN interface. The address includes a fresh session key in
its fragment. Do not paste it into Slack, tickets, screenshots, or public logs.
The page removes the fragment and may retain the key in tab-scoped session
storage for reload; customer records are not persisted in browser storage.
The separate unlock field accepts just the key when needed.

Press **Lock console** to clear displayed records and the tab's saved key.
Stop the server with Ctrl+C when finished. A restart creates a new session key.
Closing or locking the browser alone does not stop the server.

## Work through an actual shift

Create the customer and site, an item price in integer cents, and a recurring
stop plan. Weekdays are Monday `0` through Sunday `6`. Create the daily manifest
for its date and route code; the resulting route opens automatically.

Each stop offers its next recording form. Only the stop ID is prefilled: enter
observed counts and container IDs yourself. Count fields accept one
`item=count` per line, such as `towel=3`. Container fields accept one ID per line.
Blank optional fields are omitted. Unknown fields, duplicate count items,
non-integer counts, invalid identifiers, and native state conflicts are not
silently repaired.

The route displays pickup, processed-good, damaged and delivered counts
separately. Every open exception remains visible. **Review and resolve** opens
the existing resolution command with the exact exception ID; an operator must
supply a supported disposition code and note. A remaining exception blocks
invoice drafting. Resolving it is not sanitation or quality certification.

Drafts are explicitly labeled **DRAFT, not issued or paid**. Customer/route
JSON, CSV and Markdown downloads come from the native exporters. Downloading a
file does not send it, post it to accounting, authorize it, or earn revenue.
Pickers list at most 100 records each; older exact IDs can still be entered.

## Retry without duplicating an operation

The operation key stays in the form after success or failure. Repeating the
same key and fields returns `REPLAYED` without another native event. Changing
fields while reusing a committed key is rejected. Choose **New operation key**
only for a different intended operation. Choosing another operation or a stop's
next-action button also starts a new key.

A lost reply or I/O error can leave the commit outcome uncertain. Preserve the
exact key and fields, inspect the current route, and retry that same payload.
Do not invent a new key to get around uncertainty. The last operation result
is historical; **Refresh workspace** reads current SQLite state. Reloading the
page does not preserve an unsent form or its key: copy needed retry information
into an operator-controlled record before leaving an uncertain request.

## Scope and limits

All API calls require the current session key. Writes additionally require the
exact same origin. Host checks, static-path allowlisting, non-cached responses,
frame blocking and a restrictive script policy reduce exposure, but this is
still a **single-operator local tool**, not production web hosting. Do not expose
it through a proxy, tunnel, port forward, or shared workstation. Python's
[`http.server` documentation](https://docs.python.org/3.13/library/http.server.html)
explicitly warns against using it as a production server.

The database path is selected only on the server command line. The browser
cannot select arbitrary files, restore over a database, or change schema. The
console does not add backup/restore or replace the storage tools. The owning
operating-system user and code directory remain trusted: this is not isolation
from a hostile process that can modify those files. No external services,
CDNs, model calls, new workflow jobs, or additional test suites are introduced.
