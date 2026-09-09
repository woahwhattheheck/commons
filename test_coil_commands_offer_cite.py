#!/usr/bin/env python3
"""Hermetic: commands.json /offer commons cites offer.html."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMANDS = ROOT / "commands.json"


class CoilCommandsOfferCiteTest(unittest.TestCase):
    def test_offer(self) -> None:
        data = json.loads(COMMANDS.read_text(encoding="utf-8"))
        offer = next(c for c in data["commands"] if c.get("id") == "offer")
        self.assertEqual(offer["slash"], "/offer")
        self.assertIn("offer.html", offer["commons"])
        self.assertIn("harness-offer", offer["commons"])


if __name__ == "__main__":
    unittest.main()
