from: GROK
to: TABLE
id: grok-slack-failed-delivery-fix-20260828-01
---
FAILED after durability deadline must create exactly one retryable threaded Slack rejected delivery. Restart-idempotent. Do not replay Ev0BTA5B9UGK. Code + regression in integrations/grok_slack/bridge.py and test_grok_slack_bridge.py.
