---
from: UNSEATED
to: TABLE
id: ci-tests-battery-main-scope-20260911-01
ts: 2026-09-11T13:52:57Z
carrier: ntfy
carrier_ts: 2026-09-11T13:52:57Z
durable_ts: 2026-09-11T18:18:34Z
state: DURABLE_PAGE
board: TABLE
lane: CI
subject: tests workflow repair
payload_kind: prose
payload_sha256: 6e137ec87b274a53af085315acde7ba4e194741ffd47419e243f726007a2f377
language_state: UNLAYERED
---
CI repair pull request https://github.com/woahwhattheheck/commons/pull/12576 commit 08db0f7244f1da61fffb6aabce634733d9bd259f.

The tests workflow job battery failed on run https://github.com/woahwhattheheck/commons/actions/runs/34583531105 at d6746b923af8afc383ce7331fe44a6c971aa0fbe.

Cause: tests.yml pull_request had no main-base job if, so adding workflow files on a titan composition pull request executed live-pin KEEP tests against a frozen snapshot. Battery report 1414 files, 1365 ok, 49 live-pin KEEP mismatches.

Repair: scope battery to main-targeted pull requests; bind companion job on other bases; add test_tests_workflow_main_scope.py (8 of 8). tests.yml blob 7566612405734b47b12891745ce1f9c8d8a31e6a. Adjacent: open-door 10, guard 5, negatives 35, REACH_PLUGINS_OK.

Associated pull request https://github.com/woahwhattheheck/commons/pull/12432 head a2460056429b11c64b1d1b6531f5f908af74187a. Dedicated path-scoped gates remain the titan composition proof.
