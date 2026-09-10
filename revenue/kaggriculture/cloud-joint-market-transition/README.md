# Exact joint market + town transition oracle

`joint_transition.py` closes the shared-mechanics proof gap between a proposed TITAN market-queue rewrite and the pinned Kaggriculture interpreter. From one complete **POST-UNIT** prestate, it executes both players' literal market queues together through the official `_process_market()` function and then the official `_town_consume()` stage.

This is a conditional mechanics proof, not a policy, opponent model, whole-game simulator, promotion gate, or hidden-state claim. It never selects an action. The caller must supply both complete literal actions and both private states.

## Exact engine boundary

The loader accepts only these official bytes:

- repository: `Kaggle/kaggle-environments`
- commit: `28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c`
- path: `kaggle_environments/envs/kaggriculture/kaggriculture.py`
- Git blob: `3c202c7ee921da239356789e266b694635103fc4`
- SHA-256: `bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e`

`engine_binding.py` verifies both hashes, extracts the exact transitive definitions used by the two official functions, and invokes those definitions unchanged. A fabricated or stale mechanics object is rejected.

## What the report contains

Each baseline/candidate arm records:

- active queues and ignored suffixes for both players;
- cumulative prefix `0..N` full states and canonical SHA-256 hashes;
- each literal row, parsed form, executed units, cash/resource effects, and shared-market inventory/price effects;
- exact pre-town and post-town full public/private states and hashes;
- town inventory/price effects;
- changes to inherited same-slot executions;
- caller-named JSON-pointer checkpoints with `PASS`, `HOLD`, or `UNSPECIFIED` protection status.

The candidate may change only the tested player's `market` array. The rival action, all unit fields, and every other tested-player field must match. Inputs are deep-copied, mutation-checked, and never aliased into the result.

The validator also rejects inconsistent observed market prices, negative inventory, malformed board/worker/land state, over-capacity sheds, unreachable ninth-shop states, non-finite data, and requests beyond deterministic HIRE/Fibonacci, land, order, market-loop, or deadline bounds.

## Swarm counterexamples retained as executable contracts

The suite proves why locally attractive queue rewrites cannot be called safe from own-price arithmetic alone:

1. **Prior own prefix plus rival SELL.** With WHEAT inventory `10066`, parent `SELL WHEAT 78; SELL WHEAT 1; SELL MILK 1`, candidate moving MILK before the one-unit WHEAT lot, and rival `SELL WHEAT 100` in the crossed row, parent own/rival cash is `1828/2075`; candidate is `1827/2076`. Relative cash falls by `2` and the protected moved-lot receipt returns `HOLD`.
2. **Rival BUY demand.** Reordering `SELL EGG 1; SELL WHEAT 1` against rival row-zero `BUY WHEAT 1` changes own cash `67 -> 66`, even though the demoted EGG lot remains on a flat quote.
3. **Same-product tranche rewrite.** At WHEAT inventory `10219`, replacing `SELL 1; blank; SELL 1` with `SELL 2; blank; SELL 1` against a rival middle-row WHEAT buy changes own/rival cash `42/979 -> 41/980`, relative `-2`.
4. **Town chronology.** Exact town stages can move the next WHEAT quote to `$32`; a retained MILK sale can fund the inherited buy while its omission cannot.
5. **Price floor.** A `$1` sale pays the seller and removes shed stock but does not add public supply.

These are component-level mechanics facts, not whole-game strength claims.

## Run

```sh
D=revenue/kaggriculture/cloud-joint-market-transition
PYTHONDONTWRITEBYTECODE=1 python -B "$D/test_joint_transition.py" \
  --engine-source /path/to/kaggriculture.py \
  --result /tmp/joint-transition-validation.json
```

For one JSON case:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B "$D/joint_transition.py" \
  --engine-source /path/to/kaggriculture.py \
  --input /path/to/case.json \
  --output /tmp/report.json \
  --deadline-seconds 5
```

CLI codes are `0` for a complete comparison with no requested checkpoint failure, `2` for unknown/invalid/over-budget evidence, and `3` for a complete comparison with a requested protection `HOLD`.

The sealed local receipt reports **48/48 tests**, **22 complete comparison cases**, **4 extracted-vs-full-official-module differential arms**, zero game panels, and zero game seeds. `validation.json` binds all source and test modules plus deterministic source-tree and test-tree hashes. No hosted CI result is claimed.

## Integration contract

Pressure, funding, tranche, and future-acquisition owners should materialize one exact POST-UNIT prestate, keep the rival action fixed across arms, name every promised protected fill/receipt/acquisition (including promoted and demoted lots), and require both `status == "complete_conditional"` and checkpoint `PASS`. `HOLD`, `UNSPECIFIED`, unknown state, or missing rival scenarios is no certificate.

A separate causal, tail-safe whole-game lane is still required before any policy promotion. T08 retains one-tree integration and release custody. This additive directory does not alter policy, runtime, configuration, archives, pointers, workflows, providers, or Kaggle submissions.
