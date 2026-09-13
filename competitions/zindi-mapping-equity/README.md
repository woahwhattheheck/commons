# Zindi Mapping Equity — reproducible coverage-gap scorer

Competition workspace for the **Bias Bounty Mapping Equity Challenge**. The goal is a tract-level `coverage_gap_score` derived only from the challenge-supplied raw/reference datasets, with a separately reproducible exploration path for the Best Bias Discovery writeup.

This repository does **not** contain a Zindi submission receipt, prize claim, account action, or organizer acceptance. Joining the competition, accepting platform terms, selecting a team, and uploading a submission are external actions outside this source lane.

## Truth and leakage boundary

The challenge data package publishes organizer/reference coverage-gap labels. **This pipeline deliberately does not read those files.** `build_submission.py` only addresses raw challenge layers plus each region's authoritative `sample-submission.csv`. `tests/test_build_plan.py` rejects any generated SQL containing a `-coverage-gap.` path.

The raw package is pinned by the organizer to Overture Maps release `2026-08-19.0`. Source Cooperative states the GeoParquet geometry CRS is `OGC:CRS84`; DuckDB's EPSG axis behavior therefore matters. Road measurement uses `ST_Transform(..., 'EPSG:4326', 'EPSG:5070', always_xy := true)` before length.

Primary references:
- https://zindi.world/competitions/bias-bounty-mapping-equity-challenge
- https://source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge/README.md
- `s3://us-west-2.opendata.source.coop/humane-intelligence/bias-bounty-mapping-equity-challenge`

## Challenge scoring contract implemented here

For a reference count/length `R` and Overture observation `O`, each defined gap is `1 - min(1, O / R)`. When `R == 0`, that term is **undefined**, not zero and not one.

1. **Transport** — TIGER `MTFCC ∈ {S1100,S1200}` versus Overture `class ∈ {motorway,trunk,primary,secondary}`, after clipping to each tract.
2. **Buildings** — Overture footprint count versus Microsoft footprint count. ACS housing is not a denominator.
3. **POI** — mean of two halves: HIFLD half (mean of defined fire/EMS/school type gaps) and CBP half (all Overture places versus `cbp_estab`). Hospitals are excluded.

The final score is the mean of defined transport/building/POI components, so the divisor varies by tract. Point features exactly on a shared tract boundary are assigned once to the lowest lexical GEOID so `ST_Intersects` cannot silently double-count them. GEOID stays an 11-digit string throughout.

Exact Overture categories: fire `fire_department`; EMS `ambulance_and_ems_services`; schools `elementary_school`, `middle_school`, `high_school`, `school`, `private_school`, `public_school`.

## One explicit spatial ambiguity

The public scoring description specifies footprint counts per tract but does not state how a polygon touching a tract boundary is assigned. `build_submission.py` exposes the policy:
- `--building-assignment centroid` (default): footprint centroid determines tract, avoiding ordinary cross-boundary double count.
- `--building-assignment intersects`: count in every tract intersected, for a sensitivity run.

Do not silently tune this choice against organizer-published target labels. If later permitted leaderboard feedback resolves it, record the policy and submission identity.

## Reproducible run

Python scoring/tests need no third-party package. Raw geospatial aggregation uses exactly DuckDB `1.5.4`, the version Source Cooperative says it verified.

```bash
cd competitions/zindi-mapping-equity
python -m unittest discover -s tests -v
python -m py_compile score.py build_submission.py bias_discovery.py
python build_submission.py --print-sql --region northern-ca
python -m pip install -r requirements.txt
python build_submission.py --out-dir build/centroid
```

Artifacts: per-region aggregates, `all-aggregates.csv`, Zindi-shaped `submission.csv`, and diagnostic `components.csv`. The script fails if DuckDB is missing or not exactly 1.5.4; it does not pretend a dry run was a data run.

## Best Bias Discovery workflow

`bias_discovery.py` is separate from scored prediction. It joins our produced score/components file to a challenge strata CSV and ranks numeric candidate dimensions by upper-vs-lower-quartile coverage-gap difference. Fixed scorecard families are excluded by default.

```bash
python bias_discovery.py build/centroid/components.csv south-central-tx-strata-tract-table.csv build/centroid/bias-candidates.json
```

A ranked field is **not a discovery claim**. Before any writeup, inspect source semantics, map/names of affected tracts, quantify uncertainty, verify the pattern is outside the automated scorecard, and explain a concrete emergency-dispatch / evacuation / disaster-relief consequence. Additional public data is allowed only for this special-prize analysis, never the scored CSV; document URL, license and retrieval date.

## Acceptance gates

Tests kill overcoverage errors, zero-reference errors, fixed-divisor mistakes, wrong POI half weighting, leading-zero GEOID loss, non-finite/negative inputs, all-undefined rows, category drift, silent axis-order bugs, target-label reads, point-boundary double counts and hidden building-assignment policy.

## Remaining external validation

This lane proves scoring math and query construction locally. It cannot honestly prove multi-GB remote queries or leaderboard RMSE in a runtime with no network/DuckDB. Before any competition submission, run the four-region build on a networked machine, inspect row counts against authoritative sample files, check all scores are finite in `[0,1]`, and preserve hashes of `submission.csv`, aggregate files, code commit, DuckDB version and building-assignment policy.
