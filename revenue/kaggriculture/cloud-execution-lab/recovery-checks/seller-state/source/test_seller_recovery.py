"""Executable acceptance checks for the retained seller-state recovery case.

The actor comparisons use one historical own-observation sequence. They are not
new games, engine replays, strength evidence, or a production recovery patch.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CHECKER = Path(__file__).with_name("check_seller_recovery.py")
FIXTURE = ROOT / "seller-state-fixture.tar.gz"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_extract(target: Path) -> None:
    with tarfile.open(FIXTURE, "r:gz") as archive:
        root = target.resolve()
        for member in archive.getmembers():
            resolved = (target / member.name).resolve()
            if root not in (resolved, *resolved.parents):
                raise ValueError("fixture contains an unsafe path")
            if not member.isfile():
                raise ValueError("fixture contains a non-file member")
        for member in archive.getmembers():
            destination = target / member.name
            destination.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise ValueError("fixture member has no file body")
            destination.write_bytes(source.read())


def execute(fixture: Path, extra: list[str], expected_status: int) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "report.json"
        command = [
            sys.executable, "-B", str(CHECKER),
            "--runtime", str(fixture / "runtime"),
            "--pins", str(ROOT / "SOURCE-PINS.json"),
            "--input", str(fixture / "inputs/candidate-inputs.jsonl.gz"),
            "--receipt", str(ROOT / "inputs/ORIGINAL-INPUT-RECEIPT.json"),
            *extra, "--report", str(report),
        ]
        completed = subprocess.run(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            check=False,
        )
        if completed.returncode != expected_status:
            raise AssertionError(
                f"unexpected status {completed.returncode} != {expected_status}\n"
                f"stdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
            )
        return json.loads(report.read_text())


class SellerRecoveryAcceptance(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.temp = tempfile.TemporaryDirectory()
        cls.fixture = Path(cls.temp.name) / "fixture"
        cls.fixture.mkdir()
        safe_extract(cls.fixture)
        cls.baseline = execute(cls.fixture, ["--through", "453", "--require-continuity"], 1)
        cls.rehydrated = execute(cls.fixture, [
            "--through", "453",
            "--restore-fields", "planned,pending,previous,observed_harvests",
            "--observe-skipped", "--require-continuity",
        ], 0)
        cls.negative = execute(cls.fixture, [
            "--step", "447", "--through", "453",
            "--restore-fields", "planned,pending,previous,observed_harvests",
            "--observe-skipped", "--require-continuity",
        ], 1)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temp.cleanup()

    def test_exact_subject_and_retained_input(self) -> None:
        pins = json.loads((ROOT / "SOURCE-PINS.json").read_text())
        self.assertEqual(pins["source_ref"], "c7627b63419240e377a96fd26ee5c3933334b6eb")
        self.assertEqual(pins["source_count"], 9)
        for relative, expected in pins["sha256"].items():
            self.assertEqual(digest(self.fixture / "runtime" / relative), expected)
        receipt = json.loads((ROOT / "inputs/ORIGINAL-INPUT-RECEIPT.json").read_text())
        self.assertEqual(digest(self.fixture / "inputs/candidate-inputs.jsonl.gz"),
                         receipt["output_file_sha256"])
        self.assertEqual(receipt["observation_count"], 719)

    def test_identical_fallback_loses_two_later_sales(self) -> None:
        report = self.baseline
        self.assertEqual(report["calls_per_actor"], 454)
        self.assertTrue(report["fallback_equals_uninterrupted_action"])
        self.assertTrue(report["all_routes_equal"])
        self.assertFalse(report["continuity_preserved"])
        self.assertEqual(report["later_action_differences"], [451, 453])
        self.assertEqual(report["records"][451]["reference_action"]["market"],
                         [["SELL", "STRAWBERRY", 10]])
        self.assertEqual(report["records"][451]["affected_action"]["market"], [[]])
        self.assertEqual(report["records"][453]["reference_action"]["market"],
                         [["SELL", "MILK", 3]])
        self.assertEqual(report["records"][453]["affected_action"]["market"], [])
        self.assertEqual(report["actual_parent_events"], [
            {"parent_calls": 454, "transform_calls": 454},
            {"parent_calls": 454, "transform_calls": 453},
        ])

    def test_completed_checkpoint_plus_public_observer_restores_this_prefix(self) -> None:
        report = self.rehydrated
        self.assertTrue(report["fallback_equals_uninterrupted_action"])
        self.assertTrue(report["all_routes_equal"])
        self.assertTrue(report["continuity_preserved"])
        self.assertEqual(report["later_action_differences"], [])
        self.assertEqual(report["later_seller_state_differences"], [])
        self.assertFalse(report["intervention"]["production_repair"])

    def test_completed_checkpoint_does_not_recreate_cancelled_replanning(self) -> None:
        report = self.negative
        self.assertTrue(report["fallback_equals_uninterrupted_action"])
        self.assertFalse(report["continuity_preserved"])
        self.assertEqual(report["later_action_differences"], [449, 453])
        self.assertEqual(report["completed_prior_seller_checkpoint"]["planned"]["MILK"],
                         [[449, 3]])
        self.assertEqual(report["records"][447]["reference_seller"]["planned"]["MILK"],
                         [[453, 3]])
        self.assertFalse(report["intervention"]["production_repair"])

    def test_evidence_category_is_not_inflated(self) -> None:
        for report in (self.baseline, self.rehydrated, self.negative):
            self.assertEqual(report["new_games"], 0)
            self.assertEqual(report["engine_interpreter_calls"], 0)
            self.assertEqual(report["new_seed_reservations"], [])
            self.assertFalse(report["original_expected_actions_used_as_runtime_inputs"])
            self.assertFalse(report["original_outcomes_used_as_runtime_inputs"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
