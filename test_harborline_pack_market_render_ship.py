#!/usr/bin/env python3
"""SHIP leftover pack-market render. Do not remint leftover or Slack Steam card."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/harborline_pack_market_render_ship.py"
RECEIPT = ROOT / "p/cursor-harborline-pack-market-render-ship-20260902-01.md"
LEFTOVER = ROOT / "p/cursor-harborline-pack-market-render-20260902-01.md"
READBACK = ROOT / "p/cursor-harborline-pack-market-render-readback-20260902-01.md"
SLACK = ROOT / "p/cursor-harborline-pack-market-slack-render-20260902-01.md"

KEEP = {
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "p/cursor-harborline-pack-market-render-readback-20260902-01.md": "6efbac54",
    "p/cursor-harborline-pack-market-slack-render-20260902-01.md": "0d95f2ab",
    "host/harborline_pack_market_slack_render.py": "a03534da",
    "p/cursor-harborline-pack-market-render-readback-rematch-20260902-01.md": "f965e00f",
    "p/cursor-harborline-pack-market-render-readback-ack-20260902-01.md": "9d221c75",
}


def git_blob(rel: str) -> str:
    return subprocess.check_output(
        ["git", "hash-object", str(ROOT / rel)], text=True
    ).strip()


def run_helper(*flags: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(HELPER), *flags],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


class TestHarborlinePackMarketRenderShip(unittest.TestCase):
    def test_keep_leftover_readback_slack_exact(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_ship_receipt_cites_leftover_and_slack_without_remint(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        leftover = LEFTOVER.read_text(encoding="utf-8")
        readback = READBACK.read_text(encoding="utf-8")
        slack = SLACK.read_text(encoding="utf-8")
        self.assertIn("cursor-harborline-pack-market-render-ship-20260902-01", text)
        self.assertIn("cursor-harborline-pack-market-render-20260902-01", text)
        self.assertIn("cursor-harborline-pack-market-render-readback-20260902-01", text)
        self.assertIn("cursor-harborline-pack-market-slack-render-20260902-01", text)
        self.assertIn("0141bf7c8", text)
        self.assertIn("7a922545a", text)
        self.assertIn("54c348dc", text)
        self.assertIn("6efbac54", text)
        self.assertIn("0d95f2ab", text)
        self.assertIn("f965e00f", text)
        self.assertIn("9d221c75", text)
        self.assertIn("/market", text)
        self.assertIn("Commons is not the store", text)
        self.assertIn("Harborline Local Sites", text)
        self.assertIn("$200", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not dump a store HTML door onto Commons", text)
        self.assertIn("Sends 0", text)
        self.assertNotEqual(text, leftover)
        self.assertNotEqual(text, readback)
        self.assertNotEqual(text, slack)
        self.assertNotIn("qualify.html", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertFalse((ROOT / "marketplace.html").exists())

    def test_send_apply_go_dump_refused(self) -> None:
        for flag in (
            "--send",
            "--apply",
            "--go",
            "--autopilot",
            "--dump-commons",
            "--marketplace-html",
        ):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertFalse(payload.get("commons_is_store", True))

    def test_unknown_args_finder_failed_not_zero(self) -> None:
        proc = run_helper("--not-a-real-flag")
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["verdict"], "FINDER-FAILED")

    def test_ship_classifies_leftover_and_slack_card(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ship_ok"])
        self.assertEqual(payload["verdict"], "SHIP")
        self.assertEqual(payload["store"], "standalone")
        self.assertEqual(payload["desk_route"], "/market")
        self.assertFalse(payload["commons_is_store"])
        self.assertFalse(payload["marketplace_html_on_commons"])
        self.assertEqual(payload["featured"], "Harborline Local Sites")
        self.assertEqual(payload["price_usd"], 200)
        self.assertEqual(payload["odds"], 0)
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["cash"], 0)
        self.assertEqual(payload["checkout"], "FINDER-FAILED")
        self.assertEqual(
            payload["leftover_id"],
            "cursor-harborline-pack-market-render-20260902-01",
        )
        self.assertEqual(
            payload["slack_id"],
            "cursor-harborline-pack-market-slack-render-20260902-01",
        )
        self.assertTrue(payload["did_not_remint_leftover"])
        self.assertTrue(payload["did_not_remint_readback"])
        self.assertTrue(payload["did_not_remint_slack_render"])


if __name__ == "__main__":
    unittest.main()
