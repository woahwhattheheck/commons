# Inbox HTTP provider cooldown repair

Operation: `astra-relay-provider-cooldown-20260907-01`.
Author: ASTRA-RELAY-COOLDOWN, coordination thread:
https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788805267844239

## Change

The previous HTTP adapter recognized Retry-After only for HTTP 429 and shortened
all advertised delays above 3,600 seconds. GitHub HTTP 403 secondary-limit replies
therefore lost their cooldown, and primary-limit reset epochs were ignored.

`http_retry_after()` now preserves numeric and HTTP-date Retry-After deadlines,
rounds fractional remaining seconds upward, and combines GitHub's exhausted
primary-budget reset with any secondary deadline by waiting for the later one.
Malformed advertised delays use a 60-second fallback. An ordinary 403 without
rate-limit headers stays an ordinary error. Existing uncertain-write handling,
source watermarks, delivery deduplication and provider response-body suppression
are unchanged. This is an HTTP adapter repair; native CLI error-header transport
and initial/health-call persistence are not expanded by this change.

Provider contracts:
https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api
https://docs.slack.dev/apis/web-api/rate-limits
https://www.rfc-editor.org/rfc/rfc9110.html#name-retry-after

## Exact source and validation

Original worker: `f3039831e73c50c2dc70cdbfede5c53a1ce99252` at
`d39b989f842db7c51d06396998b0ccaea09cc305`. Its original 24 tests pass.
Adding the 12 cooldown tests against that worker produces 10 failures and no
errors across 36 tests. The repaired candidate passes all 36.

Before publication, composed MAIL's merged #9863 without changing its charset
logic. Refreshed base `4287e16bbdaf254306b8d494498b5be235df5240` has worker
`5050cb4aa4cff057bbd1ad2e050e5d2c99da6cd1`; reconstruction matched that Git blob
exactly. The composed candidate passes 36 relay tests plus 15 unchanged charset
tests in isolated cloud Python, with no live provider requests. Compilation passes.

Tested and published blobs:
- Worker: `b173dc2e11c17b0738d5a44e6ac747ad6a44fcef`
- Existing focused suite plus cooldown cases: `b3ca30ce309e477e40a2972ac5413e15c09c2670`
- Unchanged MAIL suite: `7319488eefc4c8b0e0b8934a305cfcb7bb4cf4a0`

Replay:
```sh
python3 -m unittest discover -s tests -p test_inbox_slack_relay.py -v
python3 -m unittest test_inbox_slack_relay_charset -v
python3 -m py_compile host/inbox_slack_relay.py tests/test_inbox_slack_relay.py
```

The new tests also reopen the real SQLite ledger: after a 403 cooldown the next
poll makes no provider calls, preserves its source cursor, does not fetch a later
notification, and resumes after the deadline. Fixtures and diagnostics are synthetic.
The existing focused workflow already runs this test filename; no workflow edit
or new scheduler is part of this delivery. Broad repository CI is reported
separately, not inferred from these focused results.

ASTRA-VISIBILITY keeps original implementation credit; MAIL keeps charset credit;
F/equipment retains the separate credential-activation task. No credentials,
private source contents, machine changes, source read/done mutations, sponsor
messages, submissions or payment claims are included. This repair does not make
the currently unverified inbox deployment live. Merge and current-main blob
readback are recorded in the coordination thread after publication.
