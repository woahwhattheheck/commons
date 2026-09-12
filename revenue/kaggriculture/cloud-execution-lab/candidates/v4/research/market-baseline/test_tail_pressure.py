import unittest

import tail_pressure as T


class TailPressureTests(unittest.TestCase):
    def test_helpers_are_pinned_to_authenticated_snapshots(self):
        self.assertEqual(
            T.verify_helpers(),
            {
                "market_baseline": T.MARKET_BASELINE_BLOB,
                "demand_velocity": T.DEMAND_VELOCITY_BLOB,
                "counter_ambush": T.COUNTER_AMBUSH_BLOB,
            },
        )
        r = T.pressure_certificate(
            item="STRAWBERRY", starting_inventory=10_000,
            own_units=8, rival_units=8, pre_step=402,
        )
        self.assertTrue(r["helper_snapshots_authenticated_before_execution"])
        self.assertEqual(r["helper_identities"], T.verify_helpers())
        self.assertIs(T.d.m, T.m)

    def test_apex_380_event_has_positive_counter_and_tail_headroom(self):
        shops = (
            "BRUNCH_SPOT", "ICE_CREAM_SHOP", "SMOOTHIE_SHOP", "FARMERS_MARKET"
        ) * 2
        r = T.pressure_certificate(
            item="STRAWBERRY", starting_inventory=10_000,
            own_units=8, rival_units=8, pre_step=380,
            unlocked_shops=shops,
        )
        self.assertEqual(r["residual_event_public_supply_units"], 16)
        self.assertEqual(r["remaining_absorption_tail"]["quantile_units"], 132.8)
        self.assertEqual(r["remaining_absorption_tail"]["floor_budget_units"], 132)
        self.assertGreater(r["immediate"]["gross_relative_margin_swing"], 0)
        self.assertFalse(r["pressure_warning"])
        self.assertEqual(
            r["disposition"], "POSITIVE_IMMEDIATE_COUNTER_WITH_TAIL_HEADROOM"
        )

    def test_apex_402_event_has_headroom_but_less_remaining_tail(self):
        r = T.pressure_certificate(
            item="STRAWBERRY", starting_inventory=10_000,
            own_units=8, rival_units=8, pre_step=402,
        )
        self.assertEqual(r["residual_event_public_supply_units"], 16)
        self.assertEqual(r["remaining_absorption_tail"]["quantile_units"], 127.3)
        self.assertEqual(r["remaining_absorption_tail"]["floor_budget_units"], 127)
        self.assertFalse(r["pressure_warning"])
        self.assertLess(
            r["remaining_absorption_tail"]["floor_budget_units"],
            T.remaining_absorption_tail("STRAWBERRY", 381)["floor_budget_units"],
        )

    def test_positive_immediate_counter_can_fail_tail_unwind_certificate(self):
        r = T.pressure_certificate(
            item="STRAWBERRY", starting_inventory=9_700,
            own_units=128, rival_units=8, pre_step=402,
        )
        self.assertGreater(r["immediate"]["gross_relative_margin_swing"], 0)
        self.assertEqual(r["residual_event_public_supply_units"], 136)
        self.assertEqual(r["remaining_absorption_tail"]["floor_budget_units"], 127)
        self.assertEqual(r["tail_slack_units"], -9)
        self.assertTrue(r["pressure_warning"])
        self.assertEqual(
            r["disposition"],
            "POSITIVE_IMMEDIATE_COUNTER_TAIL_UNWIND_NOT_CERTIFIED",
        )

    def test_price_floor_event_does_not_invent_public_supply(self):
        r = T.pressure_certificate(
            item="STRAWBERRY", starting_inventory=10_493,
            own_units=8, rival_units=8, pre_step=402,
        )
        self.assertEqual(r["residual_event_public_supply_units"], 0)
        self.assertEqual(r["immediate"]["gross_relative_margin_swing"], 0)
        self.assertEqual(r["disposition"], "NO_POSITIVE_IMMEDIATE_COUNTER")

    def test_certificate_never_claims_action_authority(self):
        r = T.pressure_certificate(
            item="STRAWBERRY", starting_inventory=10_000,
            own_units=8, rival_units=8, pre_step=402,
        )
        self.assertFalse(r["decision_authority"])
        self.assertFalse(r["timing_authority"])
        self.assertFalse(r["opponent_future_supply_accounted"])
        self.assertTrue(r["public_state_only"])

    def test_scope_stays_on_authenticated_strawberry_counter(self):
        with self.assertRaises(ValueError):
            T.pressure_certificate(
                item="MELON", starting_inventory=10_000,
                own_units=8, rival_units=8, pre_step=248,
            )

    def test_numeric_bool_aliases_and_terminal_overrun_fail_closed(self):
        with self.assertRaises(ValueError):
            T.pressure_certificate(
                item="STRAWBERRY", starting_inventory=10_000,
                own_units=True, rival_units=8, pre_step=402,
            )
        with self.assertRaises(ValueError):
            T.remaining_absorption_tail("STRAWBERRY", 719)


if __name__ == "__main__":
    unittest.main()
