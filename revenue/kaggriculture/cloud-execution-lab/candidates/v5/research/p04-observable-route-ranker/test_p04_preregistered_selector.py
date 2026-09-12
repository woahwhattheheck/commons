import copy
import json
import unittest

import p04_preregistered_selector as s


def snapshot(shops=("PIZZA_SHOP", "YARN_STORE")):
    incumbent = 7 if tuple(shops) == ("PIZZA_SHOP", "YARN_STORE") else 0
    return {
        "first_two_shops": list(shops),
        "market": {
            "prices": {"WOOL": 12, "MILK": 10, "WHEAT": 7, "CARROT": 9},
            "inventory": {"WOOL": 20, "MILK": 25, "WHEAT": 30, "CARROT": 30},
        },
        "own": {"cash": 100, "worker_count": 3, "animal_counts": {"COW": 1}, "crop_counts": {"WHEAT": 2}},
        "rival": {"animal_counts": {"SHEEP": 2}, "crop_counts": {"WHEAT": 1}},
        "incumbent_plan": incumbent,
    }


def group(seed, opponent, seat, *, incumbent=7, feature_overrides=None, plan3=(10, 5), plan4=(0, 0)):
    features = {
        "shop_pair": "PIZZA_SHOP|YARN_STORE",
        "first_two_yarn_count": 1,
        "wool_vs_milk_price": "GT",
        "wool_vs_milk_inventory": "LT",
        "wheat_vs_carrot_price": "LT",
        "rival_livestock_leader": "SHEEP",
        "rival_crop_leader": "WHEAT",
    }
    if feature_overrides:
        features.update(feature_overrides)
    plans = []
    for plan in range(13):
        dm, do = (0, 0)
        if plan == 3:
            dm, do = plan3
        elif plan == 4:
            dm, do = plan4
        if plan == incumbent:
            dm, do = 0, 0
        plans.append({
            "plan": plan,
            "delta_margin_vs_incumbent": dm,
            "delta_own_vs_incumbent": do,
            "failures": [],
        })
    return {"seed": seed, "opponent": opponent, "seat": seat, "features": features, "incumbent_plan": incumbent, "plans": plans}


def report(groups):
    return {
        "schema": s.RANKER_SCHEMA,
        "authority": {
            "production_archive_sha256": s.PRODUCTION_ARCHIVE_SHA256,
            "router_source_sha256": s.ROUTER_SOURCE_SHA256,
            "source_census_commit": s.SOURCE_CENSUS_COMMIT,
            "route_step": s.ROUTE_STEP,
            "forced_terminal_plan_step": s.FINAL_PLAN_STEP,
        },
        "complete_snapshot_groups": len(groups),
        "groups": groups,
        "policy_ready": False,
    }


def full_groups(plan3=(10, 5)):
    return [group(seed, opp, seat, plan3=plan3) for seed in (1101, 1102) for opp in ("apex", "arlene") for seat in (0, 1)]


class TestPreregisteredSelector(unittest.TestCase):
    def test_spec_is_narrow_and_plan2_is_impossible(self):
        self.assertNotIn(2, s.OVERRIDE_PLANS)
        self.assertEqual(s.SPEC["rule_class"]["max_predicates"], 1)
        self.assertEqual(set(s.SPEC["input"]["forbidden_identifiers"]), {"seed", "opponent", "seat", "snapshot_sha256"})
        self.assertEqual(s.preregistration()["spec_sha256"], s.SPEC_SHA256)

    def test_safe_global_override_is_nominated_but_not_policy_ready(self):
        out = s.fit_selector(report(full_groups()))
        self.assertIsNotNone(out["selected"])
        self.assertEqual(out["selected"]["rule"], {"predicate": None, "override_plan": 3})
        self.assertFalse(out["policy_ready"])
        self.assertFalse(out["composer_ready"])
        self.assertTrue(out["heldout_required"])

    def test_one_negative_margin_cell_disqualifies_rule(self):
        groups = full_groups()
        groups[0]["plans"][3]["delta_margin_vs_incumbent"] = -1
        out = s.fit_selector(report(groups))
        self.assertTrue(out["selected"] is None or out["selected"]["rule"]["override_plan"] != 3)

    def test_one_negative_own_cell_disqualifies_rule(self):
        groups = full_groups()
        groups[0]["plans"][3]["delta_own_vs_incumbent"] = -1
        out = s.fit_selector(report(groups))
        self.assertTrue(out["selected"] is None or out["selected"]["rule"]["override_plan"] != 3)

    def test_conditional_rule_must_span_two_seeds_opponents_and_both_seats(self):
        groups = full_groups(plan3=(-5, -5))
        for g in groups:
            value = "GT" if (g["seed"] + g["seat"] + (0 if g["opponent"] == "apex" else 1)) % 2 == 0 else "LT"
            g["features"]["wool_vs_milk_price"] = value
            if value == "GT":
                g["plans"][4]["delta_margin_vs_incumbent"] = 8
                g["plans"][4]["delta_own_vs_incumbent"] = 3
            else:
                g["plans"][4]["delta_margin_vs_incumbent"] = -2
                g["plans"][4]["delta_own_vs_incumbent"] = -1
        out = s.fit_selector(report(groups))
        self.assertEqual(out["selected"]["rule"], {
            "predicate": {"feature": "wool_vs_milk_price", "value": "GT"},
            "override_plan": 4,
        })
        self.assertEqual(out["selected"]["engaged_distinct_seeds"], 2)
        self.assertEqual(out["selected"]["engaged_distinct_opponents"], 2)
        self.assertEqual(out["selected"]["engaged_distinct_seats"], 2)

    def test_single_seed_conditional_is_rejected(self):
        groups = full_groups(plan3=(-5, -5))
        for g in groups:
            g["features"]["wool_vs_milk_price"] = "GT" if g["seed"] == 1101 else "LT"
            if g["seed"] == 1101:
                g["plans"][4]["delta_margin_vs_incumbent"] = 8
                g["plans"][4]["delta_own_vs_incumbent"] = 3
            else:
                g["plans"][4]["delta_margin_vs_incumbent"] = -2
                g["plans"][4]["delta_own_vs_incumbent"] = -1
        out = s.fit_selector(report(groups))
        self.assertTrue(out["selected"] is None or out["selected"]["rule"]["override_plan"] != 4)

    def test_authority_mismatch_fails_closed(self):
        r = report(full_groups())
        r["authority"]["router_source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "authority mismatch"):
            s.fit_selector(r)

    def test_policy_ready_true_input_fails_closed(self):
        r = report(full_groups())
        r["policy_ready"] = True
        with self.assertRaisesRegex(ValueError, "policy_ready=false"):
            s.fit_selector(r)

    def test_incomplete_plan_rows_fail_closed(self):
        r = report(full_groups())
        r["groups"][0]["plans"].pop()
        with self.assertRaisesRegex(ValueError, "exactly 13"):
            s.fit_selector(r)

    def test_duplicate_discovery_key_fails_closed(self):
        groups = full_groups()
        groups.append(copy.deepcopy(groups[0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            s.fit_selector(report(groups))

    def test_select_plan_rejects_noncanonical_snapshot_and_uses_public_features(self):
        snap = snapshot()
        rule = {"predicate": {"feature": "wool_vs_milk_price", "value": "GT"}, "override_plan": 3}
        self.assertEqual(s.select_plan(snap, rule), 3)
        bad = dict(snap, rival_private_inventory={"WOOL": 99})
        with self.assertRaises(ValueError):
            s.select_plan(bad, rule)

    def test_fitting_is_deterministic_under_group_order(self):
        groups = full_groups()
        left = s.fit_selector(report(groups))
        right = s.fit_selector(report(list(reversed(groups))))
        # Input commitment changes with order, selected frozen rule does not.
        self.assertEqual(left["selected"], right["selected"])
        self.assertEqual(left["preregistration_spec_sha256"], right["preregistration_spec_sha256"])

    def test_rule_rejects_nonpreregistered_feature(self):
        with self.assertRaisesRegex(ValueError, "non-preregistered"):
            s.selected_plan_for_features({name: "X" for name in s.ALLOWED_FEATURES}, 7, {
                "predicate": {"feature": "seed", "value": 1101}, "override_plan": 3
            })


if __name__ == "__main__":
    unittest.main()
