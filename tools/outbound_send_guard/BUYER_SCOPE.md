# Explicit buyer-scope outbound dedupe

`guard.py` is the authoritative offline outbound-email authority gate. It is intentionally exact-recipient scoped: mailbox rows match only when `counterparty == intent.recipient`, and Slack rows match only when `recipient == intent.recipient`.

That is the safest primitive, but it is not sufficient when a verified buyer has more than one legitimate email route. A provider-SENT copy of `offer-a` to `info@buyer.example` must be able to fence a later proposed net-new `offer-a` send to `ceo@buyer.example` **only when those addresses have already been explicitly verified as routes for the same buyer**.

`buyer_scope.py` supplies that explicit aggregation layer without changing `guard.py`.

## Scope contract

A buyer scope is caller-supplied JSON:

```json
{
  "schema_version": "outbound-send-buyer-scope/v1",
  "scope_id": "buyer-123",
  "members": [
    {
      "email": "ceo@buyer.example",
      "mailbox_complete": true,
      "mailbox_query_id": "gmail-ceo-query-1",
      "slack_complete": true,
      "slack_query_id": "slack-ceo-query-1"
    },
    {
      "email": "info@buyer.example",
      "mailbox_complete": true,
      "mailbox_query_id": "gmail-info-query-1",
      "slack_complete": true,
      "slack_query_id": "slack-info-query-1"
    }
  ]
}
```

The membership list is evidence, not discovery. The caller is responsible for verifying that every member belongs to the same buyer/account and that every per-member mailbox and Slack lookup covers the same intended snapshot boundary.

The companion deliberately does **not** infer buyer identity from:

- a shared email domain;
- display names or signatures;
- local parts such as `info`, `sales`, or `ceo`;
- website ownership;
- organization-name similarity;
- redirects, MX records, or other network metadata.

The intended recipient must itself be a declared member. Normalized duplicate members are rejected.

## Completeness rule

The base `outbound-send-evidence/v1` snapshot must already claim complete mailbox and Slack coverage. In addition, **every declared buyer-scope member** must carry `mailbox_complete=true` and `slack_complete=true`.

If any declared member is incomplete, the transformed evidence is marked incomplete before it reaches the core guard, so the result fails closed as `HOLD`.

Per-member query IDs are retained in the buyer-scope receipt so the completeness assertions remain auditable. This companion does not execute those queries itself.

## Authority projection

The wrapper deep-copies the source evidence. Only rows whose normalized email is an explicitly declared scope member are rebound to the intended recipient. Undeclared addresses remain untouched and therefore cannot widen authority.

The transformed snapshot is then evaluated by the unchanged v1 core guard. Its decision precedence remains authoritative:

1. hard DNR on any declared route -> `DO_NOT_RESEND`;
2. incomplete, stale, future-dated, conflicting, or otherwise non-authoritative evidence -> `HOLD`;
3. newer buyer inbound on any declared route -> `REPLY_ONLY`;
4. same-offer outbound evidence on any declared route -> `DO_NOT_RESEND`;
5. different recent outbound on any declared route -> core cross-offer cooldown / `HOLD`;
6. only when the complete aggregate contains no blocking outbound state -> `ALLOW_NEW`.

No wrapper rule can turn a core denial into send authority.

## Receipt

The wrapper emits `outbound-send-buyer-scope-receipt/v1` and binds:

- normalized, deterministically sorted explicit members;
- each member's mailbox/Slack completeness claim and query ID;
- original intent digest;
- original source-evidence digest;
- transformed scoped-evidence digest;
- buyer-scope digest;
- the complete core guard payload and its digest.

`side_effects_authorized` is always `false`.

## CLI

```bash
python -m tools.outbound_send_guard.buyer_scope \
  --intent intent.json \
  --evidence evidence.json \
  --scope buyer_scope.json \
  --out receipt.json
```

The three inputs must be distinct. The output may not alias any input. JSON parsing is strict through the existing guard parser, and file output is atomically published.

Exit codes mirror the core guard:

- `0` — `ALLOW_NEW`
- `3` — `REPLY_ONLY`
- `4` — `HOLD`
- `5` — `DO_NOT_RESEND`
- `2` — malformed/unsafe input

## Boundary

This is an offline authority projection only. It does not query Gmail or Slack, send mail, resolve identities, infer domains, contact buyers, create leases, schedule work, mutate campaigns, or grant send authority. A caller still needs independently verified scope membership and complete provider/workspace evidence.
