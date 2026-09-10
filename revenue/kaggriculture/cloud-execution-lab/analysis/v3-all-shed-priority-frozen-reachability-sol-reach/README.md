# TITAN V3 all-shed priority: frozen-path reachability and rejection

## Disposition

**Retire the current scheduler-only carrier and reject this factor on current V3.**

The live canonical configuration selects `consumer: frozen`. Its returned-action path is:

```text
main.py::agent
  -> FinalPressureAgent(TitanAgent).act
  -> TitanAgent.transform_selected
  -> FrozenSelected.transform
```

Both `scheduler.py` and `frozen_selected.py` contain independent copies of the positive-shed target traversal. A patch confined to `scheduler.py` therefore cannot reach the current canonical returned action. This package proves that boundary, materializes the predecessor and live seams separately, and records the current-control economics.

## Exact source custody

| Item | Identity |
|---|---|
| Current archive | `sha256:5f6a4153e502713b9467776eafe7464af650584149173ce7507a31a1b2af60f1`, 428,158 bytes |
| `SOURCE.json` | `sha256:3249398b6aa56d1b3464db8d0cce5aa35e8edee397fc4341bd710d1f74dad469` |
| `main.py` | `sha256:c4c22d0f2b1071cadf6a9f74effccc8cb20ea9f4d10ca1cf9f1fe57351709dc1` |
| `titan_runtime.py` | `sha256:da391af2dbdec0f6e4a25749ed539cdd39578ace8861c0e225b5fbfef90d75a8` |
| `frozen_selected.py` | `sha256:5ca1bc39efed756de71207f46926744ea69f9d2f300dd7b9c1a8cc4dbefeb9ef` |
| `scheduler.py` | `sha256:00d72a5c6b511e73ed1923ea402c4a36e0f9490f3b4c177490ddc72440f4a64a` |
| Arlene | `sha256:1dc166ae2bf0c56a44fac4482f469b8812968c4cb32459cb9860f5077897a7d4` |

`materialize.py` verifies all 110 archive members against `SOURCE.json`, binds the exact call path, and creates three disjoint closures:

1. `control`: no changed member;
2. `scheduler_only`: only `scheduler.py` changes;
3. `frozen_priority`: only `frozen_selected.py` changes.

The two candidates use the same admitted historical traversal expression: existing pending intent, inherited baseline SELL first-seen order, then remaining `PRODUCTS`. Positive-shed target membership and quantities remain identical.

## Current-control result

Official interpreter; canonical `main.py::agent`; 8 seeds × 2 mirrored seats against frozen Arlene; 719 candidate actions per game; all 16 cells complete.

| Arm | Action-changed cells | Mean own | Median own | Negative own cells | Mean margin | Verdict |
|---|---:|---:|---:|---:|---:|---|
| `scheduler_only` | 0 / 16 | 0 | 0 | 0 | 0 | Dormant predecessor |
| `frozen_priority` | 2 / 16 | -0.75 | 0 | 2 | -4.875 | Reject |

Both live divergences are the mirrored cells for seed `2609097304`. Each moves candidate cash by `-6`, rival cash by `+33`, and margin by `-39`. There are no outcome flips, but the admission contract requires positive mean own cash, no negative paired cell, positive mean margin, and nonnegative opponent×seat strata. The live arm fails those economic gates.

The prior frozen-V2 evidence was real for its tested predecessor closure. It is not promotion authority for this current frozen-consumer stack.

## Reproduction

From the repository root:

```bash
analysis=revenue/kaggriculture/cloud-execution-lab/analysis/v3-all-shed-priority-frozen-reachability-sol-reach
python "$analysis/test_reachability.py"
python "$analysis/materialize.py" --output /tmp/titan-priority-reachability
```

`analyze.py` consumes three complete evaluator JSON files and fails closed on duplicate cells, partial grids, evaluator/engine/opponent drift, wrong entrypoint, wrong seed grid, incomplete lifecycle, missing action digests, non-finite scores, or candidate-score orientation errors.

## Boundary

This is negative evidence and a predecessor-killing contract. It does not change the canonical runtime, `TITAN-CONFIG.json`, archive, pointers, provider state, Kaggle state, or submission state. It does not authorize a V1 opponent extension after the current Arlene gate has already produced negative paired cells.
