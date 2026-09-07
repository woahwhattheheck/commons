# Persistent inbox cooldowns at the finite-run boundary

Operation: `astra-relay-cooldown-persistence-20260907-01`.
Author: ASTRA-RELAY-COOLDOWN.
Coordination: https://tokenjunkielabs.slack.com/archives/C0BU51F1PL3/p1788805267844239

## Cause and correction

PR #9867 preserves HTTP provider deadlines, but the original finite-run boundary
still discarded delays from initial Slack authentication and final health writes.
Those calls are outside `run()`'s source exception handler. Gmail's token-refresh
wrapper also replaced a provider RelayError without carrying its retry delay.

`main()` now persists a propagated cooldown before releasing the existing RunLock,
then keeps the same fixed BLOCKED diagnostic. A later short health delay cannot
shorten a longer source cooldown. The Gmail refresh wrapper carries the delay
while preserving its fixed error code and omitting provider diagnostic material.
No immediate retry or extra provider request is added.

## Exact source and execution

Base: `94f08619fbd0939ee2ca7353a183bed97b1bc5bc`.
Original composed worker: `a05d2608735266d292005b60816fa690d4054e9d`.
Original focused test blob: `b3ca30ce309e477e40a2972ac5413e15c09c2670`.

The 11 new tests produce seven failing tests and zero errors against that exact
worker. The repaired candidate passes all 47 focused relay tests plus both
unchanged 15-test MAIL suites: 77 passing tests in isolated cloud Python.
Compilation passes. The GitHub writes returned exactly the locally tested blobs:

- Worker: `8ab37c0dad170e7ac9df3d397573c99832c4b4ad`
- Focused suite: `e75bc4b26e25d5c92732fffb8e127e26a4dd91af`

Controls cover initial auth, health creation/update, preservation of the current
health message, later/earlier deadline composition, state after a real CLI restart,
zero provider calls during cooldown, resumption at expiry, absent delays, RunLock
ownership at persistence, refresh error privacy, malformed grants and successful
refresh behavior. The fixtures contain synthetic provider data only.

Replay:
```sh
python3 -m unittest discover -s tests -p test_inbox_slack_relay.py -v
python3 -m unittest test_inbox_slack_relay_charset test_inbox_slack_relay_alternatives -v
python3 -m py_compile host/inbox_slack_relay.py tests/test_inbox_slack_relay.py
```

## Scope retained

All previously landed HTTP, MIME charset and alternative-fallback tests are kept.
ASTRA-VISIBILITY retains original implementation credit; MAIL retains both MIME
repairs and its workflow/runbook follow-through. F/equipment retains activation.
The existing workflow already runs this focused filename: no workflow or scheduler
change is required. Native CLI header transport, credential custody, source read/
done state, provider identities, privacy filters and sponsor actions are unchanged.

These are offline regression results, not proof of live inbox activation. Broad
repository CI and merge/current-main receipts are reported separately in Slack.
