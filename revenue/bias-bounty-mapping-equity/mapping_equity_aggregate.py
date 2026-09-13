#!/usr/bin/env python3
"""Four-region tract aggregation runner for the Mapping Equity challenge.

The scoring module consumes a deliberately narrow tract aggregate schema. This
runner is the auditable geospatial stage that produces those inputs from the
challenge-provided Source Cooperative package. DuckDB is imported lazily so
planning, receipt verification, and hostile tests do not require geospatial
packages.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable, Mapping, Optional, Sequence

SCHEMA = "mapping-equity-tract-aggregates/v1"
RECEIPT_SCHEMA = "mapping-equity-tract-aggregation-receipt/v1"
OVERTURE_RELEASE = "2026-08-19.0"
SOURCE_ROOT = (
    "https://data.source.coop/humane-intelligence/"
    "bias-bounty-mapping-equity-challenge"
)
REGIONS = ("eastern-ok", "maricopa-az", "northern-ca", "south-central-tx")
EXPECTED_SCORED_ROWS = {
    "eastern-ok": 1192,
    "maricopa-az": 1593,
    "northern-ca": 591,
    "south-central-tx": 6003,
}
AGGREGATE_COLUMNS = (
    "GEOID",
    "overture_road_length",
    "tiger_road_length",
    "overture_buildings",
    "microsoft_buildings",
    "overture_fire",
    "hifld_fire",
    "overture_ems",
    "hifld_ems",
    "overture_schools",
    "hifld_schools",
    "overture_places",
    "cbp_establishments",
)
ROAD_CLASSES = ("motorway", "trunk", "primary", "secondary")
TIGER_MTFCC = ("S1100", "S1200")
FIRE_CATEGORIES = ("fire_department",)
EMS_CATEGORIES = ("ambulance_and_ems_services",)
SCHOOL_CATEGORIES = (
    "elementary_school",
    "middle_school",
    "high_school",
    "school",
    "private_school",
    "public_school",
)
GEOID_RE = re.compile(r"^[0-9]{11}$")

REFERENCE_PARQUET_LAYERS = (
    "overture-buildings",
    "overture-roads",
    "overture-pois",
    "microsoft-buildings",
    "census-tiger-roads",
    "census-cbp",
    "hifld-fire-stations",
    "hifld-ems-stations",
    "hifld-schools",
)


class AggregationError(ValueError):
    pass


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _sql_list(values: Sequence[str]) -> str:
    return ", ".join(_sql_quote(value) for value in values)


def _validate_region(region: str) -> str:
    if region not in REGIONS:
        raise AggregationError(f"unknown region: {region!r}; expected one of {REGIONS}")
    return region


def reference_uri(region: str, layer: str, extension: str = "parquet") -> str:
    _validate_region(region)
    if not re.fullmatch(r"[a-z0-9-]+", layer):
        raise AggregationError(f"unsafe layer: {layer!r}")
    if extension not in {"parquet", "csv"}:
        raise AggregationError("extension must be parquet or csv")
    return f"{SOURCE_ROOT}/reference/{region}/{region}-{layer}.{extension}"


def tract_uri(region: str) -> str:
    _validate_region(region)
    return f"{SOURCE_ROOT}/strata/{region}/{region}-census-tracts.parquet"


def sample_uri(region: str) -> str:
    return reference_uri(region, "sample-submission", "csv")


def required_source_uris(region: str) -> tuple[str, ...]:
    _validate_region(region)
    uris = [sample_uri(region), tract_uri(region)]
    uris.extend(reference_uri(region, layer) for layer in REFERENCE_PARQUET_LAYERS)
    return tuple(uris)


def source_manifest() -> dict[str, object]:
    return {
        "source_root": SOURCE_ROOT,
        "overture_release": OVERTURE_RELEASE,
        "regions": {
            region: {
                "expected_scored_rows": EXPECTED_SCORED_ROWS[region],
                "objects": [
                    {
                        "uri": uri,
                        "uri_sha256": _sha256_bytes(uri.encode("utf-8")),
                    }
                    for uri in required_source_uris(region)
                ],
            }
            for region in REGIONS
        },
    }


def _point_assignment_cte(source_expr: str, point_expr: str) -> str:
    """Assign each source feature to at most one authoritative tract.

    ST_Intersects includes boundary points. A deterministic lowest-GEOID tie-break
    prevents boundary points from being double-counted. `fid` is query-local only.
    """
    return f"""
features AS (
    SELECT row_number() OVER () AS fid, {point_expr} AS point
    FROM {source_expr}
),
candidates AS (
    SELECT f.fid, t.GEOID,
           row_number() OVER (PARTITION BY f.fid ORDER BY t.GEOID) AS tract_rank
    FROM features f
    JOIN tracts t ON ST_Intersects(f.point, t.geometry)
),
assigned AS (
    SELECT fid, GEOID FROM candidates WHERE tract_rank = 1
)
""".strip()


def build_region_sql(region: str) -> tuple[str, ...]:
    """Return the exact DuckDB statements for one region.

    Road segments are clipped to tract polygons before EPSG:5070 length, avoiding
    whole-segment assignment across boundaries. Building polygons are assigned by
    ST_PointOnSurface with a deterministic boundary tie. Point layers use the same
    tie policy. Reference CBP is already tract keyed and is never spatially spread.
    """
    _validate_region(region)
    sample = _sql_quote(sample_uri(region))
    tracts = _sql_quote(tract_uri(region))
    ov_roads = _sql_quote(reference_uri(region, "overture-roads"))
    tiger = _sql_quote(reference_uri(region, "census-tiger-roads"))
    ov_buildings = _sql_quote(reference_uri(region, "overture-buildings"))
    ms_buildings = _sql_quote(reference_uri(region, "microsoft-buildings"))
    ov_pois = _sql_quote(reference_uri(region, "overture-pois"))
    hifld_fire = _sql_quote(reference_uri(region, "hifld-fire-stations"))
    hifld_ems = _sql_quote(reference_uri(region, "hifld-ems-stations"))
    hifld_schools = _sql_quote(reference_uri(region, "hifld-schools"))
    cbp = _sql_quote(reference_uri(region, "census-cbp"))

    setup = f"""
CREATE OR REPLACE TEMP TABLE auth AS
SELECT CAST(GEOID AS VARCHAR) AS GEOID, row_number() OVER () AS authoritative_order
FROM read_csv({sample}, header=true, types={{'GEOID': 'VARCHAR'}});

CREATE OR REPLACE TEMP TABLE tracts AS
SELECT a.GEOID, a.authoritative_order, s.geometry
FROM auth a
JOIN read_parquet({tracts}) s ON CAST(s.GEOID AS VARCHAR) = a.GEOID;
""".strip()

    road = f"""
CREATE OR REPLACE TEMP TABLE road_metrics AS
WITH overture_bits AS (
    SELECT t.GEOID, ST_Intersection(r.geometry, t.geometry) AS geometry
    FROM read_parquet({ov_roads}) r
    JOIN tracts t ON ST_Intersects(r.geometry, t.geometry)
    WHERE r."class" IN ({_sql_list(ROAD_CLASSES)})
),
overture_lengths AS (
    SELECT GEOID,
           SUM(ST_Length(ST_Transform(geometry, 'EPSG:4326', 'EPSG:5070', always_xy := true))) AS value
    FROM overture_bits
    WHERE NOT ST_IsEmpty(geometry)
    GROUP BY GEOID
),
tiger_bits AS (
    SELECT t.GEOID, ST_Intersection(r.geometry, t.geometry) AS geometry
    FROM read_parquet({tiger}) r
    JOIN tracts t ON ST_Intersects(r.geometry, t.geometry)
    WHERE r.MTFCC IN ({_sql_list(TIGER_MTFCC)})
),
tiger_lengths AS (
    SELECT GEOID,
           SUM(ST_Length(ST_Transform(geometry, 'EPSG:4326', 'EPSG:5070', always_xy := true))) AS value
    FROM tiger_bits
    WHERE NOT ST_IsEmpty(geometry)
    GROUP BY GEOID
)
SELECT a.GEOID,
       COALESCE(o.value, 0.0) AS overture_road_length,
       COALESCE(t.value, 0.0) AS tiger_road_length
FROM auth a
LEFT JOIN overture_lengths o USING (GEOID)
LEFT JOIN tiger_lengths t USING (GEOID);
""".strip()

    def building_statement(table_name: str, source: str) -> str:
        cte = _point_assignment_cte(f"read_parquet({source})", "ST_PointOnSurface(geometry)")
        return f"""
CREATE OR REPLACE TEMP TABLE {table_name} AS
WITH {cte}
SELECT a.GEOID, COALESCE(c.n, 0) AS value
FROM auth a
LEFT JOIN (SELECT GEOID, COUNT(*) AS n FROM assigned GROUP BY GEOID) c USING (GEOID);
""".strip()

    building_ov = building_statement("overture_building_metrics", ov_buildings)
    building_ms = building_statement("microsoft_building_metrics", ms_buildings)

    poi_cte = _point_assignment_cte(
        f"read_parquet({ov_pois})",
        "geometry",
    )
    poi = f"""
CREATE OR REPLACE TEMP TABLE overture_poi_metrics AS
WITH poi_source AS (
    SELECT row_number() OVER () AS fid, geometry, categories.primary AS category
    FROM read_parquet({ov_pois})
),
candidates AS (
    SELECT p.fid, p.category, t.GEOID,
           row_number() OVER (PARTITION BY p.fid ORDER BY t.GEOID) AS tract_rank
    FROM poi_source p
    JOIN tracts t ON ST_Intersects(p.geometry, t.geometry)
),
assigned AS (
    SELECT fid, category, GEOID FROM candidates WHERE tract_rank = 1
),
counts AS (
    SELECT GEOID,
           COUNT(*) AS overture_places,
           COUNT(*) FILTER (WHERE category IN ({_sql_list(FIRE_CATEGORIES)})) AS overture_fire,
           COUNT(*) FILTER (WHERE category IN ({_sql_list(EMS_CATEGORIES)})) AS overture_ems,
           COUNT(*) FILTER (WHERE category IN ({_sql_list(SCHOOL_CATEGORIES)})) AS overture_schools
    FROM assigned GROUP BY GEOID
)
SELECT a.GEOID,
       COALESCE(c.overture_places, 0) AS overture_places,
       COALESCE(c.overture_fire, 0) AS overture_fire,
       COALESCE(c.overture_ems, 0) AS overture_ems,
       COALESCE(c.overture_schools, 0) AS overture_schools
FROM auth a LEFT JOIN counts c USING (GEOID);
""".strip()

    def point_count_statement(table_name: str, source: str) -> str:
        cte = _point_assignment_cte(f"read_parquet({source})", "geometry")
        return f"""
CREATE OR REPLACE TEMP TABLE {table_name} AS
WITH {cte}
SELECT a.GEOID, COALESCE(c.n, 0) AS value
FROM auth a
LEFT JOIN (SELECT GEOID, COUNT(*) AS n FROM assigned GROUP BY GEOID) c USING (GEOID);
""".strip()

    fire = point_count_statement("hifld_fire_metrics", hifld_fire)
    ems = point_count_statement("hifld_ems_metrics", hifld_ems)
    schools = point_count_statement("hifld_school_metrics", hifld_schools)

    cbp_stmt = f"""
CREATE OR REPLACE TEMP TABLE cbp_metrics AS
SELECT a.GEOID, COALESCE(MAX(CAST(c.cbp_estab AS DOUBLE)), 0.0) AS value
FROM auth a
LEFT JOIN read_parquet({cbp}) c ON CAST(c.GEOID AS VARCHAR) = a.GEOID
GROUP BY a.GEOID;
""".strip()

    final = """
SELECT a.GEOID,
       r.overture_road_length,
       r.tiger_road_length,
       ob.value AS overture_buildings,
       mb.value AS microsoft_buildings,
       op.overture_fire,
       hf.value AS hifld_fire,
       op.overture_ems,
       he.value AS hifld_ems,
       op.overture_schools,
       hs.value AS hifld_schools,
       op.overture_places,
       cb.value AS cbp_establishments
FROM auth a
JOIN road_metrics r USING (GEOID)
JOIN overture_building_metrics ob USING (GEOID)
JOIN microsoft_building_metrics mb USING (GEOID)
JOIN overture_poi_metrics op USING (GEOID)
JOIN hifld_fire_metrics hf USING (GEOID)
JOIN hifld_ems_metrics he USING (GEOID)
JOIN hifld_school_metrics hs USING (GEOID)
JOIN cbp_metrics cb USING (GEOID)
ORDER BY a.authoritative_order;
""".strip()

    assert "tract_rank = 1" in poi_cte
    return (setup, road, building_ov, building_ms, poi, fire, ems, schools, cbp_stmt, final)


def validate_rows(region: str, rows: Sequence[Mapping[str, object]]) -> None:
    _validate_region(region)
    expected_count = EXPECTED_SCORED_ROWS[region]
    if len(rows) != expected_count:
        raise AggregationError(
            f"{region}: expected {expected_count} authoritative rows, got {len(rows)}"
        )
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if tuple(row.keys()) != AGGREGATE_COLUMNS:
            raise AggregationError(
                f"{region} row {index}: columns/order mismatch: {tuple(row.keys())!r}"
            )
        geoid = row["GEOID"]
        if not isinstance(geoid, str) or not GEOID_RE.fullmatch(geoid):
            raise AggregationError(f"{region} row {index}: invalid GEOID {geoid!r}")
        if geoid in seen:
            raise AggregationError(f"{region}: duplicate GEOID {geoid}")
        seen.add(geoid)
        for column in AGGREGATE_COLUMNS[1:]:
            value = row[column]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise AggregationError(
                    f"{region} {geoid}: {column} must be numeric, got {type(value).__name__}"
                )
            if float(value) < 0 or float(value) != float(value) or float(value) in (float("inf"), float("-inf")):
                raise AggregationError(f"{region} {geoid}: invalid {column}={value!r}")


def rows_to_csv(rows: Sequence[Mapping[str, object]]) -> str:
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=AGGREGATE_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def _rows_from_relation(relation: object) -> list[dict[str, object]]:
    columns = tuple(getattr(relation, "columns"))
    if columns != AGGREGATE_COLUMNS:
        raise AggregationError(f"DuckDB result schema mismatch: {columns!r}")
    return [dict(zip(columns, values)) for values in relation.fetchall()]


def _head_metadata(uri: str, timeout: float = 10.0) -> dict[str, object]:
    request = urllib.request.Request(
        uri,
        method="HEAD",
        headers={"User-Agent": "mapping-equity-aggregation/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return {
                "status": int(getattr(response, "status", 200)),
                "etag": response.headers.get("ETag"),
                "content_length": response.headers.get("Content-Length"),
                "last_modified": response.headers.get("Last-Modified"),
            }
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return {"metadata_error": f"{type(exc).__name__}: {exc}"}


def _safe_write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short write made no progress")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _duckdb_connect() -> object:
    try:
        import duckdb  # type: ignore
    except ImportError as exc:
        raise AggregationError(
            "DuckDB is required for real-data execution; install duckdb==1.5.4"
        ) from exc
    connection = duckdb.connect()
    connection.execute("INSTALL httpfs; LOAD httpfs;")
    connection.execute("INSTALL spatial; LOAD spatial;")
    return connection


def execute_region(region: str, connection: object) -> list[dict[str, object]]:
    statements = build_region_sql(region)
    for statement in statements[:-1]:
        connection.execute(statement)
    relation = connection.sql(statements[-1])
    rows = _rows_from_relation(relation)
    validate_rows(region, rows)
    return rows


def _duckdb_identity(connection: object) -> dict[str, object]:
    result: dict[str, object] = {}
    try:
        version_row = connection.sql("SELECT version()").fetchone()
        result["duckdb_version"] = version_row[0] if version_row else None
    except Exception as exc:
        result["duckdb_version_error"] = f"{type(exc).__name__}: {exc}"
    try:
        ext_rows = connection.sql(
            "SELECT extension_name, extension_version, loaded "
            "FROM duckdb_extensions() WHERE extension_name IN ('httpfs','spatial') "
            "ORDER BY extension_name"
        ).fetchall()
        result["extensions"] = [
            {"name": row[0], "version": row[1], "loaded": bool(row[2])} for row in ext_rows
        ]
    except Exception as exc:
        result["extension_identity_error"] = f"{type(exc).__name__}: {exc}"
    return result


def build_receipt(
    outputs: Mapping[str, bytes],
    *,
    engine: Mapping[str, object],
    metadata_lookup: Callable[[str], Mapping[str, object]] = _head_metadata,
) -> dict[str, object]:
    if set(outputs) != set(REGIONS):
        raise AggregationError("receipt requires outputs for exactly all four regions")
    regions: dict[str, object] = {}
    for region in REGIONS:
        data = outputs[region]
        objects = []
        for uri in required_source_uris(region):
            objects.append(
                {
                    "uri": uri,
                    "uri_sha256": _sha256_bytes(uri.encode("utf-8")),
                    "observed": dict(metadata_lookup(uri)),
                }
            )
        regions[region] = {
            "expected_scored_rows": EXPECTED_SCORED_ROWS[region],
            "aggregate_csv_sha256": _sha256_bytes(data),
            "aggregate_csv_bytes": len(data),
            "objects": objects,
        }
    payload = {
        "schema": RECEIPT_SCHEMA,
        "source_product": "humane-intelligence/bias-bounty-mapping-equity-challenge",
        "source_root": SOURCE_ROOT,
        "overture_release": OVERTURE_RELEASE,
        "aggregate_schema": list(AGGREGATE_COLUMNS),
        "regions": regions,
        "engine": dict(engine),
        "policy": {
            "road_allocation": "clip-each-intersection-then-length-epsg5070-always_xy",
            "polygon_assignment": "st_pointonsurface-then-lowest-geoid-boundary-tie",
            "point_assignment": "st_intersects-then-lowest-geoid-boundary-tie",
            "tiger_mtfcc": list(TIGER_MTFCC),
            "overture_road_classes": list(ROAD_CLASSES),
            "overture_fire_categories": list(FIRE_CATEGORIES),
            "overture_ems_categories": list(EMS_CATEGORIES),
            "overture_school_categories": list(SCHOOL_CATEGORIES),
            "cbp_field": "cbp_estab",
            "answer_columns_consumed": False,
            "coverage_gap_score_consumed": False,
        },
        "claims": {
            "zindi_submitted": False,
            "leaderboard_score_claimed": False,
            "rank_claimed": False,
            "prize_claimed": False,
            "payment_claimed": False,
        },
    }
    payload_text = _canonical_json(payload).encode("utf-8")
    return {"payload": payload, "payload_sha256": _sha256_bytes(payload_text)}


def verify_receipt(output_dir: Path, receipt: Mapping[str, object]) -> dict[str, object]:
    if set(receipt) != {"payload", "payload_sha256"}:
        raise AggregationError("receipt envelope shape mismatch")
    payload = receipt["payload"]
    if not isinstance(payload, dict):
        raise AggregationError("receipt payload must be object")
    expected_digest = _sha256_bytes(_canonical_json(payload).encode("utf-8"))
    if receipt["payload_sha256"] != expected_digest:
        raise AggregationError("receipt payload digest mismatch")
    if payload.get("schema") != RECEIPT_SCHEMA:
        raise AggregationError("receipt schema mismatch")
    if payload.get("source_root") != SOURCE_ROOT or payload.get("overture_release") != OVERTURE_RELEASE:
        raise AggregationError("receipt source identity mismatch")
    if payload.get("aggregate_schema") != list(AGGREGATE_COLUMNS):
        raise AggregationError("receipt aggregate schema mismatch")
    if "coverage_gap_score" in payload.get("aggregate_schema", []):
        raise AggregationError("answer leakage in aggregate schema")
    expected_claims = {
        "zindi_submitted": False,
        "leaderboard_score_claimed": False,
        "rank_claimed": False,
        "prize_claimed": False,
        "payment_claimed": False,
    }
    if payload.get("claims") != expected_claims:
        raise AggregationError("receipt authority claims mismatch")
    regions = payload.get("regions")
    if not isinstance(regions, dict) or set(regions) != set(REGIONS):
        raise AggregationError("receipt region set mismatch")
    for region in REGIONS:
        meta = regions[region]
        if not isinstance(meta, dict):
            raise AggregationError(f"{region}: receipt metadata invalid")
        if meta.get("expected_scored_rows") != EXPECTED_SCORED_ROWS[region]:
            raise AggregationError(f"{region}: scored-row count identity mismatch")
        path = output_dir / f"{region}-aggregates.csv"
        data = path.read_bytes()
        if _sha256_bytes(data) != meta.get("aggregate_csv_sha256"):
            raise AggregationError(f"{region}: aggregate digest mismatch")
        reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
        if tuple(reader.fieldnames or ()) != AGGREGATE_COLUMNS:
            raise AggregationError(f"{region}: aggregate columns mismatch")
        rows = list(reader)
        if len(rows) != EXPECTED_SCORED_ROWS[region]:
            raise AggregationError(f"{region}: aggregate row count mismatch")
        geoids = [row["GEOID"] for row in rows]
        if any(not GEOID_RE.fullmatch(value or "") for value in geoids) or len(set(geoids)) != len(geoids):
            raise AggregationError(f"{region}: aggregate GEOID custody failure")
        objects = meta.get("objects")
        expected_uris = list(required_source_uris(region))
        if not isinstance(objects, list) or [item.get("uri") for item in objects] != expected_uris:
            raise AggregationError(f"{region}: source-object identity mismatch")
    return {
        "schema": RECEIPT_SCHEMA,
        "regions_verified": list(REGIONS),
        "aggregate_rows_verified": sum(EXPECTED_SCORED_ROWS.values()),
        "verified": True,
    }


def run_all(output_dir: Path, receipt_path: Path) -> dict[str, object]:
    if output_dir.exists() and any(output_dir.iterdir()):
        raise AggregationError("output directory must not contain existing files")
    output_dir.mkdir(parents=True, exist_ok=True)
    connection = _duckdb_connect()
    outputs: dict[str, bytes] = {}
    try:
        for region in REGIONS:
            rows = execute_region(region, connection)
            data = rows_to_csv(rows).encode("utf-8")
            _safe_write_new(output_dir / f"{region}-aggregates.csv", data)
            outputs[region] = data
        receipt = build_receipt(outputs, engine=_duckdb_identity(connection))
        receipt_bytes = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode("utf-8")
        _safe_write_new(receipt_path, receipt_bytes)
    finally:
        try:
            connection.close()
        except Exception:
            pass
    return verify_receipt(output_dir, receipt)


def _print_plan() -> None:
    plan = {
        "schema": SCHEMA,
        "aggregate_columns": list(AGGREGATE_COLUMNS),
        "source": source_manifest(),
        "sql_sha256": {
            region: _sha256_bytes("\n\n".join(build_region_sql(region)).encode("utf-8"))
            for region in REGIONS
        },
    }
    print(json.dumps(plan, sort_keys=True, indent=2))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("plan", help="print deterministic source/query plan without network execution")
    run = sub.add_parser("run", help="execute all four official regions")
    run.add_argument("--output-dir", required=True)
    run.add_argument("--receipt", required=True)
    verify = sub.add_parser("verify", help="verify outputs against a saved receipt")
    verify.add_argument("--output-dir", required=True)
    verify.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            _print_plan()
            return 0
        if args.command == "run":
            result = run_all(Path(args.output_dir), Path(args.receipt))
        else:
            receipt = json.loads(Path(args.receipt).read_text(encoding="utf-8"))
            result = verify_receipt(Path(args.output_dir), receipt)
    except (AggregationError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
