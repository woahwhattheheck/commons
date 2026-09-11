import unittest

from candidate import order_sells


class RowShedTests(unittest.TestCase):
    def setUp(self):
        self.inventory = {
            "WHEAT": 10000,
            "CARROT": 10000,
            "TOMATO": 10000,
            "STRAWBERRY": 10000,
            "MELON": 10000,
            "EGG": 10000,
            "MILK": 10000,
            "WOOL": 10000,
            "FERTILIZER": 10000,
        }

    def test_single_leading_sell_returns_exact_parent_object(self):
        market = [["SELL", "CARROT", 1000], ["BUY_PRODUCT", "WHEAT", 1]]
        self.assertIs(order_sells(market, self.inventory, {"CARROT": 5}), market)

    def test_non_sell_prefix_returns_exact_parent_object(self):
        market = [["BUY_PRODUCT", "WHEAT", 1], ["SELL", "CARROT", 1000]]
        self.assertIs(order_sells(market, self.inventory, {"CARROT": 5}), market)

    def test_legacy_requested_quantity_prefers_large_carrot_request(self):
        market = [["SELL", "WHEAT", 100], ["SELL", "CARROT", 1000]]
        result = order_sells(market, self.inventory, None)
        self.assertEqual(result[0], ["SELL", "CARROT", 1000])

    def test_row_shed_cap_flips_to_sellable_wheat(self):
        market = [["SELL", "WHEAT", 100], ["SELL", "CARROT", 1000]]
        projected = {"WHEAT": 100, "CARROT": 5}
        result = order_sells(market, self.inventory, projected)
        self.assertEqual(result[0], ["SELL", "WHEAT", 100])
        self.assertEqual(result[1], ["SELL", "CARROT", 1000])

    def test_requested_quantities_are_never_rewritten(self):
        market = [["SELL", "WHEAT", 100], ["SELL", "CARROT", 1000]]
        original = [list(row) for row in market]
        result = order_sells(market, self.inventory, {"WHEAT": 100, "CARROT": 5})
        self.assertEqual(sorted(result), sorted(original))
        self.assertEqual(market, original)

    def test_tail_after_first_non_sell_is_untouched(self):
        tail = [["BUY_PRODUCT", "WHEAT", 1], ["SELL", "MILK", 1000]]
        market = [["SELL", "WHEAT", 100], ["SELL", "CARROT", 1000], *tail]
        result = order_sells(market, self.inventory, {"WHEAT": 100, "CARROT": 5, "MILK": 1000})
        self.assertEqual(result[2:], tail)

    def test_zero_projected_stock_scores_zero(self):
        market = [["SELL", "CARROT", 1000], ["SELL", "WHEAT", 10]]
        result = order_sells(market, self.inventory, {"CARROT": 0, "WHEAT": 10})
        self.assertEqual(result[0], ["SELL", "WHEAT", 10])

    def test_negative_projection_falls_back_to_whole_parent_sort(self):
        market = [["SELL", "CARROT", 1000], ["SELL", "WHEAT", 10]]
        legacy = order_sells(market, self.inventory, None)
        result = order_sells(market, self.inventory, {"CARROT": -99, "WHEAT": 10})
        self.assertEqual(result, legacy)

    def test_bool_projection_falls_back_to_whole_parent_sort(self):
        market = [["SELL", "WHEAT", 100], ["SELL", "CARROT", 1000]]
        legacy = order_sells(market, self.inventory, None)
        result = order_sells(market, self.inventory, {"WHEAT": 100, "CARROT": True})
        self.assertEqual(result, legacy)

    def test_partial_projection_falls_back_to_whole_parent_sort(self):
        market = [["SELL", "WHEAT", 100], ["SELL", "CARROT", 1000]]
        legacy = order_sells(market, self.inventory, None)
        self.assertEqual(legacy[0], ["SELL", "CARROT", 1000])
        # Per-row fallback would use CARROT=5 but legacy WHEAT=100 and flip this
        # ordering; whole-block fallback must preserve the inherited sort instead.
        result = order_sells(market, self.inventory, {"CARROT": 5})
        self.assertEqual(result, legacy)

    def test_zero_score_tie_is_stable(self):
        market = [["SELL", "UNKNOWN_A", 10], ["SELL", "UNKNOWN_B", 10]]
        result = order_sells(market, self.inventory, {})
        self.assertEqual(result, market)


if __name__ == "__main__":
    unittest.main()
