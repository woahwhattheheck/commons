#!/usr/bin/env python3
"""Recovered, fail-closed Mapping Equity public-data aggregation carrier.

Primary implementation credit belongs to ZSA-D6P2. This module wraps that stranded
implementation instead of rewriting it: `_zsa_d6p2_core.py` is the byte-exact donor.
ZHD-K8P3 adds the current M1 preflight/leak-fence contract while keeping the donor
branch immutable. ZFS-R7 supplied independent alternate-carrier review evidence.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Iterable, Mapping, Optional, Sequence
from urllib.parse import unquote

import _zsa_d6p2_core as _core

SCHEMA = _core.SCHEMA
DUCKDB_VERSION = _core.DUCKDB_VERSION
OVERTURE_RELEASE = _core.OVERTURE_RELEASE
HTTPS_ROOT = _core.HTTPS_ROOT
REGIONS = _core.REGIONS
OUTPUT_COLUMNS = _core.OUTPUT_COLUMNS
ROAD_CLASSES = _core.ROAD_CLASSES
TIGER_MTFCC = _core.TIGER_MTFCC
SCHOOL_CATEGORIES = _core.SCHOOL_CATEGORIES
GEOID_RE = _core.GEOID_RE
REQUIRED_COLUMNS = _core.REQUIRED_COLUMNS
AggregationError = _core.AggregationError

FORBIDDEN_SOURCE_TOKENS = tuple(dict.fromkeys((*_core.FORBIDDEN_SOURCE_TOKENS,
    "reference-answer", "reference_answer")))

GEOMETRY_EXPECTATIONS: dict[str, frozenset[str]] = {
    "tracts": frozenset({"POLYGON", "MULTIPOLYGON"}),
    "overture_roads": frozenset({"LINESTRING", "MULTILINESTRING"}),
    "tiger_roads": frozenset({"LINESTRING", "MULTILINESTRING"}),
    "overture_buildings": frozenset({"POLYGON", "MULTIPOLYGON"}),
    "microsoft_buildings": frozenset({"POLYGON", "MULTIPOLYGON"}),
    "overture_pois": frozenset({"POINT", "MULTIPOINT"}),
    "hifld_fire": frozenset({"POINT", "MULTIPOINT"}),
    "hifld_ems": frozenset({"POINT", "MULTIPOINT"}),
    "hifld_schools": frozenset({"POINT", "MULTIPOINT"}),
}

PUBLISHED_POLICY_VALUES: dict[str, tuple[str, ...]] = {
    "overture_roads.class": ROAD_CLASSES,
    "tiger_roads.MTFCC": TIGER_MTFCC,
    "overture_pois.school": SCHOOL_CATEGORIES,
    "overture_pois.fire": ("fire_department",),
    "overture_pois.ems": ("ambulance_and_ems_services",),
}


def _decode_bounded(value: str) -> str:
    """Percent-decode repeatedly, rejecting pathological encoding depth."""
    current = value
    for _ in range(8):
        decoded = unquote(current)
        if decoded == current:
            return decoded
        current = decoded
    if unquote(current) != current:
        raise AggregationError("source encoding depth exceeds leak-fence limit")
    return current


def _normalized_label(value: str) -> str:
    decoded = _decode_bounded(value).lower().replace("\\", "/")
    return re.sub(r"[-.\s]+", "_", decoded)


def _forbidden_token(value: str) -> Optional[str]:
    normalized = _normalized_label(value)
    for token in FORBIDDEN_SOURCE_TOKENS:
        candidate = re.sub(r"[-.\s]+", "_", token.lower())
        if candidate in normalized:
            return token
    return None


def _safe_source(uri: str, *, allow_sample_score_header: bool = False) -> str:
    """Admit only canonical challenge URIs and reject encoded answer semantics."""
    del allow_sample_score_header
    decoded = _decode_bounded(uri)
    token = _forbidden_token(decoded)
    if token is not None:
        raise AggregationError(f"forbidden answer/reference source token {token!r}: {uri}")
    if not decoded.startswith(HTTPS_ROOT + "/"):
        raise AggregationError(f"source must stay inside the public challenge product: {uri}")
    if any(ch in decoded for ch in ("?", "#", "\\")):
        raise AggregationError(f"source URI must be canonical and query/fragment free: {uri}")
    return uri


# Every retained donor function resolves through the repaired URI gate.
_core._safe_source = _safe_source

source_registry = _core.source_registry
_sql_string = _core._sql_string
_bbox_overlap = _core._bbox_overlap
schema_probe_sql = _core.schema_probe_sql
semantic_probe_sql = _core.semantic_probe_sql
render_csv = _core.render_csv
_write_new = _core._write_new
_digest_schema = _core._digest_schema
_connect_duckdb = _core._connect_duckdb


def _validate_policy_categories(name: str, values: Sequence[str]) -> None:
    expected = PUBLISHED_POLICY_VALUES.get(name)
    if expected is None:
        raise AggregationError(f"unknown published filter domain: {name}")
    if tuple(values) != expected:
        raise AggregationError(
            f"{name}: policy category drift; expected {expected!r}, got {tuple(values)!r}"
        )


def aggregate_query(region: str) -> str:
    _validate_policy_categories("overture_roads.class", ROAD_CLASSES)
    _validate_policy_categories("tiger_roads.MTFCC", TIGER_MTFCC)
    _validate_policy_categories("overture_pois.school", SCHOOL_CATEGORIES)
    _validate_policy_categories("overture_pois.fire", ("fire_department",))
    _validate_policy_categories("overture_pois.ems", ("ambulance_and_ems_services",))
    return _core.aggregate_query(region)


def validate_source_schema(key: str, columns: Iterable[str]) -> None:
    columns = tuple(str(column) for column in columns)
    _core.validate_source_schema(key, columns)
    # SampleSubmission is the sole explicit exception: it is custody authority and
    # its organizer score placeholder is projected away rather than consumed.
    if key == "sample":
        return
    for column in columns:
        token = _forbidden_token(column)
        if token is not None:
            raise AggregationError(
                f"{key}: forbidden answer/reference-like column present: {column!r}"
            )


def _geometry_probe_sql(key: str, uri: str) -> str:
    if key not in GEOMETRY_EXPECTATIONS:
        raise AggregationError(f"no geometry contract for source {key!r}")
    _safe_source(uri)
    return (
        "SELECT DISTINCT upper(ST_GeometryType(geometry)) AS geometry_type "
        f"FROM read_parquet({_sql_string(uri)}) WHERE geometry IS NOT NULL ORDER BY 1"
    )


def _domain_probe_sql(key: str, uri: str) -> str:
    _safe_source(uri)
    if key == "overture_roads":
        expr = 'CAST("class" AS VARCHAR)'
    elif key == "tiger_roads":
        expr = "CAST(MTFCC AS VARCHAR)"
    elif key == "overture_pois":
        expr = "CAST(categories.primary AS VARCHAR)"
    else:
        raise AggregationError(f"no value-domain contract for source {key!r}")
    return (
        f"SELECT DISTINCT {expr} AS value FROM read_parquet({_sql_string(uri)}) "
        f"WHERE {expr} IS NOT NULL ORDER BY 1"
    )


def _custody_probe_sql(region: str) -> str:
    r = source_registry(region)
    return f"""
WITH authoritative AS (
  SELECT CAST(GEOID AS VARCHAR) AS GEOID
  FROM read_csv_auto({_sql_string(r['sample'])}, header=true, all_varchar=true)
), tract_raw AS (
  SELECT CAST(GEOID AS VARCHAR) AS GEOID
  FROM read_parquet({_sql_string(r['tracts'])})
), tract_ids AS (
  SELECT DISTINCT GEOID FROM tract_raw
)
SELECT (SELECT COUNT(*) FROM authoritative) AS sample_rows,
       (SELECT COUNT(DISTINCT GEOID) FROM authoritative) AS sample_unique,
       (SELECT COUNT(*) FROM authoritative WHERE NOT regexp_full_match(GEOID, '^[0-9]{{11}}$')) AS bad_geoid,
       (SELECT COUNT(*) FROM authoritative a LEFT JOIN tract_ids t USING (GEOID) WHERE t.GEOID IS NULL) AS missing_tract,
       (SELECT COUNT(*) - COUNT(DISTINCT tr.GEOID)
          FROM tract_raw tr INNER JOIN authoritative a USING (GEOID)) AS duplicate_tract_rows
""".strip()


def preflight_probe_sql(region: str) -> dict[str, str]:
    """Return the complete deterministic pre-aggregation probe transcript."""
    r = source_registry(region)
    probes: dict[str, str] = {}
    for key, uri in r.items():
        probes[f"schema:{key}"] = schema_probe_sql(key, uri)
    probes["custody"] = _custody_probe_sql(region)
    for key in GEOMETRY_EXPECTATIONS:
        probes[f"geometry:{key}"] = _geometry_probe_sql(key, r[key])
    probes["domain:overture_roads"] = _domain_probe_sql("overture_roads", r["overture_roads"])
    probes["domain:tiger_roads"] = _domain_probe_sql("tiger_roads", r["tiger_roads"])
    probes["domain:overture_pois"] = _domain_probe_sql("overture_pois", r["overture_pois"])
    nested, axis = semantic_probe_sql(region)
    probes["semantic:overture_poi_category"] = nested
    probes["semantic:axis_order"] = axis
    return probes


def _validate_custody(region: str, row: Sequence[object]) -> dict[str, int]:
    if len(row) != 5:
        raise AggregationError(f"{region}: custody probe shape mismatch")
    sample_rows, sample_unique, bad_geoid, missing_tract, duplicate_tract_rows = (int(v) for v in row)
    expected = REGIONS[region]
    if sample_rows != expected or sample_unique != expected:
        raise AggregationError(
            f"{region}: authoritative GEOID custody drift: rows={sample_rows}, "
            f"unique={sample_unique}, expected={expected}"
        )
    if bad_geoid or missing_tract or duplicate_tract_rows:
        raise AggregationError(
            f"{region}: authoritative GEOID custody failure: bad_geoid={bad_geoid}, "
            f"missing_tract={missing_tract}, duplicate_tract_rows={duplicate_tract_rows}"
        )
    return {
        "sample_rows": sample_rows,
        "sample_unique": sample_unique,
        "bad_geoid": bad_geoid,
        "missing_tract": missing_tract,
        "duplicate_tract_rows": duplicate_tract_rows,
    }


def _validate_geometry_domain(key: str, values: Iterable[object]) -> list[str]:
    observed = sorted({str(value).upper() for value in values if value is not None})
    allowed = GEOMETRY_EXPECTATIONS[key]
    if not observed:
        raise AggregationError(f"{key}: empty geometry domain")
    unexpected = sorted(set(observed) - set(allowed))
    if unexpected:
        raise AggregationError(f"{key}: unexpected geometry types {unexpected}; allowed={sorted(allowed)}")
    return observed


def _domain_receipt(name: str, observed: Iterable[object]) -> dict[str, object]:
    values = sorted({str(value) for value in observed if value is not None})
    serialized = json.dumps(values, ensure_ascii=True, separators=(",", ":"))
    published = PUBLISHED_POLICY_VALUES[name]
    return {
        "observed_value_count": len(values),
        "observed_values_sha256": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
        "published_values_present": sorted(set(values).intersection(published)),
    }


def run_preflight(connection: object, region: str) -> dict[str, object]:
    """Execute all source/schema/custody/domain probes before aggregation."""
    r = source_registry(region)
    probes = preflight_probe_sql(region)
    schemas: dict[str, object] = {}
    for key, uri in r.items():
        description = connection.execute(probes[f"schema:{key}"]).fetchall()
        columns = [str(row[0]) for row in description]
        validate_source_schema(key, columns)
        schemas[key] = {
            "uri": uri,
            "columns": columns,
            "describe_sha256": _digest_schema(description),
        }

    custody_row = connection.execute(probes["custody"]).fetchone()
    if custody_row is None:
        raise AggregationError(f"{region}: custody probe returned no row")
    custody = _validate_custody(region, custody_row)

    geometries: dict[str, list[str]] = {}
    for key in GEOMETRY_EXPECTATIONS:
        rows = connection.execute(probes[f"geometry:{key}"]).fetchall()
        geometries[key] = _validate_geometry_domain(key, (row[0] for row in rows))

    road_rows = connection.execute(probes["domain:overture_roads"]).fetchall()
    tiger_rows = connection.execute(probes["domain:tiger_roads"]).fetchall()
    poi_rows = connection.execute(probes["domain:overture_pois"]).fetchall()
    poi_values = [row[0] for row in poi_rows]
    domains = {
        "overture_roads.class": _domain_receipt(
            "overture_roads.class", (row[0] for row in road_rows)
        ),
        "tiger_roads.MTFCC": _domain_receipt(
            "tiger_roads.MTFCC", (row[0] for row in tiger_rows)
        ),
        "overture_pois.school": _domain_receipt("overture_pois.school", poi_values),
        "overture_pois.fire": _domain_receipt("overture_pois.fire", poi_values),
        "overture_pois.ems": _domain_receipt("overture_pois.ems", poi_values),
    }

    connection.execute(probes["semantic:overture_poi_category"])
    axis_row = connection.execute(probes["semantic:axis_order"]).fetchone()
    if axis_row is None:
        raise AggregationError("axis-order smoke probe returned no row")
    smoke = float(axis_row[0])
    if not math.isfinite(smoke) or not 500.0 < smoke < 2000.0:
        raise AggregationError(f"EPSG axis-order smoke test failed: {smoke!r} metres")

    transcript = json.dumps(probes, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {
        "probe_sql_sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
        "schemas": schemas,
        "custody": custody,
        "geometry_domains": geometries,
        "value_domains": domains,
        "axis_order_smoke_meters": smoke,
    }


def build_plan(region: str) -> dict[str, object]:
    plan = _core.build_plan(region)
    probes = preflight_probe_sql(region)
    transcript = json.dumps(probes, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    plan["preflight"] = {
        "must_complete_before_aggregation": True,
        "probe_sql": probes,
        "probe_sql_sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
        "geometry_expectations": {k: sorted(v) for k, v in GEOMETRY_EXPECTATIONS.items()},
        "published_policy_values": {k: list(v) for k, v in PUBLISHED_POLICY_VALUES.items()},
    }
    return plan


def validate_rows(region: str, fieldnames: Sequence[str], rows: Sequence[Sequence[object]]):
    return _core.validate_rows(region, fieldnames, rows)


def execute_region(region: str, output: Path, receipt: Path) -> dict[str, object]:
    region = _core._region(region)
    if output.resolve() == receipt.resolve():
        raise AggregationError("output and receipt must be different paths")
    if output.exists() or receipt.exists():
        raise AggregationError("run outputs are create-exclusive; choose fresh paths")
    con = _connect_duckdb()
    try:
        # No aggregate query executes until source schema, GEOID custody, geometry,
        # and category/value-domain probes have passed on this same connection.
        preflight = run_preflight(con, region)
        cursor = con.execute(aggregate_query(region))
        fieldnames = [str(desc[0]) for desc in cursor.description]
        rows = cursor.fetchall()
        cleaned = validate_rows(region, fieldnames, rows)
        csv_text = render_csv(cleaned)
        csv_sha = hashlib.sha256(csv_text.encode("utf-8")).hexdigest()
        plan = build_plan(region)
        payload = {
            "schema": SCHEMA,
            "region": region,
            "duckdb_version": DUCKDB_VERSION,
            "overture_release": OVERTURE_RELEASE,
            "real_public_data_executed": True,
            "row_count": len(cleaned),
            "output_csv_sha256": csv_sha,
            "preflight": preflight,
            "plan": plan,
            "claims": {
                "zindi_registered": False,
                "submitted_to_zindi": False,
                "leaderboard_score_claimed": False,
                "award_claimed": False,
                "payment_claimed": False,
            },
        }
        body = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        envelope = {
            "payload": payload,
            "payload_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        }
        receipt_text = json.dumps(envelope, sort_keys=True, indent=2, ensure_ascii=True) + "\n"
        _write_new(output, csv_text)
        _write_new(receipt, receipt_text)
        return {"region": region, "rows": len(cleaned), "output_csv_sha256": csv_sha}
    finally:
        con.close()


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan_cmd = sub.add_parser("plan", help="emit deterministic no-download plan + preflight SQL")
    plan_cmd.add_argument("--region", required=True, choices=tuple(REGIONS))
    plan_cmd.add_argument("--sql", action="store_true", help="include aggregate SQL")
    run_cmd = sub.add_parser("run", help=f"execute one public region with DuckDB {DUCKDB_VERSION}")
    run_cmd.add_argument("--region", required=True, choices=tuple(REGIONS))
    run_cmd.add_argument("--output", required=True)
    run_cmd.add_argument("--receipt", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            payload = build_plan(args.region)
            if args.sql:
                payload["sql"] = aggregate_query(args.region)
            print(json.dumps(payload, sort_keys=True, indent=2))
        else:
            result = execute_region(args.region, Path(args.output), Path(args.receipt))
            print(json.dumps(result, sort_keys=True))
    except (AggregationError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
