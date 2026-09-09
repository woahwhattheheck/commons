# Readable email alternatives survive unavailable MIME parts

Operation: `astra-relay-readable-alternative-20260908-01`. Builder: ASTRA-RELAY.
Original ASTRA-VISIBILITY, MAIL, charset, alternative, URL and COOLDOWN contributions remain credited.

## Product behavior

The existing string-returning `mail_body()` API now delegates to a private renderer carrying a separate readable-content flag. Diagnostic-only parts cannot hide available alternatives. Plain text remains preferred; nonplain alternatives retain last-readable preference. Nested multipart content preserves diagnostics for genuinely missing portions, and all-unavailable alternatives retain the original first diagnostic. Literal diagnostic-looking source text is not mistaken for a parser status. No attachment or source URL is fetched.

Only the parser region, its already-wired alternative suite and this receipt change. Eighteen new test methods are added. Two existing combined diagnostic-plus-readable-HTML assertions are deliberately updated to expect the available content; standalone/no-readable diagnostic behavior is covered separately. No test is removed or skipped. Existing charset, privacy, source-state, deduplication and cooldown logic is unchanged.

## Actual execution

- Source base: `4df7c7ace48d7304b39c89c19d0eeb077f74fe51`; original worker `d6f87988dcf54ed14ff6cfc496e814ed3a728323`; original alternatives `8686a4261262e59d65bab366f705a42b2033ebd0`.
- [Hosted run and logs](https://github.com/woahwhattheheck/commons/actions/runs/34188772670); Python `3.12.3`.
- The original worker produced 11 assertion-failure records and zero errors on the 18 added methods. These are synthetic parser/provider fixtures, not live mailbox incidents.
- Candidate: 135 passing test methods (47 + 88); compile and whitespace checks passed.
- Candidate worker blob `6a6b7a669ee766370a0458f4df204bb641871654`; alternative suite blob `66ecbc94f4fceafd4c096f1456be3d9613eb283a`.
- The existing inbox workflow already runs the extended suite; no product workflow or scheduler configuration changed. The branch-only build recipe is excluded from the product.

Replay:
```sh
python3 -m unittest discover -s tests -p test_inbox_slack_relay.py -v
python3 -m unittest test_inbox_slack_relay_charset test_inbox_slack_relay_alternatives test_inbox_slack_relay_headers test_inbox_slack_relay_urls -v
```

Gmail's MessagePartBody contract distinguishes inline data from attachmentId-only parts: https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages.attachments . This parser uses already-returned inline alternatives; it adds no attachment request.

## Delivery boundary

No application credentials, source inbox mutations, source deliveries, account actions, paid service, or owner-PC work occurred. F/equipment retains actual relay activation. This is tested source delivery, not an activation or full-repository green claim. Merge and current-main readback belong in the existing Slack work thread.
