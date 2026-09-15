from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PKG = ROOT / "revenue" / "streaming_rendition_release_gate"
sys.path.insert(0, str(ROOT))

from revenue.streaming_rendition_release_gate import gate
from revenue.streaming_rendition_release_gate.fixture import build_fixture, canonical_fixture_bytes


class StreamingRenditionReleaseGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.packets, cls.fault_assets = build_fixture()
        cls.fixture_bytes = canonical_fixture_bytes()
        cls.manifest = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))

    def test_canonical_fixture_exact_acceptance(self):
        validation = gate.validate_packets(copy.deepcopy(self.packets))
        rows = validation["results"]
        ready = [row for row in rows if row["status"] == gate.RELEASE_READY]
        held = [row for row in rows if row["status"] == gate.HOLD]
        self.assertEqual(168, len(rows))
        self.assertEqual(140, len(ready))
        self.assertEqual(28, len(held))
        required = {
            gate.REASON_MISSING_RENDITION,
            gate.REASON_CODEC_PROFILE_MISMATCH,
            gate.REASON_SEGMENT_DISCONTINUITY,
            gate.REASON_CAPTION_AUDIO_ALIGNMENT_GAP,
            gate.REASON_DRM_REFERENCE_MISMATCH,
            gate.REASON_CHECKSUM_ORPHAN_ARTIFACT,
            gate.REASON_PUBLICATION_WINDOW_CONFLICT,
        }
        self.assertEqual(Counter({reason: 4 for reason in required}), Counter(row["reason"] for row in held))
        self.assertEqual(hashlib.sha256(self.fixture_bytes).hexdigest(), self.manifest["fixture"]["canonical_sha256"])
        self.assertEqual(validation["projection_sha256"], self.manifest["projection_sha256"])

    def test_no_defective_fixture_asset_is_ready(self):
        validation = gate.validate_packets(copy.deepcopy(self.packets))
        by_asset = {row["asset_id"]: row for row in validation["results"]}
        fault_assets = {
            asset
            for assets in self.manifest["fixture"]["fault_assets"].values()
            for asset in assets
        }
        actual_holds = {asset for asset, row in by_asset.items() if row["status"] == gate.HOLD}
        self.assertEqual(fault_assets, actual_holds)

    def test_projection_is_byte_identical_on_replay(self):
        first = gate.validate_packets(copy.deepcopy(self.packets))
        second = gate.validate_packets(copy.deepcopy(self.packets))
        self.assertEqual(first["projection"], second["projection"])
        self.assertEqual(first["projection_sha256"], second["projection_sha256"])

    def test_bool_cannot_masquerade_as_segment_integer(self):
        packet = copy.deepcopy(self.packets[0])
        packet["variants"][0]["segments"][0]["start_ms"] = False
        row = gate.validate_packet(packet)
        self.assertEqual(gate.HOLD, row["status"])
        self.assertEqual(gate.REASON_INVALID_SCHEMA, row["reason"])

    def test_duplicate_rendition_fails_closed(self):
        packet = copy.deepcopy(self.packets[0])
        packet["variants"][1]["name"] = packet["variants"][0]["name"]
        row = gate.validate_packet(packet)
        self.assertEqual(gate.HOLD, row["status"])
        self.assertEqual(gate.REASON_INVALID_SCHEMA, row["reason"])

    def test_variant_checksum_mismatch_fails_closed(self):
        packet = copy.deepcopy(self.packets[0])
        packet["variants"][0]["sha256"] = "0" * 64
        row = gate.validate_packet(packet)
        self.assertEqual(gate.HOLD, row["status"])
        self.assertEqual(gate.REASON_CHECKSUM_ORPHAN_ARTIFACT, row["reason"])

    def test_orphan_artifact_fails_closed(self):
        packet = copy.deepcopy(self.packets[0])
        packet["artifacts"]["orphan"] = "0" * 64
        row = gate.validate_packet(packet)
        self.assertEqual(gate.HOLD, row["status"])
        self.assertEqual(gate.REASON_CHECKSUM_ORPHAN_ARTIFACT, row["reason"])

    def test_cdn_region_drift_fails_closed(self):
        packet = copy.deepcopy(self.packets[0])
        packet["cdn_region"] = "eu-west-1"
        row = gate.validate_packet(packet)
        self.assertEqual(gate.HOLD, row["status"])
        self.assertEqual(gate.REASON_CDN_REGION_MISMATCH, row["reason"])

    def test_live_end_time_fails_schema_closed(self):
        live = next(copy.deepcopy(packet) for packet in self.packets if packet["mode"] == "LIVE")
        live["publication_window"]["end"] = "2026-09-13T13:00:00Z"
        row = gate.validate_packet(live)
        self.assertEqual(gate.HOLD, row["status"])
        self.assertEqual(gate.REASON_INVALID_SCHEMA, row["reason"])

    def test_unknown_field_fails_schema_closed(self):
        packet = copy.deepcopy(self.packets[0])
        packet["publish_now"] = True
        row = gate.validate_packet(packet)
        self.assertEqual(gate.HOLD, row["status"])
        self.assertEqual(gate.REASON_INVALID_SCHEMA, row["reason"])

    def test_exported_surface_has_no_effect_authority(self):
        prohibited = {
            "publish", "transcode", "upload", "deploy", "release",
            "write_cdn", "drm_secret", "rights_decision", "send",
        }
        public_names = set(gate.__all__)
        self.assertTrue(prohibited.isdisjoint(public_names))
        source = (PKG / "gate.py").read_text(encoding="utf-8")
        self.assertNotIn("requests.", source)
        self.assertNotIn("urllib.", source)
        self.assertNotIn("subprocess", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
