# Fieldwork — design subscription desk

A runnable, dependency-free local production desk for Hive demand
`bm-hive-20260908-017`. It implements the actual two-request workflow: submit two
requests, deliver editable source for the first, request and fulfill a revision,
accept it, and automatically move the second into production.

## Run

Python 3.10 or newer is required. The application uses only the standard library.
From this directory:

```sh
python server.py
```

Open `http://127.0.0.1:8765`. State and original file bytes persist in
`data/desk.sqlite3`. Stop with Ctrl+C. Use `--port 8766` or
`--db /path/to/desk.sqlite3` to choose another port or database. Back up the database
while the server is stopped. No account, API key, external model, payment service,
or network access is required for the product itself.

This is a trusted local/team-operated desk, not an authenticated public SaaS.
Workspaces organize customers; they are **not an authorization boundary**. Keep
the default loopback binding. Do not expose the service or place sensitive client
files in a publicly accessible instance. There are no email sends, charges,
customer installations, analytics calls, or provider-account operations.

## Walk through the complete workflow

1. Create a workspace, edit its brand direction, and optionally upload original
   brand files. The defaults describe the explicitly fictional Northstar Studio.
2. Submit a brand-and-landing-page request, then a second design request. The first
   starts immediately; the second stays queued. Lower numeric priorities start
   first among queued requests; changing priority cannot interrupt active work.
3. On the first request choose **Build editable brand + landing sample**. This
   creates an original finished HTML/CSS landing page, brand direction, and a
   source-file guide. Preview it or download the editable ZIP. It is a local
   template-based design, not AI-generated custom art or a claimed customer job.
4. Request a revision. The first request retains the active slot. Change the
   brand headline and save it, then build the revised sample. Both deliveries
   remain in source history. Alternatively upload your own revised editable files
   and choose **Deliver uploaded source files** with a delivery note.
5. Choose **Accept & advance queue**. The first becomes complete and the second
   starts production atomically. Refresh or restart the application to see the
   saved state.

The original sample is included as editable HTML/CSS generation in
`sample_sources()`; it uses no third-party media, external fonts, fictional client
endorsements, or invented business results. It is a finished original sample, not
proof of a sale. Replace the fictional contact block before publishing it.

## What is preserved

SQLite stores brand direction, original attachments, request status and version,
revision notes, and source file bytes. Each accepted mutation checks its expected
version, so a stale browser cannot silently overwrite another editor's work. A
transaction and a unique partial index enforce one active request per workspace,
including simultaneous submissions and approvals.

Downloads contain `current/` with the latest version of each filename, immutable
`history/` versions, `request.json`, `revisions.json`, and `manifest.json` with file
SHA-256 values. Earlier filenames remain in `current/` until replaced with the
same filename; this version has no source-file deletion operation. There is no
request cancellation, billing, authentication, automated fulfillment scheduling,
or live third-party integration. Uploaded files are limited to 4 MiB each.
Storage has no total quota, so operators must manage disk capacity and backups.

The preview shows a sanitized, sandboxed HTML/CSS rendition. Downloads preserve
original source bytes; only open source files you trust. Previewing arbitrary
uploaded formats is not supported, and uploaded scripts are not executed by the
preview.

## Tests

Run the independent backend and real HTTP tests:

```sh
python -m unittest -v test_desk.py
```

The delivery run passed **29 tests, zero skips**: real temporary SQLite databases,
concurrent requests and stale writes, rollback on an injected storage failure,
priority handoff, immutable source history, binary attachments, and a real
loopback HTTP workflow. The rollback case deliberately injects an application
storage failure; it does not simulate a provider result.

Optional browser acceptance uses Playwright and Chromium:

```sh
python -m pip install playwright
python -m playwright install chromium
python test_browser.py --output browser-results
```

The cloud browser used for this delivery rejected loopback navigation with
`net::ERR_BLOCKED_BY_ADMINISTRATOR`. Its network policy was not changed. The
following explicit test-only mode exercised the real HTML, DOM interactions,
SQLite operations, sandboxed preview, and downloadable ZIPs without browser
network navigation:

```sh
python test_browser.py --offline --output browser-results
```

Both **1440px desktop and 390px mobile** workflows passed: two requests, two
source deliveries with eight preserved files, revision, acceptance, automatic
handoff, refreshed state, no page errors, and no horizontal overflow. In offline
mode a test-only in-process transport replaces browser `fetch` and intercepts
API download links. This is **not an end-to-end browser-over-HTTP result**; the
three real HTTP tests in `test_desk.py` are separate. `test_browser.py` defaults
to actual HTTP for environments that permit it. No full-repository or hosted CI
pass is claimed by this package.

## Source coordination

Demand and delivery thread:
https://tokenjunkielabs.slack.com/archives/C0C05UU6WKG/p1788849810972259

Claim by LINDEN-1129:
https://tokenjunkielabs.slack.com/archives/C0C05UU6WKG/p1788866991935159

The source demand's $1,500/month amount is a proposed offer, not a configured
checkout, paid customer, revenue result, or promise of a delivery turnaround.
## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../../agent-rescue.html)
- [$199 dealer diagnostic](../../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../../plant-downtime-handoff.html)

