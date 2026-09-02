#!/usr/bin/env python3
"""Curbline Weekend shop instance keeps the pack laws: no earnings, no invented rails, brand + door, unique fingerprint."""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "packs" / "curbline-weekend-yard-help-20260902-01"
SPEC = importlib.util.spec_from_file_location("business_pack_desk_instance", ROOT / "host" / "business_pack_desk_instance.py")
assert SPEC and SPEC.loader
desk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(desk)


class YardHelpInstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        cls.result = desk.verify(PACK)

    def test_instance_verifies_clean(self):
        self.assertEqual(self.result["errors"], [], self.result["errors"])
        self.assertEqual(self.result["state"], "INSTANCE_OK")
        self.assertFalse(self.result["gate"])
        self.assertEqual(self.result["checkout"], "NOT_MINTED")

    def test_cli_exits_zero_for_this_pack(self):
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "business_pack_desk_instance.py"),
                "--pack",
                str(PACK),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["state"], "INSTANCE_OK")
        self.assertEqual(payload["sell_instance_verdict"], "UNIQUE_INSTANCE_SELL_OK")

    def test_manifest_matches_disk_and_law(self):
        computed = desk.compute(PACK, self.manifest)
        self.assertEqual(self.manifest["fingerprint"], computed["fingerprint"])
        self.assertEqual(self.manifest["assets"], computed["assets"])
        self.assertEqual(self.manifest["instance_fields"], computed["instance_fields"])
        self.assertEqual(self.manifest["tier_usd"], 100)
        self.assertEqual(self.manifest["brand"], "Curbline Weekend")
        self.assertEqual(self.manifest["checkout"]["state"], "OWNER_PASTE_REQUIRED")
        self.assertEqual(self.manifest["checkout"]["status"], "NOT_MINTED")
        self.assertEqual(self.manifest["checkout"]["url"], "")
        self.assertEqual(self.manifest["marketing"], "bryce_only")
        self.assertIs(self.manifest["leads_included"], False)
        self.assertIs(self.manifest["customers_provided"], False)
        self.assertEqual(self.manifest["keep_or_sell"], "UNDECIDED")
        self.assertEqual(self.manifest["demand_id"], "scout-demand-yard-card-instance-20260902-01")
        self.assertIs(self.manifest["did_not_remint_scout_demand"], True)
        self.assertTrue(all(verdict == "COPY_OK" for verdict in self.manifest["copy_verdicts"].values()), self.manifest["copy_verdicts"])
        self.assertEqual(self.manifest["twin_sale_verdict"], "CLONE_STAMP")

    def test_tjlabs_terms_slots_stay_owner_unset_and_unsaleable(self):
        terms = self.manifest["terms"]
        self.assertEqual(terms["profit_share_percent"], "OWNER_UNSET")
        self.assertEqual(terms["partial_ownership_fraction"], "OWNER_UNSET")
        self.assertIs(terms["owner_pasted"], False)
        self.assertIs(terms["counsel_cleared"], False)
        self.assertEqual(self.manifest["terms_verdict"], "TOS_INCOMPLETE")
        self.assertIs(self.manifest["saleable"], False)
        text = (PACK / "terms.md").read_text(encoding="utf-8")
        self.assertIn("tjlabs_profit_share_percent: OWNER_UNSET", text)
        self.assertIn("tjlabs_partial_ownership_fraction: OWNER_UNSET", text)
        self.assertIn("NOT_MINTED", text)

    def test_factory_slots_present_and_owner_unset(self):
        for name in ("paperwork.md", "running-cost.md", "day.md"):
            self.assertTrue((PACK / name).is_file(), name)
        slots = self.manifest["slots"]
        self.assertEqual(slots["paperwork_state"], "OWNER_UNSET")
        self.assertEqual(slots["formation_partner_link"], "OWNER_UNSET")
        self.assertEqual(slots["running_cost_amount"], "OWNER_UNSET")
        self.assertEqual(slots["running_cost_owner_pasted"], "no")
        self.assertTrue(slots["support_subscription_price"].startswith("OWNER_UNSET"))
        door = (PACK / "index.html").read_text(encoding="utf-8").lower()
        for phrase in ("we handle your legal paperwork", "we set up your llc", "compliance guaranteed", "paperwork included", "become a business owner", "for this price"):
            self.assertNotIn(phrase, door, phrase)

    def test_claimed_files_present(self):
        for name in desk.TEMPLATE_FILES + ("paperwork.md", "running-cost.md", "day.md", "rating.md", "creative_brief.md", "gems.md"):
            self.assertTrue((PACK / name).is_file(), name)
            self.assertGreater(len((PACK / name).read_text(encoding="utf-8")), 200, name)
        for name in (
            "brand.md",
            "card-copy.md",
            "price-sheet.md",
            "invoice-text.md",
            "route-log.md",
            "phone-script.md",
            "job-checklist.md",
            "paperwork-checklist.md",
            "days-8-30.md",
        ):
            self.assertTrue((PACK / "assets" / name).is_file(), name)

    def test_door_copy_is_weekend_yard_help_not_greeting_sign(self):
        door = (PACK / "index.html").read_text(encoding="utf-8")
        self.assertIn("weekend yard-help route", door)
        self.assertIn("$100", door)
        self.assertIn("NOT_MINTED", door)
        self.assertIn("mailto:tokenjunkielabs@gmail.com", door)
        self.assertNotIn("<script", door.lower())
        joined = "\n".join(p.read_text(encoding="utf-8") for p in desk.text_files(PACK))
        self.assertNotRegex(joined.lower(), r"\byard card\b")
        self.assertIn("$40", joined)
        self.assertIn("$60", joined)
        self.assertIn("$80", joined)

    def test_instructions_carry_nine_signals_and_ten_stop_route(self):
        text = (PACK / "instructions.md").read_text(encoding="utf-8")
        for signal in ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"):
            self.assertIn(f"| {signal} |", text)
        self.assertIn("ten", text.lower())
        self.assertIn("two hours", text.lower())

    def test_prices_present_and_no_earnings_or_invented_rails(self):
        sheet = (PACK / "assets" / "price-sheet.md").read_text(encoding="utf-8")
        for price in ("$40", "$60", "$80"):
            self.assertIn(price, sheet)
        joined = "\n".join(p.read_text(encoding="utf-8") for p in desk.text_files(PACK)).lower()
        for pattern in (r"\bmake\s+\$\d", r"\bearn\s+\$\d", r"\bprofit\s+\$\d", r"\bmake \$\d+ this weekend"):
            self.assertNotRegex(joined, pattern)
        self.assertNotIn("https://buy.stripe.com/", joined)
        self.assertNotIn("https://donate.stripe.com/", joined)
        self.assertNotRegex(joined, r"plink_[a-z0-9]+")

    def test_off_limits_untouched(self):
        self.assertTrue((ROOT / "revenue" / "pack_keep_sell_candidates" / "yard-card-route-20260902-01" / "RUNBOOK.md").is_file())
        self.assertTrue((ROOT / "packs" / "sidewalk-signal-web-desk-20260902-01" / "index.html").is_file())
        self.assertTrue((ROOT / "p" / "scout-demand-yard-card-instance-20260902-01.md").is_file() is False)
        self.assertTrue((ROOT / "p" / "tally-yard-help-route-instance-20260902-01.md").is_file())

    def test_invented_partner_link_fails_closed(self):
        import shutil

        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "packs" / PACK.name
            shutil.copytree(PACK, dest)
            paperwork = dest / "paperwork.md"
            paperwork.write_text(
                paperwork.read_text(encoding="utf-8").replace(
                    "Link: `OWNER_UNSET`",
                    "Link: https://example.invalid/form-my-llc",
                ),
                encoding="utf-8",
            )
            desk.write_manifest(dest)
            result = desk.verify(dest)
            self.assertTrue(any("formation partner link" in item for item in result["errors"]), result["errors"])


if __name__ == "__main__":
    unittest.main()
