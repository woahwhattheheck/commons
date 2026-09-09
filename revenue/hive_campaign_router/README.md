# RouteFoundry

RouteFoundry is a working campaign-link workspace for creators and small
agencies. A short URL and its QR code stay stable while the operator changes the
destination, campaign tags, or offer page behind it. Clicks and conversions are
attributed to the UTM preset attached to the link.

This is the first customer-facing implementation of Hive demand
`bm-hive-20260908-001`.

## What ships

- Stable branded slugs at `/r/<slug>` and scanner-compatible SVG QR files at
  `/q/<slug>.svg`.
- Editable public HTTPS destinations. Updating a destination does not change the
  slug, short URL, or QR bytes.
- Reusable UTM presets that preserve unrelated destination query parameters and
  replace stale `utm_*` values predictably.
- Product-specific offer pages selected by each campaign link. The offer CTA
  records a conversion and then redirects to the current tagged destination.
- Click, conversion, source, medium, campaign, referrer-host, and recent-event
  reporting. Visitor IP addresses are not stored.
- Idempotent event IDs, including a same-link/type/parent consistency check, so
  retried conversion notifications do not double count.
- Write-time redirect validation: HTTPS only; no credentials, local/private
  hosts, control characters, malformed ports, or non-public literal IPs.
- SQLite/WAL persistence, JSON export, a browser dashboard, a public-only server
  mode, Docker packaging, and a complete executable acceptance demo.

The server does not fetch destination URLs and therefore does not claim that a
remote page is available, honest, or unchanged. Operators remain responsible
for the offers they publish.

## Start locally

```bash
cd revenue/hive_campaign_router
python -m pip install -r requirements.txt
python app.py --db ./routefoundry.db
```

Open `http://127.0.0.1:8080`. The default bind is loopback so the editing
workspace is not accidentally exposed. Public destinations must use HTTPS.
Loopback HTTP is accepted only for the local RouteFoundry origin.

For a branded production origin:

```bash
PUBLIC_BASE_URL=https://go.example.com \
ROUTEFOUNDRY_DB=/var/lib/routefoundry/routefoundry.db \
python app.py --host 127.0.0.1 --port 8080
```

Put the service behind an existing HTTPS reverse proxy. `PUBLIC_BASE_URL` is the
origin encoded into every QR. Changing it later necessarily changes future QR
bytes, so set the branded domain before printing.

## Public/admin split without an application login

RouteFoundry can run two processes against the same WAL database:

```bash
# Operator dashboard and write API: local/private network only
PUBLIC_BASE_URL=https://go.example.com \
python app.py --host 127.0.0.1 --port 8080 --db /data/routefoundry.db

# Public routes: dashboard and /api are unavailable
PUBLIC_BASE_URL=https://go.example.com \
python app.py --host 0.0.0.0 --port 8081 --db /data/routefoundry.db --public-only
```

Expose only the public process to visitors. The included `compose.yaml` uses
this shape: the admin port is bound to `127.0.0.1`, while the public process can
be placed behind the branded HTTPS proxy. Both services share one named volume.

```bash
PUBLIC_BASE_URL=https://go.example.com docker compose up --build -d
```

## Complete acceptance flow

The demo starts a real HTTP server, writes a real SQLite database, and exercises
the customer workflow through HTTP rather than calling test doubles:

```bash
python demo.py --db /tmp/routefoundry-demo.db --reset \
  --output /tmp/routefoundry-demo.json
cat /tmp/routefoundry-demo.json
```

It creates one product, one offer, three UTM presets, and three campaign links;
downloads a QR; edits the linked destination; confirms identical QR bytes;
opens an offer; records its click and conversion; follows a direct link with
UTM values; retries one explicit event ID; and reads the campaign report.

The retained execution in `DEMO-RESULT.json` records all acceptance checks as
true. It uses documentation-only example domains and performs no external HTTP
request.

## Test

```bash
PYTHONWARNINGS="error::ResourceWarning" python -m unittest -v \
  test_validation.py test_store.py test_server.py
python -m compileall -q .
node --check static/app.js
```

The focused suite covers validation, persistence, concurrent event deduplication,
stable QR output, offer and direct routes, conversion ancestry, editing,
reporting, export, security headers, paused links, HEAD requests without event
side effects, and the public/admin split.

## API map

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/state` | Dashboard data, links, counts, and recent events |
| `POST` | `/api/products` | Create a product and brand |
| `POST` | `/api/offers` | Create an offer page for a product |
| `POST` | `/api/presets` | Create a reusable UTM preset |
| `POST` | `/api/links` | Create a stable campaign link |
| `PATCH` | `/api/links/<slug>` | Change destination, preset, offer, mode, or status |
| `POST` | `/api/events` | Record an idempotent click or conversion event |
| `GET` | `/api/report` | Campaign/source/medium and per-link counts |
| `GET` | `/api/export` | Download the complete workspace as JSON |
| `GET` | `/r/<slug>` | Log a click, then render an offer or redirect |
| `GET` | `/convert/<slug>` | Log a conversion and redirect |
| `GET` | `/q/<slug>.svg` | Export the stable short URL as an SVG QR |
| `GET` | `/health` | Process health |

The browser UI uses only these same endpoints. It has no hidden provider or
hosted-service dependency.

Pass `--quiet-access-log` when a supervisor or reverse proxy already provides
request logging. Database and request-processing errors still go to standard
error.

## Operating notes

Back up the SQLite database and its `-wal` file together, or use SQLite's online
backup API while the server is running. The JSON export is portable but is not
an atomic database backup.

`/api/events` accepts an optional caller-supplied `event_id`. Repeating the same
ID with the same link, type, and parent is a no-op. Reusing it for a different
event is rejected. A supplied `parent_event_id` must name a click for that same
link.

This version counts explicit events; it does not use fingerprinting, cookies,
cross-site pixels, purchased data, or third-party analytics. It is therefore a
transparent first-party campaign workflow, not a general web-attribution claim.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../titanmcp.html). Cite Latch Pad KEEP.
## Live cash

Verified product pages only — no invented Stripe links.

- [$29 Autopsy checkout](../../agent-rescue.html)
- [$199 dealer diagnostic](../../dealer-service-lead-rescue.html)
- [$199 referral diagnostic](../../referral-intake-completeness.html)
- [$199 repair diagnostic](../../repair-booking-preflight.html)
- [$199 plant diagnostic](../../plant-downtime-handoff.html)

