# SOL-OBJECTIVE — TITAN V3 own-value objective receipt

- Operation: `titan-v3-own-value-objective-20260909-sol-objective-01`
- Claimed in: `#titan-kaggriculture`
- Starting main: `bcf6e388b8b8d4fdca94f09d7f5493269ee14d22`
- Canonical SELL core Git blob:
  `f23d3a8b5ee5e82029026e7f8f44eb36c143a5a3`
- Canonical main entrypoint Git blob:
  `4a8cf7bcda1f0fea231a144692cb84a779a9e73e`
- Official evaluator Git blob:
  `077feb2208b6e0c1727835eb4f8089709bf67f3b`
- Canonical/frozen/runtime/config/archive/pointer mutation: **none**
- Provider/Kaggle action: **none**

## Finding

The live V3 seller optimizes all strict, expected-downside, forced-feasibility,
and minimax candidate comparisons through a scalar equal to:

```text
own receipts + continuation value - rival receipts
```

The official primary metric is own terminal cash. This is a source-level
objective mismatch, not merely an evaluator-reporting mismatch. It can reward
sacrificing candidate cash when the sacrifice suppresses the rival by a larger
amount.

No exact Slack or open-PR owner was found for this seam before claim.

## Delivered one-factor arm

The additive candidate installs a fail-closed in-memory wrapper around
`MarketPath.score`. Only tuple element zero changes:

```text
relative_value + rival_receipts = own_receipts + continuation_value
```

Tuple elements carrying own receipts, rival receipts, and remaining units stay
byte-for-byte values returned by the incumbent method. Every other V3 mechanism
continues through the canonical runtime.

## Local evidence

- `python -m unittest -v test_own_value_objective.py test_compare.py`:
  **22/22 PASS**
- `python -m py_compile ...`: **PASS**
- deterministic mechanism witness: incumbent selects own value `100`; candidate
  selects own value `112`; **+12** on the inversion case
- aligned-order witness: **no selection change**
- source tree mutation during tests: **none**

## Hosted panel contract

The workflow evaluates canonical V3 versus the candidate against frozen V1 and
public Arlene over eight canonical seeds and both seats: 32 paired cells per arm,
64 total official-interpreter games. It retains raw reports and classifies
own-cash deltas without treating an unfavorable experiment as success.

Only evidence validity is a CI gate. Promotion and hosted submission remain
explicitly unauthorized.
