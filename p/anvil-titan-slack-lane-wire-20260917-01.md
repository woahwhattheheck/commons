# anvil-titan-slack-lane-wire-20260917-01

- seat: ANVIL (Devin CLI, local)
- issue: woahwhattheheck/commons #15789
- bug: `hands target=slack` always TRANSPORT_UNCONFIGURED — `default_factories`
  registered bare `SlackServer`; `post`/`history` callables were never injected,
  so `_configured()` reported online while every post hit `_post is None`.
- fix: `host/titan_hands/one_tool.py` — new `slack_lane_server(routes=None)`
  factory builds `SlackServer(history=..., post=...)` backed by
  `HandsRoutes` (the existing env-token HTTP path to chat.postMessage /
  conversations.history). No token → bare `SlackServer()` → same typed
  TRANSPORT_UNCONFIGURED as before; `capabilities` gating unchanged.
- tests: `host/titan_hands/tests/test_one_tool.py` +2 —
  token-present lane posts through stubbed HTTP (chat.postMessage +
  conversations.history asserted) and no-token stays typed.
- verify: `python -m unittest discover -s host/titan_hands/tests` — 70/70 OK
  against a current-main tree.
- live check on this seat before fix: `TRANSPORT_UNCONFIGURED` with
  SLACK_BOT_TOKEN present — reproduces the issue exactly.
