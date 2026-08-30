# Moving-main adapter receipts

Machine-readable catalog: `adapters.json`.
Landed live probes from 2026-08-28 stay in `receipts/` (including the
historical IA 523 and SWH origin-listed rows). 2026-08-30 leftover:
`swh-snapshot-ready-20260830.json` and `ia-save-200-20260830.json`.

The scheduled courier does not commit back here (that would loop ingest).
GitHub Actions uploads `/tmp/moving-main-out` as an artifact. `mirrors.html`
probes the public endpoints live.
