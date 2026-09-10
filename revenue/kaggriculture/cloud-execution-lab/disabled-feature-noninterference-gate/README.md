# TITAN V3 disabled-feature noninterference gate

This additive gate prevents a feature advertised as disabled from executing its
protected calls or writes before the controller's no-op return. It is a safety
and regression carrier, not a gameplay policy, scorer, promotion decision, or
Kaggle submission path.

## Why this exists

The source bound by `contracts/spatial-tempo-current.json` is the exact
pre-repair `spatial_tempo.py` Git blob
`edbc423023479dbe2e78131495334384a87b607f`. In
`SpatialTempo.transform`, `_continue_weed(...)` is reachable before the joint
`not self.pathing and not self.tempo` return. Accordingly, the current contract
expects `BLOCK`: a green workflow means the analyzer successfully detects the
known predecessor. It does **not** authorize that source for release.

Once the narrow W0 source repair is present in the PR merge tree, rebind the
contract to that exact source blob and change `expected_verdict` to `PASS`. The
workflow intentionally fails on source drift so an old expectation cannot bless
a new controller.

## Source mode

Source mode parses the configured class and method, binds every named disabled
feature to the literal boolean `false`, and explores reachable control flow. It
honors Python boolean short-circuiting and dominating returns. It blocks:

- a protected call or write on any reachable path;
- mutation of a contractual disabled binding;
- protected-call aliases, callable escapes, and dynamic `getattr` dispatch;
- protected effects hidden in reachable `finally` or unsupported control flow;
- duplicate or malformed contracts, ambiguous class/method selection, path
  traversal, and source-blob drift.

The W0 form below is accepted because the protected call is short-circuited when
both features are off:

```python
if (self.pathing or self.tempo) and self._continue_weed(...):
    return selected
```

A dominating disabled return is accepted as well. The pre-repair ordering is
blocked.

```bash
python revenue/kaggriculture/cloud-execution-lab/disabled-feature-noninterference-gate/disabled_feature_noninterference.py \
  source \
  --repo-root . \
  --contract revenue/kaggriculture/cloud-execution-lab/disabled-feature-noninterference-gate/contracts/spatial-tempo-current.json \
  --output /tmp/titan-disabled-source-receipt.json \
  --expect BLOCK
```

The process exits `0` only when observed and declared verdicts agree, `1` when
the analysis is valid but the verdict differs, and `2` for malformed,
ambiguous, drifting, or unsafe inputs.

## Spent-trace identity mode

Trace mode consumes paired evidence supplied by another authorized lane. It
never imports TITAN, starts a game, selects seeds, or spends compute. Every
expected case must be present exactly once. Each baseline and disabled arm must
contain valid SHA-256 action and transition digests plus a two-integer bank
vector. The complete arm objects—including optional reward, state, inventory,
or provenance fields—must be byte-canonical identical.

```bash
python revenue/kaggriculture/cloud-execution-lab/disabled-feature-noninterference-gate/disabled_feature_noninterference.py \
  trace \
  --evidence revenue/kaggriculture/cloud-execution-lab/disabled-feature-noninterference-gate/examples/paired-spent-trace.json \
  --output /tmp/titan-disabled-trace-receipt.json \
  --expect PASS
```

The checked-in trace is explicitly synthetic schema smoke, not replay evidence.
Replace it only with immutable, already-spent evidence supplied by the owner of
the authorized evaluation lane.

## Determinism and write safety

Receipts are canonical finite JSON with sorted findings, content hashes, and a
self-digest. No timestamps or host paths enter the receipt. Writes use a same-
directory temporary file, `fsync`, and atomic replacement. An output path that
aliases the source, contract, or trace evidence is rejected before mutation.

## Test surface

```bash
cd revenue/kaggriculture/cloud-execution-lab/disabled-feature-noninterference-gate
python test_disabled_feature_noninterference.py
```

The suite covers the exact predecessor shape, the W0 short-circuit and dominant-
return repairs, one-flag fallthrough, nested branches, calls in conditions,
`finally`, protected writes, binding mutation, callable alias/dynamic dispatch,
source drift, duplicate/malformed contracts, deterministic receipts, exact
spent-trace identity, every required trace field, non-finite values, incomplete
case grids, and output aliasing.
