# Creator App Studio — Hive016

A working local studio for a creator-branded **materials-per-attendee planner**.
It saves versioned briefs in SQLite and exports a standalone browser app plus
editable launch assets. This is the reusable delivery slice of Hive demand016,
not a claim that a creator has been interviewed, partnered with, or sold an app.
The supplied workshop brief is explicitly synthetic.

## Run

Python 3.10 or newer is sufficient for the studio. No runtime packages, accounts,
external model, customer data, payment connection or provider setup are needed.

```sh
cd revenue/hive/creator-app-studio
python studio.py --db ./creator-studio.sqlite3 --port 8765
```

Open `http://127.0.0.1:8765`. Keep the server on its default loopback interface;
this is a local operator application, not a hosted multi-tenant service.

Edit the creator, audience, problem, onboarding, proposed pricing, support route
and material defaults. Save the brief, open the working app, or export its launch
ZIP. Reopen an existing project to save another revision. Competing stale edits
receive an explicit conflict instead of overwriting the current revision.

The ZIP contains `index.html`, `brief.json`, `revisions.json`, `START-HERE.md`,
`launch-copy.txt` and `SHA256SUMS`. Open its `index.html` directly. No CDN or network
request is needed by the exported app. Brief wording and defaults are editable;
another type of audience workflow still needs real implementation rather than
just changing its name.

## Complete reference workflow

Enter 12 attendees, two card sheets each, a ten-percent reserve, and ten sheets
per pack. The actual planner calculates 26.4 required sheets, three packs, and
30 purchased sheets. Edit the attendee count to 20, save a named plan, reload,
and reopen it: the result becomes 44 required sheets, five packs, and 50 purchased.
Export CSV for editing or JSON for portable saved-plan backup. Re-importing an
identical backup does not duplicate plans; conflicting plan IDs are rejected
without changing existing data. A save is only reported after browser storage
actually succeeds.

Material quantities use exact scaled-integer arithmetic, including fractional
pack boundaries such as three times 0.1 fitting one 0.3 pack. Every quantity is in
the explicitly entered unit; there is no implicit unit conversion. Reserve can
range from zero to 100 percent. Resource bounds are 1–1,000,000 attendees, 1–50
materials, six decimal places per input and 10,000 saved plans. Suggested usage
targets remain advisory; reaching a pricing-plan target does not lock the app.

## Persistence and privacy

The studio database stores brief revisions, not end users' saved workshop plans.
The generated app stores plans in its browser's local storage, scoped by project
ID. The studio preview and a downloaded file are different browser storage
locations. Use JSON export/import to move plans between them. Moving a local file,
using another browser, or clearing browser data may remove access to old plans.
Export backups first. Unreadable storage is not overwritten or exported as a
successful empty backup. Use one editing tab per project; cross-tab simultaneous
editing is not a transactional collaboration feature.

Pricing and launch copy are drafts. Support is operator-provided text. There is
no checkout, paid-plan enforcement, outbound messaging, analytics, deployment or
claim that commercial fulfillment has happened. Audience-demand notes are not
independently verified. Actual creator discovery, a source-supported niche,
a real support route and a target user's acceptance remain commercial next steps.

## Tests

```sh
python -B -m unittest discover -v
```

The shipped suite has 26 methods: real temporary SQLite files, restart and revision
history, threaded competing writes, live HTTP endpoints, packages/checksums,
input-shape handling, shipped JavaScript parsing and 500 deterministic JavaScript
arithmetic cases compared with Python Decimal. Node is required for the seven
JavaScript test methods; those are explicitly skipped when Node is absent.

Optional complete browser check:

```sh
python -m pip install playwright==1.57.0
python -m playwright install --with-deps chromium
python -B browser_check.py --output browser-results
```

This check exercises the real studio, saved-plan reload, CSV/JSON downloads,
retry-safe import, and the actual exported standalone app. It writes screenshots
and a result JSON. Existing Chromium can be selected with `--chromium PATH`.

Development execution on September 8, 2026: **26/26 methods passed, zero skips**.
The provided container's Chromium rejected local navigation with
`ERR_BLOCKED_BY_ADMINISTRATOR` before any browser check ran. That is not a browser
pass. No browser policy or host controls were changed. The included narrowly
path-scoped `.github/workflows/hive-creator-app-studio.yml` runs the same suite and
browser check through normal GitHub Actions and retains its actual result.

The browser CI setup follows the Playwright Python browser-installation guide:
https://playwright.dev/python/docs/browsers . It is a test dependency only.
