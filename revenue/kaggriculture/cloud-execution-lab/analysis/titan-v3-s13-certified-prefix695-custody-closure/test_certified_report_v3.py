# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import certified_report_v3 as v3

CONTROL_SHA = "1" * 64
UNSAFE_SHA = "2" * 64
CERTIFIED_SHA = "3" * 64
OPPONENT_SHA = "4" * 64
LOADER_SHA = "5" * 64
ENGINE_SHA = "6" * 64


def diagnostics(*, source_seat=0, steps=(), checks=None, matches=None, handoff_step=696):
    steps = list(steps)
    if matches is None:
        matches = len(steps)
    if checks is None:
        checks = matches
    return {
        "mode": "post24_full",
        "certificate_mode": "full",
        "source_seat": source_seat,
        "start_step": 24,
        "active": handoff_step is None,
        "handoff_step": handoff_step,
        "handoff_reason": None if handoff_step is None else "missing_route_row",
        "certificate_checks": checks,
        "certificate_matches": matches,
        "activation_count": len(steps),
        "activation_steps": steps,
        "certificate_donor_head": "cbfff2bec813e2c2609ce9c5819b74669e98c566",
        "certificate_donor_blob": "89a3325eb541ae0e8a81e1e0a426292820f10d98",
        "market_outcome_claim": False,
    }


def game(opponent, seed, seat, scores, trace, runtime_diagnostics=None, *, steps=4, episode_steps=720):
    actors = [{}, {}]
    if runtime_diagnostics is not None:
        actors[seat]["agent_diagnostics"] = runtime_diagnostics
    return {
        "status": "complete",
        "failure": None,
        "opponent": opponent,
        "seed": seed,
        "candidate_seat": seat,
        "scores": scores,
        "trace_sha256": trace,
        "steps": steps,
        "episode_steps": episode_steps,
        "actors": actors,
    }


def evaluator_report(*, candidate_sha, evaluator_sha, games):
    return {
        "schema_version": 1,
        "invocation_id": "fixture",
        "engine_ref": v3.ENGINE_REF,
        "engine_sha256": {"kaggriculture.py": ENGINE_SHA},
        "loader_sha256": LOADER_SHA,
        "evaluator_sha256": evaluator_sha,
        "candidate": {"entry": "candidate.py", "callable": "agent", "sha256": candidate_sha},
        "opponents": {
            "arlene": {"entry": "arlene.py", "callable": "agent", "sha256": OPPONENT_SHA},
        },
        "seeds": [1],
        "agent_rng_seed": 20260913,
        "python": "3.11-fixture",
        "platform": "linux",
        "resource_usage": {},
        "limits": {
            "action_rpc_seconds": 1.0,
            "startup_seconds": 15,
            "game_seconds_between_steps": 180,
            "remaining_overage_time": 0,
        },
        "method": "fixture with official-driver provenance shape",
        "summary": {},
        "games": games,
        "reproducibility": None,
    }


class AuthenticatedReportV3Tests(unittest.TestCase):
    def fixture(self):
        base_evaluator = v3.sha256(v3.BASE_EVALUATOR)
        diagnostic_evaluator = v3.sha256(v3.DIAGNOSTIC_EVALUATOR)
        control = evaluator_report(
            candidate_sha=CONTROL_SHA,
            evaluator_sha=base_evaluator,
            games=[
                game("arlene", 1, 0, [100, 90], "c0"),
                game("arlene", 1, 1, [90, 100], "c1"),
            ],
        )
        unsafe = evaluator_report(
            candidate_sha=UNSAFE_SHA,
            evaluator_sha=base_evaluator,
            games=[
                game("arlene", 1, 0, [120, 90], "u0"),
                game("arlene", 1, 1, [90, 120], "u1"),
            ],
        )
        certified = evaluator_report(
            candidate_sha=CERTIFIED_SHA,
            evaluator_sha=diagnostic_evaluator,
            games=[
                game(
                    "arlene",
                    1,
                    0,
                    [110, 90],
                    "g0",
                    diagnostics(steps=[1], checks=1, matches=1),
                ),
                game(
                    "arlene",
                    1,
                    1,
                    [90, 100],
                    "c1",
                    diagnostics(steps=[], checks=0, matches=0, handoff_step=0),
                ),
            ],
        )
        return control, unsafe, certified

    def write(self, root, name, value):
        path = root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def build(self, root, control, unsafe, certified):
        return v3.build_report(
            self.write(root, "control.json", control),
            self.write(root, "unsafe.json", unsafe),
            self.write(root, "certified.json", certified),
            source_seat=0,
            expected_control_candidate_sha256=CONTROL_SHA,
            expected_unsafe_candidate_sha256=UNSAFE_SHA,
            expected_certified_candidate_sha256=CERTIFIED_SHA,
            expected_seeds=[1],
            expected_opponents=["arlene"],
        )

    def test_valid_authenticated_report_survives(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = self.build(root, *self.fixture())
            self.assertEqual(result["schema"], v3.SCHEMA)
            self.assertEqual(result["verdict"], "CERTIFIED_SURVIVOR")
            self.assertTrue(result["source_seat_activated"])
            self.assertEqual(len(result["authenticated_provenance"]["sha256"]), 64)

    def test_games_only_report_cannot_authenticate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control, unsafe, certified = self.fixture()
            certified = {"games": certified["games"]}
            with self.assertRaisesRegex(v3.AuthenticatedReportError, "schema_version"):
                self.build(root, control, unsafe, certified)

    def test_wrong_candidate_fingerprint_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control, unsafe, certified = self.fixture()
            certified["candidate"]["sha256"] = "a" * 64
            with self.assertRaisesRegex(v3.AuthenticatedReportError, "candidate sha256 drift"):
                self.build(root, control, unsafe, certified)

    def test_wrong_diagnostic_evaluator_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control, unsafe, certified = self.fixture()
            certified["evaluator_sha256"] = v3.sha256(v3.BASE_EVALUATOR)
            with self.assertRaisesRegex(v3.AuthenticatedReportError, "evaluator_sha256 drift"):
                self.build(root, control, unsafe, certified)

    def test_cross_arm_engine_or_opponent_provenance_drift_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control, unsafe, certified = self.fixture()
            certified["engine_sha256"]["kaggriculture.py"] = "b" * 64
            with self.assertRaisesRegex(v3.AuthenticatedReportError, "provenance differs across arms"):
                self.build(root, control, unsafe, certified)

    def test_out_of_range_activation_step_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control, unsafe, certified = self.fixture()
            broken = deepcopy(certified["games"][0]["actors"][0]["agent_diagnostics"])
            broken["activation_steps"] = [4]
            broken["activation_count"] = 1
            broken["certificate_checks"] = 1
            broken["certificate_matches"] = 1
            certified["games"][0]["actors"][0]["agent_diagnostics"] = broken
            certified["games"][0]["steps"] = 4
            with self.assertRaisesRegex(v3.AuthenticatedReportError, "outside executed interval"):
                self.build(root, control, unsafe, certified)

    def test_missing_expected_cell_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            control, unsafe, certified = self.fixture()
            certified["games"].pop()
            with self.assertRaisesRegex(v3.AuthenticatedReportError, "cell bank drift"):
                self.build(root, control, unsafe, certified)


if __name__ == "__main__":
    unittest.main()
