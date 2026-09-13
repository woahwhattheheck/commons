from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

import mapping_equity_aggregate as agg


def row(geoid: str) -> dict[str, object]:
    return {name: (geoid if name == "GEOID" else 0) for name in agg.AGGREGATE_COLUMNS}


def region_rows(region: str) -> list[dict[str, object]]:
    count = agg.EXPECTED_SCORED_ROWS[region]
    return [row(f"{index + 1:011d}") for index in range(count)]


class MappingEquityAggregateTests(unittest.TestCase):
    def test_region_and_scorer_schema_contract(self) -> None:
        self.assertEqual(
            ("eastern-ok", "maricopa-az", "northern-ca", "south-central-tx"),
            agg.REGIONS,
        )
        self.assertEqual(9379, sum(agg.EXPECTED_SCORED_ROWS.values()))
        self.assertEqual("GEOID", agg.AGGREGATE_COLUMNS[0])
        self.assertNotIn("coverage_gap_score", agg.AGGREGATE_COLUMNS)
        try:
            import mapping_equity as scorer
        except ImportError:
            self.skipTest("landed scorer module not present in isolated authored-byte sandbox")
        self.assertEqual(tuple(scorer.AGGREGATE_COLUMNS), agg.AGGREGATE_COLUMNS)

    def test_official_filters_and_crs_are_literal_in_every_plan(self) -> None:
        for region in agg.REGIONS:
            sql = "\n".join(agg.build_region_sql(region))
            for road_class in agg.ROAD_CLASSES:
                self.assertIn(f"'{road_class}'", sql)
            for mtfcc in agg.TIGER_MTFCC:
                self.assertIn(f"'{mtfcc}'", sql)
            for category in (*agg.FIRE_CATEGORIES, *agg.EMS_CATEGORIES, *agg.SCHOOL_CATEGORIES):
                self.assertIn(f"'{category}'", sql)
            self.assertIn("'EPSG:5070'", sql)
            self.assertIn("always_xy := true", sql)
            self.assertIn("ST_Intersection", sql)
            self.assertIn("ST_PointOnSurface", sql)
            self.assertIn("cbp_estab", sql)
            self.assertNotIn("coverage_gap_score", sql)
            self.assertNotIn("coverage-gap.csv", sql)

    def test_source_manifest_is_exact_four_region_challenge_data_only(self) -> None:
        manifest = agg.source_manifest()
        self.assertEqual(agg.OVERTURE_RELEASE, manifest["overture_release"])
        self.assertEqual(set(agg.REGIONS), set(manifest["regions"]))
        for region in agg.REGIONS:
            uris = [entry["uri"] for entry in manifest["regions"][region]["objects"]]
            self.assertEqual(list(agg.required_source_uris(region)), uris)
            self.assertTrue(all(uri.startswith(agg.SOURCE_ROOT + "/") for uri in uris))
            self.assertTrue(all("coverage-gap" not in uri for uri in uris))
            self.assertEqual(len(uris), len(set(uris)))

    def test_validate_rows_preserves_geoid_text_and_column_order(self) -> None:
        rows = region_rows("northern-ca")
        agg.validate_rows("northern-ca", rows)
        bad = [dict(item) for item in rows]
        bad[0]["GEOID"] = 123
        with self.assertRaisesRegex(agg.AggregationError, "invalid GEOID"):
            agg.validate_rows("northern-ca", bad)
        reordered = [dict(item) for item in rows]
        first = reordered[0]
        reordered[0] = {key: first[key] for key in reversed(first)}
        with self.assertRaisesRegex(agg.AggregationError, "columns/order mismatch"):
            agg.validate_rows("northern-ca", reordered)

    def test_validate_rows_rejects_duplicate_and_nonfinite(self) -> None:
        rows = region_rows("northern-ca")
        rows[1]["GEOID"] = rows[0]["GEOID"]
        with self.assertRaisesRegex(agg.AggregationError, "duplicate GEOID"):
            agg.validate_rows("northern-ca", rows)
        rows = region_rows("northern-ca")
        rows[0]["tiger_road_length"] = float("nan")
        with self.assertRaisesRegex(agg.AggregationError, "invalid tiger_road_length"):
            agg.validate_rows("northern-ca", rows)

    def test_csv_is_deterministic_and_has_no_answer_column(self) -> None:
        rows = region_rows("northern-ca")
        first = agg.rows_to_csv(rows)
        second = agg.rows_to_csv(rows)
        self.assertEqual(first, second)
        header = first.splitlines()[0]
        self.assertEqual(",".join(agg.AGGREGATE_COLUMNS), header)
        self.assertNotIn("coverage_gap_score", header)

    def test_receipt_verifies_and_tamper_fails_closed(self) -> None:
        outputs = {
            region: agg.rows_to_csv(region_rows(region)).encode("utf-8")
            for region in agg.REGIONS
        }
        receipt = agg.build_receipt(
            outputs,
            engine={"duckdb_version": "v1.5.4-test"},
            metadata_lookup=lambda uri: {"etag": "fixture", "content_length": "1"},
        )
        self.assertFalse(receipt["payload"]["claims"]["zindi_submitted"])
        self.assertFalse(receipt["payload"]["policy"]["coverage_gap_score_consumed"])
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for region, data in outputs.items():
                (root / f"{region}-aggregates.csv").write_bytes(data)
            result = agg.verify_receipt(root, receipt)
            self.assertTrue(result["verified"])
            self.assertEqual(9379, result["aggregate_rows_verified"])
            target = root / "maricopa-az-aggregates.csv"
            target.write_bytes(target.read_bytes() + b"\n")
            with self.assertRaisesRegex(agg.AggregationError, "aggregate digest mismatch"):
                agg.verify_receipt(root, receipt)

    def test_receipt_payload_tamper_fails_closed(self) -> None:
        outputs = {
            region: agg.rows_to_csv(region_rows(region)).encode("utf-8")
            for region in agg.REGIONS
        }
        receipt = agg.build_receipt(outputs, engine={}, metadata_lookup=lambda uri: {})
        receipt["payload"]["claims"]["prize_claimed"] = True
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for region, data in outputs.items():
                (root / f"{region}-aggregates.csv").write_bytes(data)
            with self.assertRaisesRegex(agg.AggregationError, "payload digest mismatch"):
                agg.verify_receipt(root, receipt)

    def test_safe_write_is_create_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "receipt.json"
            agg._safe_write_new(target, b"one")
            self.assertEqual(b"one", target.read_bytes())
            with self.assertRaises(FileExistsError):
                agg._safe_write_new(target, b"two")
            self.assertEqual(b"one", target.read_bytes())

    def test_plan_rejects_unknown_region_and_unsafe_layer(self) -> None:
        with self.assertRaisesRegex(agg.AggregationError, "unknown region"):
            agg.build_region_sql("not-a-region")
        with self.assertRaisesRegex(agg.AggregationError, "unsafe layer"):
            agg.reference_uri("eastern-ok", "../coverage-gap")

    def test_cli_plan_is_machine_readable(self) -> None:
        manifest = agg.source_manifest()
        serialized = json.dumps(manifest, sort_keys=True)
        self.assertIn("2026-08-19.0", serialized)
        self.assertNotIn("coverage-gap.csv", serialized)


if __name__ == "__main__":
    unittest.main()
