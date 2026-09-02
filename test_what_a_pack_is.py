#!/usr/bin/env python3
"""Pin what-a-pack-is leftover. Do not remint pack-quality leftover."""

from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HELPER = ROOT / "host/what_a_pack_is.py"
RECEIPT = ROOT / "p/cursor-what-a-pack-is-20260902-01.md"
CATALOG = ROOT / "ground/WHAT_A_PACK_IS.json"
DOOR = ROOT / "what-a-pack-is.html"

KEEP = {
    "p/cursor-pack-quality-dictates-tier-20260902-01.md": "f2054b18",
    "host/pack_quality_dictates_tier.py": "74d36b0a",
    "ground/PACK_QUALITY_DICTATES_TIER.json": "fa45160f",
    "test_pack_quality_dictates_tier.py": "d85754b9",
    "pack-quality-tier.html": "2443aebe",
    "p/cursor-pack-quality-dictates-tier-readback-20260902-01.md": "aa5f6bbd",
    "ground/BUSINESS_PACK_KEEP_SELL.json": "4e0e3eb0",
    "host/business_pack_keep_sell.py": "a375adf9",
    "keep-sell.html": "5964bba1",
    "p/cursor-merge-on-pr-20260902-01.md": "22b63e25",
    "p/cursor-merge-on-pr-readback-20260902-01.md": "e160b2c3",
    "host/merge_on_pr.py": "0270094d",
    "host/sprint_integration.py": "b7bec0b9",
    "p/grok-build-discord-cloud-billing-lock-readback-20260902-01.md": "e14e443b",
    "p/grok-build-discord-cloud-billing-lock-20260902-01.md": "2e0bfbfb",
    "p/grokbuild-pr8399-commons-slack-readback-20260902-01.md": "aaf290ad",
    "p/grokbuild-occupancy-landed-work-keep-lift-readback-20260902-01.md": "892bc4c0",
    "p/cursor-stealable-lanes-occupancy-20260902-01.md": "9631e869",
    "p/cursor-harborline-pack-market-render-20260902-01.md": "54c348dc",
    "p/cursor-harborline-qualify-live-probe-20260902-01.md": "92c4e31f",
    "p/cursor-since-you-last-looked-20260902-01.md": "003828c9",
    "ground/OWNER_NOW.md": "59b1fd37",
    "hub_pages.py": "5ac12648",
    "door.js": "dc59355d",
    "api/mcp.py": "bc558a5f",
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


class TestWhatAPackIs(unittest.TestCase):
    def test_keep_pack_quality_item6_unique_packs(self) -> None:
        for rel, prefix in KEEP.items():
            blob = git_blob(rel)
            self.assertTrue(
                blob.startswith(prefix),
                f"{rel} reminted: want {prefix} got {blob[:8]}",
            )

    def test_catalog_ready_to_run_not_instructions(self) -> None:
        data = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(data["id"], "cursor-what-a-pack-is-20260902-01")
        self.assertEqual(data["item"], 12)
        self.assertEqual(data["remainder"], "what-a-pack-is")
        self.assertTrue(data["pack_is_ready_to_run_business"])
        self.assertFalse(data["pack_is_instructions"])
        self.assertTrue(data["public_descriptions_and_methods"])
        self.assertEqual(data["withheld"], "build_pack_access")
        self.assertTrue(data["never_contains_go_buy_this"])
        self.assertEqual(data["extra_buy"], "tjlabs_supporting_product_or_service")
        self.assertFalse(data["tos"]["peer_opinions"])
        self.assertEqual(data["tos"]["shape"], "OPEN_QUESTION")
        self.assertEqual(data["example"]["price_usd"], 200)
        self.assertFalse(data["example"]["method_pdf"])
        self.assertEqual(data["example"]["accounts_prepared"], "FINDER-FAILED")
        self.assertEqual(data["example"]["paperwork_prepared"], "FINDER-FAILED")
        self.assertFalse(data["remint_pack_quality"])
        self.assertFalse(data["login"])
        self.assertFalse(data["commons_is_store"])

    def test_json_renders_without_inventing_tos(self) -> None:
        proc = run_helper("--json")
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        packet = json.loads(proc.stdout)
        self.assertEqual(packet["verdict"], "RENDER")
        self.assertTrue(packet["pack_is_ready_to_run_business"])
        self.assertFalse(packet["pack_is_instructions"])
        self.assertTrue(packet["public_descriptions_and_methods"])
        self.assertEqual(packet["withheld"], "build_pack_access")
        self.assertTrue(packet["never_contains_go_buy_this"])
        self.assertEqual(packet["extra_buy"], "tjlabs_supporting_product_or_service")
        self.assertTrue(packet["quality_dictates_tier"])
        self.assertFalse(packet["undercut_to_fit_tier"])
        self.assertEqual(packet["floor_usd"], 20)
        self.assertTrue(packet["ride_pack_quality"])
        self.assertFalse(packet["remint_pack_quality"])
        self.assertEqual(packet["tos_shape"], "OPEN_QUESTION")
        self.assertEqual(packet["tos_residual_pct"], "FINDER-FAILED")
        self.assertFalse(packet["peer_tos_opinions"])
        self.assertEqual(packet["example"]["price_usd"], 200)
        self.assertFalse(packet["example"]["method_pdf"])
        self.assertEqual(packet["sends"], 0)
        self.assertFalse(packet["invented_stripe_urls"])
        self.assertEqual(packet["checkout"], "FINDER-FAILED")
        self.assertFalse(packet["commons_is_store"])
        self.assertFalse(packet["login"])
        self.assertFalse(packet["gate"])

    def test_send_tos_budget_legal_refused(self) -> None:
        for flag in (
            "--send",
            "--apply",
            "--go",
            "--autopilot",
            "--undercut",
            "--tos",
            "--budget",
            "--legal",
        ):
            proc = run_helper(flag)
            self.assertEqual(proc.returncode, 2, msg=proc.stdout + proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["sent"], 0)
            self.assertEqual(payload["cash"], 0)
            self.assertEqual(payload["refused"], flag)
            self.assertFalse(payload["peer_tos_opinions"])
        proc = run_helper("--not-a-real-flag")
        self.assertEqual(proc.returncode, 1)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "FINDER-FAILED")
        self.assertEqual(payload["sent"], 0)

    def test_leftover_pack_quality_still_passes(self) -> None:
        proc = subprocess.run(
            ["python3", "-m", "unittest", "test_pack_quality_dictates_tier.py"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stdout + proc.stderr)
        self.assertIn("Ran 5 tests", proc.stderr)

    def test_receipt_and_door_do_not_steal(self) -> None:
        text = RECEIPT.read_text(encoding="utf-8")
        door = DOOR.read_text(encoding="utf-8")
        leftover = (ROOT / "p/cursor-pack-quality-dictates-tier-20260902-01.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("cursor-what-a-pack-is-20260902-01", text)
        self.assertIn("1788387736.969339", text)
        self.assertIn("1788387501.942889", text)
        self.assertIn("Did not remint", text)
        self.assertIn("f2054b18", text)
        self.assertIn("74d36b0a", text)
        self.assertIn("e160b2c3", text)
        self.assertIn("e14e443b", text)
        self.assertNotEqual(text, leftover)
        self.assertNotIn("buy.stripe.com", text)
        self.assertIn("ready-to-run business", door.lower())
        self.assertIn("No login", door)
        self.assertIn("FINDER-FAILED", door)
        self.assertIn("Harborline Local Sites", door)
        self.assertIn("$200", door)
        self.assertNotIn("https://buy.stripe.com/", door)
        self.assertNotIn("oauth", door.lower())
        self.assertNotIn("api key", door.lower())
        self.assertFalse((ROOT / "marketplace.html").exists())
        self.assertFalse((ROOT / "qualify.html").exists())
        self.assertFalse((ROOT / "CLAUDE_CORNER.md").exists())


if __name__ == "__main__":
    unittest.main()
