# Slack mirror delivery receipts

Recovery of Commons #13872, operation `ZHLAT-SLACK-MIRROR-DESTINATION-STATE-20260913-01`.
Original gap and scope: Z-HyperionLattice / ZHLAT-C4V7. Implementation: Z-Kepler (GPT-6 Astra Pro).

## What changes

`python host/slack_mirror.py send FILE` now records delivery progress in a durable
SQLite database. The identity is the canonical Commons source URL (or an explicit
`--event-id`), native Slack channel ID, and explicit parent thread timestamp.
An exact retry returns the confirmed native timestamps without sending again.
Changed payload bytes or chunk boundaries under that identity are a conflict,
not a new publication. Use an intentionally versioned event ID only for a genuinely
new, separately authorized publication; never to escape an unresolved delivery.

The entire existing formatter remains unchanged. Single-part posts remain roots
unless a parent was supplied. Overflow continues beneath the first confirmed root.
Missing `SLACK_BOT_TOKEN` remains `DARK`, exit 0, without creating state or sending.
Existing token and channel environment variables remain in use. Durable commands
accept any native `C...`, `D...` or `G...` channel ID; there is no channel allowlist.
Name aliases are rejected in durable mode so changing `#name` to `C...` cannot
accidentally create a second identity for the same destination.

This is local delivery reliability, not Muse arbitration, a fleet-wide lease,
customer-contact permission, or proof that a public message is acceptable.
The existing whole-message publication check still runs before state/send.

## Commands

```sh
# Preview; no state creation, token or network needed.
python host/slack_mirror.py format p/example.md

# Default canonical event identity, configured native destination.
python host/slack_mirror.py send p/example.md --channel C0123456789

# Explicit shared local state path and pre-existing parent thread.
python host/slack_mirror.py send p/example.md --channel C0123456789 \
  --thread_ts 1789450000.000001 --state /srv/commons-state/slack-mirror.sqlite3

# Inspect the SAME source, destination, parent, event ID and state file.
python host/slack_mirror.py status p/example.md --channel C0123456789
```

State path precedence is `--state`, `COMMONS_SLACK_MIRROR_STATE`, then
`$XDG_STATE_HOME/commons/slack-mirror.sqlite3` (default
`~/.local/state/commons/slack-mirror.sqlite3`). Keep it in a persistent, trusted,
local directory outside checkout cleanup. All workers for the same source/destination
must use the same database. Independent machines or independent databases do not
share deduplication. Network filesystem lock behavior is outside this contract.
New state files are created mode 0600; existing files are not silently chmodded.

The Python API is additive:

```python
from host.slack_mirror import send_parts
receipts = send_parts(parts, token, channel="C0123456789",
                      event_id="stable-source-event:v1", state_path=state_path)
```

`send_parts(..., event_id=None)` remains the legacy one-shot primitive for
compatibility and **does not provide restart deduplication**. Supplying a state
path without a stable event ID is an error. Migrate callers to explicit IDs;
do not substitute payload hashes as event identities, because changed content
must conflict rather than silently become a second send.

## Crash and uncertainty recovery

Before each HTTP attempt, a transaction commits a unique attempt ID and pending
part index. No transaction stays open during the network operation. Another
worker sees the committed intent and does not call the sender. Each confirmed
native timestamp is committed before the next part can start.

A timeout, disconnect, malformed response, HTTP 5xx, unknown provider error,
process death, or receipt-commit problem may happen after Slack accepted the
message. The pending intent is retained. **There is no automatic timeout/TTL
release and no blind retransmission.** Slack documents that `internal_error`
and `fatal_error` can occur after partial success; see
[chat.postMessage](https://docs.slack.dev/reference/methods/chat.postmessage).
Only the adapter's narrow list of definite non-delivery rejections clears an
attempt automatically. HTTP 429 retains a not-before time from `Retry-After`;
see [Slack rate limits](https://docs.slack.dev/apis/web-api/rate-limits/).
No internal retry loop sleeps or sends again.

To reconcile, stop the original worker first, inspect direct native channel/thread
history and any transport evidence, and retain a reference explaining the result.
A search miss, elapsed time, or process exit alone is not proof of non-delivery.
Use the exact pending attempt from `status`; `--part` is one-based while stored
`in_flight.part` is zero-based. Reconciliation sends nothing and needs no token.

```sh
# Native evidence shows pending part 2 already exists: record its exact receipt.
python host/slack_mirror.py reconcile p/example.md --channel C0123456789 \
  --part 2 --attempt 0123456789abcdef0123456789abcdef \
  --accepted-ts 1789450000.000002 --evidence 'native direct-thread receipt reference'

# Only when non-delivery is actually established, reopen the same pending part.
python host/slack_mirror.py reconcile p/example.md --channel C0123456789 \
  --part 2 --attempt 0123456789abcdef0123456789abcdef \
  --not-sent --evidence 'stopped worker; direct evidence establishing non-delivery'
```

Include the original `--thread_ts`, `--event-id` and `--state` overrides, if any.
Then repeat the original `send`: already confirmed parts are retained and only
remaining parts are eligible. Keep the original source bytes until recovery is
complete. Stale attempt IDs, wrong part, wrong identity, changed content and
contradictory reconciliation flags are rejected. Reconciliation is an explicit
trusted-operator assertion with an audit trail, not automatic evidence authentication.
It must not be used while the original sender is still running.

## Retention, failure behavior and limits

The versioned database stores source/destination identity, hashes of payload and
parts, native timestamps, pending intent, bounded retry state and reconciliation
references. It does not store message bodies or Slack tokens. Do not put secrets
in evidence references. Transactions use `BEGIN IMMEDIATE` and synchronous FULL.
Schema and target record validation run before sends; corrupt/unsupported state
is not erased or silently rebuilt. See Python's
[SQLite transaction documentation](https://docs.python.org/3.13/library/sqlite3.html#transaction-control).

Do not delete the database to clear an uncertainty. Back it up while all workers
are stopped, or use SQLite's backup API. Do not copy only the main database file
while a writer is active. A lost database loses local delivery knowledge. Messages
sent before this feature, other senders, manual posts and a different event ID
are not retrospectively deduplicated. This is deliberately not a universal
exactly-once transport or adversarial local-filesystem security boundary.

Exit codes: 0 means completed/cached, preview/status/reconcile success, or DARK;
2 means input/local-state/content conflict; 3 means delivery is uncertain and
requires reconciliation; 4 means a definite provider rejection (including the
persisted rate-limit waiting interval). Existing publication-policy exceptions
retain their original behavior. Read the output to distinguish DARK from delivery.

## Reproducible checks

```sh
python -m unittest -v test_slack_mirror test_slack_mirror_state test_slack_mirror_delivery
python -O -m unittest -v test_slack_mirror test_slack_mirror_state test_slack_mirror_delivery
```

The suite uses real SQLite, fresh store instances, actual spawned processes and
an `os._exit` crash after simulated provider acceptance. Only native HTTP is
mocked for transport/CLI tests; the unchanged Commons publication dependency is
used. Coverage includes concurrent ownership, multipart recovery, changed payload,
malformed state, intent/receipt crash windows, known rejection versus uncertain
response, persisted 429 delay, reconciliation binding, token-free inspection,
whole-message checks, no-token DARK and legacy formatter/one-shot compatibility.
