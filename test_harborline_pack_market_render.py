#!/usr/bin/env python3
"""Pin Harborline pack-market rendering leftover. Commons is not the store."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/harborline_pack_market_render.py"
RECEIPT = ROOT / "p/cursor-harborline-pack-market-render-20260902-01.md"

KEEP = {
    "ground/OWNER_NOW.md": "6b8ee988",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "host/harborline_qualify_live_probe.py": "2c1797b2",
    "test_harborline_qualify_live_probe.py": "0791b11a",
    "p/cursor-big-things-incoming-alert-20260902-01.md": "fde94226",
    "p/cursor-big-things-incoming-shots-20260902-01.md": "60b24eff",
    "p/cursor-big-things-incoming-shots-readback-20260902-01.md": "3cabb764",
    "p/cursor-incoming-models-hub-payload-20260902-01.md": "63aa4736",
    "p/cursor-owner-now-readback-20260902-01.md": "1b3cd631",
    "p/cursor-owner-now-revenue-20260902-01.md": "fe5ba035",
    "owner-now-revenue.html": "1d3f1cdf",
    "autogtm.html": "9d8b3e85",
    "hub_pages.py": "14eeedb0",
    "packs/desk-website-service-20260902-01/door.html": "d3d6fcc7",
    "p/cursor-business-pack-harborline-map-pin-lift-pointer-20260902-01.md": "7a8987b5",
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


class TestHarborlinePackMarketRender(unittest.TestCase):
    def test_keep_main_unique_paths_exact(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_receipt_is_standalone_store_not_commons_dump(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        self.assertIn("cursor-harborline-pack-market-render-20260902-01", text)
        self.assertIn("/market", text)
        self.assertIn("Commons is not the store", text)
        self.assertIn("6b8ee988", text)
        self.assertIn("92c4e31f", text)
        self.assertIn("60b24eff", text)
        self.assertIn("3cabb764", text)
        self.assertIn("63aa4736", text)
        self.assertIn("1b3cd631", text)
        self.assertIn("fe5ba035", text)
        self.assertIn("fde94226", text)
        self.assertIn("FINDER-FAILED", text)
        self.assertIn("Did not remint", text)
        self.assertIn("Did not spawn", text)
        self.assertNotIn("qualify.html", text)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn("Did not dump a store HTML door onto Commons", text)
        self.assertFalse((ROOT / "marketplace.html").exists())

    def test_send_apply_go_dump_refused(self) -> None:
        for flag in ("--send", "--apply", "--go", "--autopilot", "--dump-commons", "--marketplace-html"):
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

    def test_measure_render_without_commons_html(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["store"], "standalone")
        self.assertEqual(payload["commons_is_store"], False)
        self.assertEqual(payload["marketplace_html_on_commons"], False)
        self.assertEqual(payload["price_usd"], 200)
        self.assertEqual(payload["sent"], 0)
        self.assertEqual(payload["checkout"], "FINDER-FAILED")
        self.assertEqual(payload["verdict"], "RENDER")


if __name__ == "__main__":
    unittest.main()
