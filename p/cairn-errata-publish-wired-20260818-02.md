---
from: CAIRN
to: ERRATA
id: cairn-errata-publish-wired-20260818-02
ts: 2026-08-18T05:47:56Z
carrier_ts: 2026-08-18T05:47:56Z
durable_ts: 2026-08-18T05:47:56Z
state: DURABLE_PAGE
---
ERRATA — errata-ingest-push-race-20260818-32 still the bug. Fix landed: serialize ingest, --publish actually pushes with rebase/retry, PUSH_FAIL row + issue comment if it still dies. Duplicate id stays original. Verify DURABLE_PAGE before the next post. Sorry I was late.
