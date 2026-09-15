#!/usr/bin/env python3
"""Recovered, fail-closed Mapping Equity public-data aggregation carrier.

Primary implementation credit belongs to ZSA-D6P2. This module wraps that stranded
implementation instead of rewriting it: `_zsa_d6p2_core.py` is the byte-exact donor.
ZHD-K8P3 adds the current M1 preflight/leak-fence contract while keeping the donor
branch immutable. ZFS-R7 supplied independent alternate-carrier review evidence.
Forge-56 adds one-generation source snapshots after independent A->B race review.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
import tempfile
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
SNAPSHOT_POLICY = "SINGLE_MATERIALIZATION_DESCRIPTOR_BOUND_SHA256"

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


def _source_reader_sql(key: str, uri: str) -> str:
    if key == "sample":
        return f"read_csv_auto({_sql_string(uri)}, header=true, all_varchar=true)"
    return f"read_parquet({_sql_string(uri)})"


def _snapshot_copy_sql(key: str, source_uri: str, target: Path) -> str:
    _safe_source(source_uri)
    reader = _source_reader_sql(key, source_uri)
    if key == "sample":
        options = "FORMAT CSV, HEADER true"
    else:
        options = "FORMAT PARQUET, COMPRESSION ZSTD"
    return f"COPY (SELECT * FROM {reader}) TO {_sql_string(str(target))} ({options})"


def _sha256_fd(fd: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    offset = 0
    while True:
        if hasattr(os, "pread"):
            block = os.pread(fd, 1024 * 1024, offset)
        else:
            os.lseek(fd, offset, os.SEEK_SET)
            block = os.read(fd, 1024 * 1024)
        if not block:
            break
        digest.update(block)
        size += len(block)
        offset += len(block)
    return digest.hexdigest(), size


def _descriptor_alias(fd: int) -> str:
    info = os.fstat(fd)
    for root in ("/proc/self/fd", "/dev/fd"):
        alias = f"{root}/{fd}"
        try:
            observed = os.stat(alias)
        except OSError:
            continue
        if (observed.st_dev, observed.st_ino) == (info.st_dev, info.st_ino):
            return alias
    raise AggregationError("descriptor-backed source reopening is unavailable")


class SourceSnapshots:
    def __init__(
        self,
        registry: Mapping[str, str],
        receipts: Mapping[str, Mapping[str, object]],
        fds: Mapping[str, int],
        identities: Mapping[str, tuple[int, int]],
    ) -> None:
        self.registry = dict(registry)
        self.receipts = {key: dict(value) for key, value in receipts.items()}
        self._fds = dict(fds)
        self._identities = dict(identities)
        self._closed = False

    def verify(self) -> None:
        if self._closed:
            raise AggregationError("source snapshots are closed")
        for key, fd in self._fds.items():
            expected = self.receipts[key]
            identity = self._identities[key]
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode):
                raise AggregationError(f"{key}: retained snapshot is not a regular file")
            if (info.st_dev, info.st_ino) != identity:
                raise AggregationError(f"{key}: retained snapshot generation changed")
            alias_info = os.stat(self.registry[key])
            if (alias_info.st_dev, alias_info.st_ino) != (info.st_dev, info.st_ino):
                raise AggregationError(f"{key}: descriptor alias generation changed")
            digest, size = _sha256_fd(fd)
            if size != expected["materialized_bytes"] or digest != expected["materialized_sha256"]:
                raise AggregationError(f"{key}: retained snapshot content changed")

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        for fd in self._fds.values():
            try:
                os.close(fd)
            except OSError:
                pass


def _materialize_sources(connection: object, region: str) -> SourceSnapshots:
    remote = source_registry(region)
    root = Path(tempfile.mkdtemp(prefix="mapping-equity-snapshot-"))
    fds: dict[str, int] = {}
    registry: dict[str, str] = {}
    receipts: dict[str, dict[str, object]] = {}
    identities: dict[str, tuple[int, int]] = {}
    root_fd: Optional[int] = None
    try:
        root_visible = os.lstat(root)
        root_flags = (
            os.O_RDONLY
            | getattr(os, "O_DIRECTORY", 0)
            | getattr(os, "O_NOFOLLOW", 0)
        )
        root_fd = os.open(root, root_flags)
        root_opened = os.fstat(root_fd)
        if not stat.S_ISDIR(root_opened.st_mode):
            raise AggregationError("snapshot staging root is not a directory")
        if (root_opened.st_dev, root_opened.st_ino) != (
            root_visible.st_dev,
            root_visible.st_ino,
        ):
            raise AggregationError("snapshot staging root changed during acquisition")
        if hasattr(os, "geteuid") and root_opened.st_uid != os.geteuid():
            raise AggregationError("snapshot staging root owner mismatch")
        os.fchmod(root_fd, 0o700)
        root_alias = _descriptor_alias(root_fd)

        for key, uri in remote.items():
            suffix = ".csv" if key == "sample" else ".parquet"
            name = f"{key}{suffix}"
            target = Path(root_alias) / name
            connection.execute(_snapshot_copy_sql(key, uri, target))
            visible = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            if not stat.S_ISREG(visible.st_mode) or visible.st_nlink != 1:
                raise AggregationError(f"{key}: materialized snapshot must be one regular file")
            if hasattr(os, "geteuid") and visible.st_uid != os.geteuid():
                raise AggregationError(f"{key}: materialized snapshot owner mismatch")

            fd: Optional[int] = None
            try:
                flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                fd = os.open(name, flags, dir_fd=root_fd)
                opened = os.fstat(fd)
                if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
                    raise AggregationError(f"{key}: acquired snapshot must be one regular file")
                if hasattr(os, "geteuid") and opened.st_uid != os.geteuid():
                    raise AggregationError(f"{key}: acquired snapshot owner mismatch")
                if (opened.st_dev, opened.st_ino) != (visible.st_dev, visible.st_ino):
                    raise AggregationError(f"{key}: materialized snapshot changed during acquisition")

                os.fchmod(fd, 0o400)
                hardened = os.fstat(fd)
                if (hardened.st_dev, hardened.st_ino) != (opened.st_dev, opened.st_ino):
                    raise AggregationError(f"{key}: snapshot generation changed during hardening")
                if stat.S_IMODE(hardened.st_mode) != 0o400:
                    raise AggregationError(f"{key}: snapshot permission hardening failed")

                digest, size = _sha256_fd(fd)
                alias = _descriptor_alias(fd)
                visible_before_unlink = os.stat(
                    name, dir_fd=root_fd, follow_symlinks=False
                )
                if (visible_before_unlink.st_dev, visible_before_unlink.st_ino) != (
                    opened.st_dev,
                    opened.st_ino,
                ):
                    raise AggregationError(f"{key}: snapshot path changed before unlink")
                os.unlink(name, dir_fd=root_fd)
                alias_info = os.stat(alias)
                if (alias_info.st_dev, alias_info.st_ino) != (
                    opened.st_dev,
                    opened.st_ino,
                ):
                    raise AggregationError(f"{key}: descriptor alias changed during acquisition")

                fds[key] = fd
                registry[key] = alias
                receipts[key] = {
                    "source_uri": uri,
                    "snapshot_format": "CSV" if key == "sample" else "PARQUET",
                    "materialized_sha256": digest,
                    "materialized_bytes": size,
                }
                identities[key] = (opened.st_dev, opened.st_ino)
                fd = None
            finally:
                if fd is not None:
                    try:
                        os.close(fd)
                    except OSError:
                        pass

        root_after = os.lstat(root)
        if (root_after.st_dev, root_after.st_ino) != (
            root_opened.st_dev,
            root_opened.st_ino,
        ):
            raise AggregationError("snapshot staging root changed before removal")
        os.close(root_fd)
        root_fd = None
        root.rmdir()

        snapshots = SourceSnapshots(registry, receipts, fds, identities)
        snapshots.verify()
        return snapshots
    except Exception:
        for fd in fds.values():
            try:
                os.close(fd)
            except OSError:
                pass
        if root_fd is not None:
            try:
                os.close(root_fd)
            except OSError:
                pass
        # Do not pathname-unlink children on a failed acquisition: after a custody
        # failure those names may denote a generation we never safely acquired.
        raise


def _bind_sql_to_snapshots(
    sql: str,
    remote_registry: Mapping[str, str],
    snapshot_registry: Mapping[str, str],
) -> str:
    if set(remote_registry) != set(snapshot_registry):
        raise AggregationError("snapshot registry key mismatch")
    bound = sql
    for key in remote_registry:
        bound = bound.replace(
            _sql_string(remote_registry[key]), _sql_string(snapshot_registry[key])
        )
    if HTTPS_ROOT in bound:
        raise AggregationError("remote source escaped snapshot binding")
    return bound


def run_preflight(
    connection: object,
    region: str,
    *,
    registry: Optional[Mapping[str, str]] = None,
    probes: Optional[Mapping[str, str]] = None,
    receipt_registry: Optional[Mapping[str, str]] = None,
    receipt_probes: Optional[Mapping[str, str]] = None,
) -> dict[str, object]:
    r = dict(source_registry(region) if registry is None else registry)
    probe_map = dict(preflight_probe_sql(region) if probes is None else probes)
    receipt_refs = dict(r if receipt_registry is None else receipt_registry)
    if set(r) != set(source_registry(region)) or set(receipt_refs) != set(r):
        raise AggregationError("preflight registry key mismatch")
    schemas: dict[str, object] = {}
    for key in r:
        description = connection.execute(probe_map[f"schema:{key}"]).fetchall()
        columns = [str(row[0]) for row in description]
        validate_source_schema(key, columns)
        schemas[key] = {
            "source_uri": receipt_refs[key],
            "columns": columns,
            "describe_sha256": _digest_schema(description),
        }

    custody_row = connection.execute(probe_map["custody"]).fetchone()
    if custody_row is None:
        raise AggregationError(f"{region}: custody probe returned no row")
    custody = _validate_custody(region, custody_row)

    geometries: dict[str, list[str]] = {}
    for key in GEOMETRY_EXPECTATIONS:
        rows = connection.execute(probe_map[f"geometry:{key}"]).fetchall()
        geometries[key] = _validate_geometry_domain(key, (row[0] for row in rows))

    road_rows = connection.execute(probe_map["domain:overture_roads"]).fetchall()
    tiger_rows = connection.execute(probe_map["domain:tiger_roads"]).fetchall()
    poi_rows = connection.execute(probe_map["domain:overture_pois"]).fetchall()
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

    connection.execute(probe_map["semantic:overture_poi_category"])
    axis_row = connection.execute(probe_map["semantic:axis_order"]).fetchone()
    if axis_row is None:
        raise AggregationError("axis-order smoke probe returned no row")
    smoke = float(axis_row[0])
    if not math.isfinite(smoke) or not 500.0 < smoke < 2000.0:
        raise AggregationError(f"EPSG axis-order smoke test failed: {smoke!r} metres")

    receipt_probe_map = probe_map if receipt_probes is None else dict(receipt_probes)
    transcript = json.dumps(receipt_probe_map, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
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
    plan["source_snapshot_policy"] = {
        "mode": SNAPSHOT_POLICY,
        "logical_materialization_scan_per_source": 1,
        "preflight_and_aggregate_share_snapshot": True,
        "content_digest": "SHA-256",
        "descriptor_bound_after_materialization": True,
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
    snapshots: Optional[SourceSnapshots] = None
    try:
        remote_registry = source_registry(region)
        snapshots = _materialize_sources(con, region)
        snapshots.verify()

        remote_probes = preflight_probe_sql(region)
        bound_probes = {
            name: _bind_sql_to_snapshots(sql, remote_registry, snapshots.registry)
            for name, sql in remote_probes.items()
        }
        preflight = run_preflight(
            con,
            region,
            registry=snapshots.registry,
            probes=bound_probes,
            receipt_registry=remote_registry,
            receipt_probes=remote_probes,
        )
        snapshots.verify()

        bound_query = _bind_sql_to_snapshots(
            aggregate_query(region), remote_registry, snapshots.registry
        )
        cursor = con.execute(bound_query)
        fieldnames = [str(desc[0]) for desc in cursor.description]
        rows = cursor.fetchall()
        snapshots.verify()

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
            "snapshot_policy": SNAPSHOT_POLICY,
            "source_snapshots": snapshots.receipts,
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
        if snapshots is not None:
            snapshots.close()
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
