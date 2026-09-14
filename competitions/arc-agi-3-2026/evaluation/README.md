# SAGE ablation evidence layer

This directory turns the hypotheses in `../EXPERIMENT_PLAN.md` into paired, replayable evidence without changing the production policy. `core.py` is game-agnostic and dependency-free; `mock_driver.py` exercises all four hypotheses only against `SwitchDoorEnv` and therefore caps every generated claim at `MOCK_EVIDENCE_ONLY`.

The report normalizes the primary metric so positive deltas always favor the candidate, computes a deterministic bootstrap interval plus paired sign-flip test, binds experiment configuration and source revision, and hashes the full receipt. Public-development and public-validation data may use the same compiler, but evidence classes cannot be mixed or relabeled after the fact.

Example from the ARC3 root:

```bash
python -m evaluation.mock_driver --seeds 12 --budget 80 --source-revision "$(git rev-parse HEAD)"
```

No report produced here is a Kaggle/provider score.
