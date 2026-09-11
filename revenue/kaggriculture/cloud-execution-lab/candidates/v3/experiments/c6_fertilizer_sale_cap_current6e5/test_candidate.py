import copy
import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).with_name("candidate.py")
spec = importlib.util.spec_from_file_location("c6_candidate_tested", PATH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def observation(step=24 * 24, shed=10, inventories=None):
    inventories = list(inventories or [{"FERTILIZER": 0}])
    hands = [[0, 0] for _ in inventories[1:]]
    return {
        "step": step,
        "player": 0,
        "farms": [{"tiles": [[None]], "farmer": [0, 0], "hands": hands}],
        "private": {
            "inventories": inventories,
            "shed": {"FERTILIZER": shed},
        },
        "market": {
            "prices": {"FERTILIZER": 20},
            "inventory": {"FERTILIZER": 10000},
        },
    }


def debt_state(debts):
    state = m.base.DayState()
    state.sale_window_debts = copy.deepcopy(debts)
    return state


class C6FertilizerSaleCapTest(unittest.TestCase):
    def setUp(self):
        self.saved_v219_states = m.base._V219_STATES
        m.base._V219_STATES = {}
        for key in m.REPORT:
            m.REPORT[key] = 0

    def tearDown(self):
        m.base._V219_STATES = self.saved_v219_states

    def test_live_baseline_tuple_is_explicit_and_sale_fertilizer_stays_on(self):
        self.assertEqual(m.LIVE_BASELINE, {
            "horizon": 8,
            "opening": 0,
            "row_order": True,
            "evening_flush": True,
            "sale_fertilizer": True,
            "cattle_early": True,
        })

    def test_same_callback_booking_delta_is_exact(self):
        before = {578: 4, 580: 1}
        after = {578: 7, 579: 2, 580: 1}
        self.assertEqual(m.new_fertilizer_bookings(before, after), {578: 3, 579: 2})

    def test_bool_float_and_string_debt_quantities_fail_closed(self):
        for bad in (True, 3.0, "3", -1):
            with self.subTest(bad=bad):
                state = debt_state({578: {"FERTILIZER": bad}})
                self.assertIsNone(m.snapshot_fertilizer_debts(state))

    def test_day24_two_crop_workers_reserve_five_each_minus_carried(self):
        m.base._V219_STATES[0] = {
            "committed": True,
            "day": 24,
            "workers": {
                0: {"kind": "crop", "needs_fertilizer": True},
                1: {"kind": "crop", "needs_fertilizer": True},
            },
        }
        obs = observation(inventories=[{"FERTILIZER": 2}, {"FERTILIZER": 1}])
        self.assertEqual(m.v219_fertilizer_reserve(obs), 7)

    def test_day27_only_dedicated_unloaded_worker_is_reserved(self):
        m.base._V219_STATES[0] = {
            "committed": True,
            "day": 27,
            "workers": {
                0: {"kind": "crop", "needs_fertilizer": False},
                1: {"kind": "fertilizer", "needs_fertilizer": True},
            },
        }
        obs = observation(step=27 * 24, inventories=[{}, {"FERTILIZER": 3}])
        self.assertEqual(m.v219_fertilizer_reserve(obs), 7)

    def test_pickup_requested_role_is_not_future_reserve(self):
        m.base._V219_STATES[0] = {
            "committed": True,
            "day": 24,
            "workers": {
                0: {
                    "kind": "crop",
                    "needs_fertilizer": True,
                    "loaded": False,
                    "pickup_requested": True,
                },
            },
        }
        obs = observation(inventories=[{"FERTILIZER": 0}])
        self.assertEqual(m.v219_fertilizer_reserve(obs), 0)

    def test_mixed_pickup_requested_and_future_roles_reserve_only_future_loader(self):
        m.base._V219_STATES[0] = {
            "committed": True,
            "day": 24,
            "workers": {
                0: {
                    "kind": "crop",
                    "needs_fertilizer": True,
                    "loaded": False,
                    "pickup_requested": True,
                },
                1: {
                    "kind": "crop",
                    "needs_fertilizer": True,
                    "loaded": False,
                    "pickup_requested": False,
                },
            },
        }
        obs = observation(inventories=[{"FERTILIZER": 0}, {"FERTILIZER": 2}])
        self.assertEqual(m.v219_fertilizer_reserve(obs), 3)

    def test_malformed_pickup_requested_flag_fails_closed(self):
        for bad in (1, "yes", None, [], {}):
            with self.subTest(bad=bad):
                m.base._V219_STATES[0] = {
                    "committed": True,
                    "day": 24,
                    "workers": {
                        0: {
                            "kind": "crop",
                            "needs_fertilizer": True,
                            "loaded": False,
                            "pickup_requested": bad,
                        },
                    },
                }
                self.assertIsNone(m.v219_fertilizer_reserve(observation()))

    def test_loaded_worker_and_other_days_need_no_reserve(self):
        m.base._V219_STATES[0] = {
            "committed": True,
            "day": 24,
            "workers": {0: {"kind": "crop", "needs_fertilizer": True, "loaded": True}},
        }
        self.assertEqual(m.v219_fertilizer_reserve(observation()), 0)
        self.assertEqual(m.v219_fertilizer_reserve(observation(step=25 * 24)), 0)

    def test_partial_cap_only_removes_owned_advance_and_refunds_debt(self):
        obs = observation(shed=10)
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "MILK", 1], ["SELL", "FERTILIZER", 8], ["HIRE"]],
        }
        before_action = copy.deepcopy(action)
        state = debt_state({578: {"FERTILIZER": 8}, 590: {"MILK": 2}})
        result = m.cap_owned_fertilizer_advance(obs, action, state, {578: 8}, reserve=5)
        self.assertEqual(action, before_action)
        self.assertEqual(result["market"], [["SELL", "MILK", 1], ["SELL", "FERTILIZER", 5], ["HIRE"]])
        self.assertEqual(state.sale_window_debts, {578: {"FERTILIZER": 5}, 590: {"MILK": 2}})
        self.assertEqual(m.REPORT["fert_advance_units_withheld"], 3)

    def test_partial_cap_accepts_and_preserves_existing_empty_slots(self):
        obs = observation(shed=10)
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [[], ["SELL", "FERTILIZER", 8], [], ["HIRE"]],
        }
        before_action = copy.deepcopy(action)
        state = debt_state({578: {"FERTILIZER": 8}})
        result = m.cap_owned_fertilizer_advance(obs, action, state, {578: 8}, reserve=5)
        self.assertEqual(action, before_action)
        self.assertEqual(result["market"], [[], ["SELL", "FERTILIZER", 5], [], ["HIRE"]])
        self.assertEqual(result["market"][0], before_action["market"][0])
        self.assertEqual(result["market"][2:], before_action["market"][2:])
        self.assertEqual(state.sale_window_debts, {578: {"FERTILIZER": 5}})

    def test_partial_refund_restores_latest_due_first_and_keeps_nearer_suppression(self):
        obs = observation(shed=10)
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "FERTILIZER", 8]]}
        state = debt_state({578: {"FERTILIZER": 3}, 580: {"FERTILIZER": 5}})
        result = m.cap_owned_fertilizer_advance(
            obs, action, state, {578: 3, 580: 5}, reserve=5,
        )
        # Post-sale stock would be 2, so 3 units are withheld. The farther due
        # row is restored first; the nearer due row remains fully suppressed.
        self.assertEqual(result["market"], [["SELL", "FERTILIZER", 5]])
        self.assertEqual(state.sale_window_debts, {
            578: {"FERTILIZER": 3},
            580: {"FERTILIZER": 2},
        })

    def test_full_cap_preserves_owned_slot_and_every_later_parent_index(self):
        obs = observation(shed=5)
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [
                ["SELL", "FERTILIZER", 5],
                ["BUY_SEED", "TOMATO", 2],
                ["HIRE"],
                ["SELL", "MILK", 1],
            ],
        }
        before_action = copy.deepcopy(action)
        state = debt_state({578: {"FERTILIZER": 5}, 590: {"WOOL": 3}})
        result = m.cap_owned_fertilizer_advance(obs, action, state, {578: 5}, reserve=5)
        self.assertEqual(action, before_action)
        self.assertEqual(result["market"], [
            [],
            ["BUY_SEED", "TOMATO", 2],
            ["HIRE"],
            ["SELL", "MILK", 1],
        ])
        self.assertEqual(result["market"][1:], before_action["market"][1:])
        self.assertEqual(state.sale_window_debts, {590: {"WOOL": 3}})
        self.assertEqual(m.REPORT["fert_advance_units_withheld"], 5)

    def test_full_cap_accepts_and_preserves_existing_empty_slots(self):
        obs = observation(shed=5)
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [
                ["SELL", "MILK", 1],
                [],
                ["SELL", "FERTILIZER", 5],
                [],
                ["HIRE"],
            ],
        }
        before_action = copy.deepcopy(action)
        state = debt_state({578: {"FERTILIZER": 5}})
        result = m.cap_owned_fertilizer_advance(obs, action, state, {578: 5}, reserve=5)
        self.assertEqual(action, before_action)
        self.assertEqual(result["market"], [
            ["SELL", "MILK", 1],
            [],
            [],
            [],
            ["HIRE"],
        ])
        self.assertEqual(result["market"][:2], before_action["market"][:2])
        self.assertEqual(result["market"][3:], before_action["market"][3:])
        self.assertEqual(state.sale_window_debts, {})

    def test_non_list_market_row_remains_fail_closed(self):
        obs = observation(shed=5)
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "FERTILIZER", 5], "malformed"],
        }
        before_debt = {578: {"FERTILIZER": 5}}
        state = debt_state(before_debt)
        self.assertIs(m.cap_owned_fertilizer_advance(obs, action, state, {578: 5}, reserve=5), action)
        self.assertEqual(state.sale_window_debts, before_debt)

    def test_existing_fert_debt_is_not_refunded_beyond_same_callback_increment(self):
        obs = observation(shed=3)
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "FERTILIZER", 3]]}
        state = debt_state({578: {"FERTILIZER": 7, "MILK": 2}})
        result = m.cap_owned_fertilizer_advance(obs, action, state, {578: 3}, reserve=3)
        self.assertEqual(result["market"], [[]])
        self.assertEqual(state.sale_window_debts, {578: {"FERTILIZER": 4, "MILK": 2}})

    def test_ownership_mismatch_is_exact_identity_and_keeps_debt(self):
        obs = observation(shed=10)
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "FERTILIZER", 9]]}
        state = debt_state({578: {"FERTILIZER": 8}})
        before_debt = copy.deepcopy(state.sale_window_debts)
        self.assertIs(m.cap_owned_fertilizer_advance(obs, action, state, {578: 8}, reserve=10), action)
        self.assertEqual(state.sale_window_debts, before_debt)

    def test_multiple_fertilizer_sell_rows_are_ambiguous_and_fail_closed(self):
        obs = observation(shed=10)
        action = {
            "farmer": ["PASS"],
            "hands": [],
            "market": [["SELL", "FERTILIZER", 2], ["SELL", "FERTILIZER", 3]],
        }
        state = debt_state({578: {"FERTILIZER": 5}})
        before_debt = copy.deepcopy(state.sale_window_debts)
        self.assertIs(m.cap_owned_fertilizer_advance(obs, action, state, {578: 5}, reserve=10), action)
        self.assertEqual(state.sale_window_debts, before_debt)

    def test_sufficient_post_sale_stock_keeps_parent_exact(self):
        obs = observation(shed=20)
        action = {"farmer": ["PASS"], "hands": [], "market": [["SELL", "FERTILIZER", 5]]}
        state = debt_state({578: {"FERTILIZER": 5}})
        self.assertIs(m.cap_owned_fertilizer_advance(obs, action, state, {578: 5}, reserve=10), action)
        self.assertEqual(state.sale_window_debts, {578: {"FERTILIZER": 5}})


if __name__ == "__main__":
    unittest.main()
