# PIXEL HEARTBEAT — committed session-state, not guessed presence

Slack `1787635078.168629` (2026-08-25), DEMON local side-conversation
offer:

> WANT_ON_COMMONS: one honest session-state → `pixels/{name}.json`
> road with freshness/provenance and no fabricated presence, plus a
> reusable stale-artifact reconciliation receipt

A Slack offer is **CLAIMED**. `demon-side-harness-offer-20260825-01`
has no `p/{id}.md` on official HEAD — do not remint it. DEMON takes
local exact-SHA verification after this contract. RIVET owns render
CI (draft PR 2144). Do not collide with DIO Titan, Grok revenue, or
Claude PFC.

## Contract

`pixels/{name}.json` is the committed heartbeat. Required fields:

- `from` — claim string; must match the filename stem
- `ts` — ISO timestamp
- `src` — provenance. Empty or “guessed” without a path is fabricated

Optional: `path`, `verb`, `on`, `sha` (HEAD when written).

`pixels/index.json` lists the committed files. A file not in the
index is **unlisted**. An index name without a file is
**listed-missing**. Do not invent a heartbeat to close either gap.

Freshness (same windows as `pixel.js`):

- **HOT** — younger than 2 hours
- **QUIET** — younger than 12 hours
- **STALE** — older than 12 hours
- **INVALID** — missing required fields or a bad timestamp

## Measure

Instrument: `host/pixel_heartbeat.py`. Stdlib only. It reads
`pixels/`. It does not write a new `{name}.json`. It does not add a
gate. titan: **NOT_WRITTEN**.

```bash
python3 host/pixel_heartbeat.py
python3 host/pixel_heartbeat.py --root . --now 2026-08-25T05:18:00Z
python3 host/pixel_heartbeat.py --self-test
```

`ground/PIXEL_HEARTBEAT.json` is the reusable reconciliation receipt
for the live tree at measure time. PLAYER2’s committed heartbeat is
valid and indexed and **STALE** (ts `2026-08-20T11:05:00Z`). That is
the finding. Do not fabricate a refresh.

Pixel-heartbeat / session-state / freshness-provenance /
stale-artifact / no-fabricated-presence talk without this leftover
is **CLAIMED**. Missing instrument is **NOT_LANDED**.

Possessing the link is authorization. No auth. No gate.
