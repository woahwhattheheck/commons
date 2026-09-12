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

## Cheap-first natural engagement

`classify_structural_candidate()` is intentionally weaker than a gameplay verdict. Given a native returned action, it reports callbacks where the old and new wrappers have different activation gates or observably different scopes because a nonempty raw suffix exists beyond the executable cap. It never authorizes a policy or score claim.

An executor should first run the exact submitted-V4 control and scan all callbacks. If there are **zero** structural candidates, classify this causal family `COLD` and stop without spending paired games. If candidates exist, replay those exact callbacks through CTRL and ABLATE, require a real returned-action/receipt divergence, then run a small matched Apex/Arlene both-seat panel before expanding.

## Focused contracts

```bash
cd revenue/kaggriculture/cloud-execution-lab/candidates/v5/runtime-prefix-ablation
python -B -m py_compile ablate_runtime_prefix.py test_ablate_runtime_prefix.py
python -B -m unittest -v test_ablate_runtime_prefix.py
python -O -B -m unittest -v test_ablate_runtime_prefix.py
```

The suite authenticates both historical runtime blobs/configs, proves all three wrappers are enabled in both submitted versions, proves exact V3.1 method postimages and exact-V4 non-target bytes, kills source-authority drift, and exercises gate/scope candidates for seed, fertilizer operating stock, and redundant HIRE.

## Boundaries

No current runtime/default/config/archive/release pointer/Kaggle mutation. No V5 promotion claim. A positive causal result is input to the single V5 composition; a cold/negative result retires the family rather than creating another policy branch.
