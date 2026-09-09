# Titan V3 dual-predecessor win gate

`dual_predecessor_gate.py` closes the gap between a valid one-baseline paired
comparison and the stronger release claim that one exact Titan V3 candidate
beats **both** predecessor builds.

Running `gate.py` twice is not sufficient by itself. The second invocation may
bind a different candidate panel, candidate archive, engine, runner, grid, or
policy. It may also compare two labels for the same predecessor artifact. The
dual gate makes those conditions one atomic, fail-closed decision.

## Required inputs

The command consumes seven regular files:

1. predecessor A contract, provenance evidence, and `GAMES.jsonl`;
2. predecessor B contract, provenance evidence, and `GAMES.jsonl`;
3. one shared candidate `GAMES.jsonl` used by both comparisons.

All seven inputs are privately snapshotted before either single gate runs. Each
single-gate report must bind back to those exact outer snapshot SHA-256 values.
The candidate panel is therefore byte-identical across the two decisions.

The two contracts must declare:

- the same candidate name and candidate artifact SHA-256;
- the same engine commit/hash and runner commit/hash;
- the same normalized seeds, opponents, seats, expected-cell count, and policy;
- distinct predecessor names and distinct predecessor artifact SHA-256 values;
- a candidate artifact that does not alias either predecessor artifact.

Each comparison must independently satisfy the existing complete-grid,
provenance, metric, robustness, and policy rules in `gate.py`.

## Usage

```bash
python3 dual_predecessor_gate.py \
  --predecessor-a-contract /evidence/v1.CONTRACT.json \
  --predecessor-a-evidence /evidence/v1.PROVENANCE.json \
  --predecessor-a-games /evidence/v1.GAMES.jsonl \
  --predecessor-b-contract /evidence/v2.CONTRACT.json \
  --predecessor-b-evidence /evidence/v2.PROVENANCE.json \
  --predecessor-b-games /evidence/v2.GAMES.jsonl \
  --candidate-games /evidence/v3.GAMES.jsonl \
  --report /evidence/V3-DUAL-GATE.json
```

Exit codes retain the single-gate contract:

- `0`: `PROMOTE` — both predecessor comparisons are valid and pass;
- `2`: `INVALID` — an input, identity, grid, policy, or hash binding is invalid;
- `3`: `REJECT` — evidence is valid, but one or both comparisons fail policy.

The report includes the seven outer input hashes, the shared cross-comparison
identity, both complete single-gate reports, and each comparison exit code.

## Tests

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONHASHSEED=0 \
  python3 -m pytest -q test_dual_predecessor_gate.py
```

The adversarial suite covers both-pass promotion, one-pass rejection, candidate
artifact drift, engine/runner drift, duplicate predecessor identity, candidate
artifact aliasing, stale inner candidate bytes, and the CLI/report exit path.

`PROMOTE` proves only the declared dual-predecessor panel. It does not prove a
leaderboard rank, replace the current release archive, or authorize publication.
