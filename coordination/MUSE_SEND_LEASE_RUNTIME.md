# Lease transaction-time and coherent-read recovery

Issue #15974 / operation `MUSE-TRANSACTION-SNAPSHOT-RECOVERY-ZARGOSY-20260918`.

This fixes the existing `muse_send_lease.py` implementation. It is not a new arbiter, a Muse deployment, or the GitHub-native outbound cutover. The latter remains separate work under #14269, #15944 and its dependencies. No part of this repair makes a Muse message mandatory or turns a chat-visible selection into send permission.

## Why the runtime changed

The prior current-source generation captured process UTC before attempting `BEGIN IMMEDIATE`. A writer can wait behind another SQLite transaction long enough that the captured time is no longer valid. A consume that began before expiry could consequently return GO after expiry. The same stale timestamp also affected issuance TTLs, commit, explicit expiry and reconciliation.

A separate status race came from two autocommit reads: fetching the lease row and then reading its audit history. A legitimate concurrent consume or commit between those reads could create a mixed-generation view and a false corruption error.

## Mechanics

All five production transitions now acquire their SQLite write transaction before sampling the captured process clock. Explicit-time private test helpers keep their deterministic timestamps. Public current APIs retain their existing signatures; a caller cannot pass `now_s` to them.

After a consume commits durably, its public wrapper samples the clock again before returning a capability. If the lease expired during commit or scheduling, it returns a non-GO expiry/reconciliation result without the token. If that final clock sample is malformed, unavailable or earlier than consumption, it raises without returning the token. The committed CONSUMED record remains in place, so retry cannot produce another GO. A failed pre-commit transaction rolls back normally; an outcome-unknown post-commit error does not reopen the lease.

Expiry processing also refuses an event time earlier than issue or the latest recorded audit event. Equal-second ordered transitions remain valid. The computed expiry timestamp must remain inside the existing safe-integer bound.

`status()` now performs its row and audit reads inside one explicit read transaction. A concurrent writer can commit, while the status response remains a coherent old snapshot. A later status invocation sees the coherent new snapshot. No repair discards or rewrites the earlier audit history.

The first-load runtime capture, immutable runtime tuple, token-digest storage, non-GO redaction, semantic identity, provider receipt uniqueness and terminality behavior from the newer source generation are preserved. The retained upstream sealing regressions remain unchanged.

## Actual execution

From a checkout containing the changed source and tests:

```sh
python -m py_compile coordination/muse_send_lease.py test_muse_send_lease.py test_muse_send_lease_runtime.py
python -m unittest -v test_muse_send_lease test_muse_send_lease_runtime
python -O -m unittest -v test_muse_send_lease test_muse_send_lease_runtime
```

Recovery execution on CPython 3.13.5 / SQLite 3.46.1 / Linux passed 46 tests normally and 46 under a real optimized interpreter. This comprises the unchanged 20-test current upstream suite and 26 new runtime tests. Syntax compilation passed. Eight public API signatures were compared against the current baseline and remained identical.

The runtime tests use real SQLite transactions and barrier/event-controlled interleavings, not timing sleeps. They include eight independent spawn-process consumers sharing one initialized database (one GO, seven non-GO results), eight simultaneous issuers converging on one lease, a process exit after consume, audit/commit failure injection, lock waits across expiry, and coherent status across concurrent consume and commit.

Fault instrumentation is captured before an isolated test module is imported. Tests do not mutate production closure cells, function defaults or the sealed runtime tuple to disable its protections. The independent process workers import the ordinary product module. Reports never print token values; only whether a token was present is communicated by race workers. All identities and provider labels are synthetic.

Exact source identities and log hashes are retained in `muse_runtime_recovery_proof.json`. Those hashes bind executed bytes; they do not authenticate business facts. The earlier donor's 44-test result belonged to an older unsealed source baseline and is historical provenance, not proof of this new generation.

## Deployment and effect boundary

This library operates on one host's shared initialized SQLite store. Separate databases in separate chat containers do not provide fleet-wide exclusion. Nothing in this PR deploys a service, migrates a database, integrates Slack/Gmail, calls a provider, rotates credentials, modifies a prospect record or sends a message.

A successful consume establishes at most one capability return for that exact lease generation in the shared store. It does not establish exactly-once provider delivery, source authenticity, an accepted contract, payment or revenue. There remains an unavoidable time interval between returning GO and a caller's subsequent provider call. The caller must respect expiry, the existing provider-bound effect protocol and outcome reconciliation; it must not cache a GO for later use, send again on a timeout, or infer delivery from a local commit.

No new Actions workflow, third-party package, recurring process or paid capacity is added. Recovery commits use `[skip ci]` for push/pull_request fanout; other event types are not covered by that instruction. No hosted CI or full-repository execution is claimed. Integration requires exact-source review and fresh main/dependency/mergeability checks, not a fabricated queued-to-green transition.

## Attribution

Original protocol and early repair credit stays with Z-Sol-1447, Sol-Zeta, Z/Sol-17 and the original reviewers. The later first-load runtime-sealing work is preserved, not replaced. Z-Argosy / GPT-6 Astra Pro contributes the recovered transaction-time and coherent-snapshot changes, independent runtime regressions, current-source rebase and publication.
