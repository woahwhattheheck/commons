# SPDX-License-Identifier: Apache-2.0
from promotion_test_support import *

class TrajectoryCustodyTests(unittest.TestCase):
    def test_clean_clustered_panel_is_candidate_not_authority(self) -> None:
        report = pc.assess(panel(), policy(), spent_ledger())
        self.assertEqual(report["verdict"], "PROMOTION_CANDIDATE")
        self.assertFalse(report["promotion_authority"])
        self.assertEqual(report["summary"]["positive_seed_clusters"], 5)
        self.assertEqual(report["summary"]["seed_sign_tail"]["denominator"], 32)
        detached = panel()
        detached["opponents"]["apex"]["members"][0]["sha256"] = d("detached")
        with self.assertRaisesRegex(pc.PromotionClosureError, "module .* digest is detached"):
            pc.assess(detached, policy(), spent_ledger())

    def test_score_change_with_trace_identity_is_rejected(self) -> None:
        value = panel()
        candidate = value["cells"][0]["candidate"]
        control = value["cells"][0]["control"]
        candidate["trace_sha256"] = control["trace_sha256"]
        with self.assertRaisesRegex(pc.PromotionClosureError, "trace digest is detached"):
            pc.assess(value, policy(), spent_ledger())

    def test_no_action_change_verdict_cannot_launder_score(self) -> None:
        value = panel()
        value["cells"][0]["paired_verdict"] = "NO_ACTION_CHANGE"
        with self.assertRaisesRegex(pc.PromotionClosureError, "NO_ACTION_CHANGE"):
            pc.assess(value, policy(), spent_ledger())

    def test_first_action_noop_is_rejected(self) -> None:
        value = panel()
        row = value["cells"][0]
        row["candidate"]["steps"][3]["postworld_sha256"] = row["control"]["steps"][3]["postworld_sha256"]
        refresh_arm_trace(row["candidate"])
        with self.assertRaisesRegex(pc.PromotionClosureError, "did not change the realized postworld"):
            pc.assess(value, policy(), spent_ledger())

    def test_rival_action_confound_is_rejected(self) -> None:
        value = panel()
        row = value["cells"][0]
        row["candidate"]["steps"][3]["rival_action_sha256"] = d("confounded-rival")
        refresh_arm_trace(row["candidate"])
        with self.assertRaisesRegex(pc.PromotionClosureError, "rival_action_sha256"):
            pc.assess(value, policy(), spent_ledger())

    def test_preworld_divergence_before_tested_action_is_rejected(self) -> None:
        value = panel()
        row = value["cells"][0]
        row["candidate"]["steps"][1]["preworld_sha256"] = d("early-world-drift")
        refresh_arm_trace(row["candidate"])
        with self.assertRaisesRegex(pc.PromotionClosureError, "diverged before tested action"):
            pc.assess(value, policy(), spent_ledger())

    def test_score_active_cell_requires_independent_replay(self) -> None:
        value = panel()
        value["cells"][0]["candidate"]["replay"] = None
        with self.assertRaisesRegex(pc.PromotionClosureError, "lacks deterministic replay"):
            pc.assess(value, policy(), spent_ledger())

    def test_replay_mismatch_is_rejected(self) -> None:
        value = panel()
        value["cells"][0]["candidate"]["replay"]["own_cash"] += 1
        with self.assertRaisesRegex(pc.PromotionClosureError, "replay own cash differs"):
            pc.assess(value, policy(), spent_ledger())

    def test_missing_mirrored_cell_is_rejected(self) -> None:
        value = panel()
        value["cells"].pop()
        with self.assertRaisesRegex(pc.PromotionClosureError, "grid mismatch"):
            pc.assess(value, policy(), spent_ledger())

    def test_boolean_seed_is_rejected(self) -> None:
        value = panel()
        value["cells"][0]["seed"] = True
        with self.assertRaisesRegex(pc.PromotionClosureError, "integer"):
            pc.assess(value, policy(), spent_ledger())



if __name__ == "__main__":
    unittest.main()
