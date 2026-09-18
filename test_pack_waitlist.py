#!/usr/bin/env python3
"""First-party pack waitlist. Consent, CCPA, JSONL, counts only, zero sends."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "host"))

import pack_waitlist as waitlist  # noqa: E402


LAW_ID = "cursor-pack-door-waitlist-20260902-01"
DEMAND = "scout-demand-pack-door-waitlist-20260902-01"


class PackWaitlistTest(unittest.TestCase):
    def setUp(self) -> None:
        self.law = waitlist.load_law()
        self.door_html = (ROOT / "packs" / "waitlist.html").read_text(encoding="utf-8")

    def test_law_matches_demand_and_does_not_steal(self) -> None:
        self.assertEqual(self.law["id"], LAW_ID)
        self.assertEqual(self.law["scout_demand_id"], DEMAND)
        self.assertIs(self.law["did_not_remint_scout_demand"], True)
        self.assertEqual(self.law["storage"], "owner_local_jsonl")
        self.assertIs(self.law["did_not_steal_swarm_mail"], True)
        self.assertIs(self.law["did_not_steal_agentmail"], True)
        self.assertEqual(self.law["post_url"], "")
        self.assertEqual(self.law["sends"], 0)
        self.assertIs(self.law["list_is_unsent_asset"], True)
        self.assertIs(self.law["sending_owner_gated"], True)
        self.assertIs(self.law["ccpa_do_not_sell_share"], True)
        self.assertIs(self.law["ccpa_required_before_pixel_fires"], True)
        self.assertIs(self.law["addresses_public"], False)
        self.assertIs(self.law["agents_mint_pixel_id"], False)
        self.assertIs(self.law["agents_spend_ads"], False)
        self.assertEqual(self.law["checkout"], "NOT_MINTED")
        self.assertIs(self.law["gate"], False)
        self.assertNotIn("337 NO", json.dumps(self.law))
        for path in waitlist.DO_NOT_STEAL:
            self.assertNotEqual(Path(path).name, "pack_waitlist.py")

    def test_door_has_consent_ccpa_and_no_third_party_scripts(self) -> None:
        door = waitlist.classify_door(self.door_html)
        self.assertEqual(door["verdict"], "WAITLIST_DOOR_OK")
        self.assertTrue(door["has_email_field"])
        self.assertTrue(door["has_tier_field"])
        self.assertTrue(door["has_state_field"])
        self.assertTrue(door["consent_at_form"])
        self.assertTrue(door["ccpa_link_present"])
        self.assertTrue(door["unsubscribe_any_time"])
        self.assertFalse(door["password_field"])
        self.assertEqual(door["static_third_party_scripts"], [])
        self.assertFalse(door["earnings_claim"])
        self.assertTrue(door["robots_index_follow"])
        self.assertIs(door["gate"], False)
        self.assertEqual(door["sends"], 0)
        self.assertIn("Do Not Sell or Share My Personal Information", self.door_html)
        self.assertNotIn("<script src=", self.door_html.lower())
        self.assertNotIn('type="password"', self.door_html.lower())

    def test_template_slot_is_additive(self) -> None:
        result = waitlist.classify()
        self.assertTrue(result["template_slot_present"])
        self.assertTrue(result["template_slot_points_at_shared_door"])
        self.assertTrue(result["did_not_steal_swarm_mail"])
        self.assertTrue(result["did_not_overwrite_thanks_door"])
        self.assertEqual(result["sends"], 0)
        slot = (ROOT / "packs" / "_template" / "waitlist-slot.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("packs/waitlist.html", slot)
        self.assertIn("Do Not Sell or Share My Personal Information", slot)

    def test_jsonl_append_reads_counts_without_addresses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "waitlist-signups.jsonl"
            first = waitlist.append_signup(
                path,
                {
                    "email": "Ada@Example.com",
                    "tier": "desk",
                    "state": "or",
                    "consent": True,
                },
            )
            self.assertEqual(first["verdict"], "SIGNUP_OK")
            self.assertEqual(first["sends"], 0)
            self.assertNotIn("email", first)
            self.assertEqual(first["counts"]["tiers"]["desk"], 1)
            self.assertEqual(first["counts"]["total"], 1)
            self.assertIs(first["counts"]["addresses_public"], False)
            dumped = json.dumps(first["counts"])
            self.assertNotIn("@", dumped)
            self.assertNotIn("ada@example.com", dumped.lower())

            waitlist.append_signup(
                path,
                {
                    "email": "bob@example.com",
                    "tier": "keep",
                    "state": "TX",
                    "consent": True,
                },
            )
            counts = waitlist.public_counts(path)
            self.assertEqual(counts["tiers"]["desk"], 1)
            self.assertEqual(counts["tiers"]["keep"], 1)
            self.assertEqual(counts["total"], 2)
            self.assertEqual(counts["sends"], 0)
            self.assertNotIn("@", json.dumps(counts))

            moved = waitlist.append_signup(
                path,
                {
                    "email": "ada@example.com",
                    "tier": "plant",
                    "state": "OR",
                    "consent": True,
                },
            )
            self.assertEqual(moved["counts"]["tiers"]["desk"], 0)
            self.assertEqual(moved["counts"]["tiers"]["plant"], 1)
            self.assertEqual(moved["counts"]["total"], 2)

    def test_missing_consent_or_bad_email_does_not_write(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "waitlist-signups.jsonl"
            denied = waitlist.append_signup(
                path,
                {
                    "email": "ok@example.com",
                    "tier": "desk",
                    "state": "OR",
                    "consent": False,
                },
            )
            self.assertEqual(denied["verdict"], "WAITLIST_INVALID")
            self.assertIn("consent", denied["missing"])
            self.assertFalse(path.is_file())
            bad = waitlist.append_signup(
                path,
                {
                    "email": "not-an-email",
                    "tier": "desk",
                    "state": "OR",
                    "consent": True,
                },
            )
            self.assertEqual(bad["verdict"], "WAITLIST_INVALID")
            self.assertIn("email", bad["missing"])

    def test_opt_out_drops_counts_and_blocks_pixels(self) -> None:
        self.assertFalse(waitlist.pixel_allowed(True, "tw-owner"))
        self.assertFalse(waitlist.pixel_allowed(False, ""))
        self.assertTrue(waitlist.pixel_allowed(False, "tw-owner"))
        self.assertEqual(waitlist.sends(), 0)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "waitlist-signups.jsonl"
            waitlist.append_signup(
                path,
                {
                    "email": "c@example.com",
                    "tier": "unique",
                    "state": "CA",
                    "consent": True,
                },
            )
            out = waitlist.append_signup(
                path,
                {
                    "email": "c@example.com",
                    "kind": "opt_out",
                    "ccpa_do_not_sell": True,
                },
            )
            self.assertEqual(out["verdict"], "OPT_OUT_OK")
            self.assertEqual(out["counts"]["total"], 0)
            self.assertEqual(out["counts"]["tiers"]["unique"], 0)
            self.assertFalse(out["pixel_allowed"])
            self.assertNotIn("@", json.dumps(out["counts"]))

    def test_http_post_and_get_never_expose_addresses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "waitlist-signups.jsonl"
            posted = waitlist.handle_http(
                "POST",
                "/waitlist",
                body=json.dumps(
                    {
                        "email": "desk@example.com",
                        "tier": "desk",
                        "state": "WA",
                        "consent": True,
                    }
                ).encode("utf-8"),
                jsonl_path=path,
            )
            self.assertEqual(posted["status"], 200)
            self.assertEqual(posted["body"]["verdict"], "SIGNUP_OK")
            self.assertEqual(posted["body"]["counts"]["tiers"]["desk"], 1)
            self.assertNotIn("@", json.dumps(posted["body"]))
            got = waitlist.handle_http("GET", "/waitlist/counts", jsonl_path=path)
            self.assertEqual(got["status"], 200)
            self.assertEqual(got["body"]["total"], 1)
            self.assertIs(got["body"]["addresses_public"], False)
            self.assertEqual(got["body"]["sends"], 0)
            self.assertNotIn("@", json.dumps(got["body"]))
            self.assertNotIn("email", got["body"])

    def test_cli_classify(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "pack_waitlist.py")],
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["verdict"], "WAITLIST_DOOR_OK")
        self.assertEqual(payload["law_id"], LAW_ID)
        self.assertEqual(payload["scout_demand_id"], DEMAND)
        self.assertEqual(payload["sends"], 0)
        self.assertTrue(payload["post_url_empty_by_default"])


if __name__ == "__main__":
    unittest.main()
