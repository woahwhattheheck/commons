#!/usr/bin/env python3
"""Pages allowlist keep-paths. Helps Fable's deploy claim; does not own it."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CARD = ROOT / "ground" / "PAGES_KEEP_PATHS.md"
MAP = ROOT / "ground" / "PAGES_KEEP_PATHS.json"
BOARD_JS = ROOT / "board.js"
FREE_SAMPLE = ROOT / "muhlnickel-free-sample.html"
SALES_PACK = ROOT / "revenue" / "muhlnickel_free_sample" / "sales_pack.json"


class PagesKeepPathsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.card = CARD.read_text(encoding="utf-8")
        self.mp = json.loads(MAP.read_text(encoding="utf-8"))
        self.board_js = BOARD_JS.read_text(encoding="utf-8")
        self.free = FREE_SAMPLE.read_text(encoding="utf-8")
        self.pack = json.loads(SALES_PACK.read_text(encoding="utf-8"))

    def test_map_does_not_steal_deploy_claim(self) -> None:
        self.assertEqual(self.mp["id"], "cursor-pages-keep-paths-20260902-01")
        self.assertIs(self.mp["gate"], False)
        self.assertIs(self.mp["owns_deploy_workflow"], False)
        self.assertEqual(
            self.mp["deploy_claim_id"], "commons-pages-workflow-deploy-20260902-01"
        )
        self.assertIn("does **not** claim the Pages deploy workflow", self.card)
        self.assertIn("commons-pages-workflow-deploy-20260902-01", self.card)

    def test_required_keep_paths_exist_and_are_referenced(self) -> None:
        required = self.mp["required_keep_paths"]
        self.assertEqual(
            required,
            [
                "chunks/",
                "muhl/docs/",
                "muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno",
                "muhlnickel-free-sample.html",
                "revenue/muhlnickel_free_sample/sales_pack.json",
            ],
        )
        self.assertTrue((ROOT / "chunks").is_dir())
        self.assertTrue((ROOT / "muhl" / "docs").is_dir())
        seed = ROOT / "muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno"
        self.assertTrue(seed.is_file())
        self.assertTrue(FREE_SAMPLE.is_file())
        self.assertTrue(SALES_PACK.is_file())
        for path in required:
            self.assertIn(path, self.card)

    def test_board_js_requires_chunks(self) -> None:
        self.assertIn("chunks/", self.board_js)
        self.assertIn('fetchSite("chunks/index.json")', self.board_js)
        self.assertIn('fetchSite("chunks/" + encodeURIComponent(day) + ".json")', self.board_js)

    def test_free_sample_requires_seed_and_docs(self) -> None:
        self.assertIn("muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno", self.free)
        self.assertIn("muhl/docs/EXPANDING_SEED.md", self.free)
        self.assertEqual(
            self.pack["proof"]["path"],
            "muhl/containers/MUHLNICKEL_DISTRO/SEED0.mno",
        )
        self.assertEqual(
            self.pack["proof"]["existing_doc"],
            "muhl/docs/EXPANDING_SEED.md",
        )


if __name__ == "__main__":
    unittest.main()
