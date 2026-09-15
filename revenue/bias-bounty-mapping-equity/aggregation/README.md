# Mapping Equity public-data aggregation carrier

This directory is the data execution layer for the Mapping Equity scorer in the parent directory. It is intentionally narrow: consume only the public challenge objects needed by the published formula, produce one leak-safe tract aggregate row per authoritative sample-submission GEOID, and fail closed on source, schema, geometry, custody, or numeric drift.

Primary implementation/source credit remains **ZSA-D6P2**. The byte-exact recovered donor is preserved as `_zsa_d6p2_core.py`; the live `aggregate.py` is the hardened authority path. **ZFS-R7** supplied independent alternate-carrier review evidence; **ZHD-K8P3** recovered/finalized M1 and owns the generation/policy fix-forward.

## Authority and data version

Public product: `https://source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge/`

Challenge: `https://zindi.world/competitions/bias-bounty-mapping-equity-challenge`

Pinned runtime/data contract:

- DuckDB `1.5.4`
- Overture release `2026-08-19.0`
- source CRS `OGC:CRS84`
- metric CRS `EPSG:5070` with `always_xy := true`
- authoritative scored rows: eastern-ok `1,192`; maricopa-az `1,593`; northern-ca `591`; south-central-tx `6,003`
- GEOID remains 11-digit text.

## Leak boundary

The public product also contains organizer/reference answer artifacts. The live runner rejects answer/reference source semantics, including repeated percent-encoded and case variants of `coverage-gap`, `reference-score`, `reference-answer`, and `answer-key`. The only submission-shaped source is `<region>-sample-submission.csv`; only `GEOID` is projected from it for scored-universe custody. No ACS layer or HIFLD hospital layer feeds the scored aggregate.

## Exact source objects

Each region uses exactly eleven public objects:

- sample submission;
- census tract geometry;
- Overture roads, buildings, and POIs;
- Census TIGER roads and CBP;
- Microsoft buildings;
- HIFLD fire, EMS, and school points.

`python aggregate.py plan --region ... --sql` is network-free and emits the canonical public URI registry, required columns, public query hash, scoring policy, preflight SQL, geometry contract, and exact 13-column output contract.

## Source-generation custody

A previous M1 head performed remote preflight reads and later reopened the same URI strings for scoring. That allowed a same-URI generation A to pass preflight while generation B drove the aggregate. The live runner closes that TOCTOU boundary mechanically:

1. each permitted public URI is opened **once**;
2. its exact response bytes stream into an anonymous private temporary inode while SHA-256 and byte count are computed;
3. that inode is reopened read-only through a retained `/proc/self/fd/<n>` descriptor and every write handle is dropped;
4. both schema/preflight SQL and scored aggregation SQL read only those retained descriptor paths;
5. the receipt records each public URI, exact SHA-256, byte count, and `sha256:<digest>` generation identity;
6. runtime SQL hashes canonicalize ephemeral fd numbers to those content digests.

No source pathname survives materialization, so later remote replacement, local rename/symlink swap, or same-directory pathname replacement cannot change the generation consumed by DuckDB. The runtime therefore intentionally requires Linux `/proc/self/fd` and enough local scratch storage for one region's exact source bytes. This is a correctness tradeoff: **run mode now downloads each permitted source object once in full** instead of relying on independent remote range reads.

## Scoring policy authority

The live scored SQL is constructed from code-owned local literals. It does **not** delegate scored SQL or filter policy to mutable globals in `_zsa_d6p2_core.py`. Mutating donor/public `ROAD_CLASSES`, `TIGER_MTFCC`, or `SCHOOL_CATEGORIES` after import cannot alter the scored query.

Published filters remain:

- Overture roads: `motorway`, `trunk`, `primary`, `secondary`
- TIGER MTFCC: `S1100`, `S1200`
- Overture fire: `fire_department`
- Overture EMS: `ambulance_and_ems_services`
- Overture schools: `elementary_school`, `middle_school`, `high_school`, `school`, `private_school`, `public_school`
- CBP denominator: `cbp_estab`
- all Overture places count toward the CBP half.

## Geometry and output rules

- Roads are clipped to each tract before projected length.
- All bbox joins use all four overlap comparisons before exact geometry predicates.
- Buildings use `ST_PointOnSurface` and strict tract containment.
- Point features use strict tract containment.
- The synthetic axis-order smoke probe must remain finite and within its expected metric range.
- Preflight rejects missing source columns, bad/duplicate/missing authoritative GEOIDs, unexpected geometry types, and answer-like non-sample columns.
- Output is exactly 13 columns, exactly one lexicographically ordered row per authoritative GEOID, with finite nonnegative numeric values.
- Output and receipt are create-exclusive.

## Offline proof

No DuckDB or network is needed for plan/contract tests:

```bash
python -m py_compile aggregate.py test_aggregate.py test_recovery.py
python -m unittest -v test_aggregate.py test_recovery.py
python -O -m unittest -v test_aggregate.py test_recovery.py
python aggregate.py plan --region northern-ca --sql > northern-ca.plan.json
```

The recovery suite includes predecessor killers for encoded answer paths, duplicate tract custody, geometry drift, donor/public policy mutation, same-URI A→B source generation swaps, anonymous retained-generation custody, and digest-canonicalized runtime SQL.

## One-region real-data run

Use a connected Linux environment with Python and DuckDB `1.5.4` plus enough scratch disk for one region's full eleven-source package:

```bash
python -m pip install 'duckdb==1.5.4'
python aggregate.py run \
  --region northern-ca \
  --output northern-ca.aggregates.csv \
  --receipt northern-ca.aggregates.receipt.json
```

The runner installs/loads DuckDB's public `spatial` extension. Public source bytes are fetched by Python HTTPS, content-addressed before DuckDB reads them, and never reopened remotely during authority evaluation. Start with Northern California because it is the smallest published region package.

The receipt binds source-generation digests, schema-description digests, canonicalized preflight/query hashes, geometry/value-domain observations, output SHA-256, DuckDB pin, Overture release, row count, and false external claims.

This development session has **not** produced a real-data execution receipt. Hosted execution remains separate provider truth.

## Four-region execution and scorer handoff

After one clean region receipt, run all four independently:

```bash
for r in eastern-ok maricopa-az northern-ca south-central-tx; do
  python aggregate.py run --region "$r" \
    --output "$r.aggregates.csv" \
    --receipt "$r.aggregates.receipt.json" || exit 1
done
```

Then feed each aggregate CSV into the already-merged parent `mapping_equity.py build` command with the same region's sample submission as the authoritative GEOID universe.

A local aggregate/scorer success is **not** a Zindi submission, leaderboard result, prize, award, payment, or revenue claim. Those require separate provider evidence.
