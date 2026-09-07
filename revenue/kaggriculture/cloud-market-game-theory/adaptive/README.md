# Adaptive complete-plan recourse

This executable T15 experiment consumes the current integrated selected parent
from PR9997 and the existing ASH continuation consumer. `AdaptiveTransform`
constructs no production controller. `Agent.act` calls one
`IntegratedSelectedAgent` and passes its action and current projection ledger
to the transform. The original T15 v1/v2 files and selected SELL are unchanged.

`compile_policy(model, plans, quantity, streams, branch, absorption)` requires
complete feasible plans with an identical executed prefix. It groups whole
correlated streams by shared product inventory at the future branch. Grouping
is intentionally coarse: ignored public fields retain additional hypotheses;
equal inventory never identifies rival cash receipts, exact quantity or slot.
Only the real next observation selects a suffix. Unrepresented observations
return the entire supplied fallback. Floor-price nonadmission stays grouped.

Each information set selects a row only if every included relative margin is
nonnegative, then maximizes its minimum and sum. Baseline wins exact ties.
This is an explicit weak-dominance objective. The sum is a deterministic
tie-break, not a probability-weighted expectation. Alpha remains zero. The
finite conditional bound applies to included complete streams and complete
execution, not every possible opponent or an individual full-game promise.

Current constituent and continuation feasibility comes from the existing
selected-action `ProjectionLedger`, including ordered cash, stock, production
arrivals, committed capacity, operating resources and order slots. ASH retains
its existing retry/skipped-date behavior. Previously emitted prefixes remain
unchanged; the selected suffix persists. Other products and unit fields are
preserved. Future route changes can retire a commitment to the supplied action.

## Executed development checkpoint

The initial 386 single-burst cases found no adaptive advantage. Three later
constructed EGG cases with correlated two-burst streams match 3,456 serialized
official transitions in both seats. For EGG2 at inventory9998 with BAKERY and
BRUNCH_SPOT, the baseline sells at249. At the real observation242, inventory
10000 selects one sale now and one at249. Its 32-column causal vector is zero
except +1/+2 on two correlated paths; every static alternative has a losing
column. The same public observation with different simulator-private stock
produces the same decision. An unknown inventory takes the entire fallback.

Fresh development9943001 has eight completed full games, both seats versus
frozen SELL. The current integrated control scores103532 own/103443 rival.
The fixed-plan arm scores103531/103444; static weak dominance and adaptive each
score103531/103449. All remain wins. At reached step656, the adaptive arm
selects WOOL2 for661 from new shared inventory9906. That is an executed economic
selection, but this seed provides no improvement over the static arm and loses
relative cash against the integrated control. Preserve all four arms.

The initial discovery runtime is preserved byte-exact in
`versions/discovery/runtime.py`; its manifest records all original source hashes.
The next revision changes diagnostic weights and counts projection fallbacks
separately from active-plan retirements; decision logic is unchanged. Six
focused tests cover the explicit objective and the actual ASH/selected-action
integration. The old T11/T12/T15 panels and peer suites were not rerun.

The existing public bank artifact10032525998 is reused for the next broad
development comparison, not exported again. No held result or policy promotion
is claimed at this checkpoint. Exact game receipts are under `results/`.

## Call and reproduce

With the repository-relative dependencies present, `main.py::agent` is the
production entrypoint. Construction and imports occur inside the first call.
The callable economic transform is
`AdaptiveTransform.transform(obs, cfg, supplied_action, ledger=..., offers=...)`.
An offer contains `tree`, `item`, `quantity` and `end`; the compiled tree retains
every original plan and column index. The ledger is the caller's current
`selected_action_sell.ProjectionLedger`, not a second producer.

```sh
python revenue/kaggriculture/cloud-market-game-theory/adaptive/test_recourse.py -v
python revenue/kaggriculture/cloud-market-game-theory/adaptive/panel.py \
  --engine-dir /path/to/engine --opponents /path/to/opponents.json \
  --seeds FRESH_AGREED_DEVELOPMENT_SEED --arms baseline,fixed,static,adaptive \
  --output /path/to/new-results
```

The opponent file maps names to existing runnable entrypoints. Evaluation-only
metadata is removed by the parent Actor before the official interpreter. All
market actions received by the engine are ordinary game actions.

New implementation is Apache-2.0 under the repository LICENSE. T12 flow/scenario
source remains MIT in its original directory; ASH, integrated SELL, producer
dependencies and their original licenses/notices remain in their owned paths.
No upstream source or license was copied into this component or reclassified.
