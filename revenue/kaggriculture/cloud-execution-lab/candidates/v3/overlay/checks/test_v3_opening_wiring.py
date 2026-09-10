# SPDX-License-Identifier: Apache-2.0
"""T03 materialized-package key and runtime wiring contracts."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import opening_script as opening  # noqa: E402
from opening_script_test_support import action, observation  # noqa: E402

try:
    from titan_runtime import Features, TitanAgent  # type: ignore
except ImportError:
    Features = TitanAgent = None  # type: ignore


class SourceContractTests(unittest.TestCase):
    def test_declared_variants_are_exact_and_nonempty(self):
        self.assertEqual(
            set(opening.SCRIPTS),
            {"balanced", "liquid", "gemini_legacy", "leader_legacy"},
        )
        self.assertEqual(
            opening.SCRIPTS["balanced"][0][0],
            ["BUY_SEED", "STRAWBERRY", 8],
        )
        self.assertEqual(
            opening.SCRIPTS["liquid"][0][0], ["BUY_SEED", "WHEAT", 16]
        )


@unittest.skipIf(Features is None, "materialized package wiring only")
class PackageWiringTests(unittest.TestCase):
    def test_config_key_parses_and_ships_off(self):
        data = json.loads((ROOT / "TITAN-CONFIG.json").read_text(encoding="utf-8"))
        features = Features(**data)
        self.assertIn("opening_script", data)
        self.assertIs(features.opening_script, False)
        self.assertEqual(features.opening_script_variant, "balanced")
        self.assertEqual(features.opening_cash_reserve, 350.0)
        self.assertEqual(features.opening_last_step, 47)
        self.assertFalse(TitanAgent(features)._v3_active())

    def test_runtime_post_applies_only_when_key_is_on(self):
        inherited = action()
        disabled = TitanAgent(Features())
        disabled.diagnostics = {}
        self.assertIs(disabled._v3_post(observation(), {}, inherited), inherited)

        enabled = TitanAgent(Features(opening_script=True))
        enabled.diagnostics = {}
        cfg = {
            "maxMarketOrdersPerTurn": 10,
            "titan_v3": enabled._v3_config(),
        }
        out = enabled._v3_post(observation(), cfg, inherited)
        self.assertEqual(out["market"], opening.SCRIPTS["balanced"][0])
        self.assertTrue(enabled.diagnostics["v3"]["opening_script"]["changed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
