from __future__ import annotations

import copy
import unittest

import feed_carry_oracle as o
from test_feed_carry_oracle import document


class PromotionHardeningTests(unittest.TestCase):
    def test_positive_synthetic_economics_is_source_blocked(self):
        report = o.analyze_for_promotion(document())
        self.assertEqual(report["promotion"]["conclusion"], "SOURCE_MODEL_BLOCKED")
        self.assertIsNone(report["promotion"]["selected_arm"])
        self.assertFalse(report["authority"]["authority_verified"])
        self.assertFalse(report["authority"]["source_promotion_authorized"])
        self.assertTrue(report["authority"]["terminal_evidence_root_sha256"])
        self.assertEqual(report["census"], [])
        self.assertEqual(report["paired_deltas"], [])
        self.assertEqual(report["runs"], [])

    def test_conservative_no_promotion_stays_conservative(self):
        report = o.analyze_for_promotion(document(cash_use=False))
        self.assertEqual(report["promotion"]["conclusion"], "NO_PROMOTION")

    def test_duplicate_arm_row_rejected_even_with_unique_run_id(self):
        evidence = document()
        duplicate = copy.deepcopy(evidence["runs"][0])
        duplicate["run_id"] += "-duplicate"
        evidence["runs"].append(duplicate)
        with self.assertRaisesRegex(o.EvidenceError, "duplicate arm row"):
            o.analyze_for_promotion(evidence)

    def test_cross_arm_start_snapshot_mismatch_rejected(self):
        evidence = document()
        target = next(
            row
            for row in evidence["runs"]
            if row["split"] == "dev"
            and row["opponent"] == "random"
            and row["seat"] == 1
            and row["arm"] == o.ARM_CURRENT
        )
        target["decision_windows"][0]["snapshot"]["cash"] += 1
        with self.assertRaisesRegex(o.EvidenceError, "cross-arm starting snapshot mismatch"):
            o.analyze_for_promotion(evidence)

    def test_null_boundary_activation_rejected(self):
        evidence = document()
        target = next(row for row in evidence["runs"] if row["arm"] == o.ARM_MIN)
        target["decision_windows"][0]["snapshot"]["obligations"] = []
        with self.assertRaisesRegex(o.EvidenceError, "non-empty proven obligation census"):
            o.analyze_for_promotion(evidence)

    def test_duplicate_liberated_cash_event_rejected(self):
        evidence = document()
        target = next(row for row in evidence["runs"] if row["arm"] == o.ARM_MIN)
        uses = target["decision_windows"][0]["cash_uses"]
        uses.append(copy.deepcopy(uses[0]))
        with self.assertRaisesRegex(o.EvidenceError, "duplicate liberated-cash telemetry"):
            o.analyze_for_promotion(evidence)

    def test_self_minted_authority_rejected(self):
        evidence = document()
        evidence["authority"]["authority_verified"] = True
        with self.assertRaisesRegex(o.EvidenceError, "cannot self-mint promotion authority"):
            o.analyze_for_promotion(evidence)

    def test_report_evidence_digest_binds_terminal_result(self):
        evidence = document(cash_use=False)
        report = o.analyze_for_promotion(evidence)
        raw = evidence["runs"][0]
        expected = o.sha256_json(
            {
                "decision_windows": raw["decision_windows"],
                "result": raw["result"],
            }
        )
        row = next(item for item in report["runs"] if item["run_id"] == raw["run_id"])
        self.assertEqual(row["evidence_sha256"], expected)
        changed = copy.deepcopy(raw)
        changed["result"]["own"] += 1
        changed["result"]["margin"] += 1
        self.assertNotEqual(
            expected,
            o.sha256_json(
                {
                    "decision_windows": changed["decision_windows"],
                    "result": changed["result"],
                }
            ),
        )


if __name__ == "__main__":
    unittest.main()
