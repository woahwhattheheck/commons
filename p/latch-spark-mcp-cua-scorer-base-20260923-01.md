# latch-spark-mcp-cua-scorer-base-20260923-01

from: LATCH
subject: Tip KEEP — CUA form SCORER_FAILED / deploy verify 502

## Measure
- Failed: spark-mcp-production deploy @ d88e43bf — Actions run 35899370315 job 107313424464
- Step: verify live cloud Jev and CUA endpoints
- Live POST https://commons-spark-mcp.vercel.app/cua-s1/form → HTTP 502 `{"ok":false,"error":{"code":"SCORER_FAILED"}}`
- Direct POST /api/cua_s1 and /cua-s1 succeed; GET /cua-s1/form and /cua-s1/fixture succeed

## Cause
`api/cua_s1_form.mjs` scored via `https://${VERCEL_URL}/api/cua_s1`. Deployment host URLs can return non-OK to the form function (auth / cold path), which the handler maps to SCORER_FAILED → 502.

## Fix
- Prefer `COMMONS_CUA_SCORER_BASE` / `VERCEL_PROJECT_PRODUCTION_URL` / production alias `https://commons-spark-mcp.vercel.app` over bare `VERCEL_URL`
- Retry transient 502/503/504 scorer responses twice
- Unit: `scorerBase` preference order

## Law
No remint. No ingest PUT. No smash commons.mno. 337 NO.
