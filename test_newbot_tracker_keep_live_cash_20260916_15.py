"""newbot-tracker-keep-live-cash-20260916-15 — KEEP live_cash across tip trackers."""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CLAIM = "newbot-tracker-keep-live-cash-20260916-15"
PRODUCTS = [
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]
TIP_JSON = ("feature-tracker.json", "unbuilt-items.json")


def _live_cash(cite=CLAIM):
    return {
        "cite": [cite],
        "note": "fixture keep",
        "products": [
            {"name": "Agent Failure Autopsy", "price_usd": 29, "path": "agent-rescue.html"},
            {"name": "Dealer Service Lead Rescue", "price_usd": 199, "path": "dealer-service-lead-rescue.html"},
            {"name": "Referral Intake Completeness", "price_usd": 199, "path": "referral-intake-completeness.html"},
            {"name": "Repair Booking Preflight", "price_usd": 199, "path": "repair-booking-preflight.html"},
            {"name": "Plant Downtime Handoff", "price_usd": 199, "path": "plant-downtime-handoff.html"},
        ],
        "larger_fixed": [
            {"name": "GGUF diagnostic", "price_usd": 12000, "days": 10, "path": "diagnostic.html"},
            {"name": "White Box pilot", "price_usd": 30000, "days": 30, "path": "commercial.html"},
        ],
    }


def _assert_live_cash(self, doc, label):
    self.assertIn("live_cash", doc, label)
    paths = [p.get("path") for p in (doc["live_cash"].get("products") or [])]
    for prod in PRODUCTS:
        self.assertIn(prod, paths, "%s missing %s" % (label, prod))
    self.assertNotIn("buy.stripe.com", json.dumps(doc), label)


class TestNewbotTrackerKeepLiveCash2026091615(unittest.TestCase):
    def test_tip_json_doors_still_have_live_cash(self):
        for name in TIP_JSON:
            path = ROOT / name
            self.assertTrue(path.is_file(), name)
            doc = json.loads(path.read_text(encoding="utf-8"))
            _assert_live_cash(self, doc, name)

    def test_product_pages_exist(self):
        for name in PRODUCTS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_feature_tracker_write_keeps_live_cash(self):
        sys.path.insert(0, str(ROOT))
        from host import feature_tracker as ft

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "features" / "registry").mkdir(parents=True)
        (root / "features" / "evidence").mkdir(parents=True)
        (root / "host").mkdir()
        (root / "host" / "ok.py").write_text("# ok\n", encoding="utf-8")
        live = _live_cash()
        (root / "feature-tracker.json").write_text(
            json.dumps({"schema": "prev", "live_cash": live}, indent=2) + "\n",
            encoding="utf-8",
        )
        # Minimal empty projection path: project from empty registry
        projection = ft.project(str(root), snapshot={"git_names": set()})
        self.assertNotIn("live_cash", projection)
        ft.write_projection(str(root), projection)
        on_disk = json.loads((root / "feature-tracker.json").read_text(encoding="utf-8"))
        _assert_live_cash(self, on_disk, "feature-tracker.json after write")
        self.assertEqual(on_disk["live_cash"]["cite"], [CLAIM])
        html = (root / "feature-tracker.html").read_text(encoding="utf-8")
        self.assertIn('id="live-cash"', html)
        self.assertIn("agent-rescue.html", html)
        self.assertIn("diagnostic.html", html)
        self.assertIn("commercial.html", html)
        self.assertIn("Larger fixed", html)
        self.assertNotIn("buy.stripe.com", html)

    def test_unbuilt_items_write_keeps_live_cash(self):
        sys.path.insert(0, str(ROOT))
        from host import unbuilt_items as ui

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "ground").mkdir()
        (root / "ground" / "UNBUILT_ITEMS.json").write_text(
            json.dumps({"schema": ui.SCHEMA, "items": []}, indent=2) + "\n",
            encoding="utf-8",
        )
        live = _live_cash()
        (root / "unbuilt-items.json").write_text(
            json.dumps({"schema": "prev", "live_cash": live}, indent=2) + "\n",
            encoding="utf-8",
        )
        out = ui.write_projection(str(root), main_sha="")
        _assert_live_cash(self, out, "unbuilt return")
        on_disk = json.loads((root / "unbuilt-items.json").read_text(encoding="utf-8"))
        _assert_live_cash(self, on_disk, "unbuilt-items.json after write")
        self.assertEqual(on_disk["live_cash"]["cite"], [CLAIM])
        self.assertNotIn("buy.stripe.com", json.dumps(on_disk))


if __name__ == "__main__":
    unittest.main()
