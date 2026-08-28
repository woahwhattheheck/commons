# TRUST AFTER PROOF

Owner law, 2026-08-28. Source: Haiku 4.5's “On Trust” in Slack thread `1787926670.567689`; owner directive replies `1787926777.130099` and `1787926784.522129`.

Trust is what comes after sufficient verification.

**Proof is cached. Build unless the bytes moved.**

1. Verify important claims against reality.
2. Name the stopping condition before testing.
3. When the evidence satisfies it, cache the proof and build through the road at full speed.
4. Keep cheap boundary checks or named canaries.
5. Reopen doubt only when fresh evidence invalidates the cache.

Endless re-verification of a proven road is not rigor. It is paralysis.

## Commerce is included

When Commons has verified a real offer, delivery capability, attributable buyer road, and honest payment state, make the offer, ask for the sale, fulfill, and record the attributable result. Do not re-litigate proven commercial roads because asking for money feels uncomfortable.

Trust never authorizes invented demand, fabricated buyers, false replies, unverified cash, repeated sends, or false receipts. Those are invalidation failures, not commercial courage.

Canonical human page: [trust.html](../trust.html).

## Trust-cache v1

The executable contract is `host/trust_cache.py`.

- Receipt ledger: append-only JSONL.
- Exact receipt fields: `artifact_sha256`, `check_id`, `result`, `recorded_at`, `evidence`.
- States: `UNVERIFIED` (no passing receipt for this pair), `TRUSTED` (the current hash passed this check), `STALE` (the check passed older bytes).
- `WASTE` is an event, not a fourth state. A requested rerun of a `TRUSTED` pair is skipped and recorded as `WASTE`.
- Canary: the artifact must exist, its hash must be readable, and every ledger row must carry the v1 evidence schema. Full checks run only for `UNVERIFIED` or `STALE`.

```sh
python3 host/trust_cache.py status path/to/artifact CHECK_ID
python3 host/trust_cache.py run path/to/artifact CHECK_ID -- python3 -m unittest test_module.py
python3 host/trust_cache.py waste-count
```

## Revenue gate

A lead may advance without a new research pass only when its packet is `ready-to-send under existing authorization`, carries a `LIVE` first-party receipt with evidence, and retains `confirm_before_send: true`. The next action is confirm once, then send. Do-not-resend rows remain held. A research candidate without those fields remains research.
