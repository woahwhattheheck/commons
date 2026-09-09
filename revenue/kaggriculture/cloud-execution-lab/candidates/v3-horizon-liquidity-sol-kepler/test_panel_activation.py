# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from pathlib import Path
import tempfile
import textwrap
import unittest

import run_panel


FAKE_EVALUATOR = textwrap.dedent(
    '''
    import hashlib
    import json
    import time

    def encoded(value):
        return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()

    def probe(records, candidate_seat):
        initial_cpu = time.process_time()
        actors, trace = [], hashlib.sha256()
        result = {}
        interpreted = []
        try:
            for step, responses in enumerate(records):
                actions = []
                for seat, response in enumerate(responses):
                    actions.append(response["action"])
                interpreted.append(actions)
        finally:
            result["driver_cpu_seconds"] = time.process_time() - initial_cpu
        return result, interpreted
    '''
).lstrip()


def good_game(*, seat=0, digest="a" * 64):
    return {
        "seed": 11,
        "candidate_seat": seat,
        "status": "complete",
        "candidate_action_digest_schema": 1,
        "candidate_action_sha256": digest,
        "candidate_action_count": 719,
        "steps": 719,
        "episode_steps": 720,
        "actors": [{"calls": 719}, {"calls": 719}],
        "trace_sha256": "f" * 64,
    }


class CandidateActionEvaluatorPatchTests(unittest.TestCase):
    def patch(self, source=FAKE_EVALUATOR):
        directory = tempfile.TemporaryDirectory()
        path = Path(directory.name) / "evaluate.py"
        path.write_text(source, encoding="utf-8")
        receipt = run_panel.patch_candidate_action_evaluator(path)
        return directory, path, receipt

    def test_patch_hashes_only_candidate_returned_actions(self):
        directory, path, receipt = self.patch()
        try:
            namespace = {}
            patched = path.read_text(encoding="utf-8")
            exec(compile(patched, str(path), "exec"), namespace)
            same_candidate_a = [
                [{"action": {"market": [["SELL", "MILK", 1]]}}, {"action": {"town": []}}],
                [{"action": {"farm": []}}, {"action": {"town": [["HIRE", "FARMHAND", 1]]}}],
            ]
            same_candidate_b = [
                [{"action": {"market": [["SELL", "MILK", 1]]}}, {"action": {"town": [["BUY_LAND"]]}}],
                [{"action": {"farm": []}}, {"action": {"town": []}}],
            ]
            changed_candidate = [
                [{"action": {"market": [["SELL", "MILK", 2]]}}, {"action": {"town": []}}],
                [{"action": {"farm": []}}, {"action": {"town": []}}],
            ]
            first, _ = namespace["probe"](same_candidate_a, 0)
            rival_only, _ = namespace["probe"](same_candidate_b, 0)
            changed, _ = namespace["probe"](changed_candidate, 0)
            self.assertEqual(first["candidate_action_count"], 2)
            self.assertEqual(
                first["candidate_action_sha256"],
                rival_only["candidate_action_sha256"],
            )
            self.assertNotEqual(
                first["candidate_action_sha256"],
                changed["candidate_action_sha256"],
            )
            self.assertEqual(first["candidate_action_digest_schema"], 1)
            self.assertTrue(receipt["whole_trace_is_diagnostic_only"])
            self.assertNotEqual(receipt["before_sha256"], receipt["after_sha256"])
        finally:
            directory.cleanup()

    def test_patch_is_textually_before_interpreter_observation(self):
        directory, path, _ = self.patch()
        try:
            text = path.read_text(encoding="utf-8")
            self.assertLess(
                text.index("candidate_action_trace.update(candidate_action_payload)"),
                text.index("interpreted.append(actions)"),
            )
        finally:
            directory.cleanup()

    def test_patch_fails_closed_on_missing_or_duplicate_seam(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.py"
            path.write_text(FAKE_EVALUATOR.replace(run_panel._ACTION_SEAM, ""), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                run_panel.patch_candidate_action_evaluator(path)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.py"
            path.write_text(FAKE_EVALUATOR + run_panel._INIT_SEAM, encoding="utf-8")
            with self.assertRaises(RuntimeError):
                run_panel.patch_candidate_action_evaluator(path)


class CandidateActionAdmissionTests(unittest.TestCase):
    def test_evidence_gate_accepts_exact_719_of_720_receipt(self):
        key = ("arlene", 11, 0)
        gate = run_panel.add_candidate_action_gate(
            {key: good_game()}, {"valid": True, "errors": []}
        )
        self.assertTrue(gate["valid"])
        self.assertEqual(gate["candidate_action_evidence_cells"], 1)

    def test_evidence_gate_rejects_whole_trace_only_count_drift_and_bool_seat(self):
        key = ("arlene", 11, 1)
        game = good_game(seat=True)
        game.pop("candidate_action_sha256")
        game["candidate_action_count"] = 718
        gate = run_panel.add_candidate_action_gate(
            {key: game}, {"valid": True, "errors": []}
        )
        self.assertFalse(gate["valid"])
        joined = "\n".join(gate["errors"])
        self.assertIn("nonliteral candidate seat", joined)
        self.assertIn("missing candidate action digest", joined)
        self.assertIn("candidate action/step mismatch", joined)

    def test_pair_does_not_confuse_rival_or_bank_trace_with_candidate_activation(self):
        key = ("arlene", 11, 0)
        baseline = {key: good_game(digest="a" * 64)}
        candidate = {key: good_game(digest="a" * 64)}
        candidate[key]["trace_sha256"] = "e" * 64

        def inherited(_baseline, _candidate):
            return [{
                "opponent": "arlene",
                "seed": 11,
                "candidate_seat": 0,
                "trace_changed": True,
            }]

        rows = run_panel.pair_with_candidate_actions(inherited, baseline, candidate)
        self.assertTrue(rows[0]["trace_changed"])
        self.assertFalse(rows[0]["candidate_action_changed"])
        candidate[key]["candidate_action_sha256"] = "b" * 64
        rows = run_panel.pair_with_candidate_actions(inherited, baseline, candidate)
        self.assertTrue(rows[0]["candidate_action_changed"])

    def test_summary_counts_candidate_action_activation_separately(self):
        rows = [
            {"candidate_action_changed": False, "trace_changed": True},
            {"candidate_action_changed": True, "trace_changed": True},
        ]
        summary = run_panel.summarize_with_candidate_actions(
            lambda values: {"cells": len(values), "trace_changed_cells": 2}, rows
        )
        self.assertEqual(summary["candidate_action_changed_cells"], 1)
        self.assertEqual(summary["candidate_action_unchanged_cells"], 1)

    def test_verdict_rejects_positive_scores_without_candidate_action_change(self):
        def inherited(_summary, _strata):
            return {
                "decision": "ADVANCE",
                "checks": {
                    "behavior_activated": True,
                    "positive_global_own_cash": True,
                    "positive_global_margin": True,
                    "four_of_six_nonnegative_strata": True,
                    "arlene_nonnegative": True,
                    "v1_nonnegative": True,
                    "no_large_stratum_regression": True,
                },
                "scope": "test",
            }

        strata = {
            name: {"mean_own_delta": 1.0}
            for name in ("arlene", "apex", "public_bt12", "v1")
        }
        no_action = run_panel.verdict_with_candidate_actions(
            inherited,
            {"candidate_action_changed_cells": 0},
            strata,
        )
        self.assertEqual(no_action["decision"], "REJECT")
        self.assertFalse(no_action["checks"]["candidate_returned_action_activated"])
        activated = run_panel.verdict_with_candidate_actions(
            inherited,
            {"candidate_action_changed_cells": 1},
            strata,
        )
        self.assertEqual(activated["decision"], "ADVANCE")
        self.assertEqual(activated["whole_trace_role"], "diagnostic only")


if __name__ == "__main__":
    unittest.main()
