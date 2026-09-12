# TITAN V5 — submitted-V4 WHEAT feed-stock ablation

This is one evidence-only causal carrier for the V3.1 > V4 investigation. It does **not** reconstruct submitted V3.1 and it does not activate a V5 gameplay default.

## Question

Submitted V4 expanded the already-enabled operating-stock family with a final returned-action WHEAT reservation: `TitanAgent._feed_stock_selected()` calls `operating_stock.protect_feed_stock()` and may withhold up to two WHEAT units for reachable authored FEED obligations. That source path was contract-tested, but its V4 manifest recorded no full-game strength evidence.

This carrier asks one narrow causal question: **does removing only that WHEAT reservation improve exact submitted V4?**

## Arms

- `control`: byte-identical exact submitted V4 archive, SHA256 `4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b`.
- `feed_stock_off`: same archive membership and all identical members except `titan_runtime.py`. The exact submitted-V4 runtime preimage must be Git blob `998bf5da08f61f82eafaf5750c8a86fc3adad7fb`; the AST-anchored rewrite changes only `TitanAgent._feed_stock_selected(self, obs, cfg, selected)` to `return selected`.

The fertilizer operating-stock method remains active and `operating_stock.py` must remain exact Git blob `80b372bfd34d04a2c9e2376fa02917f21f659c41`. E05 joint SELL, funding policy, E08 horizon semantics, early-capital ordering, the four V4 public booleans, and every other V4 archive byte remain untouched.

## Evidence custody

`paired.py` single-reads the caller-supplied V4 archive, authenticates that exact buffer, and parses members only from those captured bytes. It never authenticates one baseline read and then reopens the caller path. The joint-liquidity helper is likewise single-read, Git-blob authenticated, and compiled from the captured bytes.

The full game harness now follows one private-execution law. `snapshot_harness()` materializes into a private temporary runtime that stays alive through opponent preparation and the entire matched panel. Evaluator, packer, reference-policy bridge, and candidate loader bytes are each SHA256-authenticated against that snapshot receipt. Evaluator/packer/bridge execute directly from captured buffers; the loader is republished from its captured bytes to a separate private runtime-only path. Opponent adapters and candidate payloads also execute only below the private runtime. The caller-visible `.harness-snapshot` and `opponents/` trees are evidence copies only and are never execution origins.

The focused custody suite proves source swap and deletion after authentication do not alter captured execution, public evidence poisoning does not alter the loaded module, and a wrong loader capture is rejected before publication. The run receipt binds evaluator/packer/bridge/loader SHA256 values and records the private-execution/evidence-copy mode.

For engagement, the runner temporarily wraps the authenticated evaluator module's in-process `Actor.act` method only to observe candidate return values. It restores the exact method after each game. Agent, engine, evaluator, opponent, and archive bytes are unchanged by observation. Each cell records candidate-action trace digests and the exact first returned-action divergence between control and treatment.

## Source contracts

```bash
cd revenue/kaggriculture/cloud-execution-lab/candidates/v5/v4-feed-stock-ablation
python -B -m py_compile feed_stock_ablation.py paired.py test_feed_stock_ablation.py test_paired.py
python -B -m unittest -v test_feed_stock_ablation.py test_paired.py
python -O -B -m unittest -v test_feed_stock_ablation.py test_paired.py
```

The dedicated workflow repeats these on Python 3.11 and 3.12 after asserting exact pushed HEAD and requires a clean tree.

## Engagement-first game gate

On a Linux fleet VM with the exact official engine cache and exact submitted V4 archive:

```bash
python -B paired.py \
  --kg-root ../../../.. \
  --engine-dir /path/to/exact-engine-cache \
  --baseline /path/to/exact-submitted-v4.tar.gz \
  --output /path/to/new/feed-stock-result
```

Default screen = two seeds × two seats × Apex/Arlene = 8 matched cells. Report own terminal score, rival score, margin, action-trace digest, and first returned-action divergence. If all complete cells are action-identical, classify the mechanism `COLD` for that screen and stop rather than expanding compute. If it engages, expand only with matched authenticated cells and promote nothing unless own-score economics are positive with opponent/seat safety.

## Hard boundaries

No production runtime/default/config mutation, no CURRENT/archive pointer write, no release authorization, and no Kaggle submission. Real submitted-V3.1 comparison remains under the authenticated archive bridge/gauntlet and R04 recovery line; this artifact is only a submitted-V4 self-ablation feeding the one canonical V5 decision.
