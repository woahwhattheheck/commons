# Readable inbox work with malformed source links

Operation: `astra-relay-malformed-url-20260907-01`. Builder: ASTRA-RELAY.
Existing ASTRA-VISIBILITY, charset, MAIL and COOLDOWN work is preserved.

`clean()` catches only URL-parser `ValueError`, replaces the malformed link with an explicit omission marker, and retains surrounding work text. Normal links and existing redaction and mention behavior are unchanged. No source link is fetched.

## Executed evidence

[Hosted validation run 34175273169](https://github.com/woahwhattheheck/commons/actions/runs/34175273169), job 101903316874, executed on base `1f15b08e9e58d33a39770a831c6dfc84f49968a0` with baseline worker blob `d42718ceda5a6123cf19a072faf4db650b91c14c`.

Two synthetic malformed-URL controls raised ValueError before the repair; ordinary HTTPS was unchanged. After the repair, 117 targeted tests passed: 47 existing relay/cooldown tests and 70 charset/alternative/header/URL tests, including 18 new URL methods. Compile and whitespace checks passed. Tests exercise actual rendering and SQLite delivery state with synthetic provider responses, including a following work item and repeat delivery without duplicates. These are not live mailbox incidents or live deliveries.

The run's overall conclusion is failure because its runner credential cannot publish workflow-file changes. The passed test evidence remains valid. This export reconstructs the exact executed worker transformation and test literal from immutable support commit `2b43be26ae7858b7a7da63fff71322e8c93d482f`; test blob `9923da5c7105c0ab366c15d3da27a03052950866` is checked. It is source preservation, not another test execution.

[Retained test artifact](https://github.com/woahwhattheheck/commons/actions/runs/34175273169/artifacts/10037025979), ZIP SHA-256 `f9523353ee28fbd0b99d898bfa54f6b1d3814954dfe854f4a4c493f7985952d8`.

## Replay and integration

```sh
python3 -m unittest discover -s tests -p test_inbox_slack_relay.py -v
python3 -m unittest test_inbox_slack_relay_charset test_inbox_slack_relay_alternatives test_inbox_slack_relay_headers test_inbox_slack_relay_urls -v
```

The product consists of the worker, root URL test, this receipt and the existing inbox workflow's trigger/test-command update. The workflow update uses the connected account's supported write action; this runner exports only the three non-workflow product files. Neither branch-only build/export workflow belongs on main. Main integration and exact readback are recorded in the original Slack thread.

No credentials, source inbox mutations, scheduler activation, account submission, spend or owner-PC work occurred. F/equipment retains activation; this code change does not establish unattended delivery.
