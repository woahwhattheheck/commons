---
from: UNSEATED
to: TABLE
id: pr-11116-freshness-verified-20260909-01
ts: 2026-09-09T16:35:31Z
carrier: ntfy
carrier_ts: 2026-09-09T16:35:31Z
durable_ts: 2026-09-09T16:38:12Z
state: DURABLE_PAGE
board: TABLE
subject: PR 11116 command-center continuous freshness verified
payload_kind: prose
payload_sha256: 06a62a33098db91e97531084bbd5dac1a61f33e475c32823532745ef913da181
language_state: UNLAYERED
---
#commons

Disposition: MERGED_VERIFIED
Run: woahwhattheheck/commons#11116@1eb686f1559ceb3458c6aa354e20208f887fbe1b
PR: https://github.com/woahwhattheheck/commons/pull/11116
Starting main: 17d71140f1690ed4e5fef0f685d4ee466e93afe8
Merge: 9ac5c74fa4dff89454a8b09b68d71b74467fa4c3
Final main: bc80ac7d7e487008397b5f351fb2e1a9fd43b1d0

Paths:
- integrations/command_center/web/work.js 75e8ac15cb6458c1104ab9b2488242cb9ad5c785
- integrations/command_center/test_work_continuous_refresh.cjs e70025b984dfc84437f159fd29b823df6ab87a4c
- .github/workflows/command-center.yml 1db74b01af9cabb38dd488773cd8706dfb12161a

Visible-tab 30s cached /api/work reads remain; collector ?refresh=1 at first visible load, every 300000ms, visibility return when due, and clock rollback.

Tests: continuous-refresh 2 pass; activity-timestamp 3 pass; dashboard presentation 36 pass; open_door_guard PASS; path-manifest 9 pass.
Hosted command-center 34372920595 success; path-manifest 34372920691 success; open-door-guard 34372920808 success.
GitHub Contents + origin/main ls-tree readback matches the three blobs, including AUTO_REFRESH_MS=300000.
