# Terminal outbound send authority v2

This package is the terminal wrapper for paid/commercial outbound email. It exists because offline guard receipts and self-consistent lease JSON are not enough to prevent two workers from sending overlapping offers within seconds of each other.

The safety target is deliberately narrow and hard:

> for one authenticated buyer + commercial opportunity, at most one new outbound send attempt may cross the provider boundary unless a separate recovery/revision authority is explicitly designed and approved.

That means a `$5,000` offer and a `$7,500` variant for the same buyer/opportunity **must share one `commercial_scope`**. Different recipients/routes for that same buyer/opportunity also share it. `offer_scope` may describe the exact offer generation, but it is intentionally omitted from the terminal consumption-ref key.

## Trust roots

`authority.py` requires all of these immediately before provider mutation:

1. an exact `outbound-send-guard-receipt/v1` with `ALLOW_NEW`, complete mailbox + Slack evidence, email route, and `side_effects_authorized=false`;
2. an exact lease receipt whose bytes are bound by the host approval;
3. **live provider revalidation** through `tools.outbound_send_guard.lease_authority.verify_authoritative_receipt()` using out-of-band current claimant / claim-id / claim-start / anchor facts;
4. a short-lived HMAC-SHA256 `outbound-send-host-approval/v1` issued by the trusted orchestration host, binding repo, canonical buyer scope, canonical commercial scope, exact offer scope, recipient hash, exact message SHA-256, exact guard bytes/payload receipt, exact lease bytes, claimant generation, anchor, issue time, and expiry;
5. process UTC. There is no public caller-selected historical `as_of` that can revive stale readiness;
6. exact message bytes matching the host-approved SHA-256.

The host key is an operational secret. It must never appear in source control, candidate packets, receipts, logs, or chat. `sign_host_approval()` exists for a trusted host adapter; possession of an unsigned/self-authored JSON object is not authority.

The host signer is responsible for assigning the stable `buyer_scope` / `commercial_scope` from independently retained commercial context and for signing only after the live guard/evidence acquisition has completed. Hash self-consistency alone does not authenticate Gmail/Slack/provider facts.

## No reusable capability

`evaluate_current()` can return `PRECONDITIONS_READY`, but its receipt always has:

```json
{
  "external_send_authorized": false,
  "consumption_required": true
}
```

It is diagnostic only.

The only terminal path is `consume_and_send(...)`. It:

1. re-runs the current guard + host approval + live lease checks;
2. computes one deterministic seam from `{repo, buyer_scope, commercial_scope}`;
3. creates an annotated Git tag object binding the exact approval/guard/lease/message generation;
4. create-exclusively publishes `refs/tags/outbound-send-once-v1/<seam_sha256>`;
5. on an indeterminate ref-create response, performs one authoritative readback and proceeds only if the ref identifies this exact tag object;
6. invokes the supplied provider send adapter **once** only after the ref is proven acquired;
7. never returns a reusable pre-send authorization bit.

If the ref already exists, the provider callback is not invoked. A retry of the same packet is therefore `HOLD_RECONCILE_ONLY`, not another send.

If the provider send response is ambiguous, times out, is rate-limited, or reports 2xx without a provider message ID, the ref remains consumed and later calls stay reconcile-only. The wrapper favors a missed send over a duplicate paid pitch. A hard provider rejection is also non-retryable through this v1 consumption seam; route/bounce recovery requires a separately authenticated recovery lifecycle rather than changing the recipient and silently resending.

## Provider adapters

`consume_and_send()` is provider-neutral. The injected send adapter receives **the exact approved message bytes** plus a deterministic `consumption_id` and must perform at most one provider mutation per callback invocation. If the provider supports an idempotency key, the adapter should use `consumption_id` directly.

The package intentionally has no CLI that can turn caller-selected files/timestamps into a send capability. Integration belongs in the trusted host/provider adapter where the host secret, current worker identity, live lease transport, exact message bytes, and actual send operation coexist.

## Authority ceiling

This package can gate and perform exactly one adapter-level outbound send attempt. It does not establish buyer acceptance, contract formation, payment, cash settlement, accounting treatment, recognized revenue, fulfillment acceptance, legal/tax conclusions, or any right to resend after an ambiguous outcome.

## Validation

```bash
python -m py_compile \
  revenue/outbound_send_authority/authority.py \
  revenue/outbound_send_authority/test_authority.py
python -m unittest -v revenue.outbound_send_authority.test_authority
python -O -m unittest -v revenue.outbound_send_authority.test_authority
```

Focused hostiles cover fabricated/self-consistent lease receipts, copied winner identity, host-MAC tampering, stale approval replay, non-ALLOW guard states, exact-message mutation, exact retries, price-variant aliasing on one commercial scope, ambiguous consumption creation, ambiguous provider sends, definite provider rejection, and 2xx-without-provider-message-ID uncertainty.

## Stacked dependency

The development branch is intentionally stacked on the repaired outbound lease authority head from Commons #13702. This package does not modify that owner’s lease files. It imports `lease_authority.verify_authoritative_receipt()` and should be rebased/rejoined onto `main` after #13702 lands; until then it is not independently mergeable without also carrying the lease owner’s dependency.
