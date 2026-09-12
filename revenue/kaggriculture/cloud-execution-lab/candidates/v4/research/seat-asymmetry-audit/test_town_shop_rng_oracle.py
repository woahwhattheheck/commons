import json
import unittest
from pathlib import Path
import tempfile

import town_shop_rng_oracle as oracle


class ShopStreamTests(unittest.TestCase):
    def test_source_hash_and_order_are_authenticated(self):
        identity = oracle.authenticate_engine()
        self.assertEqual(identity["git_blob"], oracle.ENGINE_GIT_BLOB)
        self.assertEqual(identity["sha256"], oracle.ENGINE_SHA256)

    def test_model_seed5_one_tile_shift_changes_shop(self):
        self.assertEqual(
            oracle.shop_after_vacancy_draws(
                seed=5, day=2, empty_tiles_by_farm=(25, 25)
            ),
            "PIZZA_SHOP",
        )
        self.assertEqual(
            oracle.shop_after_vacancy_draws(
                seed=5, day=2, empty_tiles_by_farm=(24, 25)
            ),
            "BRUNCH_SPOT",
        )

    def test_model_depends_on_total_draw_count_not_farm_split(self):
        for seed in range(1, 65):
            self.assertEqual(
                oracle.shop_after_vacancy_draws(
                    seed=seed, day=2, empty_tiles_by_farm=(24, 25)
                ),
                oracle.shop_after_vacancy_draws(
                    seed=seed, day=2, empty_tiles_by_farm=(25, 24)
                ),
            )

    def test_exact_engine_seed5_matches_model_with_weeds_disabled(self):
        engine = oracle.load_authenticated_engine()
        base = oracle.official_shop_unlock(seed=5, filled=None, engine=engine)
        filled = oracle.official_shop_unlock(seed=5, filled=(0, 0), engine=engine)
        self.assertEqual((base, filled), ("PIZZA_SHOP", "BRUNCH_SPOT"))

    def test_exact_engine_same_total_split_has_same_public_shop(self):
        engine = oracle.load_authenticated_engine()
        for seed in range(1, 65):
            self.assertEqual(
                oracle.official_shop_unlock(seed=seed, filled=(0, 0), engine=engine),
                oracle.official_shop_unlock(seed=seed, filled=(1, 0), engine=engine),
            )

    def test_no_unlock_on_non_interval_day(self):
        engine = oracle.load_authenticated_engine()
        self.assertIsNone(oracle.official_shop_unlock(seed=5, day=1, engine=engine))

    def test_512_seed_exact_engine_sweep(self):
        report = oracle.build_report()
        result = report["result"]
        self.assertEqual(result["cells"], 512)
        self.assertEqual(result["shop_changed"], 337)
        self.assertEqual(result["shop_unchanged"], 175)
        self.assertEqual(result["model_mismatches"], 0)
        self.assertEqual(result["same_total_farm_placement_mismatches"], 0)
        self.assertEqual(
            result["first_witnesses"][0],
            {
                "seed": 5,
                "all_empty": "PIZZA_SHOP",
                "one_static_tile": "BRUNCH_SPOT",
            },
        )

    def test_strict_integer_contract_rejects_bool_and_negative(self):
        for bad in (True, -1, 1.0, "1"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    oracle.shop_after_vacancy_draws(
                        seed=bad, day=2, empty_tiles_by_farm=(25, 25)
                    )
        with self.assertRaises(ValueError):
            oracle.shop_after_vacancy_draws(
                seed=5, day=2, empty_tiles_by_farm=(25, True)
            )

    def test_cli_report_is_strict_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "report.json"
            self.assertEqual(
                oracle._main(["--first-seed", "5", "--last-seed", "5", "--output", str(path)]),
                0,
            )
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"]["cells"], 1)
            self.assertEqual(payload["result"]["shop_changed"], 1)


if __name__ == "__main__":
    unittest.main()
