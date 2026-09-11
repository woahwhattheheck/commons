#!/usr/bin/env python3
"""Keep browser checkout readiness aligned with the canonical Python projector."""
from __future__ import annotations

import copy
import importlib.util
import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "checkout_capability", ROOT / "host" / "checkout_capability.py"
)
assert SPEC and SPEC.loader
capability = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(capability)


class PayCheckoutCapabilityParityTests(unittest.TestCase):
    def _browser_rail_eligible(self, snapshot: dict, listing: dict) -> bool:
        node = shutil.which("node")
        if not node:
            self.skipTest("node is required to execute the browser checkout predicate")
        script = r"""
const fs = require("fs");
const payload = JSON.parse(fs.readFileSync(0, "utf8"));
const source = fs.readFileSync("pay.js", "utf8");
const marker = "  var snapshotUrl = ";
const markerIndex = source.indexOf(marker);
if (markerIndex < 0) throw new Error("pay.js runtime marker not found");
const harness = source.slice(0, markerIndex) +
  "  globalThis.__payTest = { railEligible: railEligible };\n})();";
eval(harness);
process.stdout.write(JSON.stringify({
  eligible: globalThis.__payTest.railEligible(payload.snapshot, payload.listing)
}));
"""
        completed = subprocess.run(
            [node, "-e", script],
            cwd=ROOT,
            input=json.dumps({"snapshot": snapshot, "listing": listing}),
            text=True,
            capture_output=True,
            check=True,
        )
        return bool(json.loads(completed.stdout)["eligible"])

    def _current_fixture(self) -> tuple[dict, dict, dict, str]:
        snapshot = json.loads(
            (ROOT / "revenue" / "checkout_capability" / "snapshot.json").read_text(
                encoding="utf-8"
            )
        )
        catalog = json.loads(
            (ROOT / "revenue" / "outcome_commerce" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        sku = "sku-whitebox-hour-20260826"
        listing = next(row for row in catalog["listings"] if row["id"] == sku)
        return snapshot, catalog, listing, sku

    def test_browser_account_ready_requires_the_canonical_provider_capabilities(self) -> None:
        pay_js = (ROOT / "pay.js").read_text(encoding="utf-8")
        self.assertIn('provider.card_payments === "active"', pay_js)
        self.assertIn('provider.transfers === "active"', pay_js)
        self.assertIn('if (!accountReady(snapshot)) return false;', pay_js)
        self.assertIn('var stripeReady = accountReady(snapshot);', pay_js)

        snapshot, catalog, listing, sku = self._current_fixture()

        baseline = capability.project(snapshot, catalog)
        self.assertTrue(baseline["account_ready"])
        self.assertIn(sku, {row["sku"] for row in baseline["public_rails"]})
        self.assertTrue(self._browser_rail_eligible(snapshot, listing))

        for field in ("card_payments", "transfers"):
            with self.subTest(field=field):
                dead = copy.deepcopy(snapshot)
                dead["provider"][field] = "inactive"
                projected = capability.project(dead, catalog)
                self.assertFalse(projected["account_ready"])
                self.assertNotIn(sku, {row["sku"] for row in projected["public_rails"]})
                self.assertFalse(self._browser_rail_eligible(dead, listing))

    def test_browser_checkout_requires_exact_canonical_rail_and_evidence(self) -> None:
        pay_js = (ROOT / "pay.js").read_text(encoding="utf-8")
        self.assertIn("function canonicalRailMatches(snapshot, listing)", pay_js)
        self.assertIn("if (!canonicalRailMatches(snapshot, listing)) return false;", pay_js)

        snapshot, _catalog, listing, sku = self._current_fixture()
        self.assertTrue(self._browser_rail_eligible(snapshot, listing))

        missing = copy.deepcopy(snapshot)
        missing["canonical_rails"] = [
            row for row in missing["canonical_rails"] if row.get("sku") != sku
        ]
        self.assertFalse(self._browser_rail_eligible(missing, listing))

        wrong_url = copy.deepcopy(snapshot)
        rail = next(row for row in wrong_url["canonical_rails"] if row.get("sku") == sku)
        rail["url"] = "https://buy.stripe.com/not_the_catalog_link"
        self.assertFalse(self._browser_rail_eligible(wrong_url, listing))

        wrong_evidence = copy.deepcopy(snapshot)
        rail = next(
            row for row in wrong_evidence["canonical_rails"] if row.get("sku") == sku
        )
        if isinstance(rail.get("evidence"), dict):
            rail["evidence"]["reference"] = "mismatched-provider-receipt"
        else:
            wrong_evidence.setdefault("evidence", {})["reference"] = (
                "mismatched-provider-receipt"
            )
        self.assertFalse(self._browser_rail_eligible(wrong_evidence, listing))

    def test_browser_checkout_requires_canonical_public_exposure(self) -> None:
        snapshot, catalog, listing, sku = self._current_fixture()

        checkout_first = copy.deepcopy(snapshot)
        rail = next(
            row for row in checkout_first["canonical_rails"] if row.get("sku") == sku
        )
        rail["exposure"] = "CHECKOUT_FIRST"
        projected = capability.project(checkout_first, catalog)
        self.assertIn(sku, {row["sku"] for row in projected["public_rails"]})
        self.assertTrue(self._browser_rail_eligible(checkout_first, listing))

        for value in (None, "", "BOGUS", 7, {"mode": "INTAKE_FIRST"}):
            with self.subTest(exposure=value):
                invalid = copy.deepcopy(snapshot)
                rail = next(
                    row for row in invalid["canonical_rails"] if row.get("sku") == sku
                )
                rail["exposure"] = value
                projected = capability.project(invalid, catalog)
                self.assertNotIn(sku, {row["sku"] for row in projected["public_rails"]})
                self.assertFalse(self._browser_rail_eligible(invalid, listing))

        missing = copy.deepcopy(snapshot)
        rail = next(row for row in missing["canonical_rails"] if row.get("sku") == sku)
        rail.pop("exposure", None)
        projected = capability.project(missing, catalog)
        self.assertNotIn(sku, {row["sku"] for row in projected["public_rails"]})
        self.assertFalse(self._browser_rail_eligible(missing, listing))


if __name__ == "__main__":
    unittest.main()
