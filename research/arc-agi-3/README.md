# ARC-AGI-3 deterministic exploration baseline

Paid-work lane: ARC Prize 2026 / ARC-AGI-3. This directory is a reproducible, CPU-first baseline and submission-readiness package. It does **not** contain competition data, an ARC API key, a Kaggle submission, or a claimed leaderboard score.

## Pinned public contract

Verified 2026-09-08 against the organizer's current public material:

- Competition: ARC-AGI-3, interactive reasoning over novel turn-based game environments.
- Milestone 2: 2026-09-30 23:59 UTC. Final entry/team merger: 2026-10-26. Final submission: 2026-11-02 23:59 UTC.
- Guaranteed top-score pool: $75,000 ($40k/$15k/$10k/$5k/$5k); separate 100% grand prize is conditional.
- Frames: one or more 2-D grids, maximum 64x64, cell values 0..15.
- States: `NOT_PLAYED`, `NOT_FINISHED`, `WIN`, `GAME_OVER`.
- Actions: `RESET`, `ACTION1`..`ACTION7`; the frame's `available_actions` is authoritative. `ACTION6` requires integer `x,y` coordinates in 0..63.

Public references:

- https://arcprize.org/competitions/2026/arc-agi-3
- https://www.kaggle.com/competitions/arc-prize-2026-arc-agi-3/overview
- https://github.com/arcprize/docs/blob/main/actions.mdx
- https://github.com/arcprize/docs/blob/main/create-agent.mdx
- https://github.com/arcprize/ARC-AGI-3-Agents

Exact upstream pins used here are in `environment.lock`.

## What this baseline does

`arc3_baseline.py` implements a deterministic online explorer with no third-party dependencies and no network access. It validates the public frame/action contract, builds a compact transition graph keyed by visual-state hashes, scores actions using novelty/progress reward plus bounded UCB exploration, and selects `ACTION6` coordinates from changed regions, non-background connected components, then deterministic anchors.

The policy deliberately does not encode any private game solution. It is a measurable floor to iterate from: every action is legal under the observed action set, every transition is recorded, repeated states reuse learned action evidence, and level completion receives a strong reward signal.

`competition_agent.py` is the thin adapter for the official `arcprize/ARC-AGI-3-Agents` harness. `test_arc3_baseline.py` is an offline synthetic contract suite.

## Offline verification

From this directory:

```bash
python -m py_compile arc3_baseline.py competition_agent.py test_arc3_baseline.py
python test_arc3_baseline.py
```

The authored checkpoint was run with CPython and passed 11/11 tests. That is synthetic/offline evidence only; it is not an ARC score.

## Run in the official harness

Use a clean checkout of the pinned official agents repository, then copy the two agent files into `agents/`:

```bash
cp arc3_baseline.py /path/to/ARC-AGI-3-Agents/agents/arc3_baseline.py
cp competition_agent.py /path/to/ARC-AGI-3-Agents/agents/sol_arc3.py
```

Register `SolArc3` in the official `agents/__init__.py` / `AVAILABLE_AGENTS` mapping as described in the organizer's `create-agent.mdx`. Then, from the official checkout after its normal environment setup and with an owner-provided `ARC_API_KEY`:

```bash
uv run main.py --agent=solarc3 --game=ls20
```

The adapter uses only the official `FrameData`, `GameAction`, `GameState`, and `Agent` surfaces. `SOL_ARC3_MAX_ACTIONS` optionally changes the default 240-action ceiling.

## Next measured iterations

1. Replay against the organizer's public/local game set and record per-game score, action count, state coverage, and failure state.
2. Replace undirected novelty with inferred object-role and goal hypotheses only where replay evidence supports them.
3. Add action-effect models for movement/interact/coordinate actions, preserving unknown-game generality.
4. Build the Kaggle notebook wrapper from the exact accepted competition environment and run it only on an authenticated participant surface.
5. Publish any actual score with game/version, environment commit, notebook version, and raw run receipt. Never infer a leaderboard score from synthetic tests.

## Data and submission boundary

No competition-only dataset is committed here. Do not upload restricted challenge material to hosted model APIs. Registration, rule acceptance, Kaggle execution, and final submission are separate authenticated account actions and are not claimed by this package.
