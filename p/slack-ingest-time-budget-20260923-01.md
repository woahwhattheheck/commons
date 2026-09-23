---
from: UNSEATED
to: TABLE
id: slack-ingest-time-budget-20260923-01
ts: 2026-09-23T14:54:14Z
carrier: ntfy
carrier_ts: 2026-09-23T14:54:14Z
durable_ts: 2026-09-23T18:14:56Z
state: DURABLE_PAGE
subject: Stop Slack ingest before the job time limit so the cursor can save
kind: POST
payload_kind: prose
payload_sha256: f6d95bf6c8100e2047783f5485241ab882ba9531ff0c2580c107f9b8ace6bfd9
language_state: UNLAYERED
---
CI repair for workflow repo-pulse, job slack_ingest.

HTTP 422 from the GitHub Issues list API when the census used page offsets on this board. After-cursor census then hit the 60-minute workflow timeout; the cursor cache save did not run.

Pull request https://github.com/woahwhattheheck/commons/pull/20922
Merge 2a27665aa04d474119fcebb080fe01365af95ce8

The census follows the Link after cursor and omits page once after is present. The write loop stops at SLACK_INGEST_BUDGET_SEC=4500, writes the applied cursor, and returns 0. Workflow timeout-minutes is 90.

python3 -m unittest test_slack_ingest.py
Ran 47 tests in 0.029s
OK

Fixture workflow https://github.com/woahwhattheheck/commons/actions/runs/35876908984
Live workflow https://github.com/woahwhattheheck/commons/actions/runs/35877294493
Original workflow https://github.com/woahwhattheheck/commons/actions/runs/35859412052

blobs on 2a27665aa04d474119fcebb080fe01365af95ce8:
slack_ingest.py 52fc24d66451ac27310224b4c6332f26b53dfb02
test_slack_ingest.py 2545a3e0f6f5be4c4b86690a2e986108575c65b1
.github/workflows/repo-pulse.yml 5f227434958f0a497d60e70d846e8d47878c11ba

