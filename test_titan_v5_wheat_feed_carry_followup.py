import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULE = ROOT / "revenue/kaggriculture/cloud-execution-lab/candidates/v5/lean-feed-carry-economics/wheat_feed_carry_oracle.py"
spec = importlib.util.spec_from_file_location("wheat_feed_carry_oracle_followup", MODULE)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load wheat_feed_carry_oracle")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

STATUS = ROOT / "revenue/kaggriculture/cloud-execution-lab/candidates/v5/lean-feed-carry-economics/D2_RECOVERY_STATUS.json"


class WheatCarryFollowupTests(unittest.TestCase):
    def test_machine_receipt_keeps_upstream_offer_census_open(self):
        receipt = m.source_theorem_receipt(STATUS)
        self.assertEqual(receipt["remaining_gate_state"], m.UPSTREAM_GATE)
        self.assertTrue(receipt["upstream_offer_census_required"])
        self.assertFalse(receipt["helper_seam_candidate"])
        self.assertFalse(receipt["candidate_build_authorized"])
        self.assertFalse(receipt["promotion_authorized"])
        self.assertIn(
            "AUTHENTICATED_UPSTREAM_UNDER_OFFERING_WITH_HELPER_THEOREM_INTACT",
            receipt["candidate_hypothesis_paths"],
        )
        self.assertIn(
            "SEPARATELY_REVIEWED_SOURCE_RUNTIME_CONTRADICTION",
            receipt["candidate_hypothesis_paths"],
        )
        self.assertIn("under-offer", receipt["empirical_gate"])
        self.assertNotIn(
            "candidate exists only if authenticated runtime behavior contradicts",
            receipt["empirical_gate"],
        )

    def test_upstream_under_offer_can_coexist_with_minimal_helper(self):
        # Balance alone permits selling 4/5 WHEAT while preserving required=1,
        # but the upstream selected action offers only 3. The final helper need
        # not withhold anything and remains exactly MIN_PROVABLE; the one-unit
        # upstream gap is therefore a distinct empirical question, not a helper
        # contradiction and not candidate authority.
        packet = {
            "observed_shed_wheat": 5,
            "eod_wheat_credit": 0,
            "required_wheat": 1,
            "offered_wheat": 3,
            "helper_report": {
                "certified": True,
                "changed": False,
                "reason": "feed_prefix_already_covered",
                "withheld_units": 0,
                "required_wheat": 1,
                "observed_shed_wheat": 5,
                "eod_wheat_credit": 0,
            },
        }
        out = m.analyze_certified_window(packet)
        self.assertEqual(out["state"], m.NEGATIVE)
        self.assertEqual(out["current_policy_withheld"], 0)
        self.assertEqual(out["min_provable_withheld"], 0)
        self.assertEqual(out["upstream_balance_permitted_sale"], 4)
        self.assertEqual(out["upstream_selected_offer"], 3)
        self.assertEqual(out["upstream_balance_offer_gap_units"], 1)
        self.assertEqual(out["upstream_offer_census_state"], m.UPSTREAM_GATE)
        self.assertFalse(out["candidate_build_authorized"])
        self.assertFalse(out["promotion_authorized"])

    def test_deep_status_json_normalizes_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "deep.json"
            p.write_text('{"x":' + ('[' * 2000) + '0' + (']' * 2000) + '}')
            with self.assertRaises(m.WheatCensusError):
                m._strict_json_object(p)

    def test_supported_but_over_policy_depth_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "deep.json"
            p.write_text('{"x":' + ('[' * 80) + '0' + (']' * 80) + '}')
            with self.assertRaisesRegex(m.WheatCensusError, "deeply nested"):
                m._strict_json_object(p)


if __name__ == "__main__":
    unittest.main()
