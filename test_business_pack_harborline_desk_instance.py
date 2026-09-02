#!/usr/bin/env python3
"""Harborline leftover finder: instance.json + door.html, never a silent 0."""
from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "packs" / "desk-website-service-20260902-01"
SIDEWALK = ROOT / "packs" / "sidewalk-signal-web-desk-20260902-01"
HELPER = ROOT / "host" / "business_pack_harborline_desk_instance.py"
SPEC = importlib.util.spec_from_file_location("harborline_desk", HELPER)
assert SPEC and SPEC.loader
desk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(desk)


def _copy_pack(tmp: str) -> Path:
    dest = Path(tmp) / "packs" / PACK.name
    shutil.copytree(PACK, dest)
    return dest


class HarborlineDeskFinderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.result = desk.verify(PACK)

    def test_live_pack_is_instance_ok(self):
        self.assertEqual(self.result["errors"], [], self.result["errors"])
        self.assertEqual(self.result["state"], "INSTANCE_OK")
        self.assertFalse(self.result["gate"])
        self.assertEqual(self.result["checkout"], "NOT_MINTED")
        self.assertIs(self.result["saleable"], False)
        self.assertEqual(self.result["terms_verdict"], "TOS_INCOMPLETE")
        self.assertEqual(self.result["sell_instance_verdict"], "UNIQUE_INSTANCE_SELL_OK")
        self.assertEqual(self.result["keep_or_sell_on_disk"], "SELL")
        self.assertTrue(self.result["did_not_decide_keep_sell"])
        self.assertTrue(self.result["did_not_invent_manifest"])
        self.assertFalse((PACK / "manifest.json").exists())
        self.assertEqual(self.result["copy_verdicts"].get("creative_brief.md"), "EARNINGS_CLAIM")
        self.assertFalse(any("creative_brief.md" in item for item in self.result["errors"]))

    def test_cli_exits_zero_on_harborline(self):
        proc = subprocess.run(
            [sys.executable, str(HELPER), "--pack", str(PACK)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["state"], "INSTANCE_OK")
        self.assertEqual(payload["layout"], "instance.json+door.html")
        self.assertTrue(payload["known_present"]["ground/HEAD.md"])

    def test_sidewalk_pack_is_finder_failed_not_silent_zero(self):
        result = desk.verify(SIDEWALK)
        self.assertEqual(result["state"], "FINDER-FAILED")
        self.assertTrue(result["miss"])
        self.assertTrue(any("instance.json" in item for item in result["miss"]), result["miss"])
        self.assertTrue(any("manifest.json" in item for item in result["search_space"]), result["search_space"])
        self.assertNotEqual(result["state"], "INSTANCE_OK")
        proc = subprocess.run(
            [sys.executable, str(HELPER), "--pack", str(SIDEWALK)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)

    def test_missing_instance_json_is_finder_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _copy_pack(tmp)
            (dest / "instance.json").unlink()
            result = desk.verify(dest)
            self.assertEqual(result["state"], "FINDER-FAILED")
            self.assertTrue(any("instance.json" in item for item in result["miss"]), result["miss"])
            self.assertTrue(any("instance.json" in item for item in result["search_space"]))
            self.assertNotIn("0", result["miss"])

    def test_missing_door_is_finder_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _copy_pack(tmp)
            (dest / "door.html").unlink()
            result = desk.verify(dest)
            self.assertEqual(result["state"], "FINDER-FAILED")
            self.assertTrue(result["search_space"])
            self.assertTrue(result["did_not_invent_manifest"])

    def test_invented_stripe_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _copy_pack(tmp)
            door = dest / "door.html"
            door.write_text(
                door.read_text(encoding="utf-8").replace(
                    "Owner pastes that when ready.",
                    "Pay here: https://buy.stripe.com/notreal",
                ),
                encoding="utf-8",
            )
            result = desk.verify(dest)
            self.assertEqual(result["state"], "ERROR")
            self.assertTrue(any("Stripe" in item for item in result["errors"]), result["errors"])

    def test_earnings_claim_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _copy_pack(tmp)
            offer = dest / "offer.md"
            offer.write_text(
                offer.read_text(encoding="utf-8") + "\nYou will make $900 this weekend.\n",
                encoding="utf-8",
            )
            result = desk.verify(dest)
            self.assertEqual(result["state"], "ERROR")
            self.assertTrue(any("EARNINGS_CLAIM" in item for item in result["errors"]), result["errors"])

    def test_does_not_write_manifest_or_pack_organs(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _copy_pack(tmp)
            before = {path.name: path.read_bytes() for path in dest.iterdir() if path.is_file()}
            desk.verify(dest)
            self.assertFalse((dest / "manifest.json").exists())
            after = {path.name: path.read_bytes() for path in dest.iterdir() if path.is_file()}
            self.assertEqual(before, after)

    def test_does_not_write_sidewalk_helper(self):
        helper = ROOT / "host" / "business_pack_desk_instance.py"
        before = helper.read_bytes()
        desk.verify(PACK)
        self.assertEqual(helper.read_bytes(), before)
        self.assertIn("host/business_pack_desk_instance.py", desk.DO_NOT_WRITE)


if __name__ == "__main__":
    unittest.main()
