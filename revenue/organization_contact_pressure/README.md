# Organization Contact Pressure Gate

This package prevents a different person, route, domain alias, or opportunity label at the **same canonical organization** from being treated as a fresh cold-outreach surface while another organization-level contact is active, recent, replied, unsubscribed, or marked do-not-resend.

It is an internal revenue-safety control. It does not send messages and never emits external-send authority.

## Boundary

The gate composes ahead of, and does not replace:

1. per-prospect atomic custody;
2. commercial-opportunity custody;
3. initial-outreach one-shot consumption; and
4. the provider-bound send consumer.

The strongest result is `READY_FOR_SINGLE_WRITER_REVIEW`. The receipt always carries `external_send_authorized=false` and names the downstream controls still required.

## Retained authority

Production selects a fixed root; callers cannot pass a key, key path, authority path, retained-ledger path, cooldown, or evaluation time.

- POSIX: `/var/lib/commons/organization-contact-pressure`
- Windows: `C:\ProgramData\Commons\organization-contact-pressure`

Layout:

```text
active-key.json
keys/<key-id>.key
authorities/<organization-scope-sha256>.json
ledgers/<organization-scope-sha256>.json
```

Key, pointer, authority, and ledger files must be regular non-symlink files. On POSIX they must have no group/other permission bits. The key is exactly 32 bytes encoded as 64 hexadecimal characters.

The active pointer is:

```json
{"schema":"organization-contact-pressure-key-pointer/v1","key_id":"primary-20260914","verifier_id":"commons-host-1"}
```

Authority and ledger generations are HMAC-SHA256 authenticated. The organization scope and route scopes are opaque SHA-256 commitments; the retained records contain no raw organization name, domain, email address, contact name, message body, or provider credential.

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

Positive READY receipts have short, authenticated validity and are rechecked against the live authority and ledger generation. HOLD receipts remain historically verifiable after later generations move.

## CLI

```bash
python -m revenue.organization_contact_pressure.gate compile request.json receipt.json
python -m revenue.organization_contact_pressure.gate verify receipt.json
```

Exit codes:

- `0`: READY compiled, or receipt verified;
- `2`: malformed input / unsafe file / attempted overwrite;
- `3`: canonical HOLD compiled;
- `4`: retained authority unavailable or receipt verification failure.

The CLI owns current UTC. There is deliberately no `--now`, `--key`, `--authority-root`, `--cooldown`, or provider-send option. Output creation is exclusive.

## Authority ceiling

No Gmail, Slack, customer, procurement portal, calendar, payment, wallet, or other provider is called. A READY receipt does not prove buyer interest, scope acceptance, award, payment, cash, booked revenue, or recognized revenue. It only proves that the retained organization-pressure evidence was coherent enough to proceed to the existing single-writer and provider-bound controls.
