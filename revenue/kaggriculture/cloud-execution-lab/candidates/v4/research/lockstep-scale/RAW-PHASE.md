# TITAN V4 lockstep raw-phase certificate

Research-only extension of the existing `research/lockstep-scale/` authority. It does not add a controller, runtime key, default, package, composition node, opponent classifier, or activation path.

## Engine fact

Pinned official engine Git blob: `3c202c7ee921da239356789e266b694635103fc4`.

`_process_market` truncates each player's raw market list to the executable prefix and then resolves equal raw indexes across players in lockstep. `_parse_order` accepts `BUY_PRODUCT` syntax generally, but the market executor quotes/commits `BUY_PRODUCT` only for `WHEAT` and `FERTILIZER`. Consequently, moving an existing executable WHEAT/FERT acquisition across a raw slot can change which rival row it shares a quote/commit phase with even when requested quantity and every other row remain unchanged.

This is the same raw-index fact that makes generic compaction unsafe. The new certificate uses it in the opposite direction: it proves a deliberately tiny *phase-only* edit without deleting or compacting anything.

## Certificate boundary

`raw_phase_contract.py::certify_adjacent_buy_phase()` admits only an exact one-slot swap between:

- one literal `['BUY_PRODUCT', item, quantity]`, where `item` is `WHEAT` or `FERTILIZER` and `quantity` is a plain positive integer; and
- one adjacent literal no-op (`None`, `[]`, or `['PASS']`).

The raw market list must retain the same length. Every other raw slot and every non-market field must remain exact under type-preserving canonical JSON. Both source and destination slots must stay inside `max(1, maxMarketOrdersPerTurn)`. Non-adjacent motion, cap crossing, queue compaction, extra BUY tokens, other market verbs, unsupported products, malformed quantities, type-poisoned caps, nonfinite evidence, and unrelated field drift fail closed.

A passing certificate remains `conditional_only=True` and `activation_authority=False`. It does **not** prove a rival row, fill, funding, shed capacity, future need, or episode value. Full-interpreter paired controls and current-policy reachability remain separate obligations.

## Exact authored receipt

Branch base: `main@9d3f32a60e97f7b69f583944fa3ecd450ad5cf54`.

- source Git blob `45df2f3eb2dc53720f2bdcaa795f04dddd88aa17`; SHA-256 `5141d4f289e8ecd59f71df81e8ecbef1c694bff8c5631a3ee45bbc98ba7533f5`; 6810 bytes
- test Git blob `0aaa560eb0a3dff8af93730f741660349ad858de`; SHA-256 `6f0f7dfeaec501151085ee1746e5259b1c008c73c2b08bbab8c47c1f105e40c4`; 7455 bytes
- `19/19` tests PASS under normal Python
- `19/19` tests PASS under `python -O`
- `py_compile` PASS

The focused suite covers WHEAT delay, FERTILIZER advance, literal PASS/empty slots, unsupported product domain, malformed/zero/type-poisoned quantities, extra tokens, wrong market verbs, truthy pseudo-noops, non-adjacent movement, raw-length drift, non-market drift, both executable-prefix boundary directions, minimum-one cap semantics, cap type poison, multi-slot changes, JSON scalar-type drift, nonfinite evidence, and input immutability.

## Next evidence

Use the existing full-interpreter lockstep harness to add paired same-callback controls that differ only by this certified adjacent swap, then census the current authored/native returned-action surface for natural WHEAT/FERT rows with adjacent literal no-ops. A source certificate with zero natural reach remains a research result, not a reason to mint another scheduler.
