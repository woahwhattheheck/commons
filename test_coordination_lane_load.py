import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(__file__)
SPEC = importlib.util.spec_from_file_location("lane_load", os.path.join(HERE, "host", "coordination_lane_load.py"))
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)

NOW = dt.datetime(2026, 9, 11, 14, 0, tzinfo=dt.timezone.utc)


def lanes(*rows):
    return {"schema": mod.LANES_SCHEMA, "observed_at": "2026-09-11T13:59:00Z", "lanes": list(rows)}


def lane(name="lane-10", chain=(10, 11), cks=("abcdef1234567890",), families=("FOO-BAR-01",)):
    return {"lane": name, "canonical": chain[-1], "state": "OPEN", "open": [chain[-1]],
            "chain": list(chain), "content_keys": list(cks), "families": list(families),
            "title": name}


def holding(key, holder="A", beat="2026-09-11T13:55:00Z", state="HELD", live=True, ttl_s=1800):
    return {"key": key, "holder": holder, "heartbeat_at": beat, "ttl_s": ttl_s,
            "state": state, "live": live, "note": ""}


def holdings(*rows):
    return {"branch": "state/claims", "tip": "f" * 40, "holdings": list(rows)}


class LaneLoadTests(unittest.TestCase):
    def reduce(self, lane_doc, holding_doc, **kw):
        return mod.reduce_lane_load(lane_doc, holding_doc, now=NOW, **kw)

    def row(self, result, name="lane-10"):
        return next(r for r in result["lanes"] if r["lane"] == name)

    def test_content_key_maps_and_counts(self):
        row = self.row(self.reduce(lanes(lane()), holdings(holding("ck-abcdef1234567890"))))
        self.assertEqual(row["active_count"], 1)
        self.assertEqual(row["active_holders"], ["A"])
        self.assertEqual(row["matched_keys"][0]["via"], "content")

    def test_pr_key_maps(self):
        row = self.row(self.reduce(lanes(lane()), holdings(holding("pr-11"))))
        self.assertEqual(row["active_count"], 1)
        self.assertEqual(row["matched_keys"][0]["via"], "pr")

    def test_marker_family_maps_using_change_key_normalization(self):
        row = self.row(self.reduce(lanes(lane()), holdings(holding("foo-bar-01"))))
        self.assertEqual(row["active_count"], 1)
        self.assertEqual(row["matched_keys"][0]["via"], "family")

    def test_unique_holder_count_not_key_count(self):
        doc = holdings(holding("pr-10", "A"), holding("ck-abcdef1234567890", "A"),
                       holding("foo-bar-01", "B"))
        row = self.row(self.reduce(lanes(lane()), doc))
        self.assertEqual(row["active_count"], 2)
        self.assertEqual(row["active_holders"], ["A", "B"])

    def test_window_excludes_old_or_released_rows(self):
        doc = holdings(holding("pr-10", "old", beat="2026-09-11T13:40:00Z"),
                       holding("pr-11", "released", state="RELEASED", live=False))
        row = self.row(self.reduce(lanes(lane()), doc, window_s=900))
        self.assertEqual(row["active_count"], 0)

    def test_expired_ttl_overrides_stale_live_true(self):
        doc = holdings(holding("pr-10", "expired", beat="2026-09-11T13:55:00Z",
                               live=True, ttl_s=60))
        row = self.row(self.reduce(lanes(lane()), doc, window_s=900))
        self.assertEqual(row["active_count"], 0)
        self.assertEqual(row["active_holders"], [])

    def test_invalid_ttl_poisons_mapped_lane(self):
        for ttl in (True, 0, "1800"):
            with self.subTest(ttl=ttl):
                row = self.row(self.reduce(lanes(lane()), holdings(holding("pr-10", ttl_s=ttl))))
                self.assertEqual(row["active_count"], mod.UNKNOWN)
                self.assertIn("ttl_s", row["problems"][0]["fields"])

    def test_incoming_fourth_warns(self):
        doc = holdings(holding("pr-10", "A"), holding("ck-abcdef1234567890", "B"),
                       holding("foo-bar-01", "C"))
        row = self.row(self.reduce(lanes(lane()), doc, incoming_holder="D"))
        self.assertEqual(row["active_count"], 3)
        self.assertEqual(row["would_be_count"], 4)
        self.assertEqual(row["signal"], "WOULD_BE_4_OR_MORE")

    def test_existing_holder_does_not_double_count_incoming(self):
        row = self.row(self.reduce(lanes(lane()), holdings(holding("pr-10", "A")), incoming_holder="A"))
        self.assertEqual(row["would_be_count"], 1)
        self.assertEqual(row["signal"], "CLEAR")

    def test_malformed_mapped_holding_poison_is_unknown_not_zero(self):
        bad = holding("pr-10")
        bad["live"] = 1
        row = self.row(self.reduce(lanes(lane()), holdings(bad)))
        self.assertEqual(row["active_count"], mod.UNKNOWN)
        self.assertEqual(row["signal"], "UNKNOWN")
        self.assertEqual(row["problems"][0]["reason"], "malformed-mapped-holding")

    def test_unreadable_shape_from_current_holders_cli_poison_is_unknown(self):
        unreadable = {"key": "pr-10", "holder": None, "state": None, "live": False,
                      "heartbeat_at": None, "ttl_s": None, "note": ""}
        row = self.row(self.reduce(lanes(lane()), holdings(unreadable)))
        self.assertEqual(row["active_count"], mod.UNKNOWN)
        self.assertTrue(row["problems"])

    def test_ambiguous_mapping_poison_each_candidate_lane(self):
        l1 = lane("lane-10", chain=(10,), cks=("abcdef12",), families=("ONE",))
        l2 = lane("lane-20", chain=(20,), cks=("abcdef1234",), families=("TWO",))
        result = self.reduce(lanes(l1, l2), holdings(holding("ck-abcdef12")))
        self.assertEqual(len(result["ambiguous_holdings"]), 1)
        self.assertEqual(self.row(result, "lane-10")["active_count"], mod.UNKNOWN)
        self.assertEqual(self.row(result, "lane-20")["active_count"], mod.UNKNOWN)

    def test_unmatched_is_visible_without_poisoning_other_lanes(self):
        result = self.reduce(lanes(lane()), holdings(holding("pr-999")))
        self.assertEqual(self.row(result)["active_count"], 0)
        self.assertEqual(result["unmatched_holdings"][0]["key"], "pr-999")

    def test_future_heartbeat_is_unknown(self):
        row = self.row(self.reduce(lanes(lane()), holdings(holding("pr-10", beat="2026-09-11T14:01:00Z"))))
        self.assertEqual(row["active_count"], mod.UNKNOWN)
        self.assertEqual(row["problems"][0]["reason"], "future-heartbeat")

    def test_strict_integer_settings_reject_bool(self):
        with self.assertRaises(mod.InputError):
            self.reduce(lanes(lane()), holdings(), window_s=True)
        with self.assertRaises(mod.InputError):
            self.reduce(lanes(lane()), holdings(), warn_at=False)

    def test_schema_and_duplicate_lane_ids_fail_closed(self):
        with self.assertRaises(mod.InputError):
            self.reduce({"schema": "wrong", "lanes": []}, holdings())
        with self.assertRaises(mod.InputError):
            self.reduce(lanes(lane(), lane()), holdings())

    def test_cli_replay(self):
        with tempfile.TemporaryDirectory() as td:
            lp = os.path.join(td, "lanes.json")
            hp = os.path.join(td, "holdings.json")
            with open(lp, "w", encoding="utf-8") as fh:
                json.dump(lanes(lane()), fh)
            with open(hp, "w", encoding="utf-8") as fh:
                json.dump(holdings(holding("pr-10", "A"), holding("foo-bar-01", "B")), fh)
            done = subprocess.run([sys.executable, os.path.join(HERE, "host", "coordination_lane_load.py"),
                                   "--lanes", lp, "--holdings", hp, "--holder", "C",
                                   "--now", "2026-09-11T14:00:00Z"],
                                  text=True, capture_output=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            payload = json.loads(done.stdout)
            self.assertEqual(payload["schema"], mod.OUT_SCHEMA)
            self.assertEqual(payload["lanes"][0]["would_be_count"], 3)


if __name__ == "__main__":
    unittest.main()
