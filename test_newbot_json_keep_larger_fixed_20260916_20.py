"""newbot-json-keep-larger-fixed-20260916-20 — KEEP larger_fixed on tip JSON remints."""
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent
CLAIM = "newbot-json-keep-larger-fixed-20260916-20"
DOORS = ("pulse.json", "share.json", "lanes.json", "orient.json", "wakeups.json")
PRODUCTS = [
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]
LARGER = ("diagnostic.html", "commercial.html")


def _live_cash_fixture():
    return {
        "cite": [CLAIM],
        "note": "fixture keep larger_fixed",
        "products": [
            {"name": "Agent Failure Autopsy", "price_usd": 29, "path": "agent-rescue.html"},
            {
                "name": "Dealer Service Lead Rescue",
                "price_usd": 199,
                "path": "dealer-service-lead-rescue.html",
            },
            {
                "name": "Referral Intake Completeness",
                "price_usd": 199,
                "path": "referral-intake-completeness.html",
            },
            {
                "name": "Repair Booking Preflight",
                "price_usd": 199,
                "path": "repair-booking-preflight.html",
            },
            {
                "name": "Plant Downtime Handoff",
                "price_usd": 199,
                "path": "plant-downtime-handoff.html",
            },
        ],
        "larger_fixed": [
            {
                "name": "GGUF diagnostic",
                "price_usd": 12000,
                "days": 10,
                "path": "diagnostic.html",
            },
            {
                "name": "White Box pilot",
                "price_usd": 30000,
                "days": 30,
                "path": "commercial.html",
            },
        ],
    }


class TestNewbotJsonKeepLargerFixed2026091620(unittest.TestCase):
    def test_tip_remint_json_have_larger_fixed(self):
        for name in DOORS:
            with self.subTest(name=name):
                doc = json.loads((ROOT / name).read_text(encoding="utf-8"))
                lc = doc["live_cash"]
                self.assertIn(CLAIM, lc.get("cite") or [])
                paths = [p.get("path") for p in lc.get("products") or []]
                for prod in PRODUCTS:
                    self.assertIn(prod, paths, f"{name} missing {prod}")
                larger = lc.get("larger_fixed") or []
                self.assertEqual([x.get("path") for x in larger], list(LARGER))
                self.assertEqual(larger[0].get("price_usd"), 12000)
                self.assertEqual(larger[1].get("price_usd"), 30000)
                self.assertNotIn("buy.stripe.com", json.dumps(doc))

    def test_product_pages_exist(self):
        for name in PRODUCTS + list(LARGER):
            self.assertTrue((ROOT / name).is_file(), name)

    def test_llms_pulse_remint_keeps_larger_fixed(self):
        mesh = types.ModuleType("read_mesh")
        mesh.publish = Mock(side_effect=AssertionError("network publisher must not run"))
        spec = importlib.util.spec_from_file_location("alder_llms_generator", ROOT / "llms_txt.py")
        assert spec and spec.loader
        gen = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"read_mesh": mesh}):
            spec.loader.exec_module(gen)

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        gen.ROOT = str(root)

        def git(*args):
            return subprocess.run(
                ["git", *args], cwd=root, capture_output=True, text=True, check=True
            ).stdout.strip()

        git("init", "-q")
        git("config", "user.name", "Synthetic fixture")
        git("config", "user.email", "fixture@example.invalid")
        (root / "p").mkdir()
        (root / "p" / "seed.md").write_text(
            "---\nfrom: SYNTHETIC\nid: seed\nts: 2026-09-16T00:00:00Z\n---\nseed\n",
            encoding="utf-8",
        )
        git("add", "--", "p")
        git("commit", "-qm", "seed")
        sha = git("rev-parse", "HEAD")
        live = _live_cash_fixture()
        (root / "head.json").write_text(
            json.dumps(
                {
                    "schema": "commons-head-v1",
                    "sha": sha,
                    "observed_at": "2026-09-16T00:00:00Z",
                    "source": "scheduled-pages-bake",
                    "status": "BAKED_OBSERVATION",
                    "live_cash": live,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / "pulse.json").write_text(
            json.dumps(
                {
                    "schema": "commons-pulse-v1",
                    "sha": sha,
                    "observed_at": "2026-09-16T00:00:00Z",
                    "live_cash": live,
                    "items": [],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        gen.write_head_pulse([], path=str(root / "pulse.json"), head={"sha": sha})
        out = json.loads((root / "pulse.json").read_text(encoding="utf-8"))
        larger = (out.get("live_cash") or {}).get("larger_fixed") or []
        self.assertEqual([x.get("path") for x in larger], list(LARGER))
        self.assertIn(CLAIM, (out.get("live_cash") or {}).get("cite") or [])

    def test_hub_pages_preserve_keeps_larger_fixed(self):
        sys.path.insert(0, str(ROOT))
        import hub_pages

        prev = {"live_cash": _live_cash_fixture()}
        doc = {"schema": "x", "items": []}
        out = hub_pages._preserve_live_cash(prev, doc)
        larger = (out.get("live_cash") or {}).get("larger_fixed") or []
        self.assertEqual([x.get("path") for x in larger], list(LARGER))

    def test_wakeup_preserve_keeps_larger_fixed(self):
        sys.path.insert(0, str(ROOT))
        import wakeup

        prev = {"live_cash": _live_cash_fixture()}
        doc = {"schema": "wakeups", "due": []}
        out = wakeup._preserve_live_cash(prev, doc)
        larger = (out.get("live_cash") or {}).get("larger_fixed") or []
        self.assertEqual([x.get("path") for x in larger], list(LARGER))


if __name__ == "__main__":
    unittest.main()
