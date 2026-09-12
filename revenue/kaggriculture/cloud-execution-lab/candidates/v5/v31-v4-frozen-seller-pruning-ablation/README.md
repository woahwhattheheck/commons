# V3.1 → V4 active frozen-seller early-pruning ablation

This evidence-only carrier isolates one always-on V4 optimizer change that is absent from exact submitted V3.1: PR #11017's early pruning in the active `FrozenSelected -> selected_sell_core.optimize_lot` path.

## Why this seam

Exact submitted V3.1 (`a90d888f03987ef0b35cfd20ec3519c6144db08a`) runs physical `capacity_ok(plan)` before scoring and evaluates every explicit rival scenario for each feasible strict candidate. Exact submitted V4 (`4af1113154e78c662780e6658cd920daac7902e3`) instead scores the no-rival scenario first, rejects a nonpositive candidate before `capacity_ok`, and short-circuits remaining scenarios at the first nonpositive delta.

The historical #11017 validation intentionally established optimizer-result parity while allowing fewer capacity callbacks (`new_calls <= old_calls`); its floor-tie witness reduced capacity calls to one. The PR and V4 source manifest report focused optimizer/source tests but no new full-game playing-strength evidence for the changed bytes. This makes the seam a timing/callback-order causal suspect, not a claim that the mathematical strict-dominance rule changed.

## Exact treatment

Control is the exact submitted-V4 archive SHA256:

`4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b`

Treatment keeps the same archive member set and changes only `selected_sell_core.py`. The exact V4 strict/reference-feasible pruning block is replaced with the incumbent evaluation order:

1. reject structurally invalid candidate;
2. run `capacity_ok(plan)` first;
3. evaluate all V4 scenarios;
4. apply the same V4 strict key and `key[0] > 0` admission.

Everything from V4 forced-feasibility onward is byte-identical, so later E18 acceptance branches remain V4. E05 joint SELL composition, producer/runtime, configuration, and every other archive member also remain untouched.

The treatment refuses any source other than exact V4 `selected_sell_core.py` Git blob `f23d3a8b5ee5e82029026e7f8f44eb36c143a5a3`, refuses missing/duplicate pruning blocks, parses the successor source, and proves the forced-feasibility/E18 tail remains byte-identical.

## Source gates

```bash
python -B -m unittest -v test_pruning_ablation
python -O -B -m unittest -v test_pruning_ablation
python -m py_compile pruning_ablation.py test_pruning_ablation.py
```

Authoring receipt before publication: 7/7 PASS normal, 7/7 PASS under `-O`, py_compile PASS. The discriminating witness preserves the same strict optimizer choice while the pruned arm performs zero capacity callbacks and fewer score calls; the full-evaluation treatment performs two capacity callbacks and evaluates both scenarios for both candidates.

Dedicated CI additionally reads exact submitted V3.1/V4 source with `git show`, proves V3.1 has the incumbent capacity-first/all-scenario order, proves the V4 Git blob is exact, and applies the one-block transform to those exact V4 bytes.

## Boundary

This PR materializes a causal arm only. It does not modify production runtime, defaults, `TITAN-CONFIG.json`, current archive/pointers, release state, opponents, evaluator, or Kaggle submission. A matched official-engine runner can consume `exact_v4_arms()` after source custody is green; such games are lower priority than the live 13-tape production-donor panel and the V3.1↔V4 gauntlet.
