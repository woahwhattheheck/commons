#!/usr/bin/env python3
"""Pin Slack Steam UI pack-market rendering. Do not remint leftover or peer readback."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/harborline_pack_market_slack_render.py"
RECEIPT = ROOT / "p/cursor-harborline-pack-market-slack-render-20260902-01.md"

KEEP = {
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "host/harborline_pack_market_render.py": "cc9a3320",
    "p/cursor-harborline-pack-market-render-readback-20260902-01.md": "6efbac54",
    "ground/OWNER_NOW.md": "59b1fd37",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "host/harborline_qualify_live_probe.py": "2c1797b2",
    "test_harborline_qualify_live_probe.py": "0791b11a",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "p/cursor-big-things-incoming-shots-readback-20260902-01.md": "3cabb764",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "p/cursor-owner-now-revenue-20260902-01.md": "fe5ba035",
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


class TestHarborlinePackMarketSlackRender(unittest.TestCase):
    def test_keep_leftover_and_peer_readback_exact(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_is_slack_steam_card_not_commons_dump(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-harborline-pack-market-slack-render-20260902-01", text)
        self.assertIn("/market", text)
        self.assertIn("Harborline Local Sites", text)
        self.assertIn("$200", text)
        self.assertIn("Zero odds", text)
        self.assertIn("Commons is not the store", text)
        self.assertIn("54c348dc", text)
        self.assertIn("6efbac54", text)
        self.assertIn("92c4e31f", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not invent a Payment Link", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertNotIn("marketplace.html", text)
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

    def test_slack_render_without_commons_html(self) -> None:
        proc = run_helper()
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("PACK MARKET", proc.stdout)
        self.assertIn("Harborline Local Sites — $200", proc.stdout)
        self.assertIn("Commons is not the store", proc.stdout)
        self.assertIn("FINDER-FAILED", proc.stdout)
        self.assertNotIn("buy.stripe.com", proc.stdout)
        js = run_helper("--json")
        self.assertEqual(js.returncode, 0, msg=js.stdout + js.stderr)
        payload = json.loads(js.stdout)
        self.assertEqual(payload["store"], "standalone")
        self.assertEqual(payload["commons_is_store"], False)
        self.assertEqual(payload["marketplace_html_on_commons"], False)
        self.assertEqual(payload["price_usd"], 200)
        self.assertEqual(payload["odds"], 0)
        self.assertEqual(payload["surface"], "slack")
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["checkout"], "FINDER-FAILED")
        self.assertEqual(payload["verdict"], "SLACK_RENDER")
        self.assertIn("Harborline Local Sites — $200", payload["slack_md"])


if __name__ == "__main__":
    unittest.main()
