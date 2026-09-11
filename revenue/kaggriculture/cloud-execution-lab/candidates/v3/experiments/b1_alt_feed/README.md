# B1 alternate-day feeding — source semantics audit

Claim: `TITAN-V31-B1-ALTERNATE-DAY-FEEDING-20260911-01`

## Result

**Global alternate-day FEED suppression is blocked.** The external B1 premise is only partly true in the preserved official interpreter: an animal escapes after two consecutive unfed end-of-day refreshes, so feeding every other day can keep it alive. But FEED is also the gate on CARE value. At a production boundary, `pending_care_bonus` is consumed only when `fed_today` is true, and a new pending CARE bonus is added only when both `cared_today` and `fed_today` are true.

The focused predecessor imports the preserved official engine and harvests every produced batch so max-held saturation cannot hide a loss. With CARE enabled, daily feed reaches first-batch output of GOOSE 4, COW 6 and SHEEP 6. The tested alternate parity survives but produces only 1 on that first boundary. With CARE disabled, the same alternating feed pattern survives and preserves the one-unit base production cadence exactly.

This matters directly to live V3.1 R04: V233's six-sheep worker path explicitly prioritizes `FEED` and then `CARE`. A global day-parity wrapper would therefore suppress not just wheat consumption but the controller's intended wool bonus path.

## Safe follow-up surface

B1 should be narrowed before any economics run. Viable follow-ups are limited to a route/animal state where CARE has provably no marginal value, or to a deliberately economic (not semantics-preserving) default-OFF arm with V233 explicitly excluded and full paired score evidence. A candidate must also preserve the two-consecutive-unfed escape invariant and must not strand a worker in a controller that retries FEED before CARE.

Do not promote a global alternate-day FEED rule from the cost heuristic alone.

## Focused check

```bash
python -B -m unittest -v \
  candidates/v3/experiments/b1_alt_feed/test_b1_feed_semantics.py
```

Scope is evidence-only under `experiments/`: no `overlay/**`, config/default, package, evaluator/opponent, manifest, or Kaggle mutation.
