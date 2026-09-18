# Kaggriculture public-opponent benchmark

This additive lane reuses `../cloud-eval/evaluate.py`; it does not build another
simulator. It prepares two author-attributed, Apache-2.0 public Kaggle notebook
agents, verifies their exact notebook and extracted-agent hashes, and compares a
candidate in both seats on predeclared seeds. No notebook cell is executed.

## Sources and preparation

The exact authors, URLs, Kaggle script-version IDs, notebook hashes and agent
hashes are in `UPSTREAM.json`. Upstream authors retain ownership. Preparation is
the only networked phase; evaluation remains offline:

```sh
curl -fsSL 'https://www.kaggle.com/api/v1/kernels/pull/kaitofukami/103-128-fresh-public-v43-sparse-shop-hybrid' -o /tmp/kaito.json
curl -fsSL 'https://www.kaggle.com/api/v1/kernels/pull/flexonafft/kaggriculture-multi-route-farming-agent' -o /tmp/igor.json
python -B prepare.py --kaito /tmp/kaito.json --igor /tmp/igor.json --output /tmp/public-agents
```

`prepare.py` rejects a changed ref, current notebook version, notebook source
hash, extracted source hash or source size. It uses `ast.literal_eval` plus
base85/zlib decoding and compiles the result, without executing notebook code.
The extracted third-party files stay in ephemeral storage and are not committed.

## Both-seat comparisons

Prepare the already pinned official interpreter as documented in `../cloud-eval/README.md`,
then run the predeclared development phase:

```sh
python -B benchmark.py --engine-dir /tmp/kag-engine --sources-dir /tmp/public-agents \
  --phase development --output /tmp/opponent-development.json
```

Development seeds are `9000011,9000049,9000061`. Reserved validation seeds are
`9000077,9000091`; they are disjoint from development and the previously
published Commons studies. The wrapper passes both pinned public agents to the
existing evaluator, which runs every seed in both player positions and records
final cash, runtime, resource, crash/timeout and trace diagnostics. The first
game is replayed for determinism without entering the aggregate twice.

The default candidate is the already selected `../cloud-market/main.py` lean20
artifact. Local results are official-interpreter comparisons, not hosted Kaggle
scores, submission receipts, universal strength claims, awards or payments.

Focused integrity tests:

```sh
python -B test_opponent_bench.py
```

Coordination source: [KAGGRICULTURE BUILD + SIMULATION ORDERS](https://tokenjunkielabs.slack.com/archives/C0BTB4SUCP9/p1788762339088829).

License for the new benchmark wrapper and documentation: MIT OR CC-BY-4.0,
TokenJunkieLabs / Bryce Muhlnickel. Extracted upstream agents retain their
Apache-2.0 terms and original authorship.

## Contest product (titanmcp)

Live judge pad (≠ Commons Shared Pad / ≠ Commons `/mcp`): https://webmcp-pad.vercel.app/ — **titanmcp 1.4.5**, 24 tools, Agent Resources, `syncConsents`. Board: [titanmcp.html](../../../titanmcp.html). Cite Latch Pad KEEP.
