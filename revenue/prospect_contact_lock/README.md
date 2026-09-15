# Prospect contact lock

`revenue.prospect_contact_lock` is the canonical **contact-level single-writer coordination primitive** for paid/prospective outbound work.

It exists because Slack-only TAKE messages are not atomic: two workers can discover the same hot lead, both see no claim, and send seconds apart. This package moves the collision point into one GitHub Contents compare-and-swap record keyed only by a privacy-minimized normalized contact fingerprint.

It does **not** send email/DM/provider traffic. It never emits `external_send_authorized=true`, never proves buyer acceptance/payment/revenue, and is only one prerequisite in the broader outbound safety chain.

## Canonical authority

Production authority is code-pinned. Ordinary callers cannot select an alternate repository, branch, API origin, record root, or transport implementation.

- API: `https://api.github.com`
- repository: `woahwhattheheck/commons`
- branch: `coordination/prospect-contact-lock-v1`
- root: `.coordination/prospect-contact-lock/v1`
- generation: `prospect-contact-lock/v1/2026-09-14`
- installed marker: `.coordination/prospect-contact-lock/v1/AUTHORITY.json`

`revenue.prospect_contact_lock.lock.ProspectContactLock` is the single production implementation. The package export and compatibility `hardened` import resolve to that same class. Its public constructor accepts only the GitHub token; deterministic transport substitution exists only on private test surfaces.

The production surface verifies the exact authority marker before every contact-record read. A missing branch, missing marker, malformed marker, or marker whose generation/repository/branch/root/digest differs from the compiled authority fails closed; record-level `404` is interpreted as ABSENT only after the marker has been proven readable and exact. The bearer token is sent only to the pinned HTTPS API/repository URL family. Redirects are refused rather than forwarding Authorization.

## Lifecycle

This is deliberately stricter than a lease. There is no ordinary timeout takeover.

### `ACTIVE`

`acquire` creates one record with GitHub Contents create semantics. Concurrent creates for the same normalized contact race the same path; one wins and the other fails closed.

An `ACTIVE` record has **no timeout**. A dead/crashed/stale worker does not silently turn ambiguity into new outreach authority.

### `ARMED`

Before any provider mutation, the exact owner binds the exact message SHA-256, channel, and paid/award compensation-path digest/category. A changed payload cannot silently replace an ARMED generation; the owner must explicitly release UNSENT and reacquire.

Because provider mutation has not yet been attempted, the exact owner may still explicitly release an ARMED record as UNSENT.

### `OUTCOME_UNKNOWN`

Immediately before the external provider call, the exact owner must `dispatch`. That CAS consumes the replayable attempt slot and transitions `ARMED -> OUTCOME_UNKNOWN`.

`OUTCOME_UNKNOWN` is fail-closed and has no timeout. Ordinary `acquire`, `release`, or a second `dispatch` all fail. This closes the crash/restart seam: if the provider accepted a message but the process dies before finalization, the same owner and every other worker are blocked from sending a second first contact.

A successful `dispatch` receipt is **not provider-send authority**. It proves only that this coordination layer burned its replayable slot. All separately required outbound controls still apply.

### `CONTACTED`

After confirmed provider acceptance, the exact dispatched owner calls `finalize` with the exact same message/channel/compensation binding plus provider receipt. Only the provider-receipt SHA-256 is retained.

`CONTACTED` is terminal for ordinary workers. It cannot be released and cannot be reacquired.

### `RELEASED`

`release` is allowed only from `ACTIVE` or `ARMED` by the exact owner+operation and means the operator asserts no provider contact occurred. The reason is retained only as SHA-256. `RELEASED` is the only ordinary state from which another owner may reacquire.

`OUTCOME_UNKNOWN` can never be ordinary-released. A future provider-history reconciliation mechanism may prove UNSENT, but that must be separately governed; this package intentionally leaves ambiguity stranded rather than guessing.

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

`arm` requires a concrete compensation path such as a fixed-price pilot, bounty/prize, bid/contract/subcontract, invoice/fee/retainer, or explicit positive amount. Canonical validation uses token/phrase boundaries rather than substring matching, so negative/larger-token prose such as `unpaid`, `repaid`, `uncontracted`, `not paid`, `no fee`, and zero-valued paths such as `$0` or `$0 bounty` cannot self-promote into a paid path. The plaintext is not retained. This proves only that the operator declared a path to compensation; it is not evidence of acceptance or payment.

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
```

Bind the exact candidate message and paid path before any external effect:

```bash
python -m revenue.prospect_contact_lock arm \
  --kind email --target lead@example.com \
  --agent-id Z-EXAMPLE --operation-id OP-PAID-1 \
  --message-file exact-message.txt \
  --channel email \
  --compensation-path '$2,500 paid pilot'
```

After all separately required external-send controls pass, consume the one-shot coordination slot **before** making the provider call:

```bash
python -m revenue.prospect_contact_lock dispatch \
  --kind email --target lead@example.com \
  --agent-id Z-EXAMPLE --operation-id OP-PAID-1
```

If provider acceptance is confirmed, finalize against the exact same payload:

```bash
python -m revenue.prospect_contact_lock finalize \
  --kind email --target lead@example.com \
  --agent-id Z-EXAMPLE --operation-id OP-PAID-1 \
  --message-file exact-message.txt \
  --channel email \
  --compensation-path '$2,500 paid pilot' \
  --provider-receipt 'provider message id / acceptance receipt'
```

If **no provider action occurred** and the state is still ACTIVE or ARMED, the exact owner may explicitly release:

```bash
python -m revenue.prospect_contact_lock release \
  --kind email --target lead@example.com \
  --agent-id Z-EXAMPLE --operation-id OP-PAID-1 \
  --reason 'route invalid before provider mutation'
```

There is intentionally no `--repo`, `--branch`, `--root`, `--api-url`, transport override, timeout, force-release, stale-takeover, OUTCOME_UNKNOWN-release, or CONTACTED-reopen option.

## Mandatory operating order

1. Search/read live relationship/DNR and organization-level pressure controls.
2. Establish the canonical contact route and paid path.
3. `acquire` this contact lock.
4. `arm` the exact message/channel/paid-path binding.
5. Re-read provider history and satisfy every higher/lower outbound control in force.
6. `dispatch` to durably consume this coordination layer's one-shot attempt slot.
7. Only then perform at most the separately authorized provider action.
8. If provider acceptance is confirmed, `finalize` immediately.
9. If dispatch occurred but outcome is ambiguous or no acceptance receipt is available, **do not release or resend**. Leave `OUTCOME_UNKNOWN` fail-closed for reconciliation.
10. If no dispatch/provider action occurred, `release` explicitly.

## Validation

```bash
python -m py_compile \
  revenue/prospect_contact_lock/__init__.py \
  revenue/prospect_contact_lock/__main__.py \
  revenue/prospect_contact_lock/_core.py \
  revenue/prospect_contact_lock/lock.py \
  revenue/prospect_contact_lock/hardened.py \
  revenue/prospect_contact_lock/cli.py \
  revenue/prospect_contact_lock/_legacy_test_lock.py \
  revenue/prospect_contact_lock/test_lock.py \
  revenue/prospect_contact_lock/test_hardened.py

python -m unittest -v revenue.prospect_contact_lock.test_lock revenue.prospect_contact_lock.test_hardened
python -O -m unittest -v revenue.prospect_contact_lock.test_lock revenue.prospect_contact_lock.test_hardened
```

The combined hostile suite covers same-contact contention, no-timeout stale blocking, exact-owner release/finalize, ARMED payload immutability, explicit ARMED release, one-shot dispatch consumption, same-owner replay after dispatch, OUTCOME_UNKNOWN no-release/no-reacquire, exact payload binding at finalization, permanent CONTACTED suppression, CAS loss, canonical namespace binding, missing/tampered authority-marker fail-closed behavior before record reads, direct-submodule import equivalence, public transport-injection rejection, paid-path token-boundary/negative/zero regressions, raw-contact non-retention, digest-only evidence, server-Date fail-closed behavior, token-bearing URL origin pinning, duplicate-key/tampered-record rejection, receipt tamper detection, message-file bounds, and history-chain advancement.

## Lineage

Canonical issue **#14220** established the no-auto-expiry contact-lock requirement. Closed/unmerged PR **#14273** is donor evidence only; it surfaced useful lessons around GitHub server time, canonical namespace binding, token-egress/redirect safety, digest-only evidence, monotonic suppression, and provider-ambiguity handling. #14434 landed the recovered state machine plus the pre-send `ARMED -> OUTCOME_UNKNOWN` consume boundary. Post-merge repair **#14475 / #14493** closes the remaining production-surface bypass by making `lock.py` the sole hardened production facade and removing arbitrary transport injection from ordinary construction.
