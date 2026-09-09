# Frozen V2 future-rival conservatism ablation

Operation: `titan-v2-future-rival-ablation-20260909-sol-fulcrum-01`.

## Question

Submitted V1 evaluates three SELL-scheduler scenarios: no rival sale, a same-turn paired rival sale, and a same-turn rival sale after ours. Submitted V2 preserves those scenarios and adds the full observed rival-supply stress twice more: at `now + 1` and at `end - 1`. The quantities are public-state stress magnitudes, not calibrated probabilities or forecasts. Because the optimizer requires strict improvement in every named scenario, either added stress can veto a plan that improves all three V1 scenarios.

This package asks one causal question: **did those two future placements contribute to the submitted-V2 regression?** It does not weaken tuple-aware market scoring, alter current-turn rival stress, or change any other V2 behavior.

## One-factor boundary

`materialize.py` verifies the exact frozen V2 tree and scheduler Git blob, copies the full runtime, and for the ablation removes exactly these two statements:

```python
if end > now:
    scenarios.append(("observed_next_turn", ((now + 1, rival_quantity),), "paired"))
if end > now + 2:
    scenarios.append(("observed_before_delayed_batch", ((end - 1, rival_quantity),), "paired"))
```

The committed source uses compact formatting; the materializer requires that exact byte preimage once. Every other V2 byte remains unchanged, including all-shed targets, full continuation value, forced-feasibility repair, route SELL reconstruction, max-order feasibility, and original market-index preservation. The frozen source is re-inventoried after copying to prove it was not modified.

Each generated `entry.py` embeds the complete materialized runtime inventory and refuses to import if any file, byte count, SHA-256, symlink, or special member differs. The evaluator therefore fingerprints distinct generated entries that are themselves bound to distinct complete scheduler closures; the identical 66-byte frozen `candidate.py` cannot alias the arms.

## Candidate-action activation

The pinned evaluator's ordinary `trace_sha256` contains both agents, banks, and final observations, so it cannot by itself prove that this candidate changed an action. `activation_eval.py` loads the exact evaluator Git blob and temporarily wraps the parent-side `Actor.act` method during one game. On each successful actor return it hashes the raw returned action **before** `play()` can assign it to engine state or call the official interpreter. The exact action object is then returned unchanged. For each seat it records:

```text
sha256(length_u64be || canonical_json({step, action}))
```

The completed report carries both seat digests, both covered-step counts, the candidate-seat digest/count, the explicit pre-interpreter capture boundary, overlay SHA-256, and pinned evaluator Git blob. The wrapper restores `Actor.act` in `finally`; child workers and the official interpreter are unmodified. The comparator rejects incomplete action coverage or a score/whole-trace change without a candidate-action change.

## Development screen

The workflow executes frozen V2 control and the one-factor ablation on the same eight seeds, both seats, against frozen V1 and public Arlene: 32 paired cells / 64 complete panel games, plus one deterministic replay per arm. It requires:

- exact engine, loader, evaluator, overlay, opponent, seed, RNG, timeout, and episode context equality;
- distinct invocation IDs, generated entry SHA-256 values, and complete runtime closures;
- the exact opponent × seed × literal seat grid with no missing, duplicate, failed, partial, boolean-seat, or non-finite row;
- candidate-action activation;
- positive mean own cash, nonnegative median own cash, at least as many positive as negative own-cash cells, positive mean margin, and nonnegative mean own cash in every opponent × seat stratum.

`UPSIDE_SCREEN` is a bounded development result only. `NO_ACTIVATION`, `REGRESSION`, and `INVALID` never authorize integration, archive promotion, provider action, or Kaggle submission.

## Local contracts

```bash
CASE=revenue/kaggriculture/cloud-execution-lab/analysis/v2-future-rival-ablation-sol-fulcrum
python -m py_compile "$CASE"/*.py
python -m unittest discover -s "$CASE" -p 'test_*.py' -v
python "$CASE/seam_contract.py" --output /tmp/FUTURE-RIVAL-SEAM.json
```

No canonical runtime, configuration, archive, pointer, default, provider, or Kaggle state is modified by this package.

### Real scheduler witness and collision credit

After this lane's earlier claim, SOL-CALIBER independently found a concrete CARROT
market path in later-colliding PR #11831. `test_real_scheduler_witness.py` preserves
that contribution with credit and executes the actual frozen/materialized
`optimize_lot` implementations. Frozen V2 keeps `((542, 18), (550, 2))`; removing
only the two future stress placements selects `((542, 13),)` and improves the three
V1 scenarios by `+4`, `+1`, and `+1`. This is mechanism reachability, not a gameplay
strength or leaderboard claim.
