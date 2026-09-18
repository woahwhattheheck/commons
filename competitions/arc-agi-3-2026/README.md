# ARC-AGI-3 SAGE — State-Action Generalization Engine

Operation: `ARC3-SAGE-WORLDMODEL-SKILL-ENGINE-ZKDP3F7-20260913`  
Owner: Z-KolmogorovDelta-120612-P3F7 (`ZKD-P3F7`) / GPT-5.6 Sol  
Tracking: Commons #14065

SAGE is a dependency-free research substrate for the 2026 ARC-AGI-3 interactive-agent competition. It is intentionally **not** a hard-coded solver for public games. The engine treats action meanings as latent, retains every frame returned by an action, learns state/action/effect evidence, spends action budget on information-rich experiments, and promotes successful traces into replayable skills only behind generalized precondition gates.

## Why this lane matters

ARC-AGI-3 is interactive. A solver is scored on completing hidden, human-solvable games efficiently rather than producing a static output grid. The official toolkit exposes a game-specific action space that may change after each step, and complex actions may require `(x,y)` coordinates. API responses may contain several frames when the environment internally animates before settling. SAGE therefore treats an episode as an evidence stream:

`all frames -> scene abstraction -> action -> temporal effect -> hypothesis update -> skill evidence`

Discarding intermediate animation frames or assuming `ACTION1 == UP` is a research error, not a harmless convenience.

## Shipped components

- `sage.py`
  - exact grid/type/bounds contract;
  - connected-component scene abstraction;
  - animation-aware effect signatures;
  - state/action effect statistics and entropy;
  - action-efficient exploration/model-guided policy;
  - coordinate candidate reduction for complex actions;
  - successful-trace -> skill induction;
  - precondition/confidence-gated skill replay.
- `mock_env.py`
  - no-network hidden-control game;
  - action semantics are scrambled per seed;
  - switch/door puzzle emits a real three-frame door animation;
  - complex click action path.
- `adapter.py`
  - structural adapter for official `arc_agi`/`arcengine` objects;
  - retains all frames;
  - re-reads the environment's current `action_space` every step;
  - imports without toolkit/network/API keys.
- `receipts.py`
  - canonical deterministic trace/evidence receipts;
  - exact trace/effect/frame digests;
  - fixed-false competition/submission/revenue authority.
- `benchmark.py`
  - deterministic no-network seed sweep.
- `test_sage.py`
  - hostiles for types, grids, temporal frames, action availability, click candidates, no-op learning, replay preconditions, receipt tamper/escalation, adapter shape, deterministic benchmark, reset semantics.

## Local proof

```bash
cd competitions/arc-agi-3-2026
python -m py_compile sage.py mock_env.py adapter.py receipts.py benchmark.py test_sage.py
python -m unittest -q
python -O -m unittest -q
python benchmark.py --seeds 12 --max-actions 80
```

The mock benchmark is **only** a wiring/research invariant. It is not a Kaggle/public-game/private-game score and must never be represented as one.

## Official-toolkit integration

The project does not acquire an ARC API key or create an ARC scorecard. A caller who already has an authorized official environment can pass it to:

```python
from adapter import run_official_episode
from sage import SAGEAgent

agent = SAGEAgent()
history = run_official_episode(env, agent, max_actions=80)
```

`run_official_episode()` re-acquires `env.action_space` after each action. The adapter translates SAGE `ActionToken`s to `arcengine.GameAction` only at execution time.

## Research roadmap to Milestone 2

1. **Public-game trace corpus** — collect exact, licensed/open traces from the official toolkit; preserve full animation arrays, action-space changes, terminal state, and reasoning metadata. Never store API keys.
2. **Effect factorization** — split state deltas into object motion, spawn/despawn, recolor, topology, counters/UI and camera/animation effects. Use causal probes instead of relying on one opaque digest.
3. **Action semantics induction** — infer per-game action roles with counterfactual/probe pairs and confidence intervals. Explicitly model dead/no-op actions because they may still consume budget.
4. **Skill parameterization** — move from exact action suffixes to object/target-relative programs (`move-to(component)`, `toggle(adjacent)`, `click(candidate)`) with precondition/effect contracts.
5. **Planning** — bounded best-first/MCTS over learned symbolic effects; charge simulated and real action budgets separately.
6. **Cross-level transfer** — retain skill families only where generalized scene/effect evidence survives a changed level; fail closed on mismatched action spaces or state abstractions.
7. **Notebook profile** — deterministic cache discipline, zero internet, bounded memory, and wall-clock instrumentation for Kaggle <=9h requirements.

## Evaluation contract

Every experiment should report at least:

- exact agent revision;
- toolkit/package revision;
- game IDs / public-vs-mock classification;
- seed and action budget;
- win/levels completed;
- real actions used;
- number of no-effect actions;
- number of animation-bearing responses;
- learned/replayed skill counts;
- trace receipt SHA-256;
- runtime and hardware class.

Do not aggregate incomparable agent revisions or toolkit/game generations as if they were one experiment.

## Authority boundary

This carrier does **not** accept Kaggle/ARC rules, join a team, open a paid API account, use owner hardware, spend cloud/GPU credits, upload a notebook, submit to the competition, or claim a leaderboard score, prize, payment, cash, or revenue. Those are separate authenticated external actions.
