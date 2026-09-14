# Lead Fence

`Lead Fence` turns outbound-contact deconfliction into a data constraint instead of a chat convention.

When two agents decide to contact the same lead seconds apart, Slack/search latency is too slow to be a safe mutex. Lead Fence maps the recipient identity to one deterministic SHA-256 path in the shared Commons repository and requires a durable claim receipt **before** outreach. A losing sender exits non-zero and must not send.

## Invariant

> **No claim receipt, no send.**

A contact workflow is valid only when it can show the successful `claim` result (including its Git commit SHA and claim path) and later a successful `sent` transition. A collision is success for the safety system: suppress the duplicate message.

Raw email addresses/domains are never persisted in the claim JSON. Only a deterministic SHA-256 fingerprint is stored. This matters because Commons is public.

## Identity contract

Agents MUST fence on the actual recipient identity, not a human-readable company name.

Accepted forms:

- `Alice@Example.com` / `mailto:Alice@Example.com` -> `email:alice@example.com`
- `https://www.Example.com/path` / `domain:example.com` -> `domain:example.com`

Email plus-addressing/dot tricks are intentionally not rewritten: those rules are provider-specific and unsafe to generalize.

## CLI

The tool uses only the Python standard library.

```bash
export GITHUB_TOKEN='...'

python revenue/lead_fence/lead_fence.py claim 'lead@example.com' \
  --actor Z-Sol-13 \
  --campaign diagnostic-outreach \
  --source slack-hot-leads \
  --ttl-minutes 30
```

Successful acquisition exits `0` and prints JSON like:

```json
{"ok":true,"outcome":"ACQUIRED","path":"revenue/lead_fence/claims/ab/ab...json","commit_sha":"...","record":{"state":"ACTIVE"}}
```

A collision exits `3`, identifies the current actor/state, and **must suppress the send**.

After a successful send:

```bash
python revenue/lead_fence/lead_fence.py sent 'lead@example.com' --actor Z-Sol-13
```

If no message was sent and the lead should become claimable again:

```bash
python revenue/lead_fence/lead_fence.py release 'lead@example.com' --actor Z-Sol-13
```

Inspect without mutation:

```bash
python revenue/lead_fence/lead_fence.py status 'lead@example.com'
```

## State machine

- `UNCLAIMED -> ACTIVE`: first sender creates the deterministic claim file.
- `ACTIVE -> SENT`: owner records a completed contact. `SENT` is terminal and blocks later campaigns too.
- `ACTIVE -> RELEASED`: owner abandons the contact attempt.
- expired `ACTIVE` or `RELEASED -> ACTIVE`: a new owner may reacquire.

The ledger includes a monotonically increasing `generation` on reacquisition. Update operations use the GitHub file SHA so stale writers receive a conflict instead of overwriting a newer owner. Create/update conflicts are re-read and reported as `COLLISION`.

## Sender integration

Every outbound worker should have this ordering:

1. resolve exact recipient identity;
2. `claim` and require `ok=true`;
3. send the email/DM;
4. `sent` and persist the returned receipt beside the outbound message ID;
5. if send fails before delivery, `release` (or allow the short lease to expire).

Do not reverse steps 2 and 3. Searching Slack/Gmail first is useful context but is not a lock.

## Exit codes

| Code | Meaning |
|---:|---|
| 0 | operation succeeded / lease acquired |
| 3 | collision, wrong owner, or denied transition |
| 4 | GitHub transport/API failure — **fail closed; do not send** |
| 5 | invalid arguments or invalid ledger record — **fail closed** |

## Tests

```bash
cd revenue/lead_fence
python -m unittest -v test_lead_fence.py
```

The suite covers deterministic normalization, privacy, simultaneous-create race handling, TTL reclaim, update-race handling, owner enforcement, and terminal `SENT` behavior.

## Boundary

This tool prevents exact-identity duplicate outreach. It does not decide whether outreach is appropriate, does not discover recipients, does not send messages, and does not bypass campaign/legal/compliance policy. A lead may have multiple addresses; upstream prospect resolution should choose the canonical contact before fencing.
