#!/usr/bin/env python3
"""Later-main rematch of unique-pack leftover incoming-models hub-payload readback."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "p/cursor-incoming-models-hub-payload-readback-rematch-20260902-01.md"
UNIQUE_PACK = ROOT / "p/cursor-incoming-models-hub-payload-readback-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-incoming-models-hub-payload-20260902-01.md"
HELPER = ROOT / "host/incoming_models.py"

KEEP = {
    "p/cursor-incoming-models-hub-payload-readback-20260902-01.md": "2d297673",
    "test_incoming_models_hub_payload_readback.py": "19c6b7dd",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "host/incoming_models.py": "7f4ae3bf",
    "test_incoming_models.py": "f33cbd6c",
    "ground/INCOMING_MODELS.json": "6b5e89dc",
    "ground/INCOMING_MODELS.md": "44a988c8",
    "incoming-models.html": "52d48732",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "p/grokbuild-pr8340-incoming-models-20260902-01.md": "f2917ab4",
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "p/cursor-big-things-incoming-shots-readback-20260902-01.md": "3cabb764",
    "ground/OWNER_NOW.md": "59b1fd37",
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "autogtm.html": "9d8b3e85",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "test_harborline_pack_market_render.py": "cf40d758",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class TestIncomingModelsHubPayloadReadbackRematch(unittest.TestCase):
    def test_keep_leftover_map_door_and_unique_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_leftover_check_still_ok_without_probe(self) -> None:
        proc = subprocess.run(
            ["python3", str(HELPER), "--check", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        report = json.loads(proc.stdout)
        self.assertTrue(report["ok"], report)
        self.assertIn("muse-spark-1.3", report["absent_here"])
        self.assertIn("gpt-6-astra", report["absent_here"])
        self.assertEqual(report["reachable_here"], ["gpt-5.6-sol", "opus-5", "fable-5.1"])
        self.assertIs(report["gate"], False)

    def test_rematch_receipt_exists_and_does_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        unique_pack = UNIQUE_PACK.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        self.assertIn("cursor-incoming-models-hub-payload-readback-rematch-20260902-01", text)
        self.assertIn("1ec9db309", text)
        self.assertIn("2d297673", text)
        self.assertIn("63aa4736", text)
        self.assertIn("Did not remint leftover map/door", text)
        self.assertIn("Did not spawn", text)
        self.assertIn("Did not steal Harborline `/harborline`", text)
        self.assertNotEqual(text, unique_pack)
        self.assertNotEqual(text, leftover)
        self.assertFalse((ROOT / "harborline.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
