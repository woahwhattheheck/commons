# Prospect contact lock

`revenue.prospect_contact_lock` is the canonical **contact-level single-writer coordination primitive** for paid/prospective outbound work.

It exists because Slack-only TAKE messages are not atomic: two workers can discover the same hot lead, both see no claim, and send seconds apart. This package moves the collision point into one GitHub Contents compare-and-swap record keyed only by a privacy-minimized normalized contact fingerprint.

It does **not** send email/DM/provider traffic. It never emits `external_send_authorized=true`, never proves buyer acceptance/payment/revenue, and is only one prerequisite in the broader outbound safety chain.

## Canonical authority

Production authority is code-pinned. Ordinary callers cannot select an alternate repository, branch, API origin, or record root.

- API: `https://api.github.com`
- repository: `woahwhattheheck/commons`
- branch: `coordination/prospect-contact-lock-v1`
- root: `.coordination/prospect-contact-lock/v1`
- generation: `prospect-contact-lock/v1/2026-09-14`

The bearer token is sent only to the pinned HTTPS API/repository URL family. Redirects are refused rather than forwarding Authorization.

## Lifecycle

The lifecycle is deliberately stricter than a lease.

### `ACTIVE`

`acquire` creates one record with GitHub Contents create semantics. Concurrent creates for the same normalized contact race the same path; one wins and the other fails closed.

An `ACTIVE` record has **no timeout**. A dead/crashed/stale worker does not silently turn ambiguity into new outreach authority. Another worker must not contact the prospect until the exact current owner records an explicit `RELEASED` state as UNSENT, or a separately governed recovery mechanism is added in a later control.

### `RELEASED`

`release` is allowed only for the exact `ACTIVE` owner+operation and means the worker asserts that no provider contact occurred. The reason is stored only as SHA-256. `RELEASED` is the only ordinary state from which another owner may reacquire.

### `CONTACTED`

`finalize` is allowed only for the exact `ACTIVE` owner+operation after it has observed provider acceptance. It stores only digests of the exact message, provider receipt, and compensation path plus bounded channel/category metadata.

`CONTACTED` is terminal for ordinary workers. It cannot be released and cannot be reacquired. This intentionally prefers false-negative outreach opportunities over duplicate contact.

## Why the key ignores campaign names

The record key is derived from:

```text
sha256("prospect-contact-lock/v1\0" + kind + "\0" + normalized_contact)
```

Campaign name, offer text, price, subject, opportunity ID, worker name, and Slack wording are absent. Two workers calling the same email `$2,500 pilot` and `invoice-resolution diagnostic` still contend on one contact key.

Organization-wide cross-contact pressure is a separate layer: two different people at the same company legitimately have different contact keys. The organization lease/pressure controls compose above this primitive.

## Privacy

Raw contact values never appear in record paths. Records contain the contact fingerprint and a masked hint. Message bodies, provider IDs, release reasons, and compensation-path text are never retained; only their SHA-256 digests are.

Supported target kinds:

- `email`: Unicode NFKC, case-folded local part, IDNA/lowercase domain.
- `domain`: qualified IDNA/lowercase domain.
- `phone`: normalized E.164.

## Paid-path requirement

`finalize` requires a concrete compensation path such as a fixed-price pilot, bounty/prize, bid/contract/subcontract, invoice/fee/retainer, or explicit amount. The plaintext is not retained. This proves only that the operator declared a path to compensation; it is not evidence of acceptance or payment.

## CLI

Fingerprinting does not need credentials:

```bash
python -m revenue.prospect_contact_lock fingerprint \
  --kind email --target lead@example.com
```

Remote operations require `GITHUB_TOKEN` with write access to the canonical coordination branch:

```bash
python -m revenue.prospect_contact_lock acquire \
  --kind email --target lead@example.com \
  --agent-id Z-EXAMPLE --operation-id OP-PAID-1

python -m revenue.prospect_contact_lock status \
  --kind email --target lead@example.com
```

After a confirmed provider acceptance, hash the exact sent message from a bounded regular file and finalize:

```bash
python -m revenue.prospect_contact_lock finalize \
  --kind email --target lead@example.com \
  --agent-id Z-EXAMPLE --operation-id OP-PAID-1 \
  --message-file exact-message.txt \
  --channel email \
  --compensation-path '$2,500 paid pilot' \
  --provider-receipt 'provider message id / acceptance receipt'
```

If **nothing was sent**, the exact owner may explicitly release:

```bash
python -m revenue.prospect_contact_lock release \
  --kind email --target lead@example.com \
  --agent-id Z-EXAMPLE --operation-id OP-PAID-1 \
  --reason 'route invalid before provider mutation'
```

There is intentionally no `--repo`, `--branch`, `--root`, `--api-url`, timeout, force-release, stale-takeover, or CONTACTED-reopen option.

## Mandatory operating order

1. Search/read live relationship/DNR and organization-level pressure controls.
2. Establish the canonical contact route and paid path.
3. `acquire` this contact lock.
4. Re-read provider history immediately before any external mutation.
5. Satisfy all higher/lower outbound controls in force. **An ACQUIRED receipt alone never authorizes sending.**
6. Perform at most the externally authorized provider action.
7. If provider acceptance is confirmed, `finalize` immediately.
8. If no provider action occurred, `release` explicitly. If outcome is ambiguous, **do not release**; leave ACTIVE fail-closed and reconcile under a separately governed recovery path.

## Validation

```bash
python -m py_compile \
  revenue/prospect_contact_lock/__init__.py \
  revenue/prospect_contact_lock/__main__.py \
  revenue/prospect_contact_lock/lock.py \
  revenue/prospect_contact_lock/cli.py \
  revenue/prospect_contact_lock/test_lock.py

python -m unittest -v revenue.prospect_contact_lock.test_lock
python -O -m unittest -v revenue.prospect_contact_lock.test_lock
```

Hostiles cover same-contact contention, no-timeout stale blocking, exact-owner release/finalize, explicit-release reacquisition, permanent CONTACTED suppression, CAS loss, canonical namespace binding, raw-contact non-retention, digest-only evidence, server-Date fail-closed behavior, token-bearing URL origin pinning, duplicate-key/tampered-record rejection, receipt tamper detection, message-file bounds, and history-chain advancement.

## Lineage

This lands canonical issue **#14220**. Closed/unmerged PR **#14273** is donor evidence only; it surfaced useful lessons around GitHub server time, canonical namespace binding, token-egress/redirect safety, digest-only evidence, monotonic suppression, and provider-ambiguity handling. This implementation does not revive its stale branch history. It adopts #14220's stricter requirement that stale claims fail closed rather than auto-expire.
