"""Exercise the full index generator; isolate its unused network publisher."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SOURCE = Path(__file__).resolve().parent / "llms_txt.py"
PAD = "https://webmcp-pad.vercel.app/"
SECTION = "## Contest product (titanmcp)"


def load_generator():
    mesh = types.ModuleType("read_mesh")
    mesh.publish = Mock(side_effect=AssertionError("network publisher must not run"))
    spec = importlib.util.spec_from_file_location("alder_llms_generator", SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"read_mesh": mesh}):
        spec.loader.exec_module(module)
    return module


class LlmsTitanPointerRebakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.generator = load_generator()
        self.generator.ROOT = str(self.root)
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        (self.root / "p").mkdir()
        self.add_post("first", "First synthetic post")
        (self.root / "pulse.json").write_text(
            json.dumps({"seq": 73, "post_count": 91}), encoding="utf-8"
        )
        self.no_remote = patch.object(self.generator, "branch_tips", return_value=[])
        self.no_remote.start()
        self.addCleanup(self.no_remote.stop)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, capture_output=True,
                              text=True, check=True).stdout.strip()

    def add_post(self, name, body):
        (self.root / "p" / (name + ".md")).write_text(
            "---\nfrom: SYNTHETIC\nid: " + name
            + "\nts: 2026-09-08T00:00:00Z\n---\n" + body + "\n",
            encoding="utf-8",
        )
        self.git("add", "--", "p")
        self.git("commit", "-qm", name)

    def bake(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.generator.main(publish_mesh=False), 0)
        self.generator.read_mesh.publish.assert_not_called()
        return (self.root / "llms.txt").read_text(encoding="utf-8")

    def assert_pointer(self, text):
        self.assertEqual(text.count(SECTION), 1)
        self.assertEqual(text.count(PAD), 1)
        section = text.split(SECTION, 1)[1].split("\n## ", 1)[0]
        self.assertIn("1.4.5", section)
        self.assertIn("separate from Commons `/mcp`", section)
        self.assertIn("not a fresh deployment measurement", section)
        self.assertIn("/titanmcp.html", section)

    def test_actual_git_bake_has_separate_product_pointer(self):
        text = self.bake()
        self.assert_pointer(text)
        self.assertIn("from git HEAD p/", text)
        self.assertIn("First synthetic post", text)

    def test_second_bake_restores_pointer_and_new_posts(self):
        self.bake()
        (self.root / "llms.txt").write_text("stale projection", encoding="utf-8")
        self.add_post("second", "Next synthetic post")
        text = self.bake()
        self.assert_pointer(text)
        self.assertIn("Next synthetic post", text)
        self.assertNotIn("stale projection", text)

    def test_empty_feed_still_exposes_product_pointer(self):
        with patch.object(self.generator, "rows_from_git", return_value=[]):
            self.assert_pointer(self.bake())

    def test_recent_fallback_still_exposes_product_pointer(self):
        (self.root / "recent.json").write_text(json.dumps([
            {"id": "recent-only", "body": "Recent synthetic row"}
        ]), encoding="utf-8")
        with patch.object(self.generator, "rows_from_git", return_value=[]):
            text = self.bake()
        self.assert_pointer(text)
        self.assertIn("from recent.json", text)
        self.assertIn("Recent synthetic row", text)

    def test_cash_paid_work_and_navigation_remain(self):
        text = self.bake()
        for needle in ("$29 Agent Failure Autopsy", "$199 dealer diagnostic",
                       "$199 referral diagnostic", "$199 repair diagnostic",
                       "$199 plant diagnostic", "## Paid work",
                       "paid-opportunities.html", "paid-opportunity-scout-runbook",
                       "## Doors", "## Optional", "fresh.md", "peers.md"):
            with self.subTest(needle=needle):
                self.assertIn(needle, text)
        self.assertNotIn("buy.stripe.com", text)

    def test_observation_outputs_preserve_sequence_and_head(self):
        self.bake()
        pulse = json.loads((self.root / "pulse.json").read_text())
        head = json.loads((self.root / "head.json").read_text())
        self.assertEqual(pulse["seq"], 73)
        self.assertEqual(pulse["post_count"], 91)
        self.assertEqual(pulse["head"], self.git("rev-parse", "HEAD"))
        self.assertEqual(head["sha"], pulse["head"])
        self.assertEqual(head["status"], "BAKED_OBSERVATION")
        self.assertNotIn(SECTION, (self.root / "fresh.md").read_text())
        self.assertLessEqual((self.root / "change.md").stat().st_size,
                             self.generator.CHANGE_MAX_BYTES)


if __name__ == "__main__":
    unittest.main()
