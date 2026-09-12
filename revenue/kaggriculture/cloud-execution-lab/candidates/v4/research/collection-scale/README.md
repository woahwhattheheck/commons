# ASTRA-HERDWORK: collection-scale route census

Status: additive research/tooling inside the sole canonical `candidates/v4` tree.
This package does **not** mutate runtime actions, defaults, configuration, archives,
production pointers, or Kaggle submission bytes.

## Why this lane exists

Muse's `r04_fert_liquidate` gate falsified another late fertilizer-sale timing
lever and reported a much larger production-volume gap: top teams sold roughly
1,200–1,850 units versus current R04 around 368, with R04 collecting about
379 units/game. The follow-up was to isolate a collection-scale mechanism rather
than keep tuning SELL timing.

The official engine source sharpens the terminology: animal product is collected
with `HARVEST`; `COLLECT_FERTILIZER` collects the separate per-animal fertilizer
token. GOOSE/COW/SHEEP hold at most 4/6/6 product units, and an animal escapes
after two consecutive unfed daily refreshes. Therefore a real collection-scale
repair has to distinguish at least acquisition/placement scale, FEED/CARE service,
HARVEST cadence/clipping, and shed/worker capacity. Counting only SELL rows cannot
answer that question.

Current frozen Arlene already contains bounded no-op recovery (`weed_dig`) and
capacity/sell guards, while canonical V4 separately owns narrow animal surfaces
such as H3c GOOSE EOD clipping, S8 EGG-care, feed-stock protection, and LABORFLOW.
HERDWORK must fold into those surfaces if one is causal; it must not create a
second controller.

## Tool

`collection_scale_census.py` loads an exact Git-blob-bound decoded route parent and
emits deterministic per-route structure:

- BUY_ANIMAL quantities by GOOSE/COW/SHEEP;
- animal PLACE counts;
- FEED / CARE / HARVEST / COLLECT_FERTILIZER authored rows;
- EGG/MILK/WOOL authored sell units;
- first/last authored step for each relevant operation;
- per-animal-bought service ratios;
- route-family min/max/spread for acquisition, placement, harvest, feed, care and
  fertilizer collection.

Market scanning respects only the official executable prefix
`market[:maxMarketOrdersPerTurn]`; capped suffix rows do not inflate the census.

The output declares `research_only=true` and `decision_authority=false`. Structural
counts are not a profitability theorem and do not authorize a default flip.

### Current-parent invocation

From `revenue/kaggriculture/cloud-execution-lab`:

```bash
python candidates/v4/research/collection-scale/collection_scale_census.py \
  --parent reference/next-panel/vendor/arlene.py \
  --expected-git-blob bdb9cf58148a3c7961c085f4902759537decabf6 \
  --output /tmp/herdwork-current.json
```

If the parent bytes move, rerun only after rebinding the expected Git blob. The
probe fails closed on drift.

## Local validation performed before publication

Authored bytes were exercised locally:

- `python -m unittest -v test_collection_scale_census.py`: 9/9 PASS
- `python -O -m unittest -v test_collection_scale_census.py`: 9/9 PASS
- `python -m py_compile collection_scale_census.py test_collection_scale_census.py`: PASS

SHA256 before publication:

- `collection_scale_census.py`:
  `f1463c315e2c6cd5dce3ebdbace2c5f8e94310f31a800232e02e11d0b0543326`
- `test_collection_scale_census.py`:
  `4809806151ca21e200ad83c919d946885c1aa10b32cd80451b2960794932f942`

These tests use synthetic decoded route fixtures. This session did **not** execute
the compressed current route bank locally, because connector-readable repository
bytes are not mounted into the Python runtime. The next gate is an exact-parent
probe on the current route bank, followed by a source decision:

1. if acquisition/placement scale is flat and low across routes, fold a bounded
   herd-expansion experiment into the existing animal route/admission family;
2. if acquisitions are already large but HARVEST/service ratios are deficient,
   fold the repair into H3c/S8/feed/service scheduling as appropriate;
3. if route structure is already adequate, reject the premise and move to
   current-native observation/realization loss instead of adding policy.

No new animal policy should be authored before that census.
