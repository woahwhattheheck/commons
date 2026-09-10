# TITAN V3 S13 prefix-695 causal child

This additive experiment asks a narrow question about the successful Pensukesan route arm from PR #11992: how much of its frozen-panel uplift survives if the reviewed route runtime permanently hands control back to its continuously shadowed incumbent immediately after step 695?

It does **not** modify canonical TITAN, an archive, a runtime pointer, a provider, Kaggle, or a submission. It spends no new game seeds. The hosted workflow reuses only `539131249`, `1834999074`, `2609097301`, and `2609097302`, both seats, against exact Arlene and V1.

## Why step 695

Independent source-exact local ablations over the retained #11992 artifact found:

- deleting every route SELL at step 670 or later cost `14,371.6` mean own cash and `16,128.1` mean margin across the frozen Arlene bank, flipping all eight cells to losses;
- deleting only quantity-at-least-900 catchers cost `3,888.9` mean own cash and `4,330.9` mean margin in all eight cells;
- twelve plain-control catcher transfers were neutral or harmful, proving the value is coupled to the production route rather than a standalone terminal wrapper;
- prefix-695 retained eight wins and trailed the full route by only `445.8` mean own cash / `705.1` mean margin on the same Arlene bank, while prefix-711 was materially worse. The 696–717 suffix therefore has a completion dependency rather than monotone value.

Local receipts:

- late-SELL ablation SHA-256: `0b23758697c2a325c58d2ca5a32f46b12a87b3b95a28f20e8a92b74a1482c048`
- prefix census SHA-256: `205ac622428f13aa20eacfd6b7c44a404d0c38a2413dfac16745a4d45351d15a`

Those receipts motivate the hosted test; they are not promotion evidence.

## Contracts

`prefix_route.py` decodes the generated parent arm, binds its Python and tape SHA-256 values, requires a contiguous zero-based tape, retains rows `0..695`, and emits a deterministic child arm. The unchanged `LeaderRoutePolicy` calls the incumbent every turn. Step 696 is absent, so that observation causes an irreversible handoff to the already-current incumbent.

`prefix_report.py` compares control, full route, and prefix route on identical evaluator cell keys. `PREFIX_SURVIVOR` requires positive mean own cash, nonnegative median own cash and mean margin in every opponent×seat stratum, no new losses, and action-trace activation in every cell. Even a survivor remains a frozen-seed research result, not a promotion authorization.
