# S06 compressed continuation index source checkpoint — 2026-09-09

Operation: `titan-v25-orders-20260909-S06`

## Scope

This checkpoint adds a standalone, run-only continuation index for later official-engine experiments. It does **not** modify the canonical TITAN runtime or default action path.

The implementation provides the three requested retrieval variants over the S06 public feature projection (`phase`, `positions`, `resources`, `structures`, `animals`, `market`, `commitments`):

- exact SHA-256 feature hash;
- product-quantized feature hash;
- retrieve-at-most-32 historical continuations followed by an optional caller-supplied current economic score.

Every retrieval unions caller-supplied canonical actions. Historical candidates are deduplicated against canonical actions and fail closed on explicit funding, seed, route, or caller legality conflicts. The module returns a candidate union/order only; it never selects or promotes a final action. Unknown labels such as future outcomes are excluded from the index projection.

The index has deterministic admission accounting with a hard default budget of 128 MiB. The accounting is deliberately conservative and used as the admission limit; the benchmark separately records Python `tracemalloc` usage.

## Correctness checks

```text
python -m unittest -v test_continuation_index.py
Ran 15 tests in 0.006s
OK

AST_OK continuation_index.py
AST_OK test_continuation_index.py
AST_OK benchmark_continuation_index.py
```

Covered contracts:

1. Future/outcome labels do not enter keys.
2. Exact hash is dict-order invariant.
3. Product quantization groups nearby resource/market values while exact hash differs.
4. Exact miss returns canonical fallback.
5. Quantized retrieval unions history with canonical.
6. Canonical duplicate wins over historical copy.
7. At most 32 historical records reach economic rerank.
8. Economic ties are deterministic and prefer canonical.
9. Funding collision rejects history.
10. Seed collision rejects history.
11. Route collision rejects history.
12. Caller legality rejects history without removing canonical.
13. Duplicate trajectory records are idempotent.
14. Memory overflow fails before index mutation.
15. Action hash is content-order invariant.

## Local structural benchmark

Deterministic cloud-container benchmark with 20,000 indexed records and 1,000 retrieve+rerank calls:

```text
records 20000
estimated_bytes 16240000
tracemalloc_current_bytes 22577368
tracemalloc_peak_bytes 22741243
lookup_ms_p50 1.808839
lookup_ms_p95 2.72247
lookup_ms_max 6.661936
```

This local structure benchmark is within the order's 128 MiB and 20 ms lookup/rerank budgets. It is **not** an official-engine benchmark and does not establish end-to-end game latency under the canonical simulator.

## Required remaining S06 evidence

No official-engine full games were run in this VM because shell Git repository materialization is DNS-blocked. Therefore this checkpoint makes **no held-out action, terminal outcome, win-rate, or promotion claim**.

Before any canonical integration, a game-capable peer must source-pin the current canonical archive and run the requested S-versus-no-index panel plus held-out H screen, verify zero legality mismatches, compare exact vs quantized vs retrieve-32/economic-rerank, and report held-out action/outcome improvement. Compression alone is not a promotion criterion.
