import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import p04_route_ranker as ranker
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
        "wool_vs_milk_price": "WOOL>MILK",
        "wool_vs_milk_inventory": "WOOL<MILK",
        "wheat_vs_carrot_price": "WHEAT<CARROT",
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
    return [
        group(seed, opp, seat, plan3=plan3)
        for seed in (1209131101, 1209131102)
        for opp in ("apex_v7", "arlene_v14")
        for seat in (0, 1)
    ]


def raw_rows(plan3=(10, 5), plan4=(0, 0)):
    snap = snapshot()
    digest = ranker.snapshot_sha256(snap)
    rows = []
    for seed in (1209131101, 1209131102):
        for opponent in ("apex_v7", "arlene_v14"):
            for seat in (0, 1):
                for plan in range(13):
                    delta_margin, delta_own = (0, 0)
                    if plan == 3:
                        delta_margin, delta_own = plan3
                    elif plan == 4:
                        delta_margin, delta_own = plan4
                    if plan == snap["incumbent_plan"]:
                        delta_margin, delta_own = 0, 0
                    own = 1000.0 + delta_own
                    margin = 100.0 + delta_margin
                    rows.append({
                        "seed": seed,
                        "opponent": opponent,
                        "seat": seat,
                        "forced_plan": plan,
                        "snapshot": copy.deepcopy(snap),
                        "snapshot_sha256": digest,
                        "terminal_own": own,
                        "terminal_rival": own - margin,
                        "terminal_margin": margin,
                        "failures": [],
                    })
    return rows


def git(root, *args):
    proc = subprocess.run(
        ["git", *args],
        cwd=root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout.strip()


def committed_evidence(rows):
    temp = tempfile.TemporaryDirectory()
    root = Path(temp.name)
    git(root, "init", "-b", "main")
    git(root, "config", "user.email", "p04@example.invalid")
    git(root, "config", "user.name", "P04 Test")
    path = s.EVIDENCE_PREFIX + "TEST/full-matrix.jsonl"
    target = root / path
    target.parent.mkdir(parents=True)
    target.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")
    git(root, "add", path)
    git(root, "commit", "-m", "committed route evidence")
    commit = git(root, "rev-parse", "HEAD")
    return temp, root, path, commit


class TestPreregisteredSelector(unittest.TestCase):
    def test_spec_is_narrow_and_plan2_is_impossible(self):
        self.assertNotIn(2, s.OVERRIDE_PLANS)
        self.assertEqual(s.SPEC["rule_class"]["max_predicates"], 1)
        self.assertEqual(set(s.SPEC["input"]["forbidden_identifiers"]), {"seed", "opponent", "seat", "snapshot_sha256"})
        reg = s.preregistration()
        self.assertEqual(reg["spec_sha256"], s.SPEC_SHA256)
        self.assertEqual(reg["discovery_universe_sha256"], s.DISCOVERY_UNIVERSE_SHA256)
        self.assertEqual(len(reg["discovery_universe"]["group_keys"]), 8)
        self.assertEqual(reg["accepted_evidence"]["schema"], s.EVIDENCE_SCHEMA)

    def test_safe_global_override_is_nominated_but_not_policy_ready(self):
        out = s._fit_reduced_report(report(full_groups()))
        self.assertIsNotNone(out["selected"])
        self.assertEqual(out["selected"]["rule"], {"predicate": None, "override_plan": 3})
        self.assertFalse(out["policy_ready"])
        self.assertFalse(out["composer_ready"])
        self.assertTrue(out["heldout_required"])
        self.assertEqual(out["discovery_universe_sha256"], s.DISCOVERY_UNIVERSE_SHA256)

    def test_one_negative_margin_cell_disqualifies_rule(self):
        groups = full_groups()
        groups[0]["plans"][3]["delta_margin_vs_incumbent"] = -1
        out = s._fit_reduced_report(report(groups))
        self.assertTrue(out["selected"] is None or out["selected"]["rule"]["override_plan"] != 3)

    def test_one_negative_own_cell_disqualifies_rule(self):
        groups = full_groups()
        groups[0]["plans"][3]["delta_own_vs_incumbent"] = -1
        out = s._fit_reduced_report(report(groups))
        self.assertTrue(out["selected"] is None or out["selected"]["rule"]["override_plan"] != 3)

    def test_failed_incumbent_control_disqualifies_clean_positive_override(self):
        groups = full_groups()
        groups[0]["plans"][groups[0]["incumbent_plan"]]["failures"] = ["incumbent_timeout"]
        reduced = report(groups)
        out = s._fit_reduced_report(reduced)
        self.assertTrue(out["selected"] is None or out["selected"]["rule"]["override_plan"] != 3)
        plan3 = s.evaluate_rule(
            s.validate_discovery_report(reduced),
            {"predicate": None, "override_plan": 3},
        )
        self.assertFalse(plan3["qualified"])
        self.assertEqual(plan3["candidate_failure_groups"], 0)
        self.assertEqual(plan3["incumbent_failure_groups"], 1)
        self.assertEqual(plan3["failure_groups"], 1)

    def test_conditional_rule_must_span_two_seeds_opponents_and_both_seats(self):
        groups = full_groups(plan3=(-5, -5))
        for g in groups:
            value = "WOOL>MILK" if (g["seed"] + g["seat"] + (0 if g["opponent"] == "apex_v7" else 1)) % 2 == 0 else "WOOL<MILK"
            g["features"]["wool_vs_milk_price"] = value
            if value == "WOOL>MILK":
                g["plans"][4]["delta_margin_vs_incumbent"] = 8
                g["plans"][4]["delta_own_vs_incumbent"] = 3
            else:
                g["plans"][4]["delta_margin_vs_incumbent"] = -2
                g["plans"][4]["delta_own_vs_incumbent"] = -1
        out = s._fit_reduced_report(report(groups))
        self.assertEqual(out["selected"]["rule"], {
            "predicate": {"feature": "wool_vs_milk_price", "value": "WOOL>MILK"},
            "override_plan": 4,
        })
        self.assertEqual(out["selected"]["engaged_distinct_seeds"], 2)
        self.assertEqual(out["selected"]["engaged_distinct_opponents"], 2)
        self.assertEqual(out["selected"]["engaged_distinct_seats"], 2)

    def test_single_seed_conditional_is_rejected(self):
        groups = full_groups(plan3=(-5, -5))
        for g in groups:
            g["features"]["wool_vs_milk_price"] = "WOOL>MILK" if g["seed"] == 1209131101 else "WOOL<MILK"
            if g["seed"] == 1209131101:
                g["plans"][4]["delta_margin_vs_incumbent"] = 8
                g["plans"][4]["delta_own_vs_incumbent"] = 3
            else:
                g["plans"][4]["delta_margin_vs_incumbent"] = -2
                g["plans"][4]["delta_own_vs_incumbent"] = -1
        out = s._fit_reduced_report(report(groups))
        self.assertTrue(out["selected"] is None or out["selected"]["rule"]["override_plan"] != 4)

    def test_authority_mismatch_fails_closed(self):
        r = report(full_groups())
        r["authority"]["router_source_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "authority mismatch"):
            s._fit_reduced_report(r)

    def test_policy_ready_true_input_fails_closed(self):
        r = report(full_groups())
        r["policy_ready"] = True
        with self.assertRaisesRegex(ValueError, "policy_ready=false"):
            s._fit_reduced_report(r)

    def test_incomplete_plan_rows_fail_closed(self):
        r = report(full_groups())
        r["groups"][0]["plans"].pop()
        with self.assertRaisesRegex(ValueError, "exactly 13"):
            s._fit_reduced_report(r)

    def test_duplicate_discovery_key_fails_closed(self):
        groups = full_groups()
        groups.append(copy.deepcopy(groups[0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            s._fit_reduced_report(report(groups))

    def test_partial_positive_subset_fails_preoutcome_universe_binding(self):
        groups = [
            group(1209131101, "apex_v7", 0, plan3=(10, 5)),
            group(1209131101, "apex_v7", 1, plan3=(10, 5)),
        ]
        with self.assertRaisesRegex(ValueError, "discovery universe mismatch"):
            s._fit_reduced_report(report(groups))

    def test_extra_group_fails_preoutcome_universe_binding(self):
        groups = full_groups()
        groups[-1] = group(1209131103, "arlene_v14", 1)
        with self.assertRaisesRegex(ValueError, "discovery universe mismatch"):
            s._fit_reduced_report(report(groups))

    def test_select_plan_rejects_noncanonical_snapshot_and_uses_public_features(self):
        snap = snapshot()
        rule = {"predicate": {"feature": "wool_vs_milk_price", "value": "WOOL>MILK"}, "override_plan": 3}
        self.assertEqual(s.select_plan(snap, rule), 3)
        bad = dict(snap, rival_private_inventory={"WOOL": 99})
        with self.assertRaises(ValueError):
            s.select_plan(bad, rule)

    def test_fitting_is_deterministic_under_group_order(self):
        groups = full_groups()
        left = s._fit_reduced_report(report(groups))
        right = s._fit_reduced_report(report(list(reversed(groups))))
        self.assertEqual(left["selected"], right["selected"])
        self.assertEqual(left["preregistration_spec_sha256"], right["preregistration_spec_sha256"])
        self.assertEqual(left["discovery_universe_sha256"], right["discovery_universe_sha256"])

    def test_rule_rejects_nonpreregistered_feature(self):
        with self.assertRaisesRegex(ValueError, "non-preregistered"):
            s.selected_plan_for_features({name: "X" for name in s.ALLOWED_FEATURES}, 7, {
                "predicate": {"feature": "seed", "value": 1209131101}, "override_plan": 3
            })

    def test_public_summary_interface_rejects_forged_eight_group_payload(self):
        forged = report(full_groups())
        forged["groups"][0]["features"]["shop_pair"] = "FORGED|FORGED"
        forged["groups"][0]["plans"][3]["delta_margin_vs_incumbent"] = 999999
        with self.assertRaisesRegex(ValueError, "caller-authored reduced reports are not evidence authority"):
            s.fit_selector(forged)

    def test_committed_main_ancestry_rows_are_reduced_internally(self):
        temp, root, path, commit = committed_evidence(raw_rows())
        self.addCleanup(temp.cleanup)
        out = s.fit_selector_from_committed_evidence(root, commit, [path])
        self.assertEqual(out["selected"]["rule"], {"predicate": None, "override_plan": 3})
        self.assertEqual(out["evidence"]["commit"], commit)
        self.assertEqual(out["evidence"]["rows"], 104)
        self.assertEqual(out["evidence"]["members"][0]["path"], path)
        self.assertFalse(out["policy_ready"])
        self.assertFalse(out["composer_ready"])

    def test_working_tree_tamper_cannot_change_committed_evidence(self):
        temp, root, path, commit = committed_evidence(raw_rows())
        self.addCleanup(temp.cleanup)
        before = s.fit_selector_from_committed_evidence(root, commit, [path])
        (root / path).write_text("{\"forged\":true}\n", encoding="utf-8")
        after = s.fit_selector_from_committed_evidence(root, commit, [path])
        self.assertEqual(before["selected"], after["selected"])
        self.assertEqual(before["evidence"]["members"], after["evidence"]["members"])

    def test_non_main_commit_is_rejected_as_evidence_authority(self):
        temp, root, path, commit = committed_evidence(raw_rows())
        self.addCleanup(temp.cleanup)
        git(root, "checkout", "-b", "untrusted")
        target = root / path
        target.write_text(target.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        git(root, "add", path)
        git(root, "commit", "-m", "untrusted evidence")
        untrusted = git(root, "rev-parse", "HEAD")
        self.assertNotEqual(commit, untrusted)
        with self.assertRaisesRegex(ValueError, "not an ancestor of canonical main"):
            s.fit_selector_from_committed_evidence(root, untrusted, [path])

    def test_evidence_path_must_stay_in_canonical_native_namespace(self):
        temp, root, path, commit = committed_evidence(raw_rows())
        self.addCleanup(temp.cleanup)
        with self.assertRaisesRegex(ValueError, "route-matrix-native JSONL"):
            s.load_committed_rows(root, commit, ["tmp/forged.jsonl"])


if __name__ == "__main__":
    unittest.main()
