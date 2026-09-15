from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import aggregate as a


class RecoveryLeakFenceTests(unittest.TestCase):
    def test_encoded_and_case_variant_answer_paths_fail_closed(self) -> None:
        root = a.HTTPS_ROOT + "/reference/eastern-ok/"
        hostile = (
            root + "eastern-ok-COVERAGE-gap.csv",
            root + "eastern-ok-%63overage%2Dgap.csv",
            root + "eastern-ok-%2563overage%252Dgap.csv",
            root + "eastern-ok-reference%2Danswer.csv",
            root + "eastern-ok-answer%5Fkey.csv",
        )
        for uri in hostile:
            with self.subTest(uri=uri), self.assertRaisesRegex(a.AggregationError, "forbidden"):
                a._safe_source(uri)

    def test_query_fragment_and_cross_origin_sources_fail_closed(self) -> None:
        clean = a.source_registry("eastern-ok")["overture_roads"]
        with self.assertRaises(a.AggregationError):
            a._safe_source(clean + "?alt=coverage")
        with self.assertRaises(a.AggregationError):
            a._safe_source("https://example.com/reference/eastern-ok/eastern-ok-overture-roads.parquet")

    def test_encoded_answer_like_schema_label_fails_closed(self) -> None:
        columns = ["GEOID", "cbp_estab", "reference%5Fanswer"]
        with self.assertRaisesRegex(a.AggregationError, "forbidden"):
            a.validate_source_schema("cbp", columns)


class RecoveryPreflightTests(unittest.TestCase):
    def test_plan_binds_complete_preflight_transcript(self) -> None:
        one = a.build_plan("northern-ca")
        two = a.build_plan("northern-ca")
        self.assertEqual(one, two)
        preflight = one["preflight"]
        self.assertTrue(preflight["must_complete_before_aggregation"])
        probes = preflight["probe_sql"]
        for key in a.source_registry("northern-ca"):
            self.assertIn(f"schema:{key}", probes)
        self.assertIn("custody", probes)
        for key in a.GEOMETRY_EXPECTATIONS:
            self.assertIn(f"geometry:{key}", probes)
        self.assertIn("domain:overture_roads", probes)
        self.assertIn("domain:tiger_roads", probes)
        self.assertIn("domain:overture_pois", probes)
        self.assertIn("semantic:axis_order", probes)
        serialized = json.dumps(preflight, sort_keys=True)
        self.assertIn("ST_GeometryType", serialized)
        self.assertIn("regexp_full_match", serialized)
        self.assertIn("categories.primary", serialized)
        self.assertIn("DESCRIBE SELECT", serialized)
        self.assertNotIn("coverage-gap.csv", serialized.lower())
        self.assertEqual(
            a.SNAPSHOT_POLICY,
            one["source_snapshot_policy"]["mode"],
        )
        self.assertTrue(
            one["source_snapshot_policy"]["preflight_and_aggregate_share_snapshot"]
        )

    def test_custody_requires_exact_authoritative_text_universe(self) -> None:
        expected = a.REGIONS["northern-ca"]
        receipt = a._validate_custody("northern-ca", (expected, expected, 0, 0, 0))
        self.assertEqual(expected, receipt["sample_unique"])
        hostile = (
            (expected - 1, expected - 1, 0, 0, 0),
            (expected, expected - 1, 0, 0, 0),
            (expected, expected, 1, 0, 0),
            (expected, expected, 0, 1, 0),
            (expected, expected, 0, 0, 1),
        )
        for row in hostile:
            with self.subTest(row=row), self.assertRaises(a.AggregationError):
                a._validate_custody("northern-ca", row)

    def test_geometry_domain_rejects_unknown_or_empty_types(self) -> None:
        self.assertEqual(
            ["LINESTRING", "MULTILINESTRING"],
            a._validate_geometry_domain("overture_roads", ["MULTILINESTRING", "LINESTRING"]),
        )
        with self.assertRaisesRegex(a.AggregationError, "unexpected geometry"):
            a._validate_geometry_domain("overture_roads", ["POLYGON"])
        with self.assertRaisesRegex(a.AggregationError, "empty geometry"):
            a._validate_geometry_domain("overture_roads", [])

    def test_observed_domain_receipt_is_deterministic_without_forcing_presence(self) -> None:
        receipt = a._domain_receipt("overture_roads.class", ["residential", "motorway", "motorway"])
        self.assertEqual(2, receipt["observed_value_count"])
        self.assertEqual(["motorway"], receipt["published_values_present"])
        self.assertEqual(
            receipt,
            a._domain_receipt("overture_roads.class", ["motorway", "residential"]),
        )

    def test_unknown_policy_category_fails_before_query_generation(self) -> None:
        with self.assertRaisesRegex(a.AggregationError, "policy category drift"):
            a._validate_policy_categories(
                "overture_roads.class",
                (*a.ROAD_CLASSES[:-1], "space_laser"),
            )
        with self.assertRaisesRegex(a.AggregationError, "unknown published filter domain"):
            a._validate_policy_categories("unknown.domain", ("x",))

    def test_domain_probe_sql_is_exact_source_scoped(self) -> None:
        registry = a.source_registry("maricopa-az")
        roads = a._domain_probe_sql("overture_roads", registry["overture_roads"])
        tiger = a._domain_probe_sql("tiger_roads", registry["tiger_roads"])
        pois = a._domain_probe_sql("overture_pois", registry["overture_pois"])
        self.assertIn('"class"', roads)
        self.assertIn("MTFCC", tiger)
        self.assertIn("categories.primary", pois)
        self.assertIn("maricopa-az", roads)


class SourceGenerationBindingTests(unittest.TestCase):
    class _CopyConnection:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def execute(self, sql: str):
            self.calls.append(sql)
            match = re.search(r"\bTO '((?:''|[^'])+)' \(", sql)
            if match is None:
                raise AssertionError(f"expected COPY target in {sql!r}")
            target = Path(match.group(1).replace("''", "'"))
            payload = f"snapshot-{len(self.calls):02d}\n".encode("ascii")
            target.write_bytes(payload)
            return self

    @unittest.skipIf(os.name == "nt", "descriptor-backed snapshot aliases are POSIX-only")
    def test_every_remote_source_is_materialized_once_then_unlinked(self) -> None:
        con = self._CopyConnection()
        remote = a.source_registry("northern-ca")
        snapshots = a._materialize_sources(con, "northern-ca")
        try:
            self.assertEqual(len(remote), len(con.calls))
            for key, uri in remote.items():
                self.assertEqual(1, sum(uri in call for call in con.calls), key)
                self.assertNotIn(a.HTTPS_ROOT, snapshots.registry[key])
                receipt = snapshots.receipts[key]
                self.assertEqual(uri, receipt["source_uri"])
                self.assertEqual(
                    hashlib.sha256(
                        f"snapshot-{list(remote).index(key) + 1:02d}\n".encode("ascii")
                    ).hexdigest(),
                    receipt["materialized_sha256"],
                )
                self.assertNotIn("device", receipt)
                self.assertNotIn("inode", receipt)
                self.assertEqual(
                    0o400,
                    stat.S_IMODE(os.fstat(snapshots._fds[key]).st_mode),
                )
            snapshots.verify()
        finally:
            snapshots.close()

    def test_preflight_and_aggregate_sql_cannot_reopen_same_remote_uri(self) -> None:
        remote = a.source_registry("northern-ca")
        snapshots = {
            key: f"/proc/self/fd/{700 + index}"
            for index, key in enumerate(remote)
        }
        bound_query = a._bind_sql_to_snapshots(
            a.aggregate_query("northern-ca"), remote, snapshots
        )
        bound_probes = {
            name: a._bind_sql_to_snapshots(sql, remote, snapshots)
            for name, sql in a.preflight_probe_sql("northern-ca").items()
        }
        transcript = json.dumps(bound_probes, sort_keys=True) + bound_query
        self.assertNotIn(a.HTTPS_ROOT, transcript)
        for uri in remote.values():
            self.assertNotIn(uri, transcript)
        for alias in snapshots.values():
            self.assertIn(alias, transcript)

    def test_binding_fails_closed_if_any_remote_source_escapes(self) -> None:
        remote = a.source_registry("eastern-ok")
        snapshots = dict(remote)
        snapshots["sample"] = "/proc/self/fd/999"
        with self.assertRaisesRegex(a.AggregationError, "remote source escaped"):
            a._bind_sql_to_snapshots(
                a.aggregate_query("eastern-ok"), remote, snapshots
            )

    @unittest.skipIf(os.name == "nt", "POSIX no-follow acquisition hostile")
    def test_leaf_to_foreign_symlink_swap_cannot_chmod_victim(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            parent_path = Path(parent)
            victim = parent_path / "victim.db"
            victim.write_bytes(b"foreign-victim\n")
            os.chmod(victim, 0o644)
            victim_before = victim.read_bytes(), stat.S_IMODE(os.stat(victim).st_mode)
            real_mkdtemp = a.tempfile.mkdtemp
            real_open = a.os.open
            swapped = False

            def local_mkdtemp(*, prefix: str):
                return real_mkdtemp(prefix=prefix, dir=parent)

            def racing_open(path, flags, *args, dir_fd=None, **kwargs):
                nonlocal swapped
                if (
                    not swapped
                    and dir_fd is not None
                    and isinstance(path, str)
                    and (path.endswith(".csv") or path.endswith(".parquet"))
                ):
                    os.unlink(path, dir_fd=dir_fd)
                    os.symlink(victim, path, dir_fd=dir_fd)
                    swapped = True
                return real_open(path, flags, *args, dir_fd=dir_fd, **kwargs)

            with mock.patch.object(a.tempfile, "mkdtemp", side_effect=local_mkdtemp), \
                 mock.patch.object(a.os, "open", side_effect=racing_open):
                with self.assertRaises(OSError):
                    a._materialize_sources(self._CopyConnection(), "northern-ca")

            self.assertTrue(swapped)
            self.assertEqual(victim_before[0], victim.read_bytes())
            self.assertEqual(victim_before[1], stat.S_IMODE(os.stat(victim).st_mode))

    @unittest.skipIf(os.name == "nt", "POSIX descriptor leak hostile")
    def test_alias_failure_closes_just_opened_snapshot_descriptor(self) -> None:
        with tempfile.TemporaryDirectory() as parent:
            real_mkdtemp = a.tempfile.mkdtemp
            real_alias = a._descriptor_alias
            captured: list[int] = []

            def local_mkdtemp(*, prefix: str):
                return real_mkdtemp(prefix=prefix, dir=parent)

            def failing_alias(fd: int) -> str:
                if stat.S_ISDIR(os.fstat(fd).st_mode):
                    return real_alias(fd)
                captured.append(fd)
                raise a.AggregationError("forced alias failure")

            with mock.patch.object(a.tempfile, "mkdtemp", side_effect=local_mkdtemp), \
                 mock.patch.object(a, "_descriptor_alias", side_effect=failing_alias):
                with self.assertRaisesRegex(a.AggregationError, "forced alias failure"):
                    a._materialize_sources(self._CopyConnection(), "northern-ca")

            self.assertEqual(1, len(captured))
            with self.assertRaises(OSError):
                os.fstat(captured[0])


if __name__ == "__main__":
    unittest.main()
