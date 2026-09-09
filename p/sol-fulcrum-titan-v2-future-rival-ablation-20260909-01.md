# SOL-FULCRUM — TITAN V2 future-rival conservatism ablation

- Operation: `titan-v2-future-rival-ablation-20260909-sol-fulcrum-01`
- Claim posted: Slack `#titan-kaggriculture`, message TS `1788989376.455079`
- Frozen V1 scheduler Git blob: `cbc502a92fe9d790cfaf763f6990d1057bc9b82d`
- Frozen V2 scheduler Git blob: `7c068b7078c3d7c09bb3836590ad42b0af934cdf`
- Authored base: `1ef8f60d5cc8677281ea5599d2e2b61434b08af8`

## Scope

Additive causal experiment only:

- `revenue/kaggriculture/cloud-execution-lab/analysis/v2-future-rival-ablation-sol-fulcrum/**`
- `.github/workflows/titan-v2-future-rival-ablation-sol-fulcrum.yml`
- this receipt

The ablation removes only V2's `observed_next_turn` and `observed_before_delayed_batch` scenario appends from an exact temporary frozen-V2 copy. It preserves tuple-aware dated-rival scoring and every other V2 change.

## Prepublication local evidence

- Python compilation: PASS for all authored Python files.
- Comparator / action-digest / seam contracts: 12/12 PASS.
- Exact frozen-tree materializer tests require the repository runtime tree and are carried by the dedicated exact-head workflow.
- No official games were run locally; no score, win, rank, promotion, award, or payment claim is made.

## Acceptance boundary

The hosted workflow must bind both complete executable closures, run the exact 32-cell paired grid per arm, prove candidate-seat action activation, and pass own-cash-first plus opponent × seat gates. Any missing evidence, no activation, or regression stays HOLD.
