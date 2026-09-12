#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import tempfile
import unittest

import counter_ambush_burst as b

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE / "counter_ambush.py"
SOURCE = HERE / "counter_ambush_burst.py"


class ApexEnvelopeTests(unittest.TestCase):
    def test_max_envelope_values_are_conditional_not_realized(self):
        report = b.authenticated_apex_envelope_report(BASE)
        scenario = report["conditional_max_shop_drain_scenario"]
        self.assertEqual(report["max_envelope_events"], [[499, 8], [500, 8], [501, 8]])
        self.assertTrue(report["source_rule_authenticated"])
        self.assertFalse(report["realized_events_authenticated"])
        self.assertFalse(report["result_authority"])
        self.assertFalse(report["activation_authority"])
        self.assertEqual(
            scenario["scenario_semantics"],
            "conditional_max_envelope_not_observed_events",
        )
        self.assertEqual(scenario["own_early_gross"], 905)
        self.assertEqual(scenario["own_post_envelope_gross"], 661)
        self.assertEqual(scenario["own_timing_gain"], 244)
        self.assertEqual(scenario["cumulative_rival_suppression"], 367)
        self.assertEqual(scenario["gross_relative_margin_swing"], 611)
        self.assertFalse(scenario["realized_events_authenticated"])
        self.assertFalse(scenario["decision_authority"])
        self.assertFalse(scenario["result_authority"])

    def test_source_rule_contract_is_conditional_ceiling(self):
        report = b.authenticated_apex_envelope_report(BASE)
        rule = report["source_rule"]
        self.assertEqual(rule["steps"], [499, 500, 501])
        self.assertEqual(rule["item"], "STRAWBERRY")
        self.assertEqual(rule["min_shed"], 8)
        self.assertEqual(rule["max_sell_per_callback"], 8)
        self.assertEqual(rule["semantics"], "conditional_source_rule_not_realized_event")
        self.assertGreaterEqual(len(report["required_realization_evidence"]), 3)

    def test_town_drain_occurs_inside_max_envelope_scenario(self):
        report = b.authenticated_apex_envelope_report(BASE)
        rows = report["conditional_max_shop_drain_scenario"]["events"]
        self.assertEqual([row["step"] for row in rows], [499, 500, 501])
        self.assertEqual([row["town_drain_after"] for row in rows], [0, 8, 0])
        self.assertEqual([row["rival_suppression"] for row in rows], [121, 123, 123])

    def test_max_envelope_is_not_three_isolated_dumps(self):
        report = b.authenticated_apex_envelope_report(BASE)
        self.assertEqual(report["max_envelope_isolated_first_event_swing"], 242)
        self.assertEqual(report["max_envelope_naive_three_times_isolated_swing"], 726)
        self.assertEqual(
            report["conditional_max_shop_drain_scenario"]["gross_relative_margin_swing"],
            611,
        )
        self.assertEqual(report["max_envelope_minus_naive_isolated"], -115)

    def test_predecessor_realized_event_names_do_not_return(self):
        text = SOURCE.read_text(encoding="utf-8")
        for forbidden in (
            "AUTHENTICATED_APEX_STRAWBERRY_BURST",
            '"authenticated_events"',
            '"source_real_max_shop_drain"',
            "def authenticated_apex_report(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, text)
        report = b.authenticated_apex_envelope_report(BASE)
        self.assertNotIn("authenticated_events", report)
        self.assertNotIn("source_real_max_shop_drain", report)
        self.assertFalse(report["realized_events_authenticated"])

    def test_pinned_base_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            path = pathlib.Path(td) / "counter_ambush.py"
            path.write_bytes(BASE.read_bytes() + b"\n# drift\n")
            with self.assertRaisesRegex(b.BurstError, "base drift"):
                b.load_pinned_base(path)

    def test_event_steps_must_be_strictly_increasing(self):
        for events in (
            ((499, 8), (499, 8)),
            ((500, 8), (499, 8)),
        ):
            with self.subTest(events=events):
                with self.assertRaisesRegex(b.BurstError, "strictly increasing"):
                    b.normalize_events(events)

    def test_event_units_fail_closed(self):
        for events in (
            ((499, 0),),
            ((499, -1),),
            ((499, True),),
        ):
            with self.subTest(events=events):
                with self.assertRaises(b.BurstError):
                    b.normalize_events(events)

    def test_pre_step_must_touch_envelope(self):
        base = b.load_pinned_base(BASE)
        with self.assertRaisesRegex(b.BurstError, "exactly one callback"):
            b.envelope_counterfactual(
                base,
                item="STRAWBERRY",
                starting_inventory=10000,
                own_units=8,
                events=b.APEX_STRAWBERRY_MAX_ENVELOPE,
                pre_step=497,
            )

    def test_empty_events_rejected(self):
        with self.assertRaisesRegex(b.BurstError, "nonempty event"):
            b.normalize_events(())


if __name__ == "__main__":
    unittest.main()
