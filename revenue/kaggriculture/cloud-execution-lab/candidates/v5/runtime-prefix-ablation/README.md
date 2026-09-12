# Submitted V3.1 → V4 runtime-prefix causal ablation

Evidence-only V5 carrier. This does **not** propose restoring engine-incorrect full-queue reasoning in production. It asks whether one always-on submitted-V4 correctness family contributed to the measured V4 < V3.1 strength regression.

## Exact source delta

Both submitted configs enable `seed`, `operating_stock`, and `redundant_hire`. Submitted V3.1 source commit `a90d888f03987ef0b35cfd20ec3519c6144db08a` / `titan_runtime.py` Git blob `a10ad66f990c430dc27299f518b04ea3fde9e39b` reasons over the authored full market queue in those three wrappers.

Submitted V4 source commit `4af1113154e78c662780e6658cd920daac7902e3` / runtime Git blob `998bf5da08f61f82eafaf5750c8a86fc3adad7fb` changes the wrappers to the official engine's executable raw prefix:

- `_seed_selected`: BUY_SEED activation, edit detection, and downstream dependency scan use `market[:maximum]`;
- `_operating_stock_selected`: activation and helper input are prefix-only, then the raw suffix is reattached unchanged;
- `_redundant_hire_selected`: HIRE activation uses only the executable prefix.

The engine-correctness motivation is legitimate. Historical ORDERBUDGET/PREFIX work also made the risk explicit: a row at raw slot `cap+` is not executed. What was not established for this submitted-version delta is playing-strength causality.

## Treatment

`ablate_runtime_prefix.py` requires both exact historical runtime sources. It replaces exactly those three complete submitted-V4 method spans with the exact submitted-V3.1 method spans and proves a skeleton equality invariant: every source byte outside the three methods remains submitted V4. The output is compiled and the receipt binds both historical blobs, the treatment hash, per-method pre/post hashes, and the submitted-V4 archive authority `4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b`.

This preserves submitted-V4 frozen-seller behavior (including E05/E08), the four later config flags, feed-stock, early-capital, market-pressure, finalizer order, timeout logic, package topology, and every other runtime method.

## Engagement authority

The V3.1/V4 delta is evaluated at **internal wrapper inputs**, not at the final returned action. The wrappers under test can themselves delete, reorder, or rewrite suffix rows, so a zero scan of final returned actions cannot prove that the family never engaged upstream.

`engagement_gate.py` makes that provenance explicit:

- `classify_wrapper_input(stage, action, cfg)` evaluates the exact action entering one of `seed`, `operating_stock`, or `redundant_hire` and uses only that stage's real V3.1/V4 gate/scope delta;
- `classify_final_action_hint(...)` is positive-only steering evidence; it always records `authorizes_global_cold=false`;
- `final_action_census(...)` returns `INCONCLUSIVE_NO_FINAL_ACTION_WITNESS`, never `COLD`, when no downstream hint appears.

The older `classify_structural_candidate()` in `ablate_runtime_prefix.py` is retained only as a coarse downstream hint for compatibility. It is **not** a cold-authority surface.

A future mounted execution must either capture the exact per-stage wrapper inputs with a transparent/action-equivalent probe, or skip the heuristic and run a small matched CTRL/ABLATE native panel. Only a real CTRL/ABLATE action/receipt divergence proves natural engagement. Absence on a finite matched panel may retire that tested panel, but must not be generalized to a global family `COLD` verdict without complete wrapper-input authority.

## Focused contracts

```bash
cd revenue/kaggriculture/cloud-execution-lab/candidates/v5/runtime-prefix-ablation
python -B -m py_compile ablate_runtime_prefix.py engagement_gate.py test_ablate_runtime_prefix.py test_engagement_gate.py
python -B -m unittest -v test_ablate_runtime_prefix.py test_engagement_gate.py
python -O -B -m unittest -v test_ablate_runtime_prefix.py test_engagement_gate.py
git diff --check
```

The suite authenticates both historical runtime blobs/configs, proves all three wrappers are enabled in both submitted versions, proves exact V3.1 method postimages and exact-V4 non-target bytes, kills source-authority drift, exercises stage-specific gate/scope candidates, and proves a zero final-action census remains non-authorizing.

## Boundaries

No current runtime/default/config/archive/release pointer/Kaggle mutation. No V5 promotion claim. A positive causal result is input to the single V5 composition. A negative result must be scoped to the evidence actually observed rather than inferred from a downstream surface that the treatment itself can rewrite.
