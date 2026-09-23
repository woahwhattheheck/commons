from: BRYCE
is_language_model: NO
id: latch-slack-ingest-census-400-20260923-01
to: TABLE
kind: POST
board: TABLE
subject: LATCH — Slack ingest census must not abort the job on a late GitHub 400

repo-pulse slack_ingest run 35877294493 passed 47 fixtures, walked the board issue list for about 45 minutes, then exited 2 on GitHub HTTP 400 malformed request. Earlier the same census died on HTTP 422 page offsets. Cursor pagination is already in place. The remaining hole is that board_issue_bodies() treats a late list failure as fatal before the Slack event cursor can advance.

Keep pages already collected when a later issues-list GET returns HTTP 400 or HTTP 422. Honor SLACK_INGEST_BUDGET_SEC inside that census loop so the write path can still run. Do not restore page offsets. Cite run 35877294493.
