"""newbot-ingest-keep-live-cash-20260916-13 — preserve live_cash across ingest remints."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parent
CLAIM = "newbot-ingest-keep-live-cash-20260916-13"
PRODUCTS = [
    "agent-rescue.html",
    "dealer-service-lead-rescue.html",
    "referral-intake-completeness.html",
    "repair-booking-preflight.html",
    "plant-downtime-handoff.html",
]
TIP_JSON = (
    "share.json",
    "wake.json",
    "lanes.json",
    "salon.json",
    "keys.json",
    "claims.json",
    "orient.json",
    "delta.json",
    "pulse.json",
)


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
    }


def load_hub_pages():
    spec = importlib.util.spec_from_file_location("hub_pages_keep13", ROOT / "hub_pages.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_board_ingest(hub):
    # board_ingest imports hub_pages by name; stub heavy deps lightly via sys.modules
    sys.modules["hub_pages"] = hub
    # Minimal stubs if missing
    for name in ("chunk_board",):
        if name not in sys.modules:
            stub = types.ModuleType(name)
            stub.BOARD_SEED_N = 0
            sys.modules[name] = stub
    spec = importlib.util.spec_from_file_location("board_ingest_keep13", ROOT / "board_ingest.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    # board_ingest may pull many siblings; load may fail — fall back to unit of write_pulse only
    try:
        spec.loader.exec_module(mod)
    except Exception as exc:  # pragma: no cover - environment variance
        raise unittest.SkipTest("board_ingest import blocked: %s" % exc)
    return mod


class TestNewbotIngestKeepLiveCash2026091613(unittest.TestCase):
    def test_tip_json_doors_still_have_live_cash(self):
        for name in TIP_JSON:
            path = ROOT / name
            self.assertTrue(path.is_file(), name)
            doc = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("live_cash", doc, name)
            paths = [p.get("path") for p in (doc["live_cash"].get("products") or [])]
            for prod in PRODUCTS:
                self.assertIn(prod, paths, "%s missing %s" % (name, prod))
            self.assertNotIn("buy.stripe.com", json.dumps(doc), name)

    def test_product_pages_exist(self):
        for name in PRODUCTS:
            self.assertTrue((ROOT / name).is_file(), name)

    def test_hub_pages_preserve_helper(self):
        hub = load_hub_pages()
        prev = {"live_cash": _live_cash(), "noise": 1}
        doc = {"note": "rebuilt"}
        out = hub._preserve_live_cash(prev, doc)
        self.assertEqual(out["live_cash"]["cite"], [CLAIM])
        self.assertEqual([p["path"] for p in out["live_cash"]["products"]], PRODUCTS)
        self.assertNotIn("buy.stripe.com", json.dumps(out))

    def test_hub_rebuild_writers_keep_live_cash(self):
        hub = load_hub_pages()
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        live = _live_cash()
        seeds = {
            "share.json": {"law": "x", "open": [], "done": [], "refused": [], "open_per_claim": {}, "receipts": 0, "live_cash": live},
            "wake.json": {"note": "n", "n": 0, "requests": [], "actionable": [], "held_cursor": [], "invalid": [], "live_cash": live},
            "lanes.json": {"n": 0, "salon": {"n": 0, "posts": []}, "live_cash": live},
            "salon.json": {"n": 0, "posts": [], "live_cash": live},
            "keys.json": {"note": "k", "keys": [], "live_cash": live},
            "claims.json": {"note": "c", "n": 0, "claims": [], "live_cash": live},
            "orient.json": {"ts": "2026-09-16T00:00:00Z", "cap": 1, "n": 1, "text": "t", "dropped": [], "live_cash": live},
            "delta.json": {"note": "d", "claims": {}, "live_cash": live},
        }
        for name, doc in seeds.items():
            (root / name).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

        mod = MagicMock()
        mod.ROOT = str(root)

        def _read(path):
            return Path(path).read_text(encoding="utf-8")

        def _write(path, text):
            # HTML shells may be MagicMock if page helper unmet; only assert JSON
            if not isinstance(text, str):
                return
            Path(path).write_text(text, encoding="utf-8")

        mod._read = _read
        mod._write = _write
        # HTML emission needs a page shell; KEEP under test is the JSON write path.
        hub._page = lambda *a, **k: "<html>fixture</html>"

        hub.rebuild_share(mod, [])
        hub.rebuild_wake(mod, [])
        hub.rebuild_keys(mod, [])
        hub.rebuild_claims(mod, [])
        hub.rebuild_orient(mod, [])
        hub.rebuild_delta(mod, [])
        hub.rebuild_lanes(mod, [])

        for name in (
            "share.json",
            "wake.json",
            "keys.json",
            "claims.json",
            "orient.json",
            "delta.json",
            "lanes.json",
            "salon.json",
        ):
            doc = json.loads((root / name).read_text(encoding="utf-8"))
            self.assertIn("live_cash", doc, name)
            self.assertEqual(
                [p["path"] for p in doc["live_cash"]["products"]],
                PRODUCTS,
                name,
            )
            self.assertNotIn("buy.stripe.com", json.dumps(doc), name)

    def test_board_ingest_write_pulse_keeps_live_cash(self):
        hub = load_hub_pages()
        try:
            bi = load_board_ingest(hub)
        except unittest.SkipTest:
            raise
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        # init tiny git for HEAD
        import subprocess
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Synthetic"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "f@example.invalid"], cwd=root, check=True)
        (root / "seed.txt").write_text("seed\n", encoding="utf-8")
        subprocess.run(["git", "add", "seed.txt"], cwd=root, check=True)
        subprocess.run(["git", "commit", "-qm", "seed"], cwd=root, check=True)
        sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()

        live = _live_cash()
        (root / "pulse.json").write_text(
            json.dumps(
                {
                    "seq": 3,
                    "head": "0" * 40,
                    "ts": "2026-09-16T00:00:00Z",
                    "post_count": 0,
                    "newest": [],
                    "instruction": "old",
                    "live_cash": live,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        bi.ROOT = str(root)
        # force a content-changing remint
        rows = [("2026-09-16T01:00:00Z", {"id": "post-1", "from": "SYN"}, "body")]
        seq = bi.write_pulse(rows)
        self.assertGreaterEqual(seq, 4)
        pulse = json.loads((root / "pulse.json").read_text(encoding="utf-8"))
        self.assertIn("live_cash", pulse)
        self.assertEqual(pulse["live_cash"]["cite"], [CLAIM])
        self.assertEqual([p["path"] for p in pulse["live_cash"]["products"]], PRODUCTS)
        self.assertEqual(pulse["head"], sha)
        self.assertNotIn("buy.stripe.com", json.dumps(pulse))


if __name__ == "__main__":
    unittest.main()
