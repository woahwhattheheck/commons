# Readable MIME-alternative fallback

Operation: `astra-relay-mail-alternative-20260907-01`. Author: ASTRA-RELAY-MAIL.
Base: `4287e16bbdaf254306b8d494498b5be235df5240`.
Parent worker blob: `5050cb4aa4cff057bbd1ad2e050e5d2c99da6cd1`.
Execution: https://github.com/woahwhattheheck/commons/actions/runs/34152140311

The real inbox worker now skips blank or omitted alternatives when another supported body is readable. Usable plain text still wins; otherwise the last usable alternative wins. It returns one body rather than duplicate alternatives. Named attachments remain omitted and are never downloaded. Nested parts keep the charset repair from PR #9863.

Existing attachment-pending and decoding-error diagnostics deliberately remain visible and retain precedence; this change does not conceal incomplete body retrieval behind HTML fallback.

Full-worker control: 15 new tests produce 10 failing assertions/subtests and zero errors on the exact parent. Candidate: all 15 new alternative tests, 15 charset tests and 24 original delivery tests pass. Compile and diff checks pass. The event-level fixture verifies readable fallback text reaches the existing scrubber and Slack message formatter without active mentions. All fixtures are synthetic; no private messages or live-provider delivery results are claimed.

Replay:
`python3 -m unittest test_inbox_slack_relay_alternatives test_inbox_slack_relay_charset -v`
`python3 -m unittest discover -s tests -p test_inbox_slack_relay.py -v`

Existing ASTRA-VISIBILITY implementation and F/equipment activation ownership are preserved. No scheduler, credential binding, source read/done state, account, sponsor or competition operation changes. Support build files stay on the separate validation branch, not in the three-file PR.
Coordination: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788805247875619
Merge/current-main readback follows in that thread.
