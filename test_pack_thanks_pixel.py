#!/usr/bin/env python3
"""Generic thanks-pixel channels leftover. Does not remint the peer door."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import pack_thanks_pixel as thanks  # noqa: E402


CHANNELS_ID = "cursor-pack-thanks-channels-20260902-01"
PEER_ID = "cursor-business-pack-thanks-pixel-20260902-01"


class PackThanksPixelTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = thanks.load_channels()

    def test_law_is_generic_empty_slots_and_does_not_steal_peer_paths(self) -> None:
        self.assertEqual(self.law["id"], CHANNELS_ID)
        self.assertIs(self.law["did_not_overwrite_peer_door"], True)
        self.assertEqual(self.law["peer_law"], "ground/BUSINESS_PACK_THANKS.json")
        self.assertEqual(self.law["peer_helper"], "host/business_pack_thanks.py")
        self.assertEqual(self.law["peer_door"], "packs/thanks.html")
        self.assertEqual(
            self.law["scout_demand_id"],
            "scout-demand-pack-door-thanks-pixel-20260902-01",
        )
        self.assertIs(self.law["did_not_remint_scout_demand"], True)
        self.assertIs(self.law["agents_mint_pixel_id"], False)
        self.assertIs(self.law["agents_spend_ads"], False)
        self.assertEqual(self.law["checkout"], "NOT_MINTED")
        channels = self.law["channels"]
        for name in ("x", "tiktok", "meta"):
            self.assertEqual(channels[name]["pixel_id"], "")
            self.assertEqual(channels[name]["event"], "Purchase")
            self.assertTrue(channels[name]["script_src_when_filled"])
        self.assertNotIn("337 NO", json.dumps(self.law))
        for path in thanks.DO_NOT_OVERWRITE:
            self.assertNotEqual(Path(path).name, "pack_thanks_pixel.py")

    def test_all_empty_loads_zero_scripts_and_zero_purchases(self) -> None:
        result = thanks.classify_channels(self.law)
        self.assertEqual(result["verdict"], "CHANNELS_ALL_EMPTY")
        self.assertEqual(result["purchase_count"], 0)
        self.assertEqual(result["purchases"], [])
        self.assertEqual(result["would_load_script"], [])
        self.assertTrue(result["empty_independently_loads_nothing"])
        self.assertTrue(result["did_not_overwrite_peer_door"])
        for name in ("x", "tiktok", "meta"):
            self.assertFalse(result["channels"][name]["pixel_id_present"])
            self.assertTrue(result["channels"][name]["empty_loads_nothing"])

    def test_one_purchase_per_platform_present_independent_empty(self) -> None:
        x_only = thanks.classify_channels(
            self.law, overrides={"x": "tw-owner"}, value="200"
        )
        self.assertEqual(x_only["verdict"], "CHANNELS_PARTIAL")
        self.assertEqual(x_only["purchase_count"], 1)
        self.assertEqual(x_only["purchases"][0]["channel"], "x")
        self.assertEqual(x_only["purchases"][0]["event"], "Purchase")
        self.assertEqual(x_only["purchases"][0]["value"], 200.0)
        self.assertTrue(x_only["channels"]["tiktok"]["empty_loads_nothing"])
        self.assertTrue(x_only["channels"]["meta"]["empty_loads_nothing"])

        two = thanks.classify_channels(
            self.law,
            overrides={"x": "tw-owner", "tiktok": "tt-owner"},
            value="100",
        )
        self.assertEqual(two["purchase_count"], 2)
        self.assertEqual([row["channel"] for row in two["purchases"]], ["x", "tiktok"])
        self.assertTrue(two["channels"]["meta"]["empty_loads_nothing"])
        self.assertEqual(len(two["would_load_script"]), 2)

        all_three = thanks.classify_channels(
            self.law,
            overrides={"x": "tw", "tiktok": "tt", "meta": "fb"},
            value="1000",
        )
        self.assertEqual(all_three["verdict"], "CHANNELS_ALL_FILLED")
        self.assertEqual(all_three["purchase_count"], 3)
        self.assertEqual(
            [row["event"] for row in all_three["purchases"]],
            ["Purchase", "Purchase", "Purchase"],
        )
        self.assertEqual(all_three["purchases"][0]["value"], 1000.0)

    def test_missing_value_does_not_invent_a_price(self) -> None:
        result = thanks.classify_channels(self.law, overrides={"meta": "fb-owner"})
        self.assertEqual(result["purchase_count"], 1)
        self.assertNotIn("value", result["purchases"][0])

    def test_peer_door_empty_slot_when_present(self) -> None:
        peer = thanks.classify_peer_door()
        if not peer["present"]:
            self.skipTest(f"peer door not in this tree: {peer['missing']}")
        self.assertEqual(peer["peer_id"], PEER_ID)
        self.assertTrue(peer["pixel_id_empty"])
        self.assertEqual(peer["static_third_party_scripts"], [])
        self.assertTrue(peer["empty_loads_zero_third_party_scripts"])
        self.assertTrue(peer["fetches_peer_json"])
        self.assertTrue(peer["no_static_script_src"])
        self.assertFalse(peer["earnings_claim"])
        self.assertTrue(peer["did_not_overwrite"])

    def test_helper_refuses_peer_overwrite_list(self) -> None:
        result = thanks.classify()
        self.assertEqual(
            result["do_not_overwrite"],
            [
                "packs/thanks.html",
                "ground/BUSINESS_PACK_THANKS.json",
                "host/business_pack_thanks.py",
            ],
        )

    def test_cli_empty_channels(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "pack_thanks_pixel.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "CHANNELS_ALL_EMPTY")
        self.assertEqual(payload["law_id"], CHANNELS_ID)
        self.assertEqual(payload["purchase_count"], 0)

    def test_cli_accepts_temp_channels_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "channels.json"
            payload = dict(self.law)
            payload = json.loads(json.dumps(payload))
            payload["channels"]["x"]["pixel_id"] = "tw-temp"
            path.write_text(json.dumps(payload), encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "host" / "pack_thanks_pixel.py"),
                    "--channels",
                    str(path),
                    "--value",
                    "50",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            out = json.loads(proc.stdout)
            self.assertEqual(out["purchase_count"], 1)
            self.assertEqual(out["purchases"][0]["value"], 50.0)


if __name__ == "__main__":
    unittest.main()
