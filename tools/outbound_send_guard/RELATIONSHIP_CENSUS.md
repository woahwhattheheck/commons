# Provider relationship census / integrity gate

`relationship_census.py` is a **fail-closed offline relationship census validator**. It exists to preserve exact target/route/history/transfer evidence across parallel sales workers, but v2 deliberately does **not** claim that a caller-supplied HMAC proves provider origin.

That distinction matters: a process that possesses an HMAC secret can also mint a matching signature. A valid supplied-secret HMAC proves integrity under that secret; by itself it cannot prove that Gmail, Slack, a CRM, or another independent provider produced the snapshot. The v1 implementation blurred those two facts and could therefore turn worker-authored state into a non-HOLD custody projection.

## v2 authority boundary

The public `evaluate(...)` / `evaluate_bytes(...)` surface now has a narrow live contract:

- current time is always process UTC;
- freshness is code-owned and fixed at **900 seconds**;
- future skew is code-owned and fixed at **300 seconds**;
- callers cannot supply `now`, `max_snapshot_age_seconds`, or `max_future_skew_seconds`;
- the receipt binds the exact policy generation (`process-utc-fixed-900-300-v1`);
- a supplied-secret HMAC is reported as `integrity_hmac_valid`, with `authority_scope=SUPPLIED_SECRET_INTEGRITY_ONLY`;
- `provider_origin_attested=false` and `current_authority=false` remain explicit;
- live `decision` is therefore **HOLD** until a separately verified provider-origin authority is composed.

The private `_evaluate_at(...)` helper exists only for deterministic tests/historical replay. Its receipts are explicitly marked `HISTORICAL_REPLAY_NOT_LIVE_AUTHORITY`; backdating that helper can never produce current custody authority.

This module never sends email, mutates Gmail/Slack/provider state, schedules work, accepts payment, or authorizes any side effect. Every receipt has `external_send_authorized=false` and `side_effects_authorized=false`.

## Relationship projection

The receipt keeps a non-authoritative `projected_custody` field so operators can reason about normalized relationship history without confusing that projection with live authority:

- `CLEAR` may project `CUSTODY_CLEAR` when the census is otherwise semantically valid;
- `ACTIVE_OWNER` may project `CURRENT_OWNER` when owner/generation/route observations agree;
- a valid completed `TRANSFERRED` record may project `CURRENT_OWNER` after the transfer proof checks pass;
- any semantic defect projects `UNPROVEN`.

Regardless of that projection, v2 `decision` stays `HOLD` because provider origin is not independently attested by this offline supplied-secret mechanism.

## Non-reusable lifecycle states

These aggregate **and route-level** states are mechanically blocked from reusable custody projection:

- `WAITING_REPLY`
- `INBOUND_NEEDS_OWNER`
- `UNSUBSCRIBED`
- `DNR`
- `HARD_BOUNCE`
- `TRANSFER_PENDING`
- `CLOSED`

A matching worker/generation cannot turn them into `CURRENT_OWNER`.

Complaint, unsubscribe, delivery, and DSN evidence remain separately governed by `route_lifecycle.py`. That reducer is an independent mandatory gate; this census does not invent a second complaint vocabulary or treat a route-health result as send authority.

## Identity / PII boundary

The input names the buyer/account with opaque `target_scope`; raw email addresses are rejected there and in worker/owner tokens. Routes are lowercase SHA-256 hashes. Each route observation binds to the target via:

`SHA256(canonical({schema_version, target_scope, route_sha256}))`

The signed census material also binds the target and sorted route set. Cross-target route transplantation therefore fails even if the malformed census is re-HMACed.

The receipt contains only opaque target, route hashes, provider/workspace hash, content digests, normalized relationship data, currentness policy, and authority/integrity facts. It never emits raw route addresses.

## Transfer proof

`TRANSFERRED` still requires an exact target/route-set-bound transfer record proving:

1. `to_generation == from_generation + 1`;
2. release by the prior owner, or an actor explicitly marked `ADMIN` in the supplied transfer record;
3. acceptance by the new owner;
4. release no later than acceptance, and both no later than the snapshot;
5. transferred owner/generation equal the live relationship owner/generation.

The normalized transfer receives a content-addressed `transfer_receipt_sha256`.

This verifies internal transfer semantics only. It does not elevate the supplied transfer record into independently authenticated provider authority.

## CLI

```bash
export OUTBOUND_RELATIONSHIP_CENSUS_HMAC_KEY_HEX='<64+ hex chars>'
python -m tools.outbound_send_guard.relationship_census \
  --census provider-census.json \
  --out custody-receipt.json
```

The environment key is used for **integrity checking only**. The CLI intentionally has no caller freshness/future-skew options. It reads the census bytes once, rejects duplicate JSON keys/non-finite numbers, and create-exclusively publishes the receipt using same-directory staging plus atomic hard-link publication.

Exit codes:

- `4` — valid v2 receipt published, live authority still HOLD;
- `2` — malformed input/configuration/publication failure.

There is no v2 exit-0 path from supplied-secret census input alone.

## Required live composition

A future sender must independently satisfy all applicable live controls at the same operation boundary, including:

1. **provider-origin authority** obtained from an independently verified provider/connector path (not this supplied-secret HMAC alone);
2. this module's exact census/relationship integrity projection;
3. complete mailbox + Slack outbound-send guard;
4. route-lifecycle / complaint / unsubscribe / bounce policy;
5. buyer/route scope aggregation where multiple verified routes are relevant;
6. atomic buyer+offer capability/lease; and
7. any owner/HOT-lead human approval rule in force.

No result from this module substitutes for any of those gates.

## Regression gate

```bash
python -m py_compile \
  tools/outbound_send_guard/relationship_census.py \
  tools/outbound_send_guard/test_relationship_census.py
python -m unittest -v tools.outbound_send_guard.test_relationship_census
python -O -m unittest -v tools.outbound_send_guard.test_relationship_census
```

The hostile suite covers caller-clock/policy removal, self-minted valid HMAC remaining HOLD, historical backdating remaining non-current, blocked lifecycle states at aggregate+route level, target transplantation, stale/future snapshots, transfer proof defects, exact-byte custody, and optimized-mode behavior.
