"""newbot-rebake-keep-live-cash-20260916-14 — KEEP live_cash across remaining tip reminters."""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
CLAIM = "newbot-rebake-keep-live-cash-20260916-14"
PRODUCTS = [
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]
TIP_JSON = ("builds.json", "wakeups.json", "observatory.json")


def _live_cash(cite=CLAIM):
    return {
        "cite": [cite],
        "note": "fixture keep",
        "products": [
            {"name": "Dealer Service Lead Rescue", "price_usd": 199, "path": "dealer-service-lead-rescue.html"},
            {"name": "Referral Intake Completeness", "price_usd": 199, "path": "referral-intake-completeness.html"},
            {"name": "Repair Booking Preflight", "price_usd": 199, "path": "repair-booking-preflight.html"},
            {"name": "Plant Downtime Handoff", "price_usd": 199, "path": "plant-downtime-handoff.html"},
        ],
    }


def _assert_live_cash(self, doc, label):
    self.assertIn("live_cash", doc, label)
    paths = [p.get("path") for p in (doc["live_cash"].get("products") or [])]
    for prod in PRODUCTS:
        self.assertIn(prod, paths, "%s missing %s" % (label, prod))
    self.assertNotIn("buy.stripe.com", json.dumps(doc), label)


class TestNewbotRebakeKeepLiveCash2026091614(unittest.TestCase):
    def test_tip_json_doors_still_have_live_cash(self):
        for name in TIP_JSON:
            path = ROOT / name
            self.assertTrue(path.is_file(), name)
            doc = json.loads(path.read_text(encoding="utf-8"))
            _assert_live_cash(self, doc, name)

    def test_product_pages_exist(self):
        for name in PRODUCTS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_builds_ledger_project_keeps_live_cash(self):
        import builds_ledger

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "builds" / "records").mkdir(parents=True)
        live = _live_cash()
        (root / "builds.json").write_text(
            json.dumps(
                {
                    "note": "prev",
                    "statuses": [],
                    "n_records": 0,
                    "n_invalid": 0,
                    "permits": [],
                    "pr_note": "x",
                    "n_open_prs": 0,
                    "open_prs": [],
                    "live_cash": live,
                },
                indent=1,
            )
            + "\n",
            encoding="utf-8",
        )
        written = {}

        def write(path, text):
            written[os.path.basename(path)] = text
            Path(path).write_text(text, encoding="utf-8")

        builds_ledger.project(str(root), write, open_prs=[], main_sha="0" * 40)
        self.assertIn("builds.json", written)
        doc = json.loads(written["builds.json"])
        _assert_live_cash(self, doc, "builds.json after project")
        self.assertEqual(doc["live_cash"]["cite"], [CLAIM])

    def test_wakeup_baker_keeps_live_cash(self):
        spec = importlib.util.spec_from_file_location("wakeup_keep14", ROOT / "wakeup.py")
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        (root / "wakeups").mkdir()
        live = _live_cash()
        (root / "wakeups.json").write_text(
            json.dumps(
                {
                    "door": "https://example.invalid/wakeup.html",
                    "instruction": "old",
                    "set": "x",
                    "ntfy": "https://ntfy.sh/x",
                    "ts": "2026-09-16T00:00:00Z",
                    "n": 0,
                    "due": [],
                    "pending": [],
                    "held_cursor": [],
                    "held_unrouted": [],
                    "fired": [],
                    "live_cash": live,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (root / "p").mkdir()
        old_root = mod.ROOT
        mod.ROOT = str(root)
        self.addCleanup(lambda: setattr(mod, "ROOT", old_root))
        with patch.object(mod, "ntfy", return_value=False):
            rc = mod.main()
        self.assertEqual(rc, 0)
        doc = json.loads((root / "wakeups.json").read_text(encoding="utf-8"))
        _assert_live_cash(self, doc, "wakeups.json after bake")
        self.assertEqual(doc["live_cash"]["cite"], [CLAIM])

    def test_observatory_write_snapshot_keeps_live_cash(self):
        # Load host/observatory with ROOT pointing at temp via write_snapshot(root=)
        sys.path.insert(0, str(ROOT))
        from host import observatory as obs

        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        live = _live_cash()
        # Minimal inputs so snapshot succeeds
        (root / "presence.json").write_text("[]\n", encoding="utf-8")
        (root / "lastseen.json").write_text("[]\n", encoding="utf-8")
        (root / "pulse.json").write_text("{}\n", encoding="utf-8")
        (root / "recent.json").write_text("[]\n", encoding="utf-8")
        (root / "claims.json").write_text("{}\n", encoding="utf-8")
        (root / "revenue" / "payment_ready").mkdir(parents=True)
        (root / "revenue" / "payment_ready" / "recovery.json").write_text("{}\n", encoding="utf-8")
        (root / "protocol" / "fixtures").mkdir(parents=True)
        (root / "protocol" / "fixtures" / "live_events.json").write_text("[]\n", encoding="utf-8")
        (root / "observatory.json").write_text(
            json.dumps({"schema": "prev", "live_cash": live}, indent=2) + "\n",
            encoding="utf-8",
        )
        snap = obs.write_snapshot(str(root), now="2026-09-16T12:00:00Z")
        self.assertIn("live_cash", snap)
        _assert_live_cash(self, snap, "observatory snap")
        on_disk = json.loads((root / "observatory.json").read_text(encoding="utf-8"))
        _assert_live_cash(self, on_disk, "observatory.json on disk")
        self.assertEqual(on_disk["live_cash"]["cite"], [CLAIM])
        self.assertNotIn("buy.stripe.com", json.dumps(on_disk))


if __name__ == "__main__":
    unittest.main()
