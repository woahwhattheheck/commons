#!/usr/bin/env python3
"""SHIP leftover for Harborline pack-market unique-pack readback. Does not remint."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import harborline_pack_market_render_readback_ship as ship  # noqa: E402

LEFTOVER_ID = "cursor-harborline-pack-market-render-20260902-01"
READBACK_ID = "cursor-harborline-pack-market-render-readback-20260902-01"
SHIP_ID = "cursor-harborline-pack-market-render-readback-ship-20260902-01"
LEFTOVER_HELPER = ROOT / "host/harborline_pack_market_render.py"
SHIP_HELPER = ROOT / "host/harborline_pack_market_render_readback_ship.py"
LEFTOVER_BLOB = "54c348dc"
HELPER_BLOB = "cc9a3320"
LEFTOVER_TEST_BLOB = "e8f8703c"
READBACK_BLOB = "6efbac54"
READBACK_TEST_BLOB = "f4ee4f15"
READBACK_LAND = "3a418c574"
LEFTOVER_LAND = "0141bf7c8"


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


class HarborlinePackMarketRenderReadbackShipTest(unittest.TestCase):
    def setUp(self) -> None:
        self.result = ship.measure()
        self.ship = (ROOT / "p" / f"{SHIP_ID}.md").read_text(encoding="utf-8")
        self.readback = (ROOT / "p" / f"{READBACK_ID}.md").read_text(encoding="utf-8")
        self.leftover = (ROOT / "p" / f"{LEFTOVER_ID}.md").read_text(encoding="utf-8")

    def test_leftover_unique_paths_match_without_remint(self) -> None:
        self.assertTrue(git_blob(f"p/{LEFTOVER_ID}.md").startswith(LEFTOVER_BLOB))
        self.assertTrue(git_blob("host/harborline_pack_market_render.py").startswith(HELPER_BLOB))
        self.assertTrue(git_blob("test_harborline_pack_market_render.py").startswith(LEFTOVER_TEST_BLOB))
        self.assertTrue(git_blob(f"p/{READBACK_ID}.md").startswith(READBACK_BLOB))
        self.assertTrue(git_blob("test_harborline_pack_market_render_readback.py").startswith(READBACK_TEST_BLOB))
        self.assertTrue(self.result["leftover_blobs_ok"])
        self.assertTrue(self.result["leftover_helper_not_reminted"])
        self.assertTrue(self.result["did_not_remint_leftover_helper"])
        self.assertEqual(ship.EXPECTED_BLOBS[f"p/{LEFTOVER_ID}.md"], LEFTOVER_BLOB)
        self.assertEqual(ship.EXPECTED_BLOBS["host/harborline_pack_market_render.py"], HELPER_BLOB)
        self.assertNotIn(f"p/{SHIP_ID}.md", ship.EXPECTED_BLOBS)

    def test_leftover_cli_still_renders_and_refuses_send(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(LEFTOVER_HELPER), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "RENDER")
        self.assertFalse(payload["commons_is_store"])
        self.assertFalse(payload["marketplace_html_on_commons"])
        self.assertEqual(payload["sent"], 0)
        send = subprocess.run(
            [sys.executable, str(LEFTOVER_HELPER), "--send"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(send.returncode, 2)
        send_payload = json.loads(send.stdout)
        self.assertEqual(send_payload["refused"], "--send")
        self.assertEqual(send_payload["sent"], 0)
        self.assertTrue(self.result["leftover_send_refused"])
        self.assertEqual(self.result["leftover_json_verdict"], "RENDER")
        self.assertTrue(self.result["peer_keep_unread"])
        self.assertTrue(ship.blob_prefix("p/cursor-harborline-pack-market-render-readback-rematch-20260902-01.md").startswith("f965e00f"))
        self.assertTrue(ship.blob_prefix("p/cursor-harborline-pack-market-render-readback-ack-20260902-01.md").startswith("9d221c75"))
        self.assertTrue(ship.blob_prefix("p/cursor-harborline-pack-market-render-ship-20260902-01.md").startswith("89457966"))

    def test_later_main_keep_remint_unread_not_leftover_chase(self) -> None:
        remint = self.result["later_main_keep_remint"]
        self.assertEqual(remint["path"], "hub_pages.py")
        self.assertEqual(remint["leftover_pin"], "14eeedb0")
        self.assertTrue(remint["unread"])
        self.assertTrue(remint["did_not_remint_leftover_to_chase"])
        live = git_blob("hub_pages.py")
        self.assertFalse(live.startswith("14eeedb0"))
        self.assertTrue(live.startswith(remint["live"]))
        leftover_keep = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "test_harborline_pack_market_render.TestHarborlinePackMarketRender.test_keep_main_unique_paths_exact",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(leftover_keep.returncode, 0)
        self.assertIn("hub_pages.py reminted", leftover_keep.stderr)
        self.assertTrue(git_blob("host/harborline_pack_market_render.py").startswith(HELPER_BLOB))

    def test_ship_receipt_cites_leftover_without_steal(self) -> None:
        self.assertIn(f"id: {SHIP_ID}", self.ship)
        self.assertIn(READBACK_ID, self.ship)
        self.assertIn(LEFTOVER_ID, self.ship)
        self.assertIn(READBACK_LAND, self.ship)
        self.assertIn(LEFTOVER_LAND, self.ship)
        self.assertIn(LEFTOVER_BLOB, self.ship)
        self.assertIn(READBACK_BLOB, self.ship)
        self.assertIn(HELPER_BLOB, self.ship)
        self.assertIn("#8345", self.ship)
        self.assertIn("Did not remint leftover helper", self.ship)
        self.assertIn("Did not dump `marketplace.html`", self.ship)
        self.assertIn("Did not steal Harborline `/harborline`", self.ship)
        self.assertIn("14eeedb0", self.ship)
        self.assertIn("5ac12648", self.ship)
        self.assertIn("remint leftover to chase", self.ship)
        self.assertIn("f965e00f", self.ship)
        self.assertIn("9d221c75", self.ship)
        self.assertIn("89457966", self.ship)
        self.assertIn("KEEP unread", self.ship)
        self.assertIn("NOT_MINTED", self.ship)
        self.assertNotEqual(self.ship, self.readback)
        self.assertNotEqual(self.ship, self.leftover)
        self.assertNotIn("buy.stripe.com", self.ship)
        self.assertNotIn("qualify.html", self.ship)
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "harborline").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertTrue(self.result["did_not_dump_marketplace_html"])
        self.assertTrue(self.result["did_not_steal_harborline"])
        self.assertEqual(self.result["verdict"], "MATCH")
        self.assertEqual(self.result["checkout"], "NOT_MINTED")

    def test_ship_helper_json_and_refuse(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SHIP_HELPER), "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "MATCH")
        self.assertEqual(payload["id"], SHIP_ID)
        self.assertEqual(payload["leftover_id"], LEFTOVER_ID)
        self.assertEqual(payload["readback_id"], READBACK_ID)
        self.assertTrue(payload["leftover_helper_not_reminted"])
        self.assertTrue(payload["did_not_remint_leftover_helper"])
        self.assertTrue(payload["did_not_dump_marketplace_html"])
        self.assertTrue(payload["did_not_steal_harborline"])
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["checkout"], "NOT_MINTED")
        self.assertFalse(payload["gate"])
        self.assertFalse(payload["commons_admission"])
        for flag in ("--send", "--apply", "--go", "--autopilot", "--dump-commons", "--marketplace-html"):
            refused = subprocess.run(
                [sys.executable, str(SHIP_HELPER), flag],
                cwd=ROOT,
                text=True,
                capture_output=True,
                check=False,
            )
            self.assertEqual(refused.returncode, 2, msg=flag + refused.stdout)
            body = json.loads(refused.stdout)
            self.assertEqual(body["sent"], 0)
            self.assertEqual(body["refused"], flag)
            self.assertTrue(body["did_not_remint_leftover_helper"])
        unknown = subprocess.run(
            [sys.executable, str(SHIP_HELPER), "--not-a-real-flag"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(unknown.returncode, 1)
        self.assertEqual(json.loads(unknown.stdout)["verdict"], "FINDER-FAILED")
        self.assertNotIn("337 NO", json.dumps(payload))


if __name__ == "__main__":
    unittest.main()
