# SPDX-License-Identifier: Apache-2.0
from promotion_test_support import *

class EconomicGateTests(unittest.TestCase):
    def test_one_systematically_bad_seed_fails_seed_floor(self) -> None:
        value = panel()
        for row in value["cells"]:
            if row["seed"] == 11:
                row["candidate"]["terminal"]["own_cash"] = 91.0
                refresh_arm_trace(row["candidate"])
        report = pc.assess(value, policy(), spent_ledger())
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(report["checks"]["seed_own_floor"])
        self.assertEqual(report["summary"]["negative_seed_clusters"], 1)

    def test_cell_tail_floor_is_explicit(self) -> None:
        value = panel()
        row = value["cells"][0]
        row["candidate"]["terminal"]["own_cash"] = 94.0
        refresh_arm_trace(row["candidate"])
        report = pc.assess(value, policy(), spent_ledger())
        self.assertFalse(report["checks"]["cell_own_floor"])
        self.assertEqual(report["verdict"], "HOLD")

    def test_lower_quantile_floor_is_enforced(self) -> None:
        value = panel(seeds=[11, 12, 13, 14, 15, 16, 17, 18, 19, 20])
        p = policy()
        p["min_positive_seed_clusters"] = 5
        p["max_seed_sign_tail"] = 0.05
        # Two of twenty cells are negative but each seed mean stays positive.
        for row in value["cells"][:2]:
            row["candidate"]["terminal"]["own_cash"] = 99.0
            refresh_arm_trace(row["candidate"])
        report = pc.assess(value, p, spent_ledger())
        self.assertFalse(report["checks"]["lower_quantile_own_floor"])

    def test_outcome_regression_is_rejected_even_with_positive_global_mean(self) -> None:
        value = panel()
        bad = value["cells"][0]
        bad["control"]["terminal"] = {"own_cash": 100.0, "rival_cash": 99.0}
        refresh_arm_trace(bad["control"])
        bad["candidate"]["terminal"] = {"own_cash": 101.0, "rival_cash": 200.0}
        refresh_arm_trace(bad["candidate"])
        report = pc.assess(value, policy(), spent_ledger())
        self.assertGreater(report["summary"]["mean_own_cash_delta"], 0)
        self.assertFalse(report["checks"]["zero_new_losses"])
        self.assertEqual(report["verdict"], "HOLD")

    def test_policy_digest_cannot_be_tuned_after_run(self) -> None:
        value = panel()
        changed = policy()
        changed["min_cell_own_delta"] = -1000.0
        with self.assertRaisesRegex(pc.PromotionClosureError, "policy digest"):
            pc.assess(value, changed, spent_ledger())


class StrictJsonTests(unittest.TestCase):
    def test_duplicate_json_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaisesRegex(pc.PromotionClosureError, "duplicate key"):
                pc.strict_load(path, "bad")

    def test_nonfinite_policy_value_is_rejected(self) -> None:
        value = policy()
        value["min_cell_own_delta"] = math.inf
        with self.assertRaisesRegex(pc.PromotionClosureError, "finite"):
            pc.validate_policy(value)


if __name__ == "__main__":
    unittest.main()
