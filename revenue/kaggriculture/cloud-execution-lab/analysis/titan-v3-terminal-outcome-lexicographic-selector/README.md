# TITAN V3 terminal-outcome lexicographic selector

Operation: `TITAN-V3-TERMINAL-OUTCOME-LEXICOGRAPHIC-SELECTOR-20260910-01`

This packet supplies the missing decision contract between cash optimization and tournament outcomes. It is an additive reference implementation, not a canonical runtime mutation and not playing-strength evidence.

## Why

A scalar own-cash objective correctly rejects candidates that make TITAN richer while turning a win into a loss. A scalar relative-margin objective can correctly value a loss-to-win conversion even when both players lose substantial cash. Neither scalar alone expresses both requirements.

This selector consumes complete terminal-score certificates for an incumbent and already-generated candidate plans. It admits a candidate only when:

1. no modeled scenario moves to a worse official W/T/L class;
2. every scenario whose class is unchanged has nondecreasing TITAN cash and nondecreasing margin;
3. every candidate terminal cash value remains at or above a predeclared absolute floor;
4. any TITAN cash sacrifice occurs only in a scenario whose W/T/L class strictly improves and remains within a predeclared sacrifice cap;
5. the candidate has a distinct commitment and at least one strict improvement; and
6. exactly one eligible candidate lexicographically outranks the incumbent.

The rank is, in order: worst scenario outcome, win count, tie count, minimum margin, aggregate margin, minimum TITAN cash, aggregate TITAN cash. An exact or ambiguous best preserves the incumbent.

## Scope and composition

Both tail thresholds are explicit receipt inputs; they must be fixed before candidate results are opened. The witness uses a bounded illustrative policy and deliberately rejects the observed catastrophic-scale pattern while accepting a smaller L→W conversion.

The module does **not** generate plans, model rival inventory, infer terminal scores, mutate a route, call the producer, or alter market quantities/order. It must consume terminal-complete rows from an independently source-bound engine/evaluator/scenario carrier. This keeps it distinct from λ=0/λ=1 optimizer work.

The one-tree integration seam should be atomic and before any `planned`, `pending`, or selected-action ledger is committed:

1. Generate the incumbent and candidate plan set once from one public preworld.
2. Evaluate all plans on the exact same complete scenario grid through terminal.
3. Bind engine, evaluator, scenario model/set, public preworld, terminal trace, and terminal-bank equality.
4. Call `select_document`.
5. Commit only the selected plan and all of its associated state, or preserve the exact incumbent objects and ledgers.
6. Never call the production agent a second time and never splice a selected market action onto another plan's state.

Before promotion, a current-package both-seat official-interpreter panel must show returned-action/commitment activation, zero new losses/lost wins, no negative opponent×seat outcome stratum, and an acceptable own-cash tail. This packet grants no merge, promotion, provider, Kaggle, or submission authority.

## Current custody anchors

The reference receipt records the current coordination base observed during construction:

- `main`: `c51049d671b55d282e0fed5df37a0be7c513a838`
- canonical archive: `5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1`
- source manifest: `3249398b6aa56d1b3464db8d0cce5aa35e8edee397fc4341bd710d1f74dad469`

The engine/evaluator/scenario identities in any real input must come from the executing carrier; the selector never invents them.

## Run

```bash
python -B -m py_compile terminal_outcome_selector.py test_terminal_outcome_selector.py
python -B -m unittest -v test_terminal_outcome_selector.py
python -B terminal_outcome_selector.py WITNESS-INPUT.json WITNESS-REPORT.json
```

The CLI rejects duplicate JSON keys, NaN/Infinity, non-integer/bool cash, invalid tail thresholds, malformed hashes, incomplete scenario grids, source-state mismatches, nonterminal rows, score/bank assertions that are not literal true, input/output aliases, symlink/device paths, and same-commitment contradictory effects. Output is canonical JSON, atomically written, and SHA-256 self-sealed.
