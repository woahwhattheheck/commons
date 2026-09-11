"""Source-custody contracts for the V3.1 H4 production wiring carrier.

This intentionally does not claim a rebuilt package receipt.  It proves that the
production overlay reuses the reviewed H4 bytes and that apply_v3 exposes a default-off
switch which is subordinate to the existing r04_sale_window route.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class H4ProductionWiringSourceTests(unittest.TestCase):
    def test_reviewed_h4_module_is_byte_identical_in_overlay(self):
        reviewed = ROOT / "experiments" / "h4_strawberry" / "r04_h4_strawberry.py"
        production = ROOT / "overlay" / "r04_h4_strawberry.py"
        self.assertEqual(reviewed.read_bytes(), production.read_bytes())

    def test_key_is_default_off_and_subordinate_to_r04(self):
        source = (ROOT / "apply_v3.py").read_text(encoding="utf-8")
        self.assertIn('"    r04_strawberry_topup: bool = False\\n"', source)
        self.assertIn('route = \'r04_sale_window\' if self.features.r04_sale_window else \'r03_full_router\'', source)
        self.assertIn('if bool(self.features.r04_strawberry_topup):', source)
        self.assertIn('from r04_h4_strawberry import install', source)
        self.assertIn('self.diagnostics[\'strawberry_topup\'] = bool(self.features.r04_strawberry_topup)', source)

        active_block = source.split('"    def _v3_active(self):\\n"', 1)[1].split('"    def _v3_config(self):\\n"', 1)[0]
        self.assertNotIn('r04_strawberry_topup', active_block,
                         "H4 must not activate a route when r04_sale_window is off")

    def test_generated_config_declares_h4_false(self):
        source = (ROOT / "apply_v3.py").read_text(encoding="utf-8")
        config_loop = source.split('for key in ("e11_rival_sell"', 1)[1].split('):\n', 1)[0]
        self.assertIn('"r04_strawberry_topup"', config_loop)

    def test_h4_wrapper_receives_true_only_in_h4_branch(self):
        source = (ROOT / "apply_v3.py").read_text(encoding="utf-8")
        start = source.index('if bool(self.features.r04_strawberry_topup):')
        end = source.index('self.diagnostics[\'sale_horizon\']', start)
        branch = source[start:end]
        self.assertIn('from r04_h4_strawberry import install', branch)
        self.assertIn('                                     True)(observation, configuration)', branch)
        self.assertIn('else:', branch)
        self.assertIn('from r04_full_router import install', branch)


if __name__ == "__main__":
    unittest.main()
