#!/usr/bin/env python3
"""The Sidewalk Signal desk instance keeps the pack laws: no earnings, no invented rails, brand + door, unique fingerprint."""
from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACK = ROOT / "packs" / "sidewalk-signal-web-desk-20260902-01"
SPEC = importlib.util.spec_from_file_location("business_pack_desk_instance", ROOT / "host" / "business_pack_desk_instance.py")
assert SPEC and SPEC.loader
desk = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(desk)


def _copy_pack(tmp: str) -> Path:
    dest = Path(tmp) / "packs" / PACK.name
    shutil.copytree(PACK, dest)
    return dest


class DeskInstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
        cls.result = desk.verify(PACK)

    def test_instance_verifies_clean(self):
        self.assertEqual(self.result["errors"], [], self.result["errors"])
        self.assertEqual(self.result["state"], "INSTANCE_OK")
        self.assertFalse(self.result["gate"])
        self.assertEqual(self.result["checkout"], "NOT_MINTED")

    def test_cli_exits_zero(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "host" / "business_pack_desk_instance.py")],
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
        self.assertEqual(self.manifest["tier_usd"], 200)
        self.assertEqual(self.manifest["brand"], "Sidewalk Signal")
        self.assertEqual(self.manifest["checkout"]["state"], "OWNER_PASTE_REQUIRED")
        self.assertEqual(self.manifest["checkout"]["url"], "")
        self.assertEqual(self.manifest["marketing"], "bryce_only")
        self.assertIs(self.manifest["leads_included"], False)
        self.assertIs(self.manifest["customers_provided"], False)
        self.assertEqual(self.manifest["keep_or_sell"], "UNDECIDED")
        self.assertEqual(self.manifest["demand_id"], "scout-demand-desk-website-service-pack-20260902-01")
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
        self.assertNotRegex(text, r"tjlabs_profit_share_percent:\s*\d")

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

    def test_sold_once_badge_is_rendered_from_the_verdict(self):
        self.assertIs(self.manifest["sold_once"], True)
        self.assertEqual(self.manifest["badge_line"], desk.SOLD_ONCE_LINE)
        self.assertEqual(self.manifest["anchor_line"], "OWNER_UNSET")
        door = (PACK / "index.html").read_text(encoding="utf-8")
        self.assertEqual(desk.door_badge(door), desk.badge_html(desk.SOLD_ONCE_LINE))
        self.assertIn('<code data-slot="anchor_line">OWNER_UNSET</code>', door)

    def test_recorded_clone_sale_flips_the_badge(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _copy_pack(tmp)
            manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
            clone = {"sale_id": "sale-recorded-clone", **manifest["instance_fields"]}
            manifest["sales"] = [clone]
            (dest / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            refreshed = desk.write_manifest(dest)
            self.assertIs(refreshed["sold_once"], False)
            self.assertEqual(refreshed["badge_line"], desk.SAME_METHOD_LINE)
            door = (dest / "index.html").read_text(encoding="utf-8")
            self.assertEqual(desk.door_badge(door), desk.badge_html(desk.SAME_METHOD_LINE))
            self.assertEqual(desk.verify(dest)["errors"], [])

    def test_hand_edited_badge_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _copy_pack(tmp)
            door = dest / "index.html"
            door.write_text(door.read_text(encoding="utf-8").replace(desk.SOLD_ONCE_LINE, "Sold to thousands."), encoding="utf-8")
            result = desk.verify(dest)
            self.assertTrue(any("badge" in item for item in result["errors"]), result["errors"])

    def test_invented_partner_link_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _copy_pack(tmp)
            paperwork = dest / "paperwork.md"
            paperwork.write_text(paperwork.read_text(encoding="utf-8").replace("Link: `OWNER_UNSET`", "Link: https://example.invalid/form-my-llc"), encoding="utf-8")
            desk.write_manifest(dest)
            result = desk.verify(dest)
            self.assertTrue(any("formation partner link" in item for item in result["errors"]), result["errors"])

    def test_invented_terms_number_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _copy_pack(tmp)
            terms = dest / "terms.md"
            terms.write_text(terms.read_text(encoding="utf-8").replace("tjlabs_profit_share_percent: OWNER_UNSET", "tjlabs_profit_share_percent: 15"), encoding="utf-8")
            desk.write_manifest(dest)
            result = desk.verify(dest)
            self.assertEqual(result["state"], "ERROR")
            self.assertTrue(any("owner did not paste" in item for item in result["errors"]), result["errors"])

    def test_template_files_are_filled_not_scaffold_blank(self):
        for name in desk.TEMPLATE_FILES:
            text = (PACK / name).read_text(encoding="utf-8")
            self.assertGreater(len(text), 400, name)
        for name in ("brand.md", "price-sheet.md", "gap-finder-worksheet.md", "outreach-script.md", "delivery-checklist.md", "contract-placeholder.md", "days-8-30.md", "showcase-manifest.json"):
            self.assertTrue((PACK / "assets" / name).is_file(), name)

    def test_instructions_let_a_stranger_find_ten_gap_businesses(self):
        text = (PACK / "instructions.md").read_text(encoding="utf-8")
        for signal in ("S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"):
            self.assertIn(f"| {signal} |", text)
        for phrase in ("Where to look", "Name and route", "Dedupe", "Daily loop", "Weekly loop", "Stop / pause", "Revenue signal", "A dated zero must carry its search space"):
            self.assertIn(phrase, text, phrase)
        self.assertIn("Find ten gap businesses", text)

    def test_prices_present_and_no_earnings_or_client_promises(self):
        sheet = (PACK / "assets" / "price-sheet.md").read_text(encoding="utf-8")
        for price in ("$1,500", "$2,500", "$4,000", "$6,000"):
            self.assertIn(price, sheet)
        joined = "\n".join(p.read_text(encoding="utf-8") for p in desk.text_files(PACK)).lower()
        # Same definition as host/business_pack_unique.EARNINGS_RE: a dollar figure after make/earn/profit.
        # The template's own "never write make $X" sentence has no digit and stays legal.
        for pattern in (r"\bmake\s+\$\d", r"\bearn\s+\$\d", r"\bprofit\s+\$\d", r"\bmake \$\d+ this weekend"):
            self.assertNotRegex(joined, pattern)
        for phrase in ("this weekend you", "passive income", "quit your job", "leads included", "clients a month", "recession-proof", "turnkey income"):
            self.assertNotIn(phrase, joined, phrase)
        # Same markers as test_business_packs: an invented link is a URL, the template's "do not invent" sentence is not.
        self.assertNotIn("https://buy.stripe.com/", joined)
        self.assertNotIn("https://donate.stripe.com/", joined)
        self.assertNotRegex(joined, r"plink_[a-z0-9]+")

    def test_door_is_static_open_and_unminted(self):
        door = (PACK / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("<script", door.lower())
        self.assertIn("$200", door)
        self.assertIn("NOT_MINTED", door)
        self.assertIn("mailto:tokenjunkielabs@gmail.com", door)
        self.assertIn("Sidewalk Signal", door)
        self.assertNotIn("franchise", door.lower())
        self.assertNotIn("nuts", door.lower())
        self.assertIn("No customers, leads", door)

    def test_sales_law_in_outreach(self):
        script = (PACK / "assets" / "outreach-script.md").read_text(encoding="utf-8")
        self.assertIn("The subject line never contains a price", script)
        self.assertIn("Ask for a YES", script)
        self.assertIn("opt-out", script)

    def test_showcase_manifest_points_at_private_main_not_bytes_here(self):
        data = json.loads((PACK / "assets" / "showcase-manifest.json").read_text(encoding="utf-8"))
        self.assertIs(data["in_this_repository"], False)
        self.assertEqual(data["source"]["main_sha"], "0d91231e4df3cd670cb707a28847a07495c98542")
        names = {row["name"] for row in data["files"]}
        self.assertEqual(names, {"SMB-Website-Showcase.pdf", "SMB-Workflow-App-Showcase.mp4"})
        for row in data["files"]:
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
            self.assertFalse((PACK / row["name"]).exists())

    def test_earnings_claim_in_a_copy_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _copy_pack(tmp)
            offer = dest / "offer.md"
            offer.write_text(offer.read_text(encoding="utf-8") + "\nYou will make $900 this weekend.\n", encoding="utf-8")
            manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
            result = desk.verify(dest, manifest)
            self.assertEqual(result["state"], "ERROR")
            self.assertTrue(any("EARNINGS_CLAIM" in item for item in result["errors"]), result["errors"])

    def test_invented_stripe_url_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _copy_pack(tmp)
            door = dest / "index.html"
            door.write_text(door.read_text(encoding="utf-8").replace("mailto:tokenjunkielabs@gmail.com?subject=Sidewalk%20Signal%20pack", "https://buy.stripe.com/notreal"), encoding="utf-8")
            manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
            result = desk.verify(dest, manifest)
            self.assertTrue(any("Stripe" in item for item in result["errors"]), result["errors"])

    def test_edit_without_write_reports_stale_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = _copy_pack(tmp)
            (dest / "assets" / "brand.md").write_text("# Brand\n\nRenamed.\n", encoding="utf-8")
            manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
            result = desk.verify(dest, manifest)
            self.assertTrue(any("stale" in item for item in result["errors"]), result["errors"])
            desk.write_manifest(dest)
            refreshed = desk.verify(dest)
            self.assertNotIn("stale", " ".join(refreshed["errors"]))

    def test_manifest_law_flags_fail_closed(self):
        bad = copy.deepcopy(self.manifest)
        bad["ad_peer"] = True
        bad["marketing_spend_usd"] = 25
        bad["leads_included"] = True
        bad["checkout"]["url"] = "https://example.invalid/pay"
        result = desk.verify(PACK, bad)
        joined = " ".join(result["errors"])
        for needle in ("ad_peer", "marketing_spend_usd", "leads_included", "checkout.url"):
            self.assertIn(needle, joined)


if __name__ == "__main__":
    unittest.main()
