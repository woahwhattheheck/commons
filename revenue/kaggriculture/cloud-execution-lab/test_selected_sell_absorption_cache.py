# SPDX-License-Identifier: Apache-2.0
"""Parity and reuse checks for the shared seller absorption projection cache."""
import unittest

import mechanics as m
import selected_sell_core as core


class SelectedSellAbsorptionCacheTests(unittest.TestCase):
    def setUp(self):
        core._cached_absorption.cache_clear()

    def test_cached_absorption_matches_legacy_reference(self):
        shop_sets = (
            ['YARN_STORE'],
            ['SMOOTHIE_SHOP', 'FARMERS_MARKET'],
            ['BAKERY', 'PIZZA_SHOP', 'YARN_STORE', 'PET_CAFE'],
        )
        configs = (
            {},
            {'townShopSellInterval': 3, 'townCenterSellInterval': 5},
            {'townShopSellInterval': '7', 'townCenterSellInterval': '11'},
        )
        for shops in shop_sets:
            shop_products = core._shop_products_signature(shops)
            for config in configs:
                shop_interval = int(config.get('townShopSellInterval', 4))
                center_interval = int(config.get('townCenterSellInterval', 24))
                for item in ('WOOL', 'MILK', 'WHEAT', 'FERTILIZER'):
                    for step in (0, 1, 3, 4, 5, 7, 11, 12, 21, 24, 28, 33):
                        with self.subTest(shops=shops, config=config, item=item, step=step):
                            self.assertEqual(
                                core._cached_absorption(
                                    item, step, shop_products,
                                    shop_interval, center_interval),
                                core.absorption(item, step, shops, config),
                            )

    def test_shop_product_mutation_invalidates_cache_key(self):
        shops = ['YARN_STORE']
        before = core._shop_products_signature(shops)
        self.assertEqual(core._cached_absorption('WOOL', 4, before, 4, 24), 2)

        saved = list(m.SHOPS['YARN_STORE'])
        try:
            m.SHOPS['YARN_STORE'] = ['MILK']
            after = core._shop_products_signature(shops)
            self.assertNotEqual(after, before)
            self.assertEqual(core._cached_absorption('WOOL', 4, after, 4, 24), 0)
        finally:
            m.SHOPS['YARN_STORE'] = saved

        info = core._cached_absorption.cache_info()
        self.assertEqual(info.misses, 2)

    def test_interval_change_invalidates_cache_key(self):
        signature = core._shop_products_signature(['YARN_STORE'])
        self.assertEqual(core._cached_absorption('WOOL', 4, signature, 4, 24), 2)
        self.assertEqual(core._cached_absorption('WOOL', 4, signature, 5, 24), 0)
        self.assertEqual(core._cached_absorption.cache_info().misses, 2)

    def test_sliding_market_paths_reuse_overlapping_steps(self):
        shops = ['YARN_STORE', 'SMOOTHIE_SHOP', 'FARMERS_MARKET']
        config = {'townShopSellInterval': 4, 'townCenterSellInterval': 24}
        horizon = 42

        first = core.MarketPath('WOOL', 10000, None, shops, config,
                                200, 200 + horizon - 1)
        first.score((), 0, 0, 'paired')
        cold = core._cached_absorption.cache_info()
        self.assertEqual(cold.misses, horizon)
        self.assertEqual(cold.hits, 0)

        second = core.MarketPath('WOOL', 10000, None, shops, config,
                                 201, 201 + horizon - 1)
        second.score((), 0, 0, 'paired')
        warm = core._cached_absorption.cache_info()

        # 84 requested step projections collapse to 43 unique absolute steps.
        self.assertEqual(warm.misses, horizon + 1)
        self.assertEqual(warm.hits, horizon - 1)

    def test_cache_is_bounded(self):
        signature = core._shop_products_signature(['YARN_STORE'])
        maxsize = core._cached_absorption.cache_parameters()['maxsize']
        self.assertEqual(maxsize, core._ABSORPTION_CACHE_SIZE)
        for step in range(maxsize + 64):
            core._cached_absorption('WOOL', step, signature, 4, 24)
        self.assertEqual(core._cached_absorption.cache_info().currsize, maxsize)


if __name__ == '__main__':
    unittest.main()
