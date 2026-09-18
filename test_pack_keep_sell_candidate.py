#!/usr/bin/env python3
"""KEEP vs SELL pack candidates refuse invented checkout URLs and ads."""
from __future__ import annotations

import copy
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "pack_keep_sell_candidate", ROOT / "host" / "pack_keep_sell_candidate.py"
)
assert SPEC and SPEC.loader
candidate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(candidate)

PACK = (
    ROOT
    / "revenue"
    / "pack_keep_sell_candidates"
    / "yard-card-route-20260902-01"
)


class PackKeepSellCandidate(unittest.TestCase):
    def test_current_tree_has_one_undecided_yard_card_pack(self):
        row = candidate.measure_root(str(ROOT))
        self.assertEqual(row["errors"], [], row["errors"])
        self.assertEqual(row["state"], "INTEGRATED")
        self.assertEqual(row["candidate_count"], 1)
        self.assertEqual(row["candidates"][0]["id"], "yard-card-route-20260902-01")
        self.assertEqual(row["candidates"][0]["decision"], "UNDECIDED")
        self.assertEqual(row["candidates"][0]["tier_usd"], 100)
        self.assertEqual(row["candidates"][0]["checkout_state"], "OWNER_PASTE_REQUIRED")

    def test_cli_exits_zero_on_current_tree(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "pack_keep_sell_candidate.py"),
                "--root",
                str(ROOT),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["state"], "INTEGRATED")

    def test_invented_stripe_url_is_rejected(self):
        manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        bad = copy.deepcopy(manifest)
        bad["checkout"] = {
            "state": "PROVEN_PUBLIC_RAIL",
            "url": "https://buy.stripe.com/this-is-not-a-real-link",
        }
        errors = candidate.validate_manifest(
            str(ROOT),
            "revenue/pack_keep_sell_candidates/yard-card-route-20260902-01/manifest.json",
            bad,
        )
        self.assertTrue(any("invented checkout URL" in item for item in errors), errors)

    def test_agent_ad_spend_is_rejected(self):
        manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        bad = copy.deepcopy(manifest)
        bad["marketing_spend_usd"] = 25
        bad["ad_peer"] = True
        errors = candidate.validate_manifest(
            str(ROOT),
            "revenue/pack_keep_sell_candidates/yard-card-route-20260902-01/manifest.json",
            bad,
        )
        self.assertTrue(any("marketing_spend_usd" in item for item in errors), errors)
        self.assertTrue(any("ad_peer" in item for item in errors), errors)

    def test_blank_checkout_stays_legal(self):
        manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["checkout"]["url"], "")
        self.assertEqual(manifest["checkout"]["state"], "OWNER_PASTE_REQUIRED")
        self.assertEqual(manifest["marketing"], "bryce_only")
        self.assertEqual(manifest["scaffold_owned_by"], "GOAT")
        self.assertEqual(manifest["cash_usd"], 0)
        errors = candidate.validate_manifest(
            str(ROOT),
            "revenue/pack_keep_sell_candidates/yard-card-route-20260902-01/manifest.json",
            manifest,
        )
        self.assertEqual(errors, [])

    def test_owner_pasted_proven_rail_is_accepted(self):
        host_dir = str(ROOT / "host")
        if host_dir not in sys.path:
            sys.path.insert(0, host_dir)
        urls = candidate.proven_public_urls(str(ROOT))
        self.assertTrue(urls)
        manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        good = copy.deepcopy(manifest)
        good["checkout"] = {
            "state": "PROVEN_PUBLIC_RAIL",
            "url": sorted(urls)[0],
        }
        errors = candidate.validate_manifest(
            str(ROOT),
            "revenue/pack_keep_sell_candidates/yard-card-route-20260902-01/manifest.json",
            good,
        )
        self.assertEqual(errors, [])

    def test_missing_asset_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = (
                Path(tmp)
                / "revenue"
                / "pack_keep_sell_candidates"
                / "yard-card-route-20260902-01"
            )
            shutil.copytree(PACK, dest)
            os.remove(dest / "assets" / "card-copy.txt")
            row = candidate.measure_root(tmp)
            self.assertEqual(row["state"], "ERROR")
            self.assertTrue(any("card-copy.txt" in item for item in row["errors"]), row["errors"])

    def test_does_not_steal_goat_scaffold_or_remap_channel(self):
        text = (ROOT / "host" / "pack_keep_sell_candidate.py").read_text(encoding="utf-8")
        self.assertIn("not GOAT's factory scaffold", text)
        self.assertNotIn("business-packs.html", text)
        self.assertNotIn("SLACK_CONTROL_PLANE", text)


if __name__ == "__main__":
    unittest.main()
