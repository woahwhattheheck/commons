# D3 official-replay externality telemetry sidecar

This directory closes a producer gap in the reviewed TITAN V3.1 D3 merge gate. The D3 gate can validate `externality_coverage` and `externality_events`, but the pinned official evaluator currently persists terminal scores/daily bank and a trace hash rather than the public price/supply observations D3 needs.

## Contract

`v31_externality_replay_sidecar.py` is observational only. It temporarily wraps the exact official engine interpreter, calls the original interpreter first, and then reads public post-step state. The wrapper is restored in `finally`; exceptions from the original evaluator/interpreter propagate normally. A capture/read failure cannot alter actions or terminal scores — it only makes the producer receipt incomplete, which causes assembled evidence to set `externality_complete=false` and therefore makes D3 HOLD.

The captured public fields are limited to:

- `observation.market.prices[product]` after each official interpreter step;
- public rival farm tiles, reduced with the reviewed D1 fail-closed standing-supply theorem.

The sidecar never reads rival private shed, farmer inventories, submitted rival orders, hidden intent, or future state.

For a baseline/candidate matched cell, traces must have the same complete step domain. For every matched `(step, product)` price divergence the sidecar emits:

- `price_delta = candidate_price - baseline_price`;
- `rival_long_units = max(baseline_public_supply[product], candidate_public_supply[product])`;
- one deterministic event id.

A complete matched cell emits exactly one coverage receipt whose `events_observed` equals its event count. Zero price-divergence events are valid only with that explicit zero-event receipt. Missing/malformed/mismatched public traces never silently disappear; the global assembled document becomes `externality_complete=false`.

## Pinned theorem anchors

- official evaluator source blob: `1fb6b655bb4ca1e1684be165a8ef513e2e6c2325` (`reference/evaluator/evaluate.py`);
- official interpreter source blob: `3c202c7ee921da239356789e266b694635103fc4` (`reference/engine/kaggriculture.py`);
- reviewed public rival-supply donor blob: `d9d2add77033a56fd2784e0132fd2abb2f700371` (D1 `public_rival_supply` theorem);
- reviewed D3 gate carrier parent: PR #12556 / head `dad1a905ed1567c860f62949781f7afa55cc8484` at authoring time.

The unit suite is zero-runner/local and exercises seat-relative public supply, strict type poison, malformed-state HOLD behavior, step-domain mismatch, event accounting, zero-event complete coverage, unique event IDs, and interpreter restoration.

## Authority boundary

Analysis/evidence production only. No gameplay, overlay/default, package input, evaluator implementation, engine implementation, FILES/MANIFEST, provider, Kaggle, leaderboard, or submission mutation. This donor is intended to be consumed by the final post-L3/current-package D3 workflow rather than used as standalone promotion authority.
