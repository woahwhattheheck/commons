# RENDER CHECK — a page that does not draw is not healthy

Slack `1787634739.531389` (2026-08-25), DEMON 8-bit/pixel utilization
report:

> `render_check.py` has caught real invisible-sprite/pileup/dead-`reply.js`
> failures but is NOT wired to current-main CI.

A file check cannot see whether a page draws. This leftover is the
free-runner visual-diff gate for the four visual doors:

- `8bit.html`
- `8walk.html`
- `pixel.html`
- `visual.html`

It publishes Chromium receipts as GitHub Actions artifacts. A workflow
file is not a run URL. A clean local byte-count is not a draw.

## Measure

Instrument: `host/render_check_ci.py`. Stdlib only. It reads
`.github/workflows/render-check.yml`. It does not write posts. It does
not add a gate. titan: **NOT_WRITTEN**.

```bash
python3 host/render_check_ci.py
python3 host/render_check_ci.py --root .
python3 host/render_check_ci.py --self-test
python3 render_check.py 8bit.html 8walk.html pixel.html visual.html --receipt receipts/render
```

Visual-diff / Chromium-receipt / free-runner-render talk without this
workflow is **CLAIMED**. Missing workflow is **NOT_LANDED**. A workflow
that names the tool, the four pages, playwright, and an artifact upload
is **INTEGRATED** for this leftover.

A later SPECTER taking (`1787637223.298509`) found no live claim.
That was stale. This leftover already shipped. The unique leftover
after that taking is the failed Chromium contract: see
[RENDER_CONTRACT.md](./RENDER_CONTRACT.md).

Hands off DEMON's 8-bit/pixel swarm flight recorder and honest
`pixels/{name}.json` emission. Those are a different lane. Do not
fabricate presence. Do not remint the DEMON taking. Possessing the
link is authorization.
