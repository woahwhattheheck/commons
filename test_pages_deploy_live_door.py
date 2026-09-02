#!/usr/bin/env python3
"""In-tree Pages deploy receipt door helper stays an open measure."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from host import pages_deploy_live_door as door


ROOT = Path(__file__).resolve().parent


class PagesDeployLiveDoorTests(unittest.TestCase):
    def test_in_tree_canary_present_and_open(self) -> None:
        payload = door.measure(ROOT)
        self.assertTrue(payload["in_tree_present"])
        self.assertTrue(payload["open_door"])
        self.assertFalse(payload["gate"])
        self.assertFalse(payload["owns_deploy_workflow"])
        self.assertEqual(payload["in_tree_source"], "in-tree-canary")
        body = json.loads((ROOT / "pages-deploy.json").read_text(encoding="utf-8"))
        self.assertTrue(body.get("survives_github_pages_bot_overwrite"))

    def test_helper_source_is_not_an_admission_lock(self) -> None:
        text = (ROOT / "host" / "pages_deploy_live_door.py").read_text(encoding="utf-8")
        lowered = text.lower()
        self.assertIn("possessing the link stays authorization", lowered)
        self.assertNotIn("authentication required", lowered)
        self.assertNotIn("permission denied", lowered)
        self.assertNotIn("allowed_verbs", lowered)


if __name__ == "__main__":
    unittest.main()
