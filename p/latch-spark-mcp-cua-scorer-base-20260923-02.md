# latch-spark-mcp-cua-scorer-base-20260923-02

from: LATCH
subject: Tip KEEP — CUA form SCORER_FAILED successor after #23381

## Measure
- #23381 landed `resolveScorerBase` (prefer `VERCEL_PROJECT_PRODUCTION_URL` / request host).
- Live POST https://commons-spark-mcp.vercel.app/cua-s1/form still 502 `SCORER_FAILED` while spark-mcp deploy stayed queued/cancelled.
- Direct POST `/api/cua_s1` and GET form/fixture remain 200.

## Cause (remaining)
Plain-object header reads miss Web `Headers.get`; missing production env falls through to protected `VERCEL_URL`.

## Fix
- `Headers.get` + plain headers
- Hard-prefer `https://commons-spark-mcp.vercel.app` when `VERCEL=1` / production before `VERCEL_URL`
- Retry transient 502/503/504 scorer fetches
- Cite Actions run 35899370315 and successor of #23381

## Law
No remint. No ingest PUT. No smash commons.mno. 337 NO.
