# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
from pathlib import Path
import unittest


ENGINE_SHA256 = "bc8a54879ef02c7ea64b8b333d6a976f0ea65c4949149d01f463f23bccee653e"


class TerminalHireEngineAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine_path = (
            Path(__file__).resolve().parents[4]
            / "reference"
            / "engine"
            / "kaggriculture.py"
        )
        cls.raw = cls.engine_path.read_bytes()
        cls.text = cls.raw.decode("utf-8")

    def test_exact_official_engine_bytes(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), ENGINE_SHA256)

    def test_terminal_reward_is_money_only(self):
        self.assertIn(
            's.reward = float(obs0.farms[s.observation.player]["money"])',
            self.text,
        )
        self.assertIn("if step >= cfg.episodeSteps - 2:", self.text)

    def test_hire_is_atomic_and_spends_money(self):
        self.assertIn('if op == "HIRE":', self.text)
        self.assertIn('farm["money"] -= cost', self.text)
        self.assertIn('farm["hires_today"] += 1', self.text)

    def test_empty_market_row_is_parser_noop(self):
        self.assertIn("if not isinstance(order, list) or not order:", self.text)
        self.assertIn("return None", self.text)


if __name__ == "__main__":
    unittest.main()
