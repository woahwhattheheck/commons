from __future__ import annotations

import copy
import sys
import unittest

import compare as predecessor
import compare_runtime_bound as subject


def runtime_report(invocation_id: str = "a" * 32) -> dict:
    return {
        "limits": dict(subject.EXPECTED_LIMITS),
        "method": subject.EXPECTED_METHOD,
        "python": sys.version,
        "platform": sys.platform,
        "invocation_id": invocation_id,
        "progress": {
            "state": "complete",
            "phase": "finalize",
            "planned_games": subject.EXPECTED_GAMES,
            "recorded_games": subject.EXPECTED_GAMES,
            "active_game": None,
        },
        "games": [
            {
                "episode_steps": subject.EXPECTED_EPISODE_STEPS,
                "steps": subject.EXPECTED_ACTION_STEPS,
            }
            for _ in range(subject.EXPECTED_GAMES)
        ],
    }


def valid_receipt() -> dict:
    return {
        "schema_version": 1,
        "operation": predecessor.OPERATION,
        "source": {
            "scheduler_git_blob_sha1": (
                "7c068b7078c3d7c09bb3836590ad42b0af934cdf"
            ),
            "closure_sha256": "1" * 64,
        },
        "ablation": {
            "kind": predecessor.EXPECTED_KIND,
            "changed_files": ["scheduler.py"],
            "scheduler_git_blob_sha1": "3" * 40,
            "closure_sha256": "2" * 64,
            "old_occurrences_before": 1,
            "old_occurrences_after": 0,
            "new_occurrences_before": 0,
            "new_occurrences_after": 1,
            "removed_scenario_names": list(
                predecessor.EXPECTED_REMOVED_SCENARIOS
            ),
            "preserved_v2_markers": {
                name: True for name in predecessor.EXPECTED_MARKERS
            },
        },
    }


def complete_report(
    invocation_id: str,
    *,
    own_delta: int,
    episode_steps: int,
    action_steps: int,
) -> dict:
    report = copy.deepcopy(predecessor.expected_report_custody())
    report.update(runtime_report(invocation_id))
    report["schema_version"] = 1
    games = []
    for opponent in ("arlene", "v1"):
        for seed in predecessor.EXPECTED_SEEDS:
            for seat in (0, 1):
                scores = [100, 100]
                scores[seat] += own_delta
                games.append(
                    {
                        "opponent": opponent,
                        "seed": seed,
                        "candidate_seat": seat,
                        "status": "complete",
                        "failure": None,
                        "episode_steps": episode_steps,
                        "steps": action_steps,
                        "scores": scores,
                        "trace_sha256": ("1" if own_delta else "0") * 64,
                        "daily_bank": [{"step": 0, "bank": [100, 100]}],
                    }
                )
    report["games"] = games
    report["progress"]["planned_games"] = len(games)
    report["progress"]["recorded_games"] = len(games)
    return report


class RuntimeCustodyContracts(unittest.TestCase):
    def test_exact_runtime_receipt_is_accepted(self):
        identity = subject.validate_runtime_custody(
            runtime_report(),
            "control",
        )
        self.assertEqual(identity["limits"], subject.EXPECTED_LIMITS)
        self.assertEqual(identity["episode_steps"], 720)
        self.assertEqual(identity["action_steps"], 719)

    def test_limits_are_value_and_type_exact(self):
        mutations = {
            "wrong_value": ("action_rpc_seconds", 2.0),
            "bool_alias": ("remaining_overage_time", False),
            "integer_float_alias": ("startup_seconds", 15),
        }
        for name, (key, value) in mutations.items():
            with self.subTest(name=name):
                report = runtime_report()
                report["limits"][key] = value
                with self.assertRaises(subject.RuntimeCustodyError):
                    subject.validate_runtime_custody(report, "control")
        report = runtime_report()
        report["limits"]["undeclared"] = 1
        with self.assertRaises(subject.RuntimeCustodyError):
            subject.validate_runtime_custody(report, "control")

    def test_method_python_and_platform_are_not_equality_only(self):
        for key in ("method", "python", "platform"):
            with self.subTest(key=key):
                report = runtime_report()
                report[key] = "same forged value in both arms"
                with self.assertRaises(subject.RuntimeCustodyError):
                    subject.validate_runtime_custody(report, "control")

    def test_final_progress_and_exact_game_count_are_required(self):
        for key, value in (
            ("state", "running"),
            ("phase", "games"),
            ("planned_games", 15),
            ("recorded_games", 15),
            ("active_game", {"seed": 1}),
        ):
            with self.subTest(key=key):
                report = runtime_report()
                report["progress"][key] = value
                with self.assertRaises(subject.RuntimeCustodyError):
                    subject.validate_runtime_custody(report, "control")
        report = runtime_report()
        report["games"].pop()
        with self.assertRaises(subject.RuntimeCustodyError):
            subject.validate_runtime_custody(report, "control")

    def test_lifecycle_is_literal_720_719_with_strict_integer_types(self):
        for key, value in (
            ("episode_steps", 2),
            ("steps", 1),
            ("episode_steps", True),
            ("steps", 719.0),
        ):
            with self.subTest(key=key, value=value):
                report = runtime_report()
                report["games"][0][key] = value
                with self.assertRaises(subject.RuntimeCustodyError):
                    subject.validate_runtime_custody(report, "control")

    def test_invocation_ids_are_valid_and_distinct(self):
        for value in (None, "", "A" * 32, "g" * 32, "0" * 31, "0" * 33):
            with self.subTest(value=value):
                report = runtime_report()
                report["invocation_id"] = value
                with self.assertRaises(subject.RuntimeCustodyError):
                    subject.validate_runtime_custody(report, "control")
        report = runtime_report("a" * 32)
        with self.assertRaises(subject.RuntimeCustodyError):
            subject.compare(
                copy.deepcopy(report),
                copy.deepcopy(report),
                {},
                git_head="f" * 40,
            )

    def test_production_predecessor_accepts_short_complete_grid_but_guard_rejects(self):
        control = complete_report(
            "a" * 32,
            own_delta=0,
            episode_steps=2,
            action_steps=1,
        )
        candidate = complete_report(
            "b" * 32,
            own_delta=1,
            episode_steps=2,
            action_steps=1,
        )
        predecessor_report = predecessor.compare(
            copy.deepcopy(control),
            copy.deepcopy(candidate),
            valid_receipt(),
            git_head="f" * 40,
        )
        self.assertEqual(predecessor_report["verdict"], "UPSIDE_SCREEN")
        self.assertEqual(predecessor_report["overall"]["cells"], 16)
        with self.assertRaises(subject.RuntimeCustodyError):
            subject.compare(
                control,
                candidate,
                valid_receipt(),
                git_head="f" * 40,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
