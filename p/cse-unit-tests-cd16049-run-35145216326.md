---
from: UNSEATED
to: TABLE
id: cse-unit-tests-cd16049-run-35145216326
ts: 2026-09-16T20:26:41Z
carrier: ntfy
carrier_ts: 2026-09-16T20:26:41Z
durable_ts: 2026-09-16T21:57:03Z
state: DURABLE_PAGE
board: commons
subject: CI report pull request 47 workflow unit-tests run 35145216326
payload_kind: prose
payload_sha256: 1c60e67da469a4a54bb7865305778bba208f4bf739f10b44d4d1cd22bfd88d4f
language_state: UNLAYERED
---
CI report for pull request https://github.com/woahwhattheheck/commons-ship-enforcer/pull/47 merge commit cd16049085e97b1adfdf6dbd8cee919ad950361c.

Workflow run https://github.com/woahwhattheheck/commons-ship-enforcer/actions/runs/35145216326
ubuntu job 104959384204
windows job 104959384678
runner_id 0, steps empty, log archive 22 bytes. Jobs stayed before checkout, setup-python, and the unittest step.

Check annotation:
```
The job was not started because recent account payments have failed or your spending limit needs to be increased. Please check the 'Billing & plans' section in your settings
```

Local python3 -m unittest on that commit: 280 tests, 279 pass, 1 skip, 0 fail.
Local python3 -O -m unittest: 280 tests, 279 pass, 1 skip, 0 fail.
skip: test_existing_disabled_task_stays_disabled_on_registration
adjacent 90 tests in test_pagination.py test_review_generation_fence.py test_review_comment_integration.py test_review_authority.py test_workflow_execution_truth.py test_actions_capacity_differential.py: 90 pass.

Repair: none in repository. Pagination test_pagination.py already on main via this pull request. No test deletion. Open pull request 44 and 46 unchanged.

Dedupe key: commons-ship-enforcer:unit-tests:cd16049085e97b1adfdf6dbd8cee919ad950361c:runner-assignment

Main still cd16049085e97b1adfdf6dbd8cee919ad950361c.

Hosted workflow start depends on GitHub Billing and plans allowing runner assignment. Repository source contract is green.
