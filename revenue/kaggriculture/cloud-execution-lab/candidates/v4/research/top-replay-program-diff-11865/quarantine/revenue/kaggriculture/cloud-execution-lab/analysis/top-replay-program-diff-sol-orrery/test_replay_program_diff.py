from __future__ import annotations

import gzip
import json
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import replay_program_diff as rpd


def farm(money: int, *, hands: int = 0, quadrants: int = 1, crop: str | None = None):
    tiles = [[None, None], [None, None]]
    if crop:
        tiles[0][0] = {"kind": "PLANT", "crop": crop, "yield_units": 1}
    return {
        "money": money,
        "tiles": tiles,
        "farmer": [0, 0],
        "hands": [[0, 0] for _ in range(hands)],
        "unlocked_quadrants": ["NW", "NE", "SW", "SE"][:quadrants],
        "hires_today": hands,
    }


def private(*, shed=None, seeds=None, carried=None):
    return {
        "shed": shed or {},
        "seeds": seeds or {},
        "inventories": [carried or {}],
    }


def obs(farms, own_private, day, hour):
    return {
        "player": 0,
        "farms": deepcopy(farms),
        "private": deepcopy(own_private),
        "market": {
            "inventory": {"WHEAT": 10000, "MELON": 10000},
            "prices": {"WHEAT": 25, "MELON": 250},
        },
        "town": {"unlocked_shops": []},
        "day": day,
        "hour": hour,
    }


def state(observation, action, *, reward=None, status="ACTIVE", name=None):
    value = {"observation": observation, "action": action, "status": status}
    if reward is not None:
        value["reward"] = reward
    if name:
        value["info"] = {"name": name}
    return value


def synthetic_replay():
    farms0 = [farm(3000), farm(3000)]
    farms1 = [farm(2040), farm(2979, hands=1)]
    farms2 = [farm(2040, crop="MELON"), farm(2979, hands=1, crop="WHEAT")]

    p0_0 = private(shed={"CARROT": 3}, seeds={"MELON": 0})
    p1_0 = private(shed={"WHEAT": 7}, seeds={"WHEAT": 0})
    p0_1 = private(shed={"CARROT": 3}, seeds={"MELON": 12})
    p1_1 = private(shed={"WHEAT": 7}, seeds={"WHEAT": 2})
    p0_2 = private(shed={"CARROT": 3}, seeds={"MELON": 11})
    p1_2 = private(shed={"WHEAT": 7}, seeds={"WHEAT": 1})

    step0 = [
        state(
            obs(farms0, p0_0, 0, 0),
            {"farmer": ["PASS"], "hands": [], "market": [["BUY_SEED", "MELON", 12]]},
        ),
        state(
            obs(farms0, p1_0, 0, 0),
            {
                "farmer": ["PASS"],
                "hands": [],
                "market": [["BUY_SEED", "WHEAT", 2], ["HIRE"]],
            },
        ),
    ]
    # Player 0 requests BUY_LAND but it fails: cash and quadrants are unchanged.
    step1 = [
        state(
            obs(farms1, p0_1, 0, 1),
            {"farmer": ["PLANT", "MELON"], "hands": [], "market": [["BUY_LAND"]]},
        ),
        state(
            obs(farms1, p1_1, 0, 1),
            {"farmer": ["PLANT", "WHEAT"], "hands": [["PASS"]], "market": []},
        ),
    ]
    step2 = [
        state(obs(farms2, p0_2, 0, 2), None, reward=2040, status="DONE", name="Bryce"),
        state(obs(farms2, p1_2, 0, 2), None, reward=2979, status="DONE", name="Apa"),
    ]
    return {"id": 107130860, "info": {"seed": 539131249}, "steps": [step0, step1, step2]}


class StrictInputTests(unittest.TestCase):
    def test_duplicate_key_rejected(self):
        with self.assertRaisesRegex(rpd.ReplayError, "duplicate JSON object key"):
            rpd.strict_json_loads('{"steps":[],"steps":[]}')

    def test_non_finite_rejected(self):
        with self.assertRaisesRegex(rpd.ReplayError, "non-finite"):
            rpd.strict_json_loads('{"x":NaN}')
        with self.assertRaisesRegex(rpd.ReplayError, "non-finite"):
            rpd.strict_json_loads('{"x":1e9999}')

    def test_envelope_unwrap(self):
        replay = synthetic_replay()
        payload = {"result": {"replay": json.dumps(replay)}}
        actual, path = rpd.unwrap_replay(payload)
        self.assertEqual(actual["id"], 107130860)
        self.assertEqual(path, ["result", "replay"])

    def test_malformed_step_cardinality_rejected(self):
        replay = synthetic_replay()
        replay["steps"][1].pop()
        with self.assertRaisesRegex(rpd.ReplayError, "exactly 2 player states"):
            rpd.analyze_replay(replay, {}, [], 0, 1)


class DifferentialTests(unittest.TestCase):
    def setUp(self):
        self.replay = synthetic_replay()
        self.report = rpd.analyze_replay(
            self.replay,
            {"input_sha256": "0" * 64},
            [],
            0,
            1,
        )

    def test_private_views_are_not_aliased(self):
        first = self.report["timeline"][0]["players"]
        self.assertEqual(first["0"]["before"]["shed"]["CARROT"], 3)
        self.assertNotIn("WHEAT", first["0"]["before"]["shed"])
        self.assertEqual(first["1"]["before"]["shed"]["WHEAT"], 7)

    def test_requested_action_is_separate_from_realized_transition(self):
        second = self.report["timeline"][1]["players"]["0"]
        self.assertIn("BUY_LAND", [event["op"] for event in second["economic_events"]])
        self.assertEqual(second["realized_delta"]["quadrants"], 0)
        self.assertEqual(second["realized_delta"]["cash"], 0)

    def test_seed_timing_and_program_delta(self):
        p0 = self.report["players"]["0"]["requested_seed_buy_to_plant_timing"]["MELON"]
        p1 = self.report["players"]["1"]["requested_seed_buy_to_plant_timing"]["WHEAT"]
        self.assertEqual(p0["lag_steps_mean"], 1)
        self.assertEqual(p0["unmatched_buy_units"], 11)
        self.assertEqual(p1["lag_steps_mean"], 1)
        delta = self.report["comparison"]["program_delta_a_minus_b"]
        self.assertEqual(delta["BUY_SEED:MELON"], 12)
        self.assertEqual(delta["BUY_SEED:WHEAT"], -2)
        self.assertEqual(delta["HIRE"], -1)

    def test_terminal_and_cash_gap(self):
        self.assertEqual(self.report["players"]["0"]["terminal"]["name"], "Bryce")
        self.assertEqual(self.report["players"]["1"]["terminal"]["name"], "Apa")
        swings = self.report["comparison"]["top_cash_gap_swings"]
        self.assertEqual(swings[0]["step"], 0)
        self.assertEqual(swings[0]["cash_gap_swing"], -939)

    def test_markdown_has_admission_boundary(self):
        text = rpd.render_markdown(self.report)
        self.assertIn("single replay can generate hypotheses", text)
        self.assertIn("BUY_SEED:MELON", text)
        self.assertIn("Requested seed buy-to-plant timing", text)


class CliTests(unittest.TestCase):
    def test_raw_and_gzip_envelope_are_identical(self):
        replay = synthetic_replay()
        envelope = {"result": {"replay": json.dumps(replay, separators=(",", ":"))}}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "replay.json"
            zipped = root / "replay.json.gz"
            raw.write_text(json.dumps(envelope), encoding="utf-8")
            zipped.write_bytes(gzip.compress(raw.read_bytes(), mtime=0))
            raw_payload, raw_prov = rpd._read_input(raw)
            zip_payload, zip_prov = rpd._read_input(zipped)
            raw_replay, raw_path = rpd.unwrap_replay(raw_payload)
            zip_replay, zip_path = rpd.unwrap_replay(zip_payload)
            raw_report = rpd.analyze_replay(raw_replay, raw_prov, raw_path, 0, 1)
            zip_report = rpd.analyze_replay(zip_replay, zip_prov, zip_path, 0, 1)
            self.assertEqual(
                raw_report["source"]["canonical_replay_sha256"],
                zip_report["source"]["canonical_replay_sha256"],
            )
            self.assertEqual(raw_path, zip_path)
            self.assertFalse(raw_prov["compressed"])
            self.assertTrue(zip_prov["compressed"])

    def test_cli_writes_machine_and_markdown_reports(self):
        replay = synthetic_replay()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "replay.json"
            output = root / "report.json"
            markdown = root / "report.md"
            source.write_text(json.dumps(replay), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(rpd.__file__)),
                    str(source),
                    "--expect-episode-id",
                    "107130860",
                    "--output-json",
                    str(output),
                    "--output-markdown",
                    str(markdown),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            parsed = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(parsed["schema"], rpd.SCHEMA)
            self.assertIn("Admission boundary", markdown.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
