# Outbound mutex

A duplicate outbound message can destroy a hot lead. This package makes **one writer per lead** an enforceable protocol instead of a Slack convention.

## Invariant

No agent may send outreach unless it owns the current durable lease for that exact opportunity/channel/destination and has re-read the provider immediately before send.

The canonical lock path is deterministic:

`coordination/outbound/leases/<sha256>.json`

The digest is derived from normalized `opportunity + channel + destination`. The public lease stores only a destination hash; it never stores the raw email address.

## Production protocol: GitHub CAS

GitHub `main` is the coordination authority. Do **not** treat a local file, Slack message, stale search result, or an unverified POST as ownership.

1. Compute the deterministic key/path with `lease.py key`.
2. Re-read the provider (for email: the exact thread/history). Record that provider snapshot identifier.
3. **Initial claim:** create the canonical lease path on current `main`. Use a create-if-absent operation. If the path exists or the write loses a race, you do not own the lead and must not send.
4. Fetch the just-landed lease from current `main`; verify `state=active`, `holder=<you>`, and the lease is unexpired.
5. Re-read the provider again immediately before sending. Run preflight against the current provider snapshot. Any changed provider state invalidates the send; stop and re-evaluate.
6. Send once.
7. **Immediately** replace the lease with `state=sent` using the exact current blob SHA. Persist only a hash of the provider send receipt/message ID. `sent` is terminal forever.

### Takeover / release

An active lease can be taken over only after expiration. A released lease may be taken over immediately. Fetch the current file and update using its exact blob SHA; two contenders using the same prior SHA cannot both win. A `sent` lease can never be released or taken over.

For GitHub connector seats, the primitives are deliberately boring:

- `fetch_file` current lease
- `create_file` initial claim
- `update_file(... sha=<exact current blob SHA>)` release, takeover, or sent receipt

Always fetch again after a successful write and before a send.

## Provider snapshot

The provider snapshot is a non-secret version marker that changes if relevant provider state changes. For Gmail, use a stable combination that changes when the thread changes (for example thread/message/history identity from the provider read). The lease stores only its SHA-256 fingerprint.

A provider change after claim is not permission to “send fast.” It is a mandatory stop: another agent or the prospect may have acted.

## CLI

```bash
python revenue/outbound_mutex/lease.py key \
  --opportunity "Acme / $199 diagnostic" \
  --channel email \
  --destination buyer@example.com

python revenue/outbound_mutex/lease.py claim \
  --opportunity "Acme / $199 diagnostic" \
  --channel email \
  --destination buyer@example.com \
  --holder Z-Forge \
  --provider-snapshot 'thread:abc/history:123'
```

The `claim` command emits canonical JSON for the initial create. It does not send mail and it does not claim the remote lease by itself.

## Tests

```bash
cd revenue/outbound_mutex
python -m unittest -v test_lease.py
```

The suite includes 32 simultaneous initial claimants and 24 simultaneous takeover CAS contenders. Exactly one may win each race.
