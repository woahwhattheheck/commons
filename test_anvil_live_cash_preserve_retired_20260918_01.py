#!/usr/bin/env python3
"""Hermetic: _preserve_live_cash keeps live checkout doors, drops retired ones.

hub_pages remints carry prev live_cash forward so machine readers keep product
paths across board ingests. A product whose checkout page was deleted (the
Agent Failure Autopsy / agent-rescue.html retirement) must not be resurrected
by the KEEP; with root given, each preserved entry must resolve to a file.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import hub_pages

ROOT = Path(__file__).resolve().parent


def _prev() -> dict:
    return {
        "live_cash": {
            "cite": ["newbot-json-doors-live-cash-20260916-05"],
            "note": "no invent Stripe",
            "products": [
                {
                    "name": "Agent Failure Autopsy",
                    "path": "agent-rescue.html",
                    "price_usd": 29,
                },
                {
                    "name": "Dealer Service Lead Rescue",
                    "path": "dealer-service-lead-rescue.html",
                    "price_usd": 199,
                },
            ],
            "larger_fixed": [
                {
                    "days": 30,
                    "name": "White Box pilot",
                    "path": "commercial.html",
                    "price_usd": 30000,
                },
            ],
        }
    }


class LiveCashPreserveRetiredTest(unittest.TestCase):
    def test_retired_product_path_not_resurrected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "dealer-service-lead-rescue.html").write_text(
                "<html/>", encoding="utf-8"
            )
            prev = _prev()
            out = hub_pages._preserve_live_cash(prev, {}, tmp)
            live = out["live_cash"]
            self.assertEqual(
                [p["path"] for p in live["products"]],
                ["dealer-service-lead-rescue.html"],
            )
            self.assertEqual(live["larger_fixed"], [])
            self.assertEqual(live["cite"], ["newbot-json-doors-live-cash-20260916-05"])
            # prev is not mutated by the filter
            self.assertEqual(len(prev["live_cash"]["products"]), 2)
            self.assertEqual(len(prev["live_cash"]["larger_fixed"]), 1)

    def test_all_paths_gone_drops_live_cash_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prev = _prev()
            doc = {"marker": True}
            out = hub_pages._preserve_live_cash(prev, doc, tmp)
            self.assertNotIn("live_cash", out)
            self.assertTrue(out["marker"])

    def test_entry_without_path_is_kept(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            prev = {
                "live_cash": {
                    "products": [{"name": "Pathless", "price_usd": 5}],
                }
            }
            out = hub_pages._preserve_live_cash(prev, {}, tmp)
            self.assertEqual(out["live_cash"]["products"][0]["name"], "Pathless")

    def test_no_root_preserves_unfiltered(self) -> None:
        prev = _prev()
        out = hub_pages._preserve_live_cash(prev, {})
        self.assertEqual(
            [p["path"] for p in out["live_cash"]["products"]],
            ["agent-rescue.html", "dealer-service-lead-rescue.html"],
        )

    def test_live_doors_on_tip_survive(self) -> None:
        out = hub_pages._preserve_live_cash(_prev(), {}, str(ROOT))
        live = out["live_cash"]
        self.assertEqual(
            [p["path"] for p in live["products"]],
            ["dealer-service-lead-rescue.html"],
        )
        self.assertEqual(
            [p["path"] for p in live["larger_fixed"]],
            ["commercial.html"],
        )


if __name__ == "__main__":
    unittest.main()
