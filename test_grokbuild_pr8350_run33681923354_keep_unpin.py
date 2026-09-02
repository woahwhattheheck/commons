#!/usr/bin/env python3
"""Pin grok-build leftover for PR 8350 run 33681923354 KEEP unpin already on main."""

from __future__ import annotations

import importlib
import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-pr8350-run33681923354-keep-unpin-20260902-01.md"
VERIFY = ROOT / "p/grokbuild-pr8350-verify-20260902-01.md"
SLACK_HELPER = ROOT / "host/harborline_pack_market_slack_render.py"
SLACK_LEFTOVER = ROOT / "p/cursor-harborline-pack-market-slack-render-20260902-01.md"
SLACK_TEST = ROOT / "test_harborline_pack_market_slack_render.py"
RENDER_HELPER = ROOT / "host/harborline_pack_market_render.py"

KEEP_UNREAD = {
    "p/cursor-harborline-pack-market-slack-render-20260902-01.md": "0d95f2ab",
    "host/harborline_pack_market_slack_render.py": "a03534da",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "p/cursor-harborline-pack-market-render-readback-20260902-01.md": "6efbac54",
    "p/grokbuild-pr8350-verify-20260902-01.md": "538a4d1e",
    "p/grokbuild-owner-now-337-closer-strip-20260902-01.md": "71135011",
    "ground/OWNER_NOW.md": "59b1fd37",
    "autogtm.html": "9d8b3e85",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
}

KEEP_MODULES = (
    "test_harborline_pack_market_slack_render",
    "test_harborline_pack_market_render",
    "test_harborline_pack_market_render_readback",
    "test_autogtm_door_hub_readback_ack",
    "test_autogtm_hub_pages_live_get_readback",
    "test_owner_now_revenue",
    "test_grokbuild_autogtm_hub_pages_keep_unpin",
)


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestGrokbuildPr8350Run33681923354KeepUnpin(unittest.TestCase):
    def test_leftover_keep_does_not_freeze_stale_hub_or_door(self) -> None:
        for name in KEEP_MODULES:
            mod = importlib.import_module(name)
            keep = getattr(mod, "KEEP", {})
            unread = getattr(mod, "KEEP_UNREAD", {})
            self.assertNotIn("hub_pages.py", keep, name)
            self.assertNotEqual(keep.get("hub_pages.py"), "14eeedb0", name)
            self.assertNotEqual(keep.get("door.js"), "1f9e8d14", name)
            self.assertNotEqual(unread.get("hub_pages.py"), "14eeedb0", name)
            self.assertNotEqual(unread.get("door.js"), "1f9e8d14", name)
        self.assertNotIn('"hub_pages.py": "14eeedb0"', SLACK_TEST.read_text(encoding="utf-8"))
        self.assertTrue(git_blob("hub_pages.py").startswith("5ac12648"))
        self.assertFalse(git_blob("hub_pages.py").startswith("14eeedb0"))
        self.assertTrue(git_blob("door.js").startswith("dc59355d"))
        self.assertFalse(git_blob("door.js").startswith("1f9e8d14"))

    def test_slack_helper_still_renders_and_refuses_send(self) -> None:
        proc = subprocess.run(
            ["python3", str(SLACK_HELPER), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "SLACK_RENDER")
        self.assertEqual(payload["store"], "standalone")
        self.assertFalse(payload["commons_is_store"])
        self.assertFalse(payload["marketplace_html_on_commons"])
        self.assertEqual(payload["price_usd"], 200)
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["checkout"], "FINDER-FAILED")
        refused = subprocess.run(
            ["python3", str(SLACK_HELPER), "--send"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(refused.returncode, 2)
        self.assertEqual(json.loads(refused.stdout)["sent"], 0)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        render = subprocess.run(
            ["python3", str(RENDER_HELPER), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(render.returncode, 0, msg=render.stdout + render.stderr)
        self.assertEqual(json.loads(render.stdout)["verdict"], "RENDER")
        self.assertEqual(json.loads(render.stdout)["sent"], 0)

    def test_keep_unread_unique_leftovers_and_receipt(self) -> None:
        for rel, prefix in KEEP_UNREAD.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = SLACK_LEFTOVER.read_text(encoding="utf-8")
        verify = VERIFY.read_text(encoding="utf-8")
        self.assertIn("id: grokbuild-pr8350-run33681923354-keep-unpin-20260902-01", text)
        self.assertIn("33681923354", text)
        self.assertIn("08dd1584349f30b2a3330b3ee3475003fe32eac6", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8350", text)
        self.assertIn("https://github.com/woahwhattheheck/commons/pull/8390", text)
        self.assertIn("569526cc", text)
        self.assertIn("14eeedb0", text)
        self.assertIn("5ac12648", text)
        self.assertIn("Did not remint leftover unique p/", text)
        self.assertIn("NOT_MINTED", text)
        self.assertIn("ALREADY_MERGED_VERIFIED", text)
        self.assertIn("0d95f2ab", text)
        self.assertIn("54c348dc", text)
        self.assertIn("538a4d1e", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, verify)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
