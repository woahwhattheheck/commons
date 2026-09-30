# H3/S420 current-ABI SELL carrier

This extends the existing `exec-pace-2` V4 family; it does not create a sibling SELL controller or a second V4.

Riot's earlier materialization reported `{sale_horizon=3, no_late_sale_advance_step=420}` positive in 16/16 cells with mean paired margin delta +$441. That receipt is historical provenance only: current `titan_runtime.Features` has no such fields, so adding those names to production JSON would fail construction rather than activate the candidate.

`compose_h3s420_current.py` pins both canonical current SELL inputs by Git blob and performs two edits only:

1. `scheduler.py`: inherited baseline horizon `8 -> 3`; current event-aware market-service/unit extensions, day/checkpoint bounds, capacity, funding and feasibility remain intact.
2. `frozen_selected.py`: at step >=420, if a non-forced optimizer plan would SELL more **now** than its unchanged reference, retain the reference. Forced-feasibility repairs are never suppressed. Producer-owned sales and future timing that does not pull quantity into the current step remain untouched.

The composer writes candidate source files. It does not alter production, defaults, `TITAN-CONFIG.json`, archive artifacts, or Kaggle output. LOOM/current native assembler remains the only composition/release sink.

## Acceptance

```bash
python -B test_h3s420_current.py
python -O -B test_h3s420_current.py
python -B compose_h3s420_current.py \
  ../../../../../scheduler.py ../../../../../frozen_selected.py /tmp/h3s420 \
  --receipt /tmp/h3s420.json
```

The authored suite is 8/8 PASS in both normal and `-O`. Exact input pins were reverified on canonical main immediately before publication: scheduler Git blob `a483b24dd72b580d7d8811636b54d2d44f391575`; frozen-selected Git blob `fc7baf5c179818a55037f6a61d92984d81d1a21c`.

Promotion is `NOT_ASSESSED` until the generated pair is consumed by the existing current-native assembler and tested OFF vs ON in both seats across current starter + pressure/stronger opponents. Required evidence: exact source/output identities, engagement/suppression counts, callbacks/fallbacks, deadline behavior and terminal own/rival margin. Do not quote +$441 as current-ABI EV.
