from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from materialize_arms import (
    ARM_FEATURES,
    PACKAGED_SELL_CORE_PATH,
    PRESSURE_PATH,
    RUNTIME_PATH,
    apply_arm,
    verify_arm,
)


PRESSURE = '''def transform(action: dict, observation: Mapping,
              configuration: Mapping | None = None, *, quote: PriceFunction,
              rival_supply: Mapping[str, int] | None = None) -> dict:
    """Sort.

    ``rival_supply`` is an optional product->public-quantity scenario. Missing
    product keys retain the historical same-sized proxy for that product; an
    explicit zero means no rival flow. Present malformed values (including
    ``None``) are barriers, so ambiguity cannot silently become proxy evidence.

    Preserve all orders, quantities, duplicate lots, economic barriers,
    executable-prefix boundaries and unit instructions.
    """
    if not isinstance(action, dict) or not isinstance(action.get('market', []), list):
        raise ValueError('parent policy must return an object with a market list')
    orders = []
    scores = []
    start = stop = 0
    if True:
        ranked = sorted(zip(orders[start:stop], scores[start:stop]), key=lambda p: -p[1])
        orders[start:stop] = [order for order, _ in ranked]
    return action
'''
RUNTIME = '''def f(pressure, selected, obs, cfg, mechanics):
        result = pressure.transform(selected, obs, cfg, quote=mechanics.market_price)
        return result
'''
OWN = '''def score():
        own_cash=carry=other_cash=remaining=0
        return own_cash+carry-other_cash, own_cash,other_cash,remaining
'''


class MaterializeArmsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for relative, text in (
            (PRESSURE_PATH, PRESSURE),
            (RUNTIME_PATH, RUNTIME),
            (PACKAGED_SELL_CORE_PATH, OWN),
        ):
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_all_four_arms_verify_and_touch_expected_files(self):
        for arm in ARM_FEATURES:
            with self.subTest(arm=arm):
                case = self.root.parent / (self.root.name + "-" + arm)
                shutil.copytree(self.root, case)
                receipt = apply_arm(case, arm)
                verify_arm(case, arm)
                touched = {row["path"] for row in receipt["touched_files"]}
                expected = set()
                if arm in ("strict-only", "combined"):
                    expected |= {PRESSURE_PATH.as_posix(), RUNTIME_PATH.as_posix()}
                if arm in ("own-only", "combined"):
                    expected.add(PACKAGED_SELL_CORE_PATH.as_posix())
                self.assertEqual(touched, expected)
                shutil.rmtree(case)

    def test_patch_is_fail_closed_on_anchor_drift(self):
        path = self.root / PRESSURE_PATH
        path.write_text(path.read_text().replace("ranked = sorted", "ranked=sorted"))
        with self.assertRaisesRegex((ValueError, AssertionError), "pressure ranking|stable partition"):
            apply_arm(self.root, "strict-only")

    def test_patch_refuses_double_application(self):
        apply_arm(self.root, "combined")
        with self.assertRaises((AssertionError, ValueError)):
            apply_arm(self.root, "combined")


if __name__ == "__main__":
    unittest.main(verbosity=2)
