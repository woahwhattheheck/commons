# TITAN V3 Capillary action-bound panel — SOL-CAMBIUM

Operation: `op:titan-v3-capillary-action-bound-panel-20260910-01`

## Why this exists

The admitted Capillary carrier is source-complete and passed its inherited
contracts, private-evaluator smoke, and canonical build check, but it has no
full-game score evidence. Replay `107130860` supplies a concrete reason to
test it: the submitted policy commits twelve MELON seeds (`$960`) before the
opening HIRE/animal program, while the higher-scoring opponent preserves that
liquidity and establishes the full worker route.

An earlier open-loop probe showed that simply deleting those twelve seed buys
can reconverge under a frozen action tape. That does **not** answer the
closed-loop question. This lane therefore measures the actual emitted action
stream and terminal cash under the official interpreter.

## Exact arms

Control:

- exact canonical standalone archive
  `17f536087b3a6baf4ae1222a051285766a3ea8c2ca5af6edc190d4f527e12b86`;
- no overlays;
- private materialization;
- `main.py::agent`.

Candidate:

- the same exact canonical archive;
- the four source-pinned Capillary overlays;
- the already-admitted executable carrier at
  `candidates/capillary-executable-sol-prism/candidate.py::agent`.

`audit.py` rejects archive, evaluator, engine, carrier, overlay, loader, or
opponent drift before any game runs.

## Panel

The workflow runs four fixed seeds against frozen Arlene and frozen V1, with
the candidate in both seats:

- 16 paired cells;
- 16 control games;
- 16 candidate games;
- 32 complete official-interpreter games total;
- 720 observations / 719 decisions per game;
- 1 second action RPC, 15 second startup, 180 second game ceiling;
- role-stable agent RNG seed `20260909`.

`materialize_evaluator.py` patches the exact evaluator blob only in the hosted
working directory. It hashes the candidate's returned action object after both
actors respond and before the interpreter sees either action. The repository
evaluator is never modified.

## Advance contract

The candidate advances only when all of these are true:

1. at least one paired cell has a different pre-interpreter candidate action
   stream;
2. global mean own-cash delta is positive;
3. global median own-cash delta is nonnegative;
4. every opponent × candidate-seat stratum has nonnegative mean own-cash
   delta.

Margin and opponent-cash deltas are reported, but they are secondary. Any
incomplete lifecycle, actor failure, source drift, closure alias, score/bank
mismatch, evaluator drift, or missing cell fails closed.

A positive verdict nominates a fresh-main port. It does not mutate canonical
runtime, archive pointers, providers, or Kaggle submissions. A rejection
closes this exact Capillary carrier as a V3 scoring arm while retaining the
full causal receipt.
