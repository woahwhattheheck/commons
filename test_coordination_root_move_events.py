import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(__file__)
SPEC = importlib.util.spec_from_file_location("root_moves", os.path.join(HERE, "host", "coordination_root_move_events.py"))
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

A = "a" * 40
B = "b" * 40
C = "c" * 40
D = "d" * 40


def row(n, status, base="main", lane=None, head=None):
    out = {"number": n, "base_ref": base, "head": head or ("1" * 39 + str(n % 10)),
           "drift": {"status": status}}
    if lane is not None:
        out["lane"] = lane
    return out


def snap(at, tips, rows):
    rows = list(rows)
    return {"schema": mod.STATE_SCHEMA, "observed_at": at, "tips": dict(tips), "prs": rows,
            "counts": {"open_prs": len(rows), "listed_open": len(rows)}, "degraded": []}


class RootMoveTests(unittest.TestCase):
    def test_unchanged_root_emits_nothing(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [row(1, "current")])
        c = snap("2026-09-11T13:01:00Z", {"main": A}, [row(1, "current")])
        out = mod.reduce_root_moves(p, c)
        self.assertEqual(out["roots"], [])
        self.assertEqual(out["events"], [])

    def test_disjoint_is_safe(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B}, [row(1, "disjoint")])
        e = mod.reduce_root_moves(p, c)["events"][0]
        self.assertEqual(e["state"], "DISJOINT_OK")

    def test_current_after_rebind_is_safe(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B}, [row(1, "current")])
        self.assertEqual(mod.reduce_root_moves(p, c)["events"][0]["state"], "DISJOINT_OK")

    def test_contained_is_safe(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B}, [row(1, "contained")])
        self.assertEqual(mod.reduce_root_moves(p, c)["events"][0]["state"], "DISJOINT_OK")

    def test_overlap_requires_rebind(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B}, [row(1, "overlap")])
        self.assertEqual(mod.reduce_root_moves(p, c)["events"][0]["state"], "REBIND_REQUIRED")

    def test_multi_pr_lane_any_overlap_requires_rebind(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B},
                 [row(1, "disjoint", lane="lane-1"), row(2, "overlap", lane="lane-1")])
        events = mod.reduce_root_moves(p, c)["events"]
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["members"], [1, 2])
        self.assertEqual(events[0]["state"], "REBIND_REQUIRED")

    def test_unknown_drift_never_becomes_safe(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B}, [row(1, "unknown")])
        self.assertEqual(mod.reduce_root_moves(p, c)["events"][0]["state"], mod.UNKNOWN)

    def test_missing_drift_object_becomes_unknown(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [])
        r = row(1, "current")
        del r["drift"]
        c = snap("2026-09-11T13:01:00Z", {"main": B}, [r])
        self.assertEqual(mod.reduce_root_moves(p, c)["events"][0]["state"], mod.UNKNOWN)

    def test_unknown_root_endpoint_poison(self):
        p = snap("2026-09-11T13:00:00Z", {"main": mod.UNKNOWN}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B}, [row(1, "disjoint")])
        out = mod.reduce_root_moves(p, c)
        self.assertEqual(out["roots"][0]["state"], mod.UNKNOWN)
        self.assertEqual(out["events"][0]["state"], mod.UNKNOWN)

    def test_multiple_roots_are_scoped(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A, "titan/v3.1": C}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B, "titan/v3.1": D},
                 [row(1, "disjoint"), row(2, "overlap", base="titan/v3.1")])
        out = mod.reduce_root_moves(p, c)
        states = {(e["base_ref"], e["state"]) for e in out["events"]}
        self.assertEqual(states, {("main", "DISJOINT_OK"), ("titan/v3.1", "REBIND_REQUIRED")})

    def test_singletons_get_stable_pr_lane(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B}, [row(77, "disjoint")])
        self.assertEqual(mod.reduce_root_moves(p, c)["events"][0]["lane"], "pr-77")

    def test_duplicate_pr_numbers_fail_closed(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B}, [row(1, "disjoint"), row(1, "disjoint")])
        with self.assertRaises(mod.InputError):
            mod.reduce_root_moves(p, c)

    def test_non_monotonic_snapshots_fail_closed(self):
        p = snap("2026-09-11T13:01:00Z", {"main": A}, [])
        c = snap("2026-09-11T13:00:00Z", {"main": B}, [])
        with self.assertRaises(mod.InputError):
            mod.reduce_root_moves(p, c)

    def test_invalid_sha_fails_closed(self):
        p = snap("2026-09-11T13:00:00Z", {"main": "abc"}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B}, [])
        with self.assertRaises(mod.InputError):
            mod.reduce_root_moves(p, c)

    def test_partial_current_open_listing_cannot_emit_disjoint_ok(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B},
                 [row(1, "disjoint", lane="lane-1")])
        c["degraded"] = ["open-listing-partial"]
        c["counts"] = {"open_prs": 2, "listed_open": 1}
        with self.assertRaisesRegex(mod.InputError, "listing is partial"):
            mod.reduce_root_moves(p, c)

    def test_mismatched_current_open_counts_fail_closed(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B}, [row(1, "disjoint")])
        c["counts"]["open_prs"] = 2
        with self.assertRaisesRegex(mod.InputError, "listing incomplete"):
            mod.reduce_root_moves(p, c)

    def test_declared_complete_counts_must_match_listed_rows(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B}, [row(1, "disjoint", lane="lane-1")])
        c["counts"] = {"open_prs": 2, "listed_open": 2}
        with self.assertRaisesRegex(mod.InputError, "observed_rows=1"):
            mod.reduce_root_moves(p, c)

    def test_current_open_counts_reject_bool_coercion(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B}, [row(1, "disjoint")])
        c["counts"]["open_prs"] = True
        with self.assertRaisesRegex(mod.InputError, "exact integer"):
            mod.reduce_root_moves(p, c)

    def test_counts_bind_event_states(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B},
                 [row(1, "disjoint"), row(2, "overlap"), row(3, "unknown")])
        counts = mod.reduce_root_moves(p, c)["counts"]
        self.assertEqual(counts["disjoint_ok"], 1)
        self.assertEqual(counts["rebind_required"], 1)
        self.assertEqual(counts["unknown"], 1)

    def test_cli_replay(self):
        p = snap("2026-09-11T13:00:00Z", {"main": A}, [])
        c = snap("2026-09-11T13:01:00Z", {"main": B}, [row(1, "disjoint")])
        with tempfile.TemporaryDirectory() as td:
            pp = os.path.join(td, "prev.json")
            cp = os.path.join(td, "cur.json")
            with open(pp, "w", encoding="utf-8") as fh:
                json.dump(p, fh)
            with open(cp, "w", encoding="utf-8") as fh:
                json.dump(c, fh)
            done = subprocess.run([sys.executable, os.path.join(HERE, "host", "coordination_root_move_events.py"),
                                   "--previous", pp, "--current", cp],
                                  text=True, capture_output=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            payload = json.loads(done.stdout)
            self.assertEqual(payload["schema"], mod.OUT_SCHEMA)
            self.assertEqual(payload["events"][0]["state"], "DISJOINT_OK")


if __name__ == "__main__":
    unittest.main()
