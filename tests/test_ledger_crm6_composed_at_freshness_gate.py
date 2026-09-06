"""Freshness reports the saved timestamp's age without changing peer access."""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "crm6_freshness_handoff", ROOT / "host/lm_gtm_relationship_handoff.py"
)
assert spec and spec.loader
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)
idx = handoff.idx
STAMP = "2026-09-05T08:00:00Z"


class FreshnessTests(unittest.TestCase):
    def test_existing_twelve_hour_boundary(self):
        composed = idx.parse_time(STAMP)
        for elapsed, expected in [
            (dt.timedelta(0), "FRESH"),
            (dt.timedelta(hours=1), "FRESH"),
            (dt.timedelta(hours=10), "FRESH"),
            (dt.timedelta(hours=12), "FRESH"),
            (dt.timedelta(hours=12, microseconds=1), "STALE"),
            (dt.timedelta(hours=13), "STALE"),
        ]:
            with self.subTest(elapsed=elapsed):
                result = idx.composed_at_freshness(
                    composed_at_value=STAMP, now=composed + elapsed
                )
                self.assertEqual(result["status"], expected)
                self.assertEqual(result["threshold_hours"], 12)
                self.assertEqual("stale_warning" in result, expected == "STALE")
                self.assertEqual(result["cash_usd"], 0)

    def test_offsets_compare_instants(self):
        result = idx.composed_at_freshness(
            composed_at_value="2026-09-05T01:00:00-07:00",
            now=idx.parse_time("2026-09-05T21:00:00+01:00"),
        )
        self.assertEqual(result["status"], "FRESH")
        self.assertEqual(result["age_hours"], 12)
        self.assertEqual(result["as_of"], "2026-09-05T20:00:00Z")

    def test_reads_saved_header_without_recomposing_or_writing(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = idx.default_paths(Path(folder))
            paths["index"].parent.mkdir(parents=True)
            paths["index"].write_text(json.dumps({
                "kind": idx.KIND_HEADER, "composed_at": STAMP
            }) + "\n", encoding="utf-8")
            paths["state"].write_text(json.dumps({
                "composed_at": "2026-09-05T20:00:00Z"
            }), encoding="utf-8")
            before = {key: paths[key].read_bytes() for key in ("index", "state")}
            with patch.object(idx, "build_index", side_effect=AssertionError("must not rebuild")):
                result = idx.composed_at_freshness(
                    paths, now=idx.parse_time("2026-09-05T21:00:00Z")
                )
            self.assertEqual(result["status"], "STALE")
            self.assertEqual(result["composed_at"], STAMP)
            self.assertEqual(before, {key: paths[key].read_bytes() for key in before})

    def test_state_fallback_when_index_absent(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = idx.default_paths(Path(folder))
            paths["state"].parent.mkdir(parents=True)
            paths["state"].write_text(json.dumps({"composed_at": STAMP}), encoding="utf-8")
            self.assertEqual(idx.read_committed_composed_at(paths), STAMP)
            self.assertFalse(paths["index"].exists())

    def test_missing_or_invalid_saved_timestamp_is_not_fresh(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = idx.default_paths(Path(folder))
            with self.assertRaises(idx.IndexError_):
                idx.read_committed_composed_at(paths)
            paths["index"].parent.mkdir(parents=True)
            paths["state"].write_text(json.dumps({"composed_at": STAMP}), encoding="utf-8")
            for content in [
                "invalid json\n",
                json.dumps({"kind": idx.KIND_ROW, "composed_at": STAMP}),
                json.dumps({"kind": idx.KIND_HEADER, "composed_at": ""}),
            ]:
                with self.subTest(content=content):
                    paths["index"].write_text(content, encoding="utf-8")
                    with self.assertRaises(idx.IndexError_):
                        idx.read_committed_composed_at(paths)

    def test_invalid_future_or_timezone_free_clock_is_not_fresh(self):
        clock = idx.parse_time(STAMP)
        for composed in ("", "invalid", "2026-09-05T08:00:00", "2026-09-05T08:00:01Z", 123):
            with self.subTest(composed=composed):
                with self.assertRaises(idx.IndexError_):
                    idx.composed_at_freshness(composed_at_value=composed, now=clock)
        with self.assertRaises(idx.IndexError_):
            idx.composed_at_freshness(composed_at_value=STAMP, now=dt.datetime(2026, 9, 5, 9))

    def test_actual_freshness_cli_exit_codes_and_saved_source(self):
        stamp = idx.read_committed_composed_at()
        for hours, status, exit_code in [(1, "FRESH", 0), (13, "STALE", 2)]:
            instant = idx.parse_time(stamp) + dt.timedelta(hours=hours)
            process = subprocess.run([
                sys.executable, str(ROOT / "host/lm_gtm_index.py"),
                "freshness", "--as-of", idx.iso_z(instant),
            ], text=True, capture_output=True, cwd=ROOT)
            self.assertEqual(process.returncode, exit_code, process.stderr)
            result = json.loads(process.stdout)
            self.assertEqual(result["status"], status)
            self.assertEqual(result["composed_at"], stamp)
            self.assertEqual(result["age_hours"], hours)
        process = subprocess.run([
            sys.executable, str(ROOT / "host/lm_gtm_index.py"),
            "freshness", "--as-of", "2026-09-05T20:00:00",
        ], text=True, capture_output=True, cwd=ROOT)
        self.assertEqual(process.returncode, 1)
        self.assertNotIn("Traceback", process.stderr)

    def test_default_handoff_does_not_require_freshness(self):
        with patch.object(idx, "composed_at_freshness", side_effect=AssertionError("optional")):
            packet = handoff.relationship_handoff("composio")
        self.assertNotIn("index_freshness", packet)
        self.assertIsNotNone(handoff.successor_reads_next_action(packet))

    def test_stale_and_unknown_annotations_preserve_full_packet(self):
        original = handoff.relationship_handoff("composio")
        stamp = idx.read_committed_composed_at()
        packet = handoff.relationship_handoff(
            "composio", include_index_freshness=True,
            as_of=idx.parse_time(stamp) + dt.timedelta(hours=13),
        )
        self.assertEqual(packet["index_freshness"]["status"], "STALE")
        self.assertEqual(handoff.successor_reads_next_action(packet),
                         handoff.successor_reads_next_action(original))
        self.assertIn('"status": "STALE"', handoff.successor_brief(packet))
        packet.pop("index_freshness")
        self.assertEqual(packet, original)
        with patch.object(idx, "read_committed_composed_at", side_effect=idx.IndexError_("missing")):
            packet = handoff.relationship_handoff("composio", include_index_freshness=True)
        self.assertEqual(packet.pop("index_freshness")["status"], "UNKNOWN")
        self.assertEqual(packet, original)

    def test_actual_handoff_cli_remains_usable_with_stale_metadata(self):
        stamp = idx.read_committed_composed_at()
        instant = idx.iso_z(idx.parse_time(stamp) + dt.timedelta(hours=13))
        command = [
            sys.executable, str(ROOT / "host/lm_gtm_relationship_handoff.py"),
            "composio", "--index-freshness", "--as-of", instant,
        ]
        process = subprocess.run(command, text=True, capture_output=True, cwd=ROOT)
        self.assertEqual(process.returncode, 0, process.stderr)
        packet = json.loads(process.stdout)
        self.assertEqual(packet["index_freshness"]["status"], "STALE")
        self.assertIsNotNone(handoff.successor_reads_next_action(packet))
        process = subprocess.run(command + ["--brief"], text=True, capture_output=True, cwd=ROOT)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn('"status": "STALE"', process.stdout)
        self.assertIn("successor_next_action: SOURCED", process.stdout)


if __name__ == "__main__":
    unittest.main()
