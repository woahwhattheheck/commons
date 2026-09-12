import json
import tempfile
import unittest
from pathlib import Path

import compare_episode_extracts as mod


HASHES = {
    "farmer_actions": "1" * 64,
    "market_orders": "2" * 64,
    "matches_meta": "3" * 64,
}


def payload(
    episode,
    *,
    max_step=719,
    farmer=None,
    market=None,
    tail=None,
    hash_suffix=None,
):
    hashes = dict(HASHES)
    if hash_suffix is not None:
        hashes["market_orders"] = hash_suffix * 64
    return {
        "schema": mod.INPUT_SCHEMA,
        "episode": str(episode),
        "inputs": {
            name: {
                "path": f"/data/{name}.csv",
                "bytes": 100 + i,
                "sha256": hashes[name],
            }
            for i, name in enumerate(mod.SOURCE_NAMES)
        },
        "coverage": {"max_step": max_step},
        "farmer_summary": farmer or [],
        "market_summary": market or [],
        "tail": {
            "requested_callbacks": 96,
            "start_step": max_step - 95 if max_step is not None else None,
            "events": tail or [],
        },
    }


class CompareTests(unittest.TestCase):
    def test_recurrence_is_descriptive_and_relative_tail(self):
        farmer_a = [
            {"player": "0", "day": 29, "verb": "HARVEST", "target": "WOOL", "rows": 4},
            {"player": "0", "day": 28, "verb": "CARE", "target": "SHEEP", "rows": 1},
        ]
        farmer_b = [
            {"player": "0", "day": 29, "verb": "HARVEST", "target": "WOOL", "rows": 7},
        ]
        market_a = [
            {
                "player": "0", "day": 29, "verb": "SELL", "item": "WOOL",
                "rows": 2, "explicit_qty_sum": 10,
            }
        ]
        market_b = [
            {
                "player": "0", "day": 29, "verb": "SELL", "item": "WOOL",
                "rows": 3, "explicit_qty_sum": 12,
            }
        ]
        tail_a = [
            {
                "kind": "market_order", "row_index": 99, "step": 718,
                "player_raw": "0", "verb": "SELL", "item": "WOOL",
                "qty": 5, "qty_raw": "5",
            }
        ]
        tail_b = [
            {
                "kind": "market_order", "row_index": 11, "step": 598,
                "player_raw": "0", "verb": "SELL", "item": "WOOL",
                "qty": 5, "qty_raw": "5",
            }
        ]

        report = mod.compare_extracts(
            [
                payload("a", max_step=719, farmer=farmer_a, market=market_a, tail=tail_a),
                payload("b", max_step=599, farmer=farmer_b, market=market_b, tail=tail_b),
            ]
        )

        self.assertEqual(report["schema"], mod.OUTPUT_SCHEMA)
        self.assertEqual(report["episodes"], ["a", "b"])
        self.assertEqual(len(report["repeated_farmer_summary"]), 1)
        self.assertEqual(
            [row["rows"] for row in report["repeated_farmer_summary"][0]["episodes"]],
            [4, 7],
        )
        self.assertEqual(len(report["repeated_market_summary"]), 1)
        self.assertEqual(
            report["repeated_market_summary"][0]["episodes"][1]["explicit_qty_sum"], 12
        )
        self.assertEqual(len(report["repeated_tail_events"]), 1)
        self.assertEqual(report["repeated_tail_events"][0]["relative_step"], -1)
        self.assertNotIn("CARE", json.dumps(report["repeated_farmer_summary"]))

    def test_min_three_requires_three_episode_recurrence(self):
        shared = [{"player": "1", "day": 10, "verb": "FEED", "target": "SHEEP", "rows": 1}]
        other = [{"player": "1", "day": 10, "verb": "CARE", "target": "SHEEP", "rows": 1}]
        report = mod.compare_extracts(
            [
                payload("1", farmer=shared),
                payload("2", farmer=shared),
                payload("3", farmer=other),
            ],
            min_episodes=3,
        )
        self.assertEqual(report["repeated_farmer_summary"], [])

    def test_source_snapshot_mismatch_fails_closed(self):
        with self.assertRaisesRegex(mod.CompareError, "source snapshot mismatch"):
            mod.compare_extracts([payload("1"), payload("2", hash_suffix="4")])

    def test_duplicate_episode_ids_fail_closed(self):
        with self.assertRaisesRegex(mod.CompareError, "unique"):
            mod.compare_extracts([payload("1"), payload("1")])

    def test_malformed_sha_fails_closed(self):
        bad = payload("1")
        bad["inputs"]["farmer_actions"]["sha256"] = "xyz"
        with self.assertRaisesRegex(mod.CompareError, "lowercase sha256"):
            mod.compare_extracts([bad, payload("2")])

    def test_bool_summary_count_is_rejected(self):
        bad = payload(
            "1",
            farmer=[
                {"player": "0", "day": 0, "verb": "FEED", "target": "COW", "rows": True}
            ],
        )
        with self.assertRaisesRegex(mod.CompareError, "plain integer"):
            mod.compare_extracts([bad, payload("2")])

    def test_tail_without_numeric_max_step_not_claimed_recurrent(self):
        event = {
            "kind": "farmer_action", "row_index": 1, "step": 10,
            "player_raw": "0", "verb": "PASS", "target": None,
            "qty": None, "qty_raw": None,
        }
        report = mod.compare_extracts(
            [payload("1", max_step=None, tail=[event]), payload("2", max_step=None, tail=[event])]
        )
        self.assertEqual(report["repeated_tail_events"], [])

    def test_duplicate_json_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "bad.json"
            path.write_text('{"schema":"a","schema":"b"}', encoding="utf-8")
            with self.assertRaisesRegex(mod.CompareError, "duplicate JSON key"):
                mod.load_extract(path)

    def test_cli_round_trip_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            one = root / "1.json"
            two = root / "2.json"
            out = root / "out.json"
            shared = [
                {"player": "0", "day": 3, "verb": "WATER", "target": "TOMATO", "rows": 2}
            ]
            one.write_text(json.dumps(payload("1", farmer=shared)), encoding="utf-8")
            two.write_text(json.dumps(payload("2", farmer=shared)), encoding="utf-8")
            self.assertEqual(mod.main([str(one), str(two), "--output", str(out)]), 0)
            first = out.read_bytes()
            self.assertEqual(mod.main([str(one), str(two), "--output", str(out)]), 0)
            self.assertEqual(out.read_bytes(), first)


if __name__ == "__main__":
    unittest.main()
