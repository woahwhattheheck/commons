#!/usr/bin/env python3
"""Pin unique verification that Harborline leftover KEEP no longer freezes hub_pages."""
from __future__ import annotations

import importlib
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/grokbuild-harborline-hub-pages-keep-unpin-20260902-01.md"
REMATCH = ROOT / "p/cursor-harborline-pack-market-render-readback-rematch-20260902-01.md"
HELPER = ROOT / "host/harborline_pack_market_render.py"
LIVE_GET = "live GET /public/api/v1/autogtm/projects credentials=omit"
RUN_URL = "https://github.com/woahwhattheheck/commons/actions/runs/33682015747"
DEDUPE = (
    "woahwhattheheck/commons:tests:"
    "77fcb08c0b7c763df2cf3a59db8ea2027e2ef568:"
    "the whole battery, one failure fails the run"
)

KEEP_UNREAD = {
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "p/cursor-harborline-pack-market-render-readback-20260902-01.md": "6efbac54",
    "p/cursor-harborline-pack-market-render-readback-rematch-20260902-01.md": "f965e00f",
    "ground/OWNER_NOW.md": "59b1fd37",
    "autogtm.html": "9d8b3e85",
}

KEEP_MODULES = (
    "test_autogtm_door_hub_readback_ack",
    "test_autogtm_hub_pages_live_get_readback",
    "test_autogtm_hub_pages_live_get_readback_ack",
    "test_big_things_incoming_alert",
    "test_big_things_incoming_alert_ack",
    "test_big_things_incoming_shots",
    "test_big_things_incoming_shots_readback",
    "test_grokbuild_autogtm_hub_pages_keep_unpin",
    "test_harborline_pack_market_render",
    "test_harborline_pack_market_render_readback",
    "test_owner_now_revenue",
    "test_owner_now_revenue_readback",
)


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class GrokbuildHarborlineHubPagesKeepUnpinTest(unittest.TestCase):
    def test_leftover_keep_does_not_freeze_stale_hub_or_door(self) -> None:
        for name in KEEP_MODULES:
            mod = importlib.import_module(name)
            keep = getattr(mod, "KEEP", {})
            unread = getattr(mod, "KEEP_UNREAD", {})
            self.assertNotEqual(keep.get("hub_pages.py"), "14eeedb0", name)
            self.assertNotEqual(keep.get("door.js"), "1f9e8d14", name)
            self.assertNotEqual(unread.get("hub_pages.py"), "14eeedb0", name)
            self.assertNotEqual(unread.get("door.js"), "1f9e8d14", name)

    def test_leftover_harborline_and_rematch_now_pass(self) -> None:
        proc = subprocess.run(
            [
                "python3",
                "-m",
                "unittest",
                "test_harborline_pack_market_render.py",
                "test_harborline_pack_market_render_readback.py",
                "test_harborline_pack_market_render_readback_rematch.py",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        combined = proc.stdout + proc.stderr
        self.assertEqual(proc.returncode, 0, msg=combined)
        self.assertNotIn("hub_pages.py reminted: want 14eeedb0 got 5ac12648", combined)
        self.assertNotIn("cursor-harborline-pack-market-render-20260902-01.md reminted", combined)
        self.assertNotIn("harborline_pack_market_render.py reminted", combined)

    def test_hub_still_names_live_get_without_remint(self) -> None:
        hub = git_blob("hub_pages.py")
        door = git_blob("door.js")
        self.assertTrue(hub.startswith("5ac12648"), hub)
        self.assertFalse(hub.startswith("14eeedb0"), hub)
        self.assertTrue(door.startswith("dc59355d"), door)
        self.assertFalse(door.startswith("1f9e8d14"), door)
        text = (ROOT / "hub_pages.py").read_text(encoding="utf-8")
        self.assertIn(LIVE_GET, text)
        self.assertIn('href="./autogtm.html">AutoGTM</a>', text)

    def test_did_not_remint_leftover_unique_or_rematch_receipt(self) -> None:
        for rel, prefix in KEEP_UNREAD.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )
        rematch = REMATCH.read_text(encoding="utf-8")
        self.assertIn("Did **not** remint leftover tests to lift that pin", rematch)
        self.assertIn("want `14eeedb0` got `5ac12648`", rematch)
        helper = subprocess.run(
            ["python3", str(HELPER), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(helper.returncode, 0, msg=helper.stdout + helper.stderr)
        self.assertIn('"verdict": "RENDER"', helper.stdout)
        self.assertIn('"store": "standalone"', helper.stdout)
        refused = subprocess.run(
            ["python3", str(HELPER), "--send"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(refused.returncode, 2)
        self.assertIn('"sent": 0', refused.stdout)
        unpin = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("id: grokbuild-harborline-hub-pages-keep-unpin-20260902-01", unpin)
        self.assertIn(RUN_URL, unpin)
        self.assertIn(DEDUPE, unpin)
        self.assertIn("14eeedb0", unpin)
        self.assertIn("5ac12648", unpin)
        self.assertIn("#8390", unpin)
        self.assertIn("dc19ba4a", unpin)
        self.assertIn("ALREADY_MERGED_VERIFIED", unpin)
        self.assertIn("Did not remint leftover unique", unpin)
        self.assertIn("#7915", unpin)
        self.assertIn("NOT_MINTED", unpin)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
