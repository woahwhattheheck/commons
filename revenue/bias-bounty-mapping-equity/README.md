# Bias Bounty Mapping Equity — deterministic scorer carrier

This directory is a reproducible implementation carrier for the Zindi / Humane Intelligence **Bias Bounty Mapping Equity Challenge**. It now contains two intentionally separated stages:

1. `mapping_equity_aggregate.py`: streams the challenge-provided Source Cooperative package into tract aggregates while recording the exact source/filter/CRS policy.
2. `mapping_equity.py`: turns those aggregates into the organizer-published coverage-gap formula, compiles a minimal `GEOID,coverage_gap_score` submission, and emits a deterministic scorer receipt.

Neither stage registers an account, submits to Zindi, or claims any leaderboard result, award, payment, or revenue.

## Paid target

Public challenge: `https://zindi.world/competitions/bias-bounty-mapping-equity-challenge`

Public dataset/readme: `https://source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge/`

At carrier creation the challenge advertised a $10,000 USD pool, with $4,500 / $2,500 / $1,500 leaderboard awards, a $1,000 Best Bias Discovery award, and a $500 Best Documentation award, closing 2026-10-31. The public dataset pins Overture to release `2026-08-19.0`.

## What the scorer binds

For each census tract, upstream aggregation must produce exactly these columns:

```text
GEOID,
overture_road_length,tiger_road_length,
overture_buildings,microsoft_buildings,
overture_fire,hifld_fire,
overture_ems,hifld_ems,
overture_schools,hifld_schools,
overture_places,cbp_establishments
```

`GEOID` is an **11-digit string**. Do not allow a spreadsheet or dataframe import to coerce it to an integer; leading zeroes are part of identity.

For any observed/reference pair with a positive reference, the component deficit is:

```text
1 - min(1, observed / reference)
```

A zero reference makes that component **undefined**. Undefined components are omitted from the relevant mean; they are never silently converted to either zero or one.

The public challenge methodology maps those quantities as follows:

- **Transport:** Overture length for named highways in classes `motorway`, `trunk`, `primary`, `secondary` versus TIGER/Line roads with MTFCC `S1100` or `S1200`.
- **Buildings:** Overture building count versus Microsoft US Building Footprints count. ACS housing is context only and is **not** the denominator.
- **Critical facilities:** per-type gaps for HIFLD fire stations, EMS stations, and public schools; the HIFLD half is the mean of whichever reference types are defined in that tract.
- **Establishments:** all Overture places versus Census County Business Patterns establishment count.
- **POI:** mean of the defined HIFLD half and CBP half.
- **Composite:** mean of the defined transport, building, and POI components.

A tract for which all three top-level components are undefined is refused rather than assigned a fabricated score.

## Why the aggregation boundary is explicit

The expensive/geospatial stage and the scoring stage have different failure modes. Keeping tract aggregation as an explicit artifact makes the following auditable before any provider submission:

1. Overture release and feature filters.
2. TIGER MTFCC filter and length CRS.
3. Point/polygon tract assignment and boundary policy.
4. County Business Patterns tract allocation method supplied by the challenge.
5. Exact authoritative tract universe from the challenge sample submission.
6. No accidental use of reference/answer columns as scorer inputs.

The aggregate reader accepts **only** the schema above. A `coverage_gap_score` or other extra column is rejected; this prevents a published reference-score artifact from silently contaminating the scored pipeline. That separation is deliberate: the challenge rules reserve disqualification authority for data leaks or practices that compromise solution value, so the aggregation runner never reads any `coverage-gap` answer artifact.

## Four-region public-data aggregation runner

`mapping_equity_aggregate.py` operates only on the official public Source Cooperative objects and fixes the challenge regions as:

```text
eastern-ok
maricopa-az
northern-ca
south-central-tx
```

The authoritative sample-submission file is the membership and ordering source for every region. Expected scored row counts are 1,192 / 1,593 / 591 / 6,003 respectively (9,379 total).

The runner binds the current public methodology literally:

- Overture release: `2026-08-19.0`.
- Every shipped spatial layer is treated as CRS84 lon/lat.
- Road pieces are clipped to each tract and transformed to EPSG:5070 with DuckDB `always_xy := true` before length is measured. This prevents the silent axis-order `inf` failure documented by the dataset publisher.
- Overture roads are restricted to `motorway`, `trunk`, `primary`, `secondary`; TIGER is restricted to `S1100`, `S1200`.
- Building polygons are assigned by `ST_PointOnSurface`; an exact boundary hit deterministically selects the lowest GEOID, preventing double counting.
- Point layers use `ST_Intersects` with the same lowest-GEOID tie policy.
- Overture POI categories are `fire_department`; `ambulance_and_ems_services`; and the school set `elementary_school`, `middle_school`, `high_school`, `school`, `private_school`, `public_school`.
- Census CBP is consumed from the challenge-provided tract-keyed `cbp_estab` field; it is not reallocated or augmented by external data.

Inspect the complete deterministic source/query plan without DuckDB or network access:

```bash
python mapping_equity_aggregate.py plan > aggregation-plan.json
```

Real execution uses DuckDB 1.5.4 and its open-source `httpfs` + `spatial` extensions:

```bash
python -m pip install -r requirements-runner.txt
python mapping_equity_aggregate.py run \
  --output-dir aggregates \
  --receipt aggregation.receipt.json
```

That produces one exact-schema aggregate CSV per region plus a receipt that records:

- every challenge object URI and a URI identity digest;
- observed HTTP object metadata (`ETag`, length, last-modified) when the source endpoint supplies it;
- DuckDB / extension identity;
- exact CRS, feature-filter, boundary, and CBP policy;
- expected scored row counts;
- SHA-256 for every aggregate CSV;
- explicit false claims for Zindi submission, score, rank, prize, payment, and revenue.

Verify later without rerunning geospatial joins:

```bash
python mapping_equity_aggregate.py verify \
  --output-dir aggregates \
  --receipt aggregation.receipt.json
```

## Run the proof suites

From this directory:

```bash
python -m py_compile mapping_equity.py mapping_equity_aggregate.py test_mapping_equity.py test_mapping_equity_aggregate.py
python -m unittest -v test_mapping_equity.py test_mapping_equity_aggregate.py
python -O -m unittest -v test_mapping_equity.py test_mapping_equity_aggregate.py
python mapping_equity_aggregate.py plan | python -m json.tool >/dev/null
```

Build a submission from a tract aggregate CSV plus the challenge sample-submission file used only as the authoritative GEOID universe:

```bash
python mapping_equity.py build \
  --aggregates aggregates.csv \
  --authoritative SampleSubmission.csv \
  --output submission.csv \
  --receipt submission.receipt.json
```

Verify later without recomputing geospatial joins:

```bash
python mapping_equity.py verify \
  --submission submission.csv \
  --receipt submission.receipt.json \
  --authoritative SampleSubmission.csv
```

Outputs are create-exclusive. A pre-existing output path is refused rather than overwritten.

## Submission discipline

Before a real Zindi submission, separately record:

- exact challenge dataset object identities / ETags / byte hashes where available;
- exact Overture release (`2026-08-19.0` for this carrier generation);
- aggregation code/version and environment;
- tract aggregate file SHA-256;
- authoritative sample-submission SHA-256;
- scorer source commit;
- generated CSV and receipt SHA-256;
- challenge account/team identity and actual provider submission ID only after the provider returns it.

Do not convert local validation into a leaderboard, eligibility, prize, payment, or revenue claim. Entry into the challenge constitutes acceptance of Zindi's rules; account joining, team formation, or submission is therefore an owner/provider action outside this source carrier.
