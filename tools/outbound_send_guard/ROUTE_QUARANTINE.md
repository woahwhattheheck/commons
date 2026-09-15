# Route-aware outbound quarantine gate

`route_quarantine.py` closes the authority gap between the ordinary outbound send guard and post-send route lifecycle evidence.

The existing layers answer different questions:

- `guard.py`: given complete recipient-scoped mailbox + Slack evidence, is a net-new/reply action clear of duplicate-send / cooldown / DNR rules?
- `route_lifecycle.py`: for one exact provider-SENT message and recipient, did later delivery evidence prove the route blocked, require review, prove delivery, or remain unconfirmed?

Before this composition layer, those answers were not joined. A prior outbound for offer A can age beyond the send guard's cross-offer cooldown and make offer B `ALLOW_NEW` even when a later authoritative DSN for the exact provider message says the destination mailbox is dead. `route_quarantine.py` makes route health a mandatory reducing gate: route evidence may remove send eligibility, but never creates it.

## Contract

Inputs:

1. one strict `outbound-send-intent/v1`;
2. one strict `outbound-send-evidence/v1` accepted by `guard.py`;
3. one `outbound-route-quarantine-bundle/v1`:

```json
{
  "schema_version": "outbound-route-quarantine-bundle/v1",
  "recipient": "buyer@example.com",
  "as_of": "2026-09-13T15:00:00Z",
  "route_checks": []
}
```

The route bundle and send evidence MUST share the exact `as_of/generated_at` boundary. Every recipient-scoped provider outbound in mailbox evidence must have exactly one complete `outbound-route-lifecycle-evidence/v1` check at that same boundary. Slack `sent` evidence is accepted only when it binds a `provider_message_id` present in mailbox provider-SENT evidence; a Slack-only/unbound send cannot silently escape route-health coverage.

Extra checks, missing checks, duplicate checks, route/recipient drift, provider-message drift, and send-time drift fail closed.

## Decision composition

`route_lifecycle.py` decisions are reducing only:

- any `BLOCK_ROUTE` -> final `DO_NOT_USE_ROUTE`;
- else any `HOLD_ROUTE` -> final `HOLD`;
- else route state is `CLEAR`, and the ordinary send-guard decision is preserved exactly (`ALLOW_NEW`, `REPLY_ONLY`, `HOLD`, or `DO_NOT_RESEND`).

`DELIVERED` and `UNCONFIRMED` never upgrade a restrictive send-guard decision.

A blocked route emits a deterministic human-research obligation `FIND_INDEPENDENT_PUBLIC_BUSINESS_ROUTE`. It explicitly forbids automatic replacement and says any candidate alternate route needs an independent source and a **fresh send preflight**. No address is guessed or contacted.

## Authority ceiling

This module is read-only and offline. Every receipt sets:

- `same_route_send_authorized=false`;
- `alternate_route_send_requires_fresh_preflight=true`;
- `side_effects_authorized=false`.

It does not read Gmail/Slack itself, send or reply to email, discover replacement contacts, infer buyer intent, infer acceptance/payment, or recognize revenue.

Route checks must obey the authority contract documented by `DSN_NORMALIZER.md` / `ROUTE_LIFECYCLE.md`: a normalized DSN event should come from the independent source-authority recomputation boundary, not a self-authored receipt. This composition gate does not turn a fabricated route event into positive send authority; route evidence can only preserve or reduce the normal send guard's decision.

## Durable receipt / verification

The output schema is `outbound-route-aware-send-receipt/v1`. It binds SHA-256 of the intent, send evidence, route bundle, ordinary send-guard receipt, and each recomputed route-lifecycle receipt. `verify()` fully recomputes from all supplied sources and requires exact canonical equality; refreshing the output hash after changing a decision does not verify.

The CLI prints the canonical receipt to stdout and performs no output-file mutation:

```bash
python -m tools.outbound_send_guard.route_quarantine \
  --intent intent.json \
  --send-evidence evidence.json \
  --route-bundle route-bundle.json
```

Verification uses the same three sources plus `--receipt receipt.json` and prints `VERIFIED` only on exact recomputation.

Input files are opened once with no-follow where supported, must be regular files, are bounded to 8 MiB, and are generation-fenced across the retained descriptor read.

## Regression gate

```bash
python -m py_compile \
  tools/outbound_send_guard/route_quarantine.py \
  tools/outbound_send_guard/test_route_quarantine.py
python -m unittest -v tools.outbound_send_guard.test_route_quarantine
python -O -m unittest -v tools.outbound_send_guard.test_route_quarantine
```

Hostiles cover: a 30-day-old different offer whose route later proves `5.1.1`; policy-rejection / mailbox-full / transient DSN holds; same-offer DNR preservation; delivery and unconfirmed non-upgrade behavior; missing/extra/duplicate lifecycle coverage; mismatched send generation and capture boundary; conflicting delivery/failure evidence; Slack sends without provider identity; Slack provider identity absent from mailbox truth; source-bound verification; duplicate JSON keys; and non-regular CLI ingress.
