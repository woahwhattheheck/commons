# TITAN V4 result provenance bridge (CHAINLOCK)

This package closes the producer-side gap between raw engine result rows and the
existing V4 agent-index analysis without creating a second evaluator or a new V4
root.

The trust theorem is inherited from merged provenance carrier **#11727**:
regression evidence is only comparable when candidate bytes, engine bytes,
environment seed, opponent bytes, and candidate seat are bound exactly. This
bridge makes those identities from the files actually present on disk rather
than trusting caller-supplied digest strings.

## What it does

`bind_result_provenance.py`:

- hashes the candidate artifact and engine artifact from their real bytes;
- hashes every referenced opponent artifact under one declared opponent root;
- supports either regular files or deterministic symlink-free directory trees;
- reads files with no-follow semantics where available and rejects identity /
  size / mtime changes during the read;
- parses strict JSONL (duplicate JSON members and non-standard numeric constants
  fail closed);
- requires every result to be `status == "DONE"` with a two-item engine-style
  `rewards` vector;
- derives candidate and opponent score from `seat` and `rewards`; any redundant
  `margin`, `candidate_score`, or `opponent_score` must agree;
- rejects bool/type-poison seats, non-finite and numeric-overflow values,
  duplicate cells, errors/timeouts, path traversal, and symlinked artifacts;
- requires both seats for every `(seed, opponent, replicate)` cell;
- preserves legitimate large finite outcomes. There is **no guessed score
  ceiling** and no winsorization;
- emits a #11727-compatible ledger using
  `(engine_sha256, environment_seed, opponent_sha256, seat)` plus an analyzer
  JSONL where opponent identity is the artifact SHA rather than a mutable name;
- folds an explicit replicate into the legacy `environment_seed` string so
  repeated cells remain distinct without changing the historical pair-key
  contract.

## Input row

Each JSONL row minimally contains:

```json
{"environment_seed":9922023,"opponent_artifact":"starter.py","seat":0,"status":"DONE","rewards":[168572,3550]}
```

`opponent_artifact` is a canonical relative path under `--opponent-root`. An
optional non-negative literal integer `replicate` is supported. Optional
`margin`, `candidate_score`, and `opponent_score` are consistency assertions,
not authorities.

## Run

From this directory:

```bash
python -B bind_result_provenance.py \
  --candidate /path/to/candidate-artifact-or-tree \
  --engine /path/to/pinned-engine-artifact-or-tree \
  --opponent-root /path/to/opponents \
  --results /path/to/raw-results.jsonl \
  --ledger-out /tmp/titan-ledger.json \
  --analyzer-jsonl /tmp/titan-analyzer.jsonl \
  --receipt-out /tmp/titan-provenance.json
```

The ledger can be compared with another exact candidate ledger using the
already-merged root `titan_regression_gate.py`; the analyzer JSONL is the
provenance-bound input surface for this directory's `analyze_agent_index.py`.

When gauntlet wall-clock evidence matters, run the already-landed QUIETBOX
contention gate as a separate trust oracle on the corresponding panel. CHAINLOCK
binds identities and score provenance; it does not duplicate contention
calibration.

## Assurance boundary

This adapter authenticates **the bytes and result rows it consumes**. It does
not claim process isolation, remote attestation, or that an untrusted runner was
incapable of fabricating a raw result row before it reached this tool. Runner /
execution trust remains a separate layer. The important improvement here is
that downstream analysis no longer needs to trust caller-declared candidate,
engine, or opponent digests, and it never lets a direct `margin` override the
engine-style reward vector.

No gameplay source, feature default, canonical archive, evaluator policy,
provider state, Kaggle state, or submission behavior is changed by this package.
