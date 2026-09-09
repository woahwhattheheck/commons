# TITAN V3 — market-prefix suffix rescue candidate

Operation: `op:titan-v3-market-prefix-rescue-20260909-01`

## Confirmed mechanism

The canonical feed- and fertilizer-stock guards can fully withhold a selected sale by replacing its market row with the exact placeholder `[]`. The official Kaggriculture engine first truncates the raw market list to `maxMarketOrdersPerTurn`, then parses each retained row. Therefore an empty row inside the live prefix consumes one issued position while a later valid order outside the prefix is silently excluded.

The engine also advances both players' market queues in lockstep by **absolute row index** and refreshes prices after each index. Broad stable packing across an interior blank therefore retimes already-live orders against different rival orders and quote states. That is a separate score-bearing timing intervention, not a transport-only repair.

This candidate now performs the causally narrow arm: it moves exact `[]` placeholders only when the live prefix blanks form a suffix. At least one engine-executable tail row must cross the cap. Every already-live non-empty row keeps both its value and its absolute index. Interior blanks fail closed with `interior_blank_would_retime_active_order` and a machine-readable list of the blocked active rows.

## Scope and safety

- Default-off candidate only; canonical `main.py`, runtime, config, archive, and release pointers are untouched.
- `candidate.py::agent` is submission-compatible and emits no diagnostic fields.
- `candidate.py::instrumented_agent` is evidence-only. The paired runner strips its marker before the official interpreter sees the action.
- Successful events carry schema v2 and `activation_class: suffix_only`.
- Source contract is pinned to base `853c2e3ea5195dbc957f479b87b2f240fa003a2c`, including the exact canonical agent, runtime, stock guard, evaluator, and engine blobs.
- The installed-engine contracts prove both the positive suffix rescue and the predecessor-discriminating interior-index repricing mechanism.
- The panel uses the pinned official interpreter, fresh persistent agent processes per game, the same public Arlene opponent, the same seeds, and both seats for baseline and candidate.
- Zero activation must be byte-behavior equivalent: any zero-event trace or score divergence fails the run.
- A positive development result is not sufficient for promotion. It still needs broader opponents and disjoint held seeds through the native paired-game gate.

## Commands

```bash
python -m unittest -v test_market_prefix_rescue.py
python -m unittest -v test_official_engine_contract.py  # needs kaggle-environments==1.32.7
python run_panel.py \
  --seeds 2609099601,2609099602,2609099603,2609099604 \
  --output RESULTS.json --markdown RESULTS.md
```

## Decision use

- `activation_cells == 0`: retire the pure suffix arm; do not silently broaden it into an interior timing heuristic.
- Any failed or incomplete cell: invalid evidence; do not compare scores.
- Negative activated strata: reject the candidate.
- Positive activated development strata: expand to the current opponent matrix, then freeze selection before any held-seed evaluation.
- An interior stable-pack arm, if pursued separately, must identify every retimed active row and stratify its evidence as a timing policy rather than attributing the result solely to tail rescue.

No Kaggle submission, hosted-score claim, leaderboard claim, spend, or canonical promotion is made here.
