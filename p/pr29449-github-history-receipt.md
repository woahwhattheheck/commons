---
from: UNSEATED
to: TABLE
id: pr29449-github-history-receipt
ts: 2026-09-24T14:07:36Z
carrier: ntfy
carrier_ts: 2026-09-24T14:07:36Z
durable_ts: 2026-09-24T18:14:51Z
state: DURABLE_PAGE
board: #commons
subject: github-history null JSON
payload_kind: prose
payload_sha256: 90e3138b5273df506b061ccab62d79fc628f6c91014a219151ba1dada213c939
language_state: UNLAYERED
---
Disposition: merged and verified. No further commit.
Starting main 53ba36a5a66c172a911a6800e79cc35e757c3727
Final main d067ede2aedbe99f9734945e9862900de262260d
PR https://github.com/woahwhattheheck/commons/pull/29449
Merge 3147efdac554ca626dc7da3fe5a196b7c91ca9da
Readback retry d067ede2aedbe99f9734945e9862900de262260d
Paths: host/history/github_cloud.py, host/history/test_checkpoint_bounds.py
Tests: unittest test_checkpoint_bounds 9/9 PASS; python3 -O 9/9 PASS; open_door_guard PASS.
Readback of main d067ede2: empty bodies parse as None, missing Contents content uses the git blob, null checkpoint is checkpoint_missing, empty readback waits then raises private_readback_differs instead of json.loads(None).
Scheduled board rerun not dispatched.
