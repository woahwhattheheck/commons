"""newbot-bake-keep-live-cash-20260916-12 — preserve live_cash across llms bake."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "llms_txt.py"
PRODUCTS = [
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]
CLAIM = "newbot-bake-keep-live-cash-20260916-12"


def load_generator():
    mesh = types.ModuleType("read_mesh")
    mesh.publish = Mock(side_effect=AssertionError("network publisher must not run"))
    spec = importlib.util.spec_from_file_location("alder_llms_generator", SOURCE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"read_mesh": mesh}):
        spec.loader.exec_module(module)
    return module


class TestNewbotBakeKeepLiveCash2026091612(unittest.TestCase):
    def test_tip_head_and_pulse_have_live_cash_products(self):
        for name in ("head.json", "pulse.json"):
            doc = json.loads((ROOT / name).read_text(encoding="utf-8"))
            self.assertIn("live_cash", doc, name)
            lc = doc["live_cash"]
            self.assertIn(CLAIM, lc.get("cite") or [])
            paths = [p.get("path") for p in lc.get("products") or []]
            for prod in PRODUCTS:
                self.assertIn(prod, paths, f"{name} missing {prod}")
            blob = json.dumps(doc)
            self.assertNotIn("buy.stripe.com", blob, name)

    def test_head_keeps_larger_fixed_paths(self):
        doc = json.loads((ROOT / "head.json").read_text(encoding="utf-8"))
        larger = (doc.get("live_cash") or {}).get("larger_fixed") or []
        paths = {row.get("path") for row in larger}
        self.assertIn("diagnostic.html", paths)
        self.assertIn("commercial.html", paths)

    def test_product_pages_exist(self):
        for name in PRODUCTS + ["diagnostic.html", "commercial.html"]:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_bake_preserves_live_cash_on_head_and_pulse(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        gen = load_generator()
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

        live_cash = {
            "cite": [CLAIM],
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
        (root / "head.json").write_text(
            json.dumps(
                {
                    "schema": "commons-head-v1",
                    "sha": sha,
                    "observed_at": "2026-09-16T00:00:00Z",
                    "source": "scheduled-pages-bake",
                    "status": "BAKED_OBSERVATION",
                    "live_cash": live_cash,
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
                    "seq": 7,
                    "head": sha,
                    "ts": "2026-09-16T00:00:00Z",
                    "post_count": 3,
                    "newest": ["seed"],
                    "instruction": "fixture",
                    "live_cash": {
                        "cite": [CLAIM],
                        "note": "fixture keep",
                        "products": live_cash["products"],
                    },
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        with patch.object(gen, "branch_tips", return_value=[]):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(gen.main(publish_mesh=False), 0)

        head = json.loads((root / "head.json").read_text(encoding="utf-8"))
        pulse = json.loads((root / "pulse.json").read_text(encoding="utf-8"))
        self.assertIn("live_cash", head)
        self.assertIn("live_cash", pulse)
        self.assertEqual(head["live_cash"]["cite"], [CLAIM])
        self.assertEqual(
            [p["path"] for p in head["live_cash"]["products"]],
            PRODUCTS,
        )
        self.assertEqual(
            [p["path"] for p in pulse["live_cash"]["products"]],
            PRODUCTS,
        )
        self.assertEqual(pulse["seq"], 7)
        self.assertNotIn("buy.stripe.com", json.dumps(head) + json.dumps(pulse))


if __name__ == "__main__":
    unittest.main()
