#!/usr/bin/env python3
"""Feature-film organ reference: exact bytes, deterministic source, zero fabricated execution."""
from __future__ import annotations

import copy
import hashlib
import io
import os
import sys
from pathlib import Path
import unittest
from contextlib import redirect_stdout


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from muhl_film_organ import (
    DEFAULT_CARD,
    DEFAULT_DOOR,
    DEFAULT_REEL,
    DEFAULT_SOURCE,
    EXPECTED_BYTES,
    EXPECTED_FINAL_STATE,
    EXPECTED_LIVE_CELLS,
    EXPECTED_MAGIC,
    EXPECTED_PREFIX_BITS,
    EXPECTED_SHA256,
    classify,
    lcg_reference,
    load_json,
    main,
    measure_root,
    self_test,
)


class TestMuhlFilmOrgan(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(ROOT, "ground", "muhl_film_organ", "source.json"), encoding="utf-8") as handle:
            self.source = load_json(handle.read())

    def live_row(self):
        row = measure_root(ROOT)
        self.assertEqual(row["misses"], [])
        return row

    def assert_not_landed(self, row, label):
        verdict = classify(row)
        self.assertEqual(verdict["state"], "NOT_LANDED", (label, verdict))

    def test_self_test(self):
        self.assertEqual(self_test(), "ok")

    def test_deterministic_lcg_reference(self):
        result = lcg_reference(self.source)
        self.assertEqual(result["state"], "REFERENCE_SOURCE_VERIFIED")
        self.assertEqual(result["cells"], 4096)
        self.assertEqual(result["live_cells"], EXPECTED_LIVE_CELLS)
        self.assertEqual(result["final_state"], EXPECTED_FINAL_STATE)
        self.assertEqual(result["prefix_bits"], EXPECTED_PREFIX_BITS)
        self.assertEqual(result["fps"] * result["runtime_s_declared"], 129600)

    def test_live_tree_is_reference_integrated_not_executed(self):
        row = self.live_row()
        self.assertEqual(row["reel"]["bytes"], EXPECTED_BYTES)
        self.assertEqual(row["reel"]["magic"], EXPECTED_MAGIC.decode("ascii"))
        self.assertEqual(row["reel"]["sha256"], EXPECTED_SHA256)
        verdict = classify(row)
        self.assertEqual(verdict["state"], "SPEC_INTEGRATED")
        self.assertFalse(verdict["movie_executed"])
        self.assertEqual(verdict["executed_pulses"], 0)

    def test_reel_hash_is_directly_verified(self):
        path = os.path.join(ROOT, "muhl", "docs", "FILM_REEL.pfc")
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            self.assertEqual(handle.read(8), EXPECTED_MAGIC)
            handle.seek(0)
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        self.assertEqual(os.path.getsize(path), EXPECTED_BYTES)
        self.assertEqual(digest.hexdigest(), EXPECTED_SHA256)

    def test_catalog_reel_is_bound_to_measured_bytes(self):
        for replacement in (None, [], "not-an-object"):
            row = self.live_row()
            row["catalog"]["reel"] = replacement
            self.assert_not_landed(row, "catalog.reel type")
        for key, value in (("bytes", 1), ("magic", "FORGED"), ("sha256", "0" * 64)):
            row = self.live_row()
            row["catalog"]["reel"][key] = value
            self.assert_not_landed(row, "catalog.reel." + key)

    def test_catalog_identity_and_path_declarations_are_exact(self):
        expected = {
            "kind": "MUHL_FILM_ORGAN_REFERENCE",
            "state": "REFERENCE_ONLY",
            "reference_organ": DEFAULT_REEL.replace(os.sep, "/"),
            "source_fixture": DEFAULT_SOURCE.replace(os.sep, "/"),
            "public_surface": DEFAULT_DOOR.replace(os.sep, "/"),
            "card": DEFAULT_CARD.replace(os.sep, "/"),
            "instrument": "host/muhl_film_organ.py",
            "feature_length_pulses_declared": 129600,
        }
        row = self.live_row()
        for key, value in expected.items():
            self.assertEqual(row["catalog"][key], value, key)
            changed = copy.deepcopy(row)
            changed["catalog"][key] = "FORGED" if isinstance(value, str) else 1
            self.assert_not_landed(changed, "catalog." + key)

    def test_source_receipt_is_bound_to_recomputed_lcg(self):
        fields = {
            "kind": "MUHL_FILM_SOURCE",
            "organ": DEFAULT_REEL.replace(os.sep, "/"),
            "expected_live_cells": EXPECTED_LIVE_CELLS,
            "expected_final_state": EXPECTED_FINAL_STATE,
            "expected_prefix_bits": EXPECTED_PREFIX_BITS,
            "feature_length_pulses_declared": 129600,
            "fps": 24,
            "runtime_s_declared": 5400,
        }
        row = self.live_row()
        for key, value in fields.items():
            self.assertEqual(row["source"][key], value, key)
            changed = copy.deepcopy(row)
            changed["source"][key] = "FORGED" if isinstance(value, str) else value + 1
            changed["source_measure"] = row["source_measure"]
            self.assert_not_landed(changed, "source." + key)

    def test_every_existing_source_action_flag_is_false(self):
        flags = (
            "movie_executed",
            "byte_exact_feature_run",
            "host_frame_simulation",
            "invented_dest",
            "invented_mouth",
            "fire_337",
            "pulse_78",
            "light_7913",
            "dc_injected",
            "mp4",
            "ffmpeg",
        )
        for key in flags:
            row = self.live_row()
            row["source"][key] = True
            self.assert_not_landed(row, "source." + key)
        row = self.live_row()
        row["source"].update({"ffmpeg": True, "host_frame_simulation": True, "invented_dest": True})
        self.assert_not_landed(row, "combined peer probe")
        row = self.live_row()
        row["source"]["executed_pulses"] = 1
        self.assert_not_landed(row, "source.executed_pulses")
        row = self.live_row()
        row["source"]["titan"] = "WRITTEN"
        self.assert_not_landed(row, "source.titan")

    def test_catalog_action_boundaries_are_exact(self):
        flags = (
            "movie_executed",
            "byte_exact_feature_run",
            "host_inference",
            "host_gate_walk",
            "host_frame_simulation",
            "invented_dest",
            "invented_mouth",
            "fire_337",
            "pulse_78",
            "light_7913",
            "dc_injected",
            "private_owner_media",
            "pirated_mp4",
            "mp4",
            "ffmpeg",
        )
        for key in flags:
            row = self.live_row()
            row["catalog"][key] = True
            self.assert_not_landed(row, "catalog." + key)

    def test_each_public_surface_independently_preserves_every_marker(self):
        markers = (
            "REFERENCE VISOR",
            "MOVIE_EXECUTED: NO",
            "129,600 pulses were not executed",
            "No invented mouth or destination",
            "PFCGAME1",
            EXPECTED_SHA256,
        )
        for surface in ("door", "card"):
            for marker in markers:
                row = self.live_row()
                row[surface] = row[surface].replace(marker, "REMOVED", 1)
                self.assert_not_landed(row, surface + ":" + marker)

    def test_hostile_types_fail_closed_without_exceptions(self):
        probes = (
            ("catalog", "executed_pulses", "0"),
            ("catalog", "feature_length_pulses_declared", "129600"),
            ("source", "executed_pulses", "0"),
            ("source", "feature_length_pulses_declared", "129600"),
            ("source", "lcg", "not-an-object"),
        )
        for container, key, value in probes:
            row = self.live_row()
            row[container][key] = value
            self.assert_not_landed(row, container + "." + key)

    def test_missing_and_unmeasured_are_not_integrated(self):
        self.assertEqual(classify({})["state"], "UNMEASURED")
        row = self.live_row()
        row["misses"] = ["film.html"]
        self.assert_not_landed(row, "missing path")

    def test_go_is_inert_and_reel_unchanged(self):
        path = os.path.join(ROOT, "muhl", "docs", "FILM_REEL.pfc")
        before = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--root", ROOT, "--go"])
        after = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        self.assertEqual(code, 1)
        self.assertEqual(before, after)
        self.assertIn('"state": "REFUSED"', output.getvalue())
        self.assertIn('"executed_pulses": 0', output.getvalue())

    def test_host_contains_no_execution_engine(self):
        source = Path(ROOT, "host", "muhl_film_organ.py").read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("mmap", source)
        self.assertNotIn("render_frame", source)
        self.assertNotIn("write_bytes", source)
        self.assertNotIn("r+b", source)


if __name__ == "__main__":
    unittest.main()
