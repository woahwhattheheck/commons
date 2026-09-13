# Mapping Equity public-data aggregation carrier

This directory is the data execution layer for the merged Mapping Equity scorer in the parent directory. It is intentionally narrow: read only the public challenge objects needed for the scored formula, produce one leak-safe tract aggregate row per authoritative sample-submission GEOID, and stop hard on schema drift or non-finite geometry math.

## Authority and data version

Public product: `https://source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge/`

Challenge: `https://zindi.world/competitions/bias-bounty-mapping-equity-challenge`

The current product pins Overture Maps release `2026-08-19.0`, GeoParquet CRS `OGC:CRS84`, and documents DuckDB `1.5.4` for its remote examples and geometry gotchas. This carrier pins the same DuckDB version.

The four scored universes are fixed from each region's `*-sample-submission.csv`: `eastern-ok` 1,192; `maricopa-az` 1,593; `northern-ca` 591; `south-central-tx` 6,003. GEOID is always text. Maricopa's leading `04` must survive, and its one New Mexico member `35023970000` is intentional.

## Leak boundary

The product publicly contains Reliabl's `<region>-coverage-gap.csv` reference answers. **This runner will not read them.** Any source URI containing `coverage-gap`, `coverage_gap`, `reference-score`, or answer-key variants is rejected. The only submission-shaped input is `<region>-sample-submission.csv`, and the generated query projects **only `GEOID`** from it to establish the authoritative tract universe. The placeholder score column is ignored.

No ACS layer or HIFLD hospital layer feeds the scored aggregates. ACS is contextual only; hospitals are explicitly excluded from the published POI formula.

## Exact source objects

For each region the runner permits only:

- `reference/<region>/<region>-sample-submission.csv` — authoritative scored GEOIDs only;
- `strata/<region>/<region>-census-tracts.parquet` — tract geometry;
- Overture `roads`, `buildings`, `pois`;
- Census TIGER roads and CBP;
- Microsoft buildings;
- HIFLD fire stations, EMS stations, and schools.

`aggregate.py plan --region ...` emits the full URI registry, required source columns, source/data pins, query hash, geometry policy, and output contract without importing DuckDB or touching the network.

## Geometry rules that must not be relaxed

The publisher warns that DuckDB spatial operations can fail **silently** on this data:

1. Every layer is lon/lat `OGC:CRS84`. `ST_Transform(..., 'EPSG:4326', 'EPSG:5070')` without `always_xy := true` can return infinite coordinates. The runner transforms with `always_xy := true` and executes a synthetic road-length smoke check before the real query.
2. `ST_Length_Spheroid(geometry)` on lon/lat order can return `NaN`; the publisher requires coordinate flipping for that function. This runner avoids the trap entirely by transforming to EPSG:5070 with explicit XY order, clipping road geometry to each tract, then measuring projected intersection length.
3. GeoParquet `bbox` filters use **all four overlap comparisons** before exact `ST_Intersects` / containment. Two-comparison corner tests silently drop edge-straddling features.
4. Every final numeric value must be finite and nonnegative. A single `NaN`/`inf` aborts publication.

Roads are clipped to tract geometry before length measurement, so a cross-tract segment contributes only its within-tract length. Buildings are assigned once by `ST_PointOnSurface(footprint)` strictly within a tract. Point POIs/facilities are assigned by strict containment. These policies are recorded in every plan/receipt rather than hidden in an implementation detail.

## Published scoring filters

- Overture road classes: `motorway`, `trunk`, `primary`, `secondary`.
- TIGER MTFCC: `S1100`, `S1200`.
- Overture fire: `categories.primary = fire_department`.
- Overture EMS: `ambulance_and_ems_services`.
- Overture school categories: `elementary_school`, `middle_school`, `high_school`, `school`, `private_school`, `public_school`.
- CBP denominator: `cbp_estab` (the package's default business-address weighting).
- All Overture places count toward the CBP half.

## Offline proof

No DuckDB or network is needed for the plan/contract suite:

```bash
python -m py_compile aggregate.py test_aggregate.py
python -m unittest -v test_aggregate.py
python -O -m unittest -v test_aggregate.py
python aggregate.py plan --region northern-ca --sql > northern-ca.plan.json
```

The tests bind the current object layout, exact filters, all-four bbox comparisons, `always_xy`, clip-before-length behavior, nested POI category probe, output schema, tract counts, leading-zero custody, finite/nonnegative gates, answer-artifact denial, deterministic plans, and create-exclusive output publication.

## One-region real-data run

Use an ordinary connected environment with Python and DuckDB `1.5.4`. DuckDB will install/load its public `httpfs` and `spatial` core extensions; the challenge bucket requires no account or credentials.

```bash
python -m pip install 'duckdb==1.5.4'
python aggregate.py run \
  --region northern-ca \
  --output northern-ca.aggregates.csv \
  --receipt northern-ca.aggregates.receipt.json
```

Start with Northern California because its reference package is the smallest (~0.45 GB). The query range-reads cloud-native Parquet; it does not intentionally bulk-download the corpus.

Before aggregation, the runner `DESCRIBE`s every current object and refuses missing required columns. It also probes the Overture nested `categories.primary` field and runs the axis-order metric smoke test. The receipt records the exact allowed URIs, schema descriptions/digests, query hash, DuckDB pin, Overture release, smoke-test length, row count and output SHA-256.

This cloud development turn cannot resolve outbound DNS to install DuckDB, so it does **not** claim a real-data execution. That is a runtime/environment limitation, not a data-access or challenge-permission limitation.

## Four-region execution and scorer handoff

After one clean region receipt, run all four independently so a failure cannot contaminate the others:

```bash
for r in eastern-ok maricopa-az northern-ca south-central-tx; do
  python aggregate.py run --region "$r" \
    --output "$r.aggregates.csv" \
    --receipt "$r.aggregates.receipt.json" || exit 1
done
```

Then feed each aggregate CSV into the already-merged parent `mapping_equity.py build` command together with the same region's sample submission as the authoritative GEOID universe. Do not convert a local aggregate/scorer success into a Zindi submission, leaderboard, prize, award, payment, or revenue claim without provider evidence.
