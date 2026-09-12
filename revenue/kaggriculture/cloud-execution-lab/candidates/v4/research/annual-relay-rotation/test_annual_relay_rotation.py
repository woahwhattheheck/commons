import copy
import unittest

from annual_relay_rotation import ENGINE_GIT_BLOB, certify_relays


def fixture(crop="WHEAT", new="CARROT", day=4):
    tiles = [[None for _ in range(5)] for _ in range(5)]
    tiles[1][1] = {
        "kind": "PLANT",
        "crop": crop,
        "planted_day": 0 if crop != "MELON" else 0,
        "yield_units": 3,
        "watered_today": True,
    }
    farm = {"farmer": [1, 1], "hands": [[1, 1], [1, 1]], "tiles": tiles}
    action = {"farmer": ["HARVEST"], "hands": [["PLANT", new], ["WATER"]], "market": []}
    private = {"seeds": {"WHEAT": 2, "CARROT": 2, "MELON": 2}}
    return action, farm, private, day


class RelayTests(unittest.TestCase):
    def test_engine_pin(self):
        self.assertEqual(ENGINE_GIT_BLOB, "3c202c7ee921da239356789e266b694635103fc4")

    def test_basic_wheat_to_carrot(self):
        a, f, p, d = fixture()
        certs = certify_relays(a, f, p, day=d)
        self.assertEqual(len(certs), 1)
        c = certs[0]
        self.assertEqual((c.harvest_actor, c.plant_actor, c.water_actor), (0, 1, 2))
        self.assertEqual((c.old_crop, c.new_crop, c.harvest_units), ("WHEAT", "CARROT", 3))

    def test_unrelated_actor_between_is_allowed(self):
        a, f, p, d = fixture()
        f["hands"].insert(0, [4, 4])
        a["hands"].insert(0, ["PASS"])
        cert = certify_relays(a, f, p, day=d)[0]
        self.assertEqual((cert.harvest_actor, cert.plant_actor, cert.water_actor), (0, 2, 3))

    def test_same_tile_mutator_between_blocks(self):
        a, f, p, d = fixture()
        f["hands"].insert(0, [1, 1])
        a["hands"].insert(0, ["DIG"])
        self.assertEqual(certify_relays(a, f, p, day=d), ())

    def test_reversed_plant_water_order_blocks(self):
        a, f, p, d = fixture()
        a["hands"] = [["WATER"], ["PLANT", "CARROT"]]
        self.assertEqual(certify_relays(a, f, p, day=d), ())

    def test_immature_blocks(self):
        a, f, p, _ = fixture(day=1)
        self.assertEqual(certify_relays(a, f, p, day=1), ())

    def test_ongoing_source_crop_blocks(self):
        a, f, p, d = fixture(crop="TOMATO", day=12)
        f["tiles"][1][1]["crop"] = "TOMATO"
        self.assertEqual(certify_relays(a, f, p, day=12), ())

    def test_ongoing_target_blocks(self):
        a, f, p, d = fixture(new="TOMATO")
        self.assertEqual(certify_relays(a, f, p, day=d), ())

    def test_atomic_raw_plant_demand_blocks_all(self):
        a, f, p, d = fixture()
        # A real fourth actor asks for the same seed elsewhere; one seed is insufficient.
        f["hands"].append([4, 4])
        a["hands"].append(["PLANT", "CARROT"])
        p["seeds"]["CARROT"] = 1
        self.assertEqual(certify_relays(a, f, p, day=d), ())

    def test_bool_seed_poison_fails_closed(self):
        a, f, p, d = fixture()
        p["seeds"]["CARROT"] = True
        self.assertEqual(certify_relays(a, f, p, day=d), ())

    def test_actor_cardinality_mismatch_fails_closed(self):
        a, f, p, d = fixture()
        f["hands"].pop()
        self.assertEqual(certify_relays(a, f, p, day=d), ())

    def test_out_of_bounds_fails_closed(self):
        a, f, p, d = fixture()
        f["hands"][1] = [99, 99]
        self.assertEqual(certify_relays(a, f, p, day=d), ())

    def test_read_only(self):
        a, f, p, d = fixture()
        before = copy.deepcopy((a, f, p))
        certify_relays(a, f, p, day=d)
        self.assertEqual((a, f, p), before)

    def test_melon_mature(self):
        a, f, p, _ = fixture(crop="MELON", new="WHEAT", day=10)
        cert = certify_relays(a, f, p, day=10)[0]
        self.assertEqual((cert.old_crop, cert.new_crop), ("MELON", "WHEAT"))


if __name__ == "__main__":
    unittest.main()
