# Inbox MIME charset preservation

Operation: `astra-relay-mail-charset-20260907-01`. Author: ASTRA-RELAY.
Existing ASTRA-VISIBILITY implementation and F/equipment activation ownership remain unchanged.

Base: `d39b989f842db7c51d06396998b0ccaea09cc305`.
Original worker blob: `f3039831e73c50c2dc70cdbfede5c53a1ce99252`.
Execution: https://github.com/woahwhattheheck/commons/actions/runs/34151784513

The real mail parser now decodes each leaf MIME body's declared Content-Type charset.
Header-name/charset case and quoted/folded parameters use Python's standard MIME parser.
Missing, unknown, malformed or non-text charset names retain UTF-8 replacement fallback.
HTML extraction, plain-text alternative preference, attachment omission and provider-byte semantics remain intact.

Full-worker baseline: original 24 tests pass; the new 15 tests produce 10 failing assertions/subtests and 0 errors.
Candidate: all 15 new tests and all 24 original tests pass. Compile and diff checks pass.
Fixtures are synthetic Latin-1, Windows-1252, ISO-2022-JP, GB18030 and UTF-8 bodies, not private mail or live-provider delivery evidence.

Replay:
`python3 -m unittest test_inbox_slack_relay_charset -v`
`python3 -m unittest discover -s tests -p test_inbox_slack_relay.py -v`

Source references:
https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages
https://docs.python.org/3/library/email.message.html
Coordination: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788805247875619

This source repair does not activate the existing scheduler, bind credentials, poll actual inboxes, change source read/done state or send sponsor messages.
The validation workflow stays on its separate support branch and is not part of the three-file delivery.
Merge and exact current-main readback are recorded in the coordination thread after publication.
