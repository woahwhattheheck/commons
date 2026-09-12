# ASTRA-HERDSCALE: fixed-route animal throughput census

This lane is **research-only and policy-inert**. It exists because the 2026-09-12 current-V4 fertilizer gate showed a structural mismatch: sale-side behavior was already moving hundreds of FERT/game while the base route collected only hundreds, far below the four-figure fertilizer volume seen in the stronger traces. Tweaking the seller cannot create fertilizer that the worker schedule never collects.

## Source theorem

The official engine makes fertilizer collection unusually crisp:

* every animal owns one boolean `fertilizer_available` flag;
* EOD refresh sets that flag to `True`;
* one successful `COLLECT_FERTILIZER` clears the flag and adds exactly one FERT.

Therefore the number of scheduled `COLLECT_FERTILIZER` worker rows in an effective fixed route is a hard **upper bound** on fertilizer units that route can collect. Bad positioning, duplicate workers on one animal, missed placement, starvation, or any other no-op can only make realized output lower.

`r04_full_router.py` is also source-bound here: it uses plan 0 for steps 0..143, swaps to the selected route plan at step 144, and forces plan 2 at step 648. The census reconstructs exactly that splice for all 13 routes.

## Run

```bash
python revenue/kaggriculture/cloud-execution-lab/candidates/v4/research/animal-throughput/animal_throughput_census.py \
  --output /tmp/herdscale-current.json

python revenue/kaggriculture/cloud-execution-lab/candidates/v4/research/animal-throughput/test_animal_throughput_census.py
```

The tool authenticates the exact `r01_tapes.py` and `r04_full_router.py` Git blobs before reporting. If either source changes, it fails closed so nobody accidentally cites a stale ceiling.

The JSON reports, for each effective route, scheduled collection ceiling, daily collection slots, animal buys/placements, BUILD/FEED/CARE/HARVEST/DROP/PICKUP cadence, and relevant market rows. That is the admission surface for the next HERDSCALE step: do not add animals unless current-native evidence shows enough executable worker, feed, structure, carry/shed, and sale capacity to service them. HOMESTEAD, LABORFLOW, CARRYBANK, and existing service-semantics lanes remain the authorities for those pieces; this lane does not fork them.

No runtime/default/archive/Kaggle activation is made here.
