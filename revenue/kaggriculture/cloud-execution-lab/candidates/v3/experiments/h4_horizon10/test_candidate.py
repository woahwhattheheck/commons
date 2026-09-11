# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
V3_ROOT = Path(__file__).resolve().parents[2]
H4_DIR = V3_ROOT / "experiments" / "h4_strawberry"
OVERLAY = V3_ROOT / "overlay"
for path in (H4_DIR, OVERLAY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import r04_full_router as r04  # noqa: E402
import r04_h4_strawberry as h4  # noqa: E402


EXPECTED_CONTROL = {
    "r04_sale_horizon": 8,
    "r04_opening_roundtrip": 0,
    "r04_row_order": True,
    "r04_evening_flush": True,
    "r04_sale_fertilizer": True,
    "r04_cattle_early": True,
    "h4_strawberry_topup": True,
}


class H4Horizon10CandidateTests(unittest.TestCase):
    def load_candidate(self):
        name = "_titan_h4_horizon10_candidate_test"
        sys.modules.pop(name, None)
        spec = importlib.util.spec_from_file_location(name, HERE / "candidate.py")
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return name, module

    def test_candidate_changes_only_sale_horizon(self):
        old_path = list(sys.path)
        old = {
            "SALE_HORIZON": r04.SALE_HORIZON,
            "OPEN_ROUNDTRIP": r04.OPEN_ROUNDTRIP,
            "ROW_ORDER": r04.ROW_ORDER,
            "EVENING_FLUSH": r04.EVENING_FLUSH,
            "SALE_EXCLUDED": r04.SALE_EXCLUDED,
            "_V231_EARLY": r04._V231_EARLY,
            "STRAWBERRY_TOPUP": h4.STRAWBERRY_TOPUP,
        }
        name = None
        try:
            name, candidate = self.load_candidate()
            self.assertEqual(candidate.CONTROL_CONFIG, EXPECTED_CONTROL)
            expected_candidate = dict(EXPECTED_CONTROL)
            expected_candidate["r04_sale_horizon"] = 10
            self.assertEqual(candidate.EXPERIMENT_CONFIG, expected_candidate)

            changed = {
                key: (EXPECTED_CONTROL[key], candidate.EXPERIMENT_CONFIG[key])
                for key in EXPECTED_CONTROL
                if EXPECTED_CONTROL[key] != candidate.EXPERIMENT_CONFIG[key]
            }
            self.assertEqual(changed, {"r04_sale_horizon": (8, 10)})

            self.assertEqual(r04.SALE_HORIZON, 10)
            self.assertEqual(r04.OPEN_ROUNDTRIP, 0)
            self.assertIs(r04.ROW_ORDER, True)
            self.assertIs(r04.EVENING_FLUSH, True)
            self.assertEqual(r04.SALE_EXCLUDED, ("WHEAT",))
            self.assertIs(r04._V231_EARLY, True)
            self.assertIs(h4.STRAWBERRY_TOPUP, True)
            self.assertIs(candidate.agent, h4.h4_agent)
        finally:
            r04.SALE_HORIZON = old["SALE_HORIZON"]
            r04.OPEN_ROUNDTRIP = old["OPEN_ROUNDTRIP"]
            r04.ROW_ORDER = old["ROW_ORDER"]
            r04.EVENING_FLUSH = old["EVENING_FLUSH"]
            r04.SALE_EXCLUDED = old["SALE_EXCLUDED"]
            r04._V231_EARLY = old["_V231_EARLY"]
            h4.STRAWBERRY_TOPUP = old["STRAWBERRY_TOPUP"]
            sys.path[:] = old_path
            if name is not None:
                sys.modules.pop(name, None)

    def test_entrypoint_stays_experiment_only(self):
        relative = (HERE / "candidate.py").relative_to(V3_ROOT)
        self.assertEqual(relative.parts[:2], ("experiments", "h4_horizon10"))
        source = (HERE / "candidate.py").read_text(encoding="utf-8")
        self.assertIn("import r04_h4_strawberry as h4", source)
        self.assertNotIn("overlay/r04_h4_strawberry", source)


if __name__ == "__main__":
    unittest.main()
