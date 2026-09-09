# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import unittest

import seam_contract as target


class SeamContractTests(unittest.TestCase):
    def test_future_scenarios_alone_reverse_admission(self):
        report = target.report()
        self.assertTrue(report["three_scenario_admitted"])
        self.assertFalse(report["five_scenario_admitted"])
        self.assertEqual("mechanism_reachability_not_game_strength", report["claim"])

    def test_duplicate_or_missing_scenarios_fail_closed(self):
        with self.assertRaises(target.SeamError):
            target.admitted(("no_rival", "no_rival"), target.WITNESS)
        with self.assertRaises(target.SeamError):
            target.admitted(("unknown",), target.WITNESS)


if __name__ == "__main__":
    unittest.main()
