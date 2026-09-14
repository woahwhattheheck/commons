# Organization Contact Pressure Prerequisite

This package authenticates retained cross-contact pressure for one **canonical organization**. It prevents a different person, route, domain alias, or opportunity label from being treated as fresh when the retained ledger already records active, recent, replied, unsubscribed, bounced, or do-not-resend pressure.

It is a **read-only prerequisite**, not the organization-wide mutex. Two callers can inspect the same quiet generation concurrently and both receive `READY_FOR_SINGLE_WRITER_REVIEW`. Every positive receipt therefore requires the separately retained `ATOMIC_ORGANIZATION_OUTBOUND_LEASE` before any external-send boundary. This package does not send messages and never emits external-send authority.

## Boundary

The gate composes ahead of, and does not replace:

1. the atomic organization-wide outbound lease;
2. per-prospect atomic custody;
3. commercial-opportunity custody;
4. initial-outreach one-shot consumption; and
5. the provider-bound send consumer.

The strongest result is `READY_FOR_SINGLE_WRITER_REVIEW`. The signed receipt always carries `external_send_authorized=false` and names every downstream control still required. A READY receipt is not an acquired organization lease.

## Retained authority

Production selects a fixed POSIX root; callers cannot pass a key, key path, authority path, retained-ledger path, ledger-head path, cooldown, or evaluation time.

- POSIX: `/var/lib/commons/organization-contact-pressure`
- Windows: production verification fails closed until handle-bound reparse-point traversal and retained-root owner/ACL verification are implemented.

Layout:

```text
active-key.json
keys/<key-id>.key
authorities/<organization-scope-sha256>.json
ledgers/<organization-scope-sha256>.json
ledger-heads/<organization-scope-sha256>/
  <policy-generation>-<ledger-generation>-<ledger-sha256>-<verifier-epoch-sha256>.json
```

Key, pointer, authority, ledger, and ledger-head files must be regular non-symlink files. On POSIX they must have no group/other permission bits. The key is exactly 32 bytes encoded as 64 hexadecimal characters.

The active pointer is:

```json
{"schema":"organization-contact-pressure-key-pointer/v1","key_id":"primary-20260914","verifier_id":"commons-host-1"}
```

Authority, ledger, and ledger-head records are HMAC-SHA256 authenticated. The organization scope and route scopes are opaque SHA-256 commitments; retained records contain no raw organization name, domain, email address, contact name, message body, or provider credential.

### Rollback-resistant currentness

The mutable ledger is accepted only when it exactly matches the highest checkpoint in the active verifier-and-policy epoch by generation, SHA-256, and `updated_at`.

- restoring an older authentic ledger below a retained higher head fails closed;
- a ledger newer than the committed head fails closed;
- two active-epoch checkpoints with the same generation and different ledger identities are a fork and fail closed;
- verifier-key rotation requires a fresh checkpoint under the new active key/verifier epoch;
- policy-generation rotation requires a fresh checkpoint and does not misclassify an unchanged event-count generation as a fork;
- old verifier or policy epoch checkpoints may remain for history but cannot authorize the current ledger.

The checkpoint journal is a separate host-owned retained object. A publisher may write the ledger and checkpoint in either order; readers fail closed during the incomplete transition and resume only when the pair agrees. This closes partial ledger-file rollback while the host-owned head journal remains current.

## Event semantics

Supported events:

- `PROPOSED`: a route is under active internal consideration;
- `SENT`: provider-confirmed outbound contact;
- `HUMAN_REPLY`: real human response, never equivalent to acceptance;
- `AUTO_REPLY`: automated response, distinct from human interest;
- `HARD_BOUNCE`: permanent suppression of that exact route;
- `UNSUBSCRIBE`: organization-wide do-not-contact;
- `DNR`: organization-wide explicit do-not-resend;
- `OWNER_RELEASE`: resolves one earlier `PROPOSED`, `SENT`, `HUMAN_REPLY`, or `AUTO_REPLY` event.

Exact event replay is idempotent. Reusing an event ID with changed bytes is `HOLD_CONFLICT`. Release must point to an existing releasable event and occur later than it. `UNSUBSCRIBE`, `DNR`, and route hard-bounce state are not erased by an ordinary release.

A release resolves active work; it does **not** erase the authenticated cooldown. A recent released send/reply remains `HOLD_RECENT_CONTACT` until the policy-bound cooldown ends.

## Decisions

- `READY_FOR_SINGLE_WRITER_REVIEW`
- `HOLD_ORG_ACTIVE`
- `HOLD_RECENT_CONTACT`
- `HOLD_HUMAN_REPLY`
- `HOLD_DNR`
- `HOLD_AUTHORITY`
- `HOLD_CONFLICT`

Positive READY receipts have short, authenticated validity and are rechecked against the live authority, ledger generation, ledger digest, and retained ledger head. HOLD receipts remain historically verifiable after later generations move.

## CLI

```bash
python -m revenue.organization_contact_pressure.gate compile request.json receipt.json
python -m revenue.organization_contact_pressure.gate verify receipt.json
```

Exit codes:

- `0`: READY compiled, or receipt verified;
- `2`: malformed input / unsafe file / attempted overwrite / ambiguous publication;
- `3`: canonical HOLD compiled;
- `4`: retained authority unavailable or receipt verification failure.

The CLI owns current UTC. There is deliberately no `--now`, `--key`, `--authority-root`, `--cooldown`, or provider-send option. Output creation is exclusive. Immediately before success, the CLI reopens the requested lexical path and proves inode identity, regular-file mode, exact size, and exact bytes. Failure cleanup unlinks only the inode created by that invocation; a renamed or foreign replacement is preserved.

## Authority ceiling

No Gmail, Slack, customer, procurement portal, calendar, payment, wallet, or other provider is called. A READY receipt does not prove exclusive organization ownership, buyer interest, scope acceptance, award, payment, cash, booked revenue, or recognized revenue. It proves only that retained pressure evidence and its current-head checkpoint were coherent enough to request the separately atomic organization lease and the other named downstream controls.
