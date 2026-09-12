# TITAN V5 · exact-V4 module-cache namespace-binding ablation

This is an additive causal evidence carrier for the single TITAN V5 line. It does not change production runtime, defaults, `TITAN-CONFIG.json`, `CURRENT`, release archives, or Kaggle submission state.

## Question

Submitted V3.1 and V4 differ in an always-on runtime loader behavior outside the current V5 runtime-prefix ablation. On a path-aware `load(..., cache=True)` hit:

- exact submitted V3.1 runtime Git blob `a10ad66f990c430dc27299f518b04ea3fde9e39b` returns `_MODULE_CACHE[key]` without changing the public module namespace;
- exact submitted V4 runtime Git blob `998bf5da08f61f82eafaf5750c8a86fc3adad7fb` first restores that cached module into `sys.modules[name]`, then returns it.

The V4 behavior was intentionally recovered by historical #12788 as a relocated-package correctness repair. That proves the mechanism is real; it does not establish whether the change helped or hurt submitted-V4 playing strength.

## Causal arms

- **CTRL**: exact submitted V4 archive SHA256 `4d9601552b5e25d02d8a33961c0bed54ed92d032dbcd4a72f6ab8e03515ed21b`.
- **TREAT**: identical archive membership and bytes except `titan_runtime.py`, where the exact V4 cache-hit block is replaced by the exact V3.1 two-line cache-hit behavior.

The transform fails closed unless the runtime preimage is the exact submitted-V4 Git blob and the V4 cache-hit source block occurs exactly once. It then proves `titan_runtime.py` is the only changed archive member.

## Reachability and interpretation

Submitted V4 naturally makes repeated cached loads after cold initialization, including the default-enabled `market_pressure` path (`sell_priority`, pressure policy, and mechanics). A synthetic relocated-package probe in the source contracts proves the two cache semantics can select different sibling module bindings.

That synthetic discriminator is **not** gameplay evidence. Before any playing-strength claim, an authenticated official-engine run must show natural callback/module-origin or returned-action divergence between CTRL and TREAT. If the natural path never diverges, retire this family `COLD`. If it engages, run only a small matched Apex/Arlene both-seat panel first and expand only on matched economic signal.

## Source contracts

`test_module_cache_binding_ablation.py` checks:

- exact one-block rewrite and compileability;
- fail-closed runtime preimage and source-shape custody;
- archive parser path safety;
- exactly one changed archive member;
- a relocated-package namespace discriminator where V4 restores package A on a cache hit while V3.1 semantics leave the competing public binding B in place.

No result from this carrier authorizes restoring the V3.1 loader behavior to production V5 by itself.
