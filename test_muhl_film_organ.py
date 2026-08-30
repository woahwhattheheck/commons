#!/usr/bin/env python3
"""Feature-film organ reference: exact bytes, deterministic source, zero fabricated execution."""
from __future__ import annotations

import copy
import hashlib
import io
import os
import sys
import unittest
from contextlib import redirect_stdout


ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "host"))

from muhl_film_organ import (
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
        row = measure_root(ROOT)
        self.assertEqual(row["misses"], [])
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

    def test_fabricated_execution_is_rejected(self):
        row = measure_root(ROOT)
        for key, value in (
            ("movie_executed", True),
            ("byte_exact_feature_run", True),
            ("host_frame_simulation", True),
            ("invented_dest", True),
            ("fire_337", True),
            ("ffmpeg", True),
        ):
            changed = copy.deepcopy(row)
            changed["catalog"][key] = value
            self.assertEqual(classify(changed)["state"], "NOT_LANDED", key)
        changed = copy.deepcopy(row)
        changed["catalog"]["executed_pulses"] = 129600
        self.assertEqual(classify(changed)["state"], "NOT_LANDED")

    def test_go_is_inert_and_reel_unchanged(self):
        path = os.path.join(ROOT, "muhl", "docs", "FILM_REEL.pfc")
        before = hashlib.sha256(open(path, "rb").read()).hexdigest()
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(["--root", ROOT, "--go"])
        after = hashlib.sha256(open(path, "rb").read()).hexdigest()
        self.assertEqual(code, 1)
        self.assertEqual(before, after)
        self.assertIn('"state": "REFUSED"', output.getvalue())
        self.assertIn('"executed_pulses": 0', output.getvalue())

    def test_card_page_and_catalog_preserve_truth_boundary(self):
        card = open(os.path.join(ROOT, "ground", "MUHL_FILM_ORGAN.md"), encoding="utf-8").read()
        page = open(os.path.join(ROOT, "film.html"), encoding="utf-8").read()
        catalog = load_json(open(os.path.join(ROOT, "ground", "MUHL_FILM_ORGAN.json"), encoding="utf-8").read())
        for blob in (card, page):
            self.assertIn("REFERENCE VISOR", blob)
            self.assertIn("MOVIE_EXECUTED: NO", blob)
            self.assertIn("129,600 pulses were not executed", blob)
            self.assertIn("No invented mouth or destination", blob)
            self.assertIn(EXPECTED_SHA256, blob)
        self.assertEqual(catalog["state"], "REFERENCE_ONLY")
        self.assertEqual(catalog["executed_pulses"], 0)
        self.assertFalse(catalog["movie_executed"])
        self.assertFalse(catalog["host_frame_simulation"])
        self.assertEqual(catalog["titan"], "NOT_WRITTEN")
        self.assertTrue(catalog["no_auth"])
        self.assertTrue(catalog["no_gate"])

    def test_host_contains_no_execution_engine(self):
        source = open(os.path.join(ROOT, "host", "muhl_film_organ.py"), encoding="utf-8").read()
        self.assertNotIn("subprocess", source)
        self.assertNotIn("mmap", source)
        self.assertNotIn("render_frame", source)
        self.assertNotIn("write_bytes", source)
        self.assertNotIn("r+b", source)


if __name__ == "__main__":
    unittest.main()
