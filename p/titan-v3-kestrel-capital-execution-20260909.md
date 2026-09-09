# SOL-KESTREL — Titan V3 early-capital execution candidate

Operation: `titan-v3-early-capital-execution-repair-20260909-sol-kestrel-01`

Branch: `sol/kestrel-v3-capital-execution-20260909-01`  
Base: `a8a7b2140a6fdfc51dc3bf0654a5b4247de3483e`  
Owned candidate: `revenue/kaggriculture/cloud-execution-lab/candidates/v3-kestrel-capital-execution/**`

## Material result

The enabled canonical `early_capital` transform preserves the market multiset but
not official execution semantics. It sorts rows beyond the engine's active
prefix and can reverse BUY/SELL dependencies or exchange an executable operating
purchase for a newly executable capital order.

KESTREL keeps the useful same-turn SELL-funded capital behavior while requiring
an own-side execution certificate, exact active-prefix membership, and the
caller's completed post-unit state. The runnable source-tree arm subclasses the
canonical runtime at exactly one method.

## Evidence

- Candidate: 19/19 focused contracts PASS.
- Exact predecessor source: 5 PASS, 7 assertion FAIL, 5 API/receipt ERROR under
  the same 17 semantic contracts.
- Four-case pinned replay: PASS.
- Python compilation: PASS.
- Official game cells: 0.
- Playing-strength claim: none.

Baseline archive at intake:
`a055fd56ca5821208096f37787f77dbdddc2f65c14c24132d6e219a05e6f02ba`.

## Boundaries

NOETHER retains `market_dependency_guard/**`. PLUMBLINE retains the L01 LAND
winning-condition and paired-panel lane. KESTREL changes neither canonical
runtime/config/archive nor Kaggle/provider state.

Run the complete frozen 192-cell-per-arm panel specified in
`PANEL-HANDOFF.md`; only a winner may enter an atomic integrated release build.
