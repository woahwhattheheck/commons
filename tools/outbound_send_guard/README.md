# Outbound send guard

`tools/outbound_send_guard` is a read-only, offline preflight for parallel sales and email workers. It exists because a workspace-only search can say “no send receipt” while the mailbox already contains a provider-SENT message to the buyer. A second worker must not turn that visibility gap into duplicate outreach.

The package does not search Gmail or Slack and cannot send email. An adapter/operator supplies:

- an `outbound-send-intent/v1` describing one intended email route and offer;
- an `outbound-send-evidence/v1` snapshot from complete bidirectional mailbox and Slack receipt queries.

## Supported current boundary

Use the package API or package CLI:

```python
from tools.outbound_send_guard import compile_current, verify_current

receipt = compile_current(intent_object, evidence_object)
verification = verify_current(intent_object, evidence_object, receipt)
```

```bash
python -m tools.outbound_send_guard compile \
  --intent intent.json \
  --evidence evidence.json \
  --out receipt.json

python -m tools.outbound_send_guard verify \
  --intent intent.json \
  --evidence evidence.json \
  --receipt receipt.json \
  --out verification.json
```

The package-level `evaluate` alias is `compile_current`. It samples process UTC and has no caller clock parameter. See `CURRENT_TIME.md` for the exact currentness, expiry, historical replay, custody, and verification contract.

The old `guard.py::evaluate()` routine is the deterministic decision engine used underneath the current wrapper. It is suitable for historical reconstruction and focused engine tests, but **its caller-supplied timestamps do not establish present freshness**. Direct invocation of `python -m tools.outbound_send_guard.guard` is legacy/historical and is not the supported production preflight route.

## Current receipt decisions

The current receipt preserves the core decision while binding verifier-owned time and expiry:

- `ALLOW_NEW` — complete evidence is fresh at verifier time, contains no same-offer send, and no outbound is inside the cross-offer cooldown;
- `REPLY_ONLY` — a recipient inbound is newer than the latest outbound; the receipt identifies the reply event but does not authorize a net-new thread;
- `HOLD` — evidence is incomplete, stale, future-dated, contradictory, expired, or another outbound is inside cooldown;
- `DO_NOT_RESEND` — a hard DNR or exact-offer outbound exists.

Every compiler and verifier result sets `side_effects_authorized=false`. A current `ALLOW_NEW` or `REPLY_ONLY` is only one prerequisite. Organization/opportunity custody, route health, relationship state, an atomic lease or one-shot consumer, current provider reread, customer-link checks, and the actual provider mutation remain separate controls.

## Safety and authority rules

1. Mailbox and Slack lookups must both be complete. Rate limits or partial pagination are `HOLD`, never “not found.”
2. Provider-SENT evidence is authoritative even when Slack has no send receipt.
3. Exact-offer outbound evidence never ages out by itself. A newer inbound changes the lane to `REPLY_ONLY`, not `ALLOW_NEW`.
4. Unknown or different prior outreach enforces the route-level cooldown.
5. `hard_dnr` is terminal. There is no automatic DNR release event.
6. Duplicate provider/event identifiers with conflicting facts make authority unknown and `HOLD`.
7. Email identity is case-folded; plus tags are not stripped or guessed equivalent.
8. Input JSON is strict: duplicate keys, non-finite values, coercive booleans/integers, unknown fields, naive timestamps, and malformed addresses fail closed.
9. Current authority uses code-owned ceilings: evidence age 900 seconds, request age 900 seconds, future skew 300 seconds, and positive receipt lifetime 60 seconds. Candidate policy may tighten but never widen them.
10. Historical explicit-time replay is labeled `HISTORICAL_INTEGRITY_ONLY`, outwardly `HOLD`, and can never clear current preflight.
11. Parsed-object inputs are detached at the supported API entry. Exact-byte APIs hash the same bytes they strict-parse.
12. The current CLI consumes one bounded no-follow regular-file generation and creates outputs exclusively; overwrite and final-component symlink targets are refused.

## Evidence envelope

Each mailbox row is metadata-only: `message_id`, `direction`, `counterparty`, `observed_at`, and optional `offer_id`. The guard does not require or persist email bodies. Slack rows use `event_id`, `kind` (`lead`, `sent`, `hard_dnr`), `recipient`, `observed_at`, optional `offer_id`, and optional `provider_message_id`.

The current wrapper binds:

- canonical intent/evidence object digests;
- exact source byte digests when called through the byte API/CLI;
- the deterministic core receipt;
- process-owned `verified_at`;
- `valid_until`;
- code-owned policy generation and effective limits;
- current and historical decision truth.

These are local integrity and custody claims, not external provider authentication.

## Exit codes

Compile: `0 ALLOW_NEW`, `3 REPLY_ONLY`, `4 HOLD`, `5 DO_NOT_RESEND`, `2 invalid input or I/O failure`.

Verify: `0` only for an unexpired positive receipt whose current decision still matches; `5` for current `DO_NOT_RESEND`; `4` for expired, changed, historical-only, or non-positive authority; `2` for malformed/tampered input or I/O failure.

## Regression gate

```bash
python -m py_compile \
  tools/outbound_send_guard/guard.py \
  tools/outbound_send_guard/current.py \
  tools/outbound_send_guard/test_guard.py \
  tools/outbound_send_guard/test_current.py
python -m unittest -v \
  tools.outbound_send_guard.test_guard \
  tools.outbound_send_guard.test_current
python -O -m unittest -v \
  tools.outbound_send_guard.test_guard \
  tools.outbound_send_guard.test_current
```

The hostile matrix includes the original provider-SENT-without-Slack-receipt incident plus matched stale/future timestamp replay, one-sided stale request/snapshot, policy widening, expiry, verifier-time reseal, source change, caller mutation after snapshot, exact-byte custody, create-exclusive output, and symlink refusal.
