# TITAN v3 self-cross cancellation — opponent-contingency review

Operation: `titan-v3-self-cross-theorem-review-20260909-01`

Evidence base: main `87e02813b8c8fe4b19b8edccd181584da07f6499`, inherited non-force through merge `5ca5bb395e30ca6ead76568e16a5e6a6e367a80d`.

Owner boundary: SOL-ROSTER retains `analysis/self-cross-cancel/**`, replay incidence, physical-divergence attribution, implementation, and any gameplay panel. This disjoint packet is an exact-engine review theorem only.

## Result

Deleting an own `SELL WHEAT 1` and later `BUY_PRODUCT WHEAT 1` is **not an opponent-independent dominance transform** merely because own terminal WHEAT stock is unchanged on one observed replay.

The official market resolves each market-row index in lockstep. Both players receive quotes from the same pre-commit market inventory, then commits occur. An own sale can therefore change the price paid or received by an intervening rival order, which changes the inventory and cash presented to the later own repurchase and every subsequent cash-sensitive order.

`official_witness.py` binds the preserved engine Git blob `3c202c7ee921da239356789e266b694635103fc4` and executes the same own three-row pattern under two legal rival tapes from identical public state:

| Intervening rival row | Terminal non-money state | Cancelled − baseline own cash | Cancelled − baseline rival cash | Bound-tape verdict |
|---|---:|---:|---:|---|
| `BUY_PRODUCT WHEAT 1` | identical | `+1` | `-1` | `REPLAY_BENEFIT` |
| `SELL WHEAT 1` | identical | `-1` | `+1` | `REPLAY_HARM` |

The sign reversal is reproduced with the transformed policy in player 0 and player 1. Player-order choice therefore does not rescue a policy that cannot observe the simultaneous rival action.

A third exact case starts in the price-floor region. Official `SELL` at price `$1` removes own stock but deliberately does **not** increase market supply; the later `BUY_PRODUCT` still decreases supply. The original round-trip and cancelled action end with equal own stock and equal own cash but different public market inventory. Any cancellation certificate must explicitly reject this asymmetry.

## Admission boundary

An observed two-player replay counterfactual can establish `REPLAY_BENEFIT` or `REPLAY_HARM` for those exact action tapes. It cannot by itself establish `RUNTIME_DOMINANCE`, because the rival's current market queue is hidden when Titan selects its action.

A runtime transform needs one of:

1. a proof covering every legal rival current action and every later cash-sensitive consequence; or
2. a public, selection-time observable condition under which every excluded rival path is impossible.

At minimum, a certificate must bind successful matched fills, active-prefix indices, sale-price-above-floor supply behavior, shed capacity, cash affordability, every intervening same-item own and rival unit, residual unmatched quantities, later market orders whose fills depend on either player's changed cash, final public inventory, and all non-money state. Replacing orders with `[]` preserves positions; shifting rows is not admissible.

## Commands

```bash
python -m py_compile official_witness.py test_official_witness.py
python -m unittest -v test_official_witness.py
python official_witness.py \
  --output SELF-CROSS-THEOREM.json \
  --require-opponent-contingency
```

The JSON verdict deliberately separates:

- `observed_replay_counterfactual_can_prove`: a bound-tape result;
- `runtime_dominance_proven`: always false for this witness; and
- `runtime_requirement`: the missing all-rival-action or observable fail-closed certificate.

## Non-claims

This packet changes no gameplay source, scheduler, controller, route, config, archive, pointer, default entrypoint, evaluator, provider state, Kaggle submission, or SOL-ROSTER path. It does not dispute the reported `$15` loss on replay `107130860`; it limits what that replay can prove about a general runtime cancellation rule.
