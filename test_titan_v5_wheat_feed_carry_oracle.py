import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULE = ROOT / "revenue/kaggriculture/cloud-execution-lab/candidates/v5/lean-feed-carry-economics/wheat_feed_carry_oracle.py"
spec = importlib.util.spec_from_file_location("wheat_feed_carry_oracle", MODULE)
if spec is None or spec.loader is None:
    raise RuntimeError("cannot load wheat_feed_carry_oracle")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

STATUS = ROOT / "revenue/kaggriculture/cloud-execution-lab/candidates/v5/lean-feed-carry-economics/D2_RECOVERY_STATUS.json"


class WheatCarryOracleTests(unittest.TestCase):
    def packet(self, stock=5, returned=0, required=1, offered=5):
        withheld = m.source_current_policy_withheld(stock, returned, required, offered)
        return {
            "observed_shed_wheat": stock,
            "eod_wheat_credit": returned,
            "required_wheat": required,
            "offered_wheat": offered,
            "helper_report": {
                "certified": True,
                "changed": withheld > 0,
                "reason": "reserve_reachable_feed" if withheld else "feed_prefix_already_covered",
                "withheld_units": withheld,
                "required_wheat": required,
                "observed_shed_wheat": stock,
                "eod_wheat_credit": returned,
            },
        }

    def test_retained_status_is_authenticated_but_not_authorizing(self):
        out = m.validate_authenticated_status(STATUS)
        self.assertEqual(out["state"], m.STATE_AUTHENTICATED)
        receipt = m.source_theorem_receipt(STATUS)
        self.assertFalse(receipt["candidate_build_authorized"])
        self.assertFalse(receipt["promotion_authorized"])
        self.assertIsNone(receipt["empirical_result"])

    def test_current_equation_equals_minimum_across_supported_grid(self):
        # Exhaustive representative grid including capacity and reset-return edges.
        values = [0, 1, 2, 3, 5, 10, 50, 99, 100]
        for stock in values:
            for returned in values:
                for offered in values:
                    for required in values:
                        if required > stock + returned:
                            continue
                        minimum = m.minimum_required_withheld(stock, returned, required, offered)
                        if minimum > m.MAX_HELPER_WITHHOLD:
                            with self.assertRaises(m.WheatCensusError):
                                m.source_current_policy_withheld(stock, returned, required, offered)
                        else:
                            current = m.source_current_policy_withheld(stock, returned, required, offered)
                            self.assertEqual(current, minimum)

    def test_positive_reservation_is_not_discretionary_buffer(self):
        out = m.analyze_certified_window(self.packet(stock=5, returned=0, required=1, offered=5))
        self.assertEqual(out["state"], m.NEGATIVE)
        self.assertEqual(out["current_policy_withheld"], 1)
        self.assertEqual(out["min_provable_withheld"], 1)
        self.assertEqual(out["discretionary_excess_units"], 0)
        self.assertEqual(out["cash_liberated_by_min_provable"], 0)
        self.assertFalse(out["candidate_build_authorized"])

    def test_returned_wheat_can_make_reservation_zero(self):
        out = m.analyze_certified_window(self.packet(stock=5, returned=1, required=1, offered=5))
        self.assertEqual(out["current_policy_withheld"], 0)
        self.assertEqual(out["min_provable_withheld"], 0)

    def test_partial_sale_already_preserves_obligation(self):
        out = m.analyze_certified_window(self.packet(stock=5, returned=0, required=2, offered=1))
        self.assertEqual(out["current_policy_withheld"], 0)
        self.assertEqual(out["min_provable_withheld"], 0)

    def test_plus_one_is_stress_not_candidate(self):
        out = m.analyze_certified_window(self.packet(stock=5, returned=0, required=1, offered=5))
        self.assertEqual(out["plus_one_withheld"], 2)
        self.assertFalse(out["candidate_build_authorized"])

    def test_uncertified_runtime_window_never_builds_candidate(self):
        p = self.packet()
        p["helper_report"] = {"certified": False, "reason": "feed_reservation_exceeds_two_units"}
        out = m.analyze_certified_window(p)
        self.assertEqual(out["state"], m.UNCERTIFIED)
        self.assertFalse(out["candidate_build_authorized"])

    def test_helper_report_mismatch_is_fail_closed(self):
        p = self.packet()
        p["helper_report"]["withheld_units"] = 0
        with self.assertRaises(m.WheatCensusError):
            m.analyze_certified_window(p)

    def test_bool_is_not_integer(self):
        p = self.packet()
        p["offered_wheat"] = True
        with self.assertRaises(m.WheatCensusError):
            m.analyze_certified_window(p)

    def test_impossible_obligation_rejected(self):
        with self.assertRaises(m.WheatCensusError):
            m.minimum_required_withheld(1, 0, 2, 1)

    def test_source_helper_ceiling_fail_closed(self):
        # Selling all five while needing five implies withholding five; the
        # retained helper deliberately refuses that unsupported window.
        self.assertEqual(m.minimum_required_withheld(5, 0, 5, 5), 5)
        with self.assertRaises(m.WheatCensusError):
            m.source_current_policy_withheld(5, 0, 5, 5)

    def test_status_duplicate_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            p.write_text('{"schema":"x","schema":"y"}')
            with self.assertRaises(m.WheatCensusError):
                m.validate_authenticated_status(p)

    def test_status_huge_integer_rejected_before_int_conversion(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            p.write_text('{"n":' + ('9' * 5000) + '}')
            with self.assertRaises(m.WheatCensusError):
                m.validate_authenticated_status(p)

    def test_status_cannot_escalate_candidate_authority(self):
        data = json.loads(STATUS.read_text())
        data["candidate_build_authorized"] = True
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "s.json"
            p.write_text(json.dumps(data))
            with self.assertRaises(m.WheatCensusError):
                m.validate_authenticated_status(p)


if __name__ == "__main__":
    unittest.main()
