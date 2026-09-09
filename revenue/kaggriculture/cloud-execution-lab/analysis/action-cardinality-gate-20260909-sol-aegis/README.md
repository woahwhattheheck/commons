# TITAN V3 observable-hand/action-cardinality gate

`action_cardinality_gate.py` is a downstream, fail-closed release gate for a concrete submitted-replay defect: TITAN can serialize more hired-hand action rows than the acting player could observe before that action. The Kaggriculture interpreter silently ignores the nonexistent-hand suffix, so a run can look structurally complete while executing a different program.

## Exact alignment contract

Kaggriculture replay step `k` stores the action selected from observation `k-1`. The gate therefore compares:

- step `0` action against the step `0` initial observation (bootstrap only);
- every step `k > 0` action against the acting seat's own farm in step `k-1` observation.

Comparing an action to the same-step observation is unsound at HIRE and end-of-day boundaries. The tests contain a predecessor-failing trap where the post-state has five hands but the actual pre-state has four.

## Verdicts

- `PASS`: every submitted `hands` array has length at most the exact observable hand count.
- `REJECT`: one or more actions contain a nonexistent-hand suffix.
- `INVALID`: evidence is missing, ambiguous, malformed, mis-seated, misidentified, or hash-mismatched.

Explicitly omitted hand rows are counted but allowed; the official interface can represent no action by omission. A present market row `['SELL', 'WHEAT', 0]` is counted as the canonical market no-order sentinel and is not confused with an absent `market` field. Literal empty market rows are separately counted as present, noncanonical evidence but are not adjudicated here; their producer/normalization belongs to the existing market-row lane.

## Usage

```bash
python action_cardinality_gate.py check replay.json.gz \
  --seat 1 \
  --expected-sha256 <raw-gzip-sha256> \
  --expected-episode-id 107140666 \
  --expected-agent-name 'Bryce Muhlnickel' \
  --output receipt.json
```

Exit codes are `0=PASS`, `2=REJECT`, `3=INVALID`. A REJECT receipt is still a valid, sealed evidence artifact. Verify any receipt without replay bytes:

```bash
python action_cardinality_gate.py verify receipt.json
```

The receipt binds raw and decoded replay bytes, environment/module identity, episode/seed/seat/agent identity, exact transition alignment, the compact transition-ledger digest, every over-cardinality witness in a compact columnar matrix, a digest of the full violation ledger, contiguous ranges, trailing action rows/opcodes, and a hash over the complete four-file gate implementation (`action_cardinality_gate.py`, `gate_common.py`, `gate_core.py`, and `gate_receipt.py`). `receipt_sha256` seals canonical JSON; output replacement is atomic.

## Local acceptance

```bash
./run_tests.sh
```

The 41-test suite covers the submitted day-5 5-vs-4 shape, a distinct failed-HIRE boundary, exact and under-cardinality cases, own-seat indexing, the same-step alignment trap, canonical no-order vs absence, bool/int ambiguity, malformed rows, wrong seat/player, missing farm/action evidence, gzip/plain parity, raw-hash and identity mismatch, corrupt gzip/JSON, deterministic ledgers, atomic output, and receipt tampering.

## Truth boundary

This package does not edit policy, controller, HIRE logic, routes, engine, evaluator, canonical archives/pointers, provider configuration, or submission state. It proves release integrity only. A clean receipt is necessary evidence, not a score gain or leaderboard-win claim.
