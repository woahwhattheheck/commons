# ARC3 SAGE ablation lab

This additive lab executes the experiment plan already checked into `competitions/arc-agi-3-2026/EXPERIMENT_PLAN.md` as a strict paired design. It is **not** an official ARC/Kaggle scorer and it never upgrades mock results into provider evidence.

## One-factor variants

Every non-baseline row differs from `sage_full` in exactly one factor:

1. `settled_frame` — collapse each observation to its settled frame before learning.
2. `uniform_random` — spend the same real-action budget on deterministic uniform candidate probing instead of SAGE's information/model-guided policy.
3. `all_grid_coordinates` — expose every board cell as an `ACTION6` candidate instead of SAGE's object-centroid/bbox/corner reduction.
4. `reset_between_levels` — discard learned world/skill state before each translated synthetic level rather than transfer knowledge.

The synthetic `LevelSwitchDoorEnv` preserves hidden action semantics across translated layouts and deliberately changes object coordinates. This is a **transfer stress test**, not evidence of official cross-level generalization.

## Run

From `competitions/arc-agi-3-2026/ablation`:

```bash
python run_ablation.py --seeds 24 --levels 3 --source-revision <git-sha> --output report.json
python verify_report.py report.json
```

The report requires a complete Cartesian product of variants × seeds × levels, rejects duplicates/missing trials, emits aggregate metrics plus paired deltas against the baseline, and SHA-256 binds the exact plan and trial rows. Suggested competition work should use the same manifest discipline on public-development/public-validation traces and keep provider-confirmed score evidence separate.

## Metrics

- win rate and actions (all / winning trials)
- no-effect action rate
- first-progress action
- animation frames actually retained
- coordinate candidates considered and coordinate actions taken
- skill replay count / learned-skill count
- paired discordant wins and action deltas for pairs where both variants win

No p-value or causal language is emitted by the harness. A measured delta says what happened on the bound trials; it does not assert why or imply official leaderboard performance.
