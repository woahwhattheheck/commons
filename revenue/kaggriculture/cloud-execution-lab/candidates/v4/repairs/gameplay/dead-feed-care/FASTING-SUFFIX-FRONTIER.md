# FASTING suffix frontier — earlier same-day no-CARE admission

Status: **RESEARCH-ONLY FIXED-TAPE SUCCESSOR / DEFAULT-OFF / NO NATIVE ACTIVATION CLAIM**.

The canonical FASTING lane has a real source theorem but its current-native mechanism gate is intentionally hour-23-only. The native seed-17 census is therefore `COLD`: no natural eligible rows were observed. This file does not reinterpret that cold result as a kill.

## What this successor tests

`trace_no_care_feed_skip.py` asks whether the hour-23 restriction itself is suppressing reachability. For a current FEED earlier in the day, the caller supplies the complete already-materialized observation/action suffix through hour 23. A candidate is admitted only when:

1. the same current state/action passes every existing FASTING mechanical guard after changing only the step label to the same day's hour 23;
2. the suffix is gapless, same-player, same-day, and covers every remaining callback through EOD;
3. no later authored FEED or CARE row targets that animal site.

The synthetic step is not a forecast and does not alter the animal, inventories, positions, CARE state, market rows, or day. It only reuses the canonical helper's exact animal validity, one-missed-EOD, pending-CARE production-boundary, duplicate-FEED, physical-WHEAT, and type/configuration guards. The explicit suffix supplies the one guarantee hour 23 previously gave for free: nothing later that day will feed or care for the site.

The counterfactual builder rewrites exactly one certified current FEED to PASS. It is intended for complete-interpreter replay against that fixed suffix, not direct runtime composition.

## Why reject later FEED as well as CARE

A later same-site FEED would change which actor consumes WHEAT and overlaps the existing W2 redundant-FEED/CARE salvage lane. This frontier declines that ambiguity rather than stealing custody from `dead_feed_care.py`.

## What this can tell us

Run a replay/current-native trace census before any controller work:

- `hour23_fast_candidates`: existing FASTING opportunity count;
- `suffix_certified_earlier_candidates`: opportunities recovered solely by proving the remaining same-day suffix;
- candidate hour/species/site distribution;
- full-interpreter product/fertilizer/CARE/escape equivalence for each isolated rewrite;
- WHEAT consumption and terminal both-seat economics.

If earlier certified candidates remain zero, the starvation seam is genuinely unreachable under the current route rather than merely hidden by the hour-23 gate. If they exist, they become a research/economic frontier; they do **not** authorize a live predictor or scheduler.

## Boundaries

- Existing `uncared_eod_feed_skip.py` remains the native/activation owner.
- Existing next-day stock/re-feed custody in the guarded FASTING path is not weakened or bypassed.
- Blanket alternate-day feeding remains economically rejected when CARE is active.
- No feature key, runtime/default/config/COMPOSITION/archive/Kaggle mutation is introduced.
