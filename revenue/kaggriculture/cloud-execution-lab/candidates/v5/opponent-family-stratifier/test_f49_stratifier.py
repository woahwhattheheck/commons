import copy
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import f49_stratifier as s


def action(farmer=None, hands=None, market=None, **extra):
    row = {"farmer": farmer or [], "hands": hands or [], "market": market or []}
    row.update(extra)
    return row


def trace(kind, n=90):
    out = []
    for i in range(n):
        if kind == "farmer":
            out.append(action(farmer=[{"op": "MOVE", "x": 1 + i % 2}]))
        elif kind == "hands":
            out.append(action(hands=[{"op": "DROP", "slot": i % 3}]))
        elif kind == "market":
            out.append(action(market=[{"op": "SELL", "qty": 1 + i % 2}]))
        elif kind == "late":
            out.append(action(market=[{"op": "SELL"}]) if i >= 60 else action())
        elif kind == "sparse":
            out.append(action(farmer=[{"op": "WAIT"}]) if i % 5 == 0 else action())
        else:
            out.append(action(farmer=[{"op": "MOVE"}]) if i % 3 == 0 else action(market=[{"op": "SELL"}]))
    return out


class F49Tests(unittest.TestCase):
    def test_feature_vector_rejects_identity_fields(self):
        with self.assertRaises(ValueError):
            s.feature_vector([action(team_name="leak")])
        with self.assertRaises(ValueError):
            s.feature_vector([action(submission_id=123)])
        with self.assertRaises(ValueError):
            s.feature_vector([action(market=[{"op": "SELL", "meta": {"team_name": "nested-leak"}}])])

    def test_numeric_magnitude_does_not_change_shape(self):
        a = s.feature_vector([action(market=[{"op": "SELL", "qty": 1}]) for _ in range(30)])
        b = s.feature_vector([action(market=[{"op": "SELL", "qty": 999999}]) for _ in range(30)])
        self.assertEqual(a, b)

    def test_phase_signal_detects_late_liquidation(self):
        v = s.feature_vector(trace("late"))
        self.assertGreater(v["skew.market_late_minus_early"], 0.8)
        self.assertEqual(s.phenotype(v), "late-liquidator")

    def test_build_model_is_key_identity_invariant(self):
        kinds = ["farmer"] * 4 + ["hands"] * 4 + ["market"] * 4 + ["late"] * 4 + ["sparse"] * 4
        rows = []
        for i, kind in enumerate(kinds):
            base = s.feature_vector(trace(kind))
            rows.append({"key": f"sub-{i}", "vectors": [base, copy.deepcopy(base), copy.deepcopy(base)]})
        a = s.build_model(rows, k=5, min_support=3)
        poisoned = copy.deepcopy(rows)
        for i, row in enumerate(poisoned):
            row["key"] = f"completely-different-identity-{999-i}"
        b = s.build_model(poisoned, k=5, min_support=3)
        self.assertEqual(
            [(x["family_id"], x["phenotype"], x["support_targets"], x["medoid"]) for x in a["families"]],
            [(x["family_id"], x["phenotype"], x["support_targets"], x["medoid"]) for x in b["families"]],
        )

    def test_holdout_stability_and_support(self):
        kinds = ["farmer"] * 4 + ["hands"] * 4 + ["market"] * 4
        rows = []
        for i, kind in enumerate(kinds):
            v = s.feature_vector(trace(kind))
            rows.append({"key": str(i), "vectors": [v, copy.deepcopy(v), copy.deepcopy(v)]})
        model = s.build_model(rows, k=3, min_support=3)
        self.assertEqual(model["held_out"]["exact_family_matches"], 12)
        self.assertEqual(model["held_out"]["abstentions"], 0)
        self.assertTrue(all(f["status"] == "ACTIVE" for f in model["families"]))
        self.assertTrue(model["runtime_policy"]["unknown_is_noop"])
        self.assertFalse(model["runtime_policy"]["candidate_policy_modified"])

    def test_ambiguous_holdout_abstains(self):
        rows = []
        for i, kind in enumerate(["farmer"] * 4 + ["market"] * 4):
            v = s.feature_vector(trace(kind))
            rows.append({"key": str(i), "vectors": [v, copy.deepcopy(v), copy.deepcopy(v)]})
        farmer = s.feature_vector(trace("farmer"))
        market = s.feature_vector(trace("market"))
        midpoint = {k: (farmer[k] + market[k]) / 2 for k in farmer}
        rows[0]["vectors"][-1] = midpoint
        model = s.build_model(rows, k=2, min_support=3)
        self.assertGreaterEqual(model["held_out"]["abstentions"], 1)

    def test_fixture_digest_and_path_are_enforced(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            replay = {"info": {"seed": 7}, "statuses": ["DONE", "DONE"], "steps": []}
            for step in range(4):
                replay["steps"].append([
                    {"action": action(farmer=[{"op": "MOVE"}])},
                    {"action": action(market=[{"op": "SELL"}])},
                ])
            raw = gzip.compress(json.dumps(replay).encode())
            p = root / "r.json.gz"; p.write_bytes(raw)
            fixture = {"path": "r.json.gz", "sha256": hashlib.sha256(raw).hexdigest(), "seed": 7, "recorded_opponent_seat": 1}
            actions = s.read_fixture(root, fixture)
            self.assertEqual(len(actions), 3)
            bad = dict(fixture); bad["sha256"] = "0" * 64
            with self.assertRaises(ValueError):
                s.read_fixture(root, bad)

    def test_runtime_geometry_contains_no_leaderboard_inputs(self):
        v = s.feature_vector(trace("market"))
        for forbidden in s.IDENTITY_FORBIDDEN:
            self.assertNotIn(forbidden, " ".join(v.keys()).lower())


if __name__ == "__main__":
    unittest.main()
