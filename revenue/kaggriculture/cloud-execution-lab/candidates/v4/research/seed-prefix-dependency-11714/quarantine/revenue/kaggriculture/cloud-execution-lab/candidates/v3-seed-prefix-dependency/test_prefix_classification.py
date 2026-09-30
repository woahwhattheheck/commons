# SPDX-License-Identifier: Apache-2.0
"""Pure active-prefix classification contracts."""
from copy import deepcopy
import random
import unittest

from seed_prefix_test_support import _proposal, _selected, prefix


class PrefixClassificationTests(unittest.TestCase):
    def test_inactive_tail_only_is_the_single_bypass_class(self):
        baseline = _selected(
            [["BUY_SEED", "WHEAT", 2], *([[]] * 9), ["HIRE"]]
        )
        proposed = _proposal(baseline, {0: []})
        report = prefix.classify_prefix_dependency(
            baseline, proposed, {"maxMarketOrdersPerTurn": 10}
        )
        self.assertEqual(report["status"], "inactive_tail_only")
        self.assertEqual(report["changed_slots"], [0])
        self.assertEqual(report["active_dependency_slots"], [])
        self.assertEqual(report["inactive_dependency_slots"], [10])

    def test_active_dependency_delegates(self):
        baseline = _selected(
            [["BUY_SEED", "WHEAT", 2], ["HIRE"], *([[]] * 9)]
        )
        proposed = _proposal(baseline, {0: []})
        report = prefix.classify_prefix_dependency(
            baseline, proposed, {"maxMarketOrdersPerTurn": 10}
        )
        self.assertEqual(report["status"], "delegate")
        self.assertEqual(report["reason"], "executable_downstream_capital_dependency")
        self.assertEqual(report["active_dependency_slots"], [1])

    def test_no_dependency_keeps_canonical_fast_path(self):
        baseline = _selected([["BUY_SEED", "WHEAT", 2], *([[]] * 10)])
        proposed = _proposal(baseline, {0: []})
        report = prefix.classify_prefix_dependency(baseline, proposed, {})
        self.assertEqual(report["status"], "delegate")
        self.assertEqual(report["reason"], "no_downstream_capital_dependency")

    def test_edit_at_cap_is_rejected(self):
        baseline = _selected(
            [*([[]] * 10), ["BUY_SEED", "WHEAT", 2], ["HIRE"]]
        )
        proposed = _proposal(baseline, {10: []})
        report = prefix.classify_prefix_dependency(
            baseline, proposed, {"maxMarketOrdersPerTurn": 10}
        )
        self.assertEqual(report["status"], "delegate")
        self.assertIn("engine-inactive", report["reason"])

    def test_non_market_change_is_rejected(self):
        baseline = _selected(
            [["BUY_SEED", "WHEAT", 2], *([[]] * 9), ["HIRE"]]
        )
        proposed = _proposal(baseline, {0: []})
        proposed["farmer"] = ["NORTH"]
        report = prefix.classify_prefix_dependency(baseline, proposed, {})
        self.assertEqual(report["status"], "delegate")
        self.assertEqual(report["reason"], "non-market action fields changed")

    def test_non_seed_or_quantity_growth_is_rejected(self):
        baseline = _selected(
            [["BUY_SEED", "WHEAT", 2], *([[]] * 9), ["HIRE"]]
        )
        for replacement in (
            ["BUY_SEED", "WHEAT", 3],
            ["BUY_SEED", "CARROT", 1],
            ["SELL", "WHEAT", 1],
            ["BUY_SEED", "WHEAT", True],
        ):
            with self.subTest(replacement=replacement):
                proposed = _proposal(baseline, {0: replacement})
                report = prefix.classify_prefix_dependency(baseline, proposed, {})
                self.assertEqual(report["status"], "delegate")
                self.assertIn("strict", report["reason"])

    def test_invalid_limit_fails_closed(self):
        baseline = _selected(
            [["BUY_SEED", "WHEAT", 2], *([[]] * 9), ["HIRE"]]
        )
        proposed = _proposal(baseline, {0: []})
        for bad in (True, 1.5, "10", None):
            with self.subTest(limit=bad):
                report = prefix.classify_prefix_dependency(
                    baseline, proposed, {"maxMarketOrdersPerTurn": bad}
                )
                self.assertEqual(report["status"], "delegate")

    def test_default_limit_is_ten(self):
        baseline = _selected(
            [["BUY_SEED", "WHEAT", 2], *([[]] * 9), ["BUY_ANIMAL", "COW", 1]]
        )
        proposed = _proposal(baseline, {0: []})
        report = prefix.classify_prefix_dependency(baseline, proposed)
        self.assertEqual(report["order_limit"], 10)
        self.assertEqual(report["status"], "inactive_tail_only")

    def test_deterministic_random_reference_predicate(self):
        rng = random.Random(20260909)
        capital = [
            ["HIRE"],
            ["BUY_LAND"],
            ["BUY_PRODUCT", "WHEAT", 1],
            ["BUY_ANIMAL", "COW", 1],
        ]
        inert = [[], ["PASS"], ["SELL", "MILK", 1], ["BUY_SEED", "CARROT", 1]]
        for case in range(1000):
            length = rng.randint(2, 18)
            limit = rng.randint(1, min(10, length))
            market = [deepcopy(rng.choice(capital + inert)) for _ in range(length)]
            edit = rng.randrange(limit)
            market[edit] = ["BUY_SEED", "WHEAT", rng.randint(1, 9)]
            baseline = _selected(market)
            proposed = _proposal(
                baseline,
                {edit: ["BUY_SEED", "WHEAT", rng.randrange(market[edit][2])]},
            )
            report = prefix.classify_prefix_dependency(
                baseline, proposed, {"maxMarketOrdersPerTurn": limit}
            )
            active = [
                i
                for i in range(edit + 1, min(limit, length))
                if market[i] and market[i][0] in prefix.CAPITAL_OPERATIONS
            ]
            tail = [
                i
                for i in range(max(limit, edit + 1), length)
                if market[i] and market[i][0] in prefix.CAPITAL_OPERATIONS
            ]
            expected = (
                "inactive_tail_only"
                if not active and tail
                else "delegate"
            )
            self.assertEqual(report["status"], expected, msg=f"case {case}")
            self.assertEqual(report["active_dependency_slots"], active)
            self.assertEqual(report["inactive_dependency_slots"], tail)
