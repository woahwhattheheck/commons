# SPDX-License-Identifier: Apache-2.0
"""End-to-end promotion queue tests against contract-shaped mock gates."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

PROMOTE_PY = Path(__file__).resolve().parent.parent / "promote.py"

STUB_GATE = r'''#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path


def load_rows(path):
    rows = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            key = (row["opponent"], row["seed"], row["candidate_seat"])
            if key in rows:
                raise ValueError("duplicate cell")
            rows[key] = row
    return rows


def evaluate(contract_path, evidence_path, baseline_path, candidate_path):
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    evidence = json.loads(Path(evidence_path).read_text(encoding="utf-8"))
    if evidence["provenance"] != contract["provenance"]:
        return None, 2, "INVALID: provenance drift"
    baseline = load_rows(baseline_path)
    candidate = load_rows(candidate_path)
    if set(baseline) != set(candidate):
        return None, 2, "INVALID: cell sets differ"
    deltas = [
        candidate[key]["scores"][candidate[key]["candidate_seat"]]
        - baseline[key]["scores"][baseline[key]["candidate_seat"]]
        for key in sorted(baseline)
    ]
    mean_delta = sum(deltas) / len(deltas)
    passed = mean_delta >= contract["policy"]["min_mean_own_delta"]
    verdict = "PROMOTE" if passed else "REJECT"
    report = {
        "schema_version": 1,
        "verdict": verdict,
        "valid": True,
        "panel_id": contract["panel_id"],
        "grid": {
            "seeds": contract["seeds"],
            "opponents": contract["opponents"],
            "seats": contract["seats"],
            "expected_cells": contract["expected_cells"],
        },
        "checks": [
            {
                "name": "min_mean_own_delta",
                "pass": passed,
                "detail": {"mean": mean_delta},
            }
        ],
        "metrics": {
            "aggregate": {
                "own_delta": {"mean": mean_delta, "median": mean_delta},
                "margin_delta": {"mean": mean_delta},
                "result_regressions": 0,
                "new_losses": 0,
            }
        },
    }
    return report, (0 if passed else 3), ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    try:
        report, code, error = evaluate(
            args.contract,
            args.evidence,
            args.baseline,
            args.candidate,
        )
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    if error:
        print(error, file=sys.stderr)
        return code
    Path(args.report).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
'''

STUB_DUAL_GATE = r'''#!/usr/bin/env python3
import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate as paired


def main():
    parser = argparse.ArgumentParser()
    for slot in ("predecessor-a", "predecessor-b"):
        parser.add_argument(f"--{slot}-contract", required=True)
        parser.add_argument(f"--{slot}-evidence", required=True)
        parser.add_argument(f"--{slot}-games", required=True)
        parser.add_argument(f"--{slot}-receipt", required=True)
        parser.add_argument(f"--{slot}-artifact", required=True)
    parser.add_argument("--candidate-games", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--engine-artifact", required=True)
    parser.add_argument("--runner-artifact", required=True)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()

    reports = {}
    codes = []
    for key, prefix in (
        ("predecessor_a", "predecessor_a"),
        ("predecessor_b", "predecessor_b"),
    ):
        report, code, error = paired.evaluate(
            getattr(args, f"{prefix}_contract"),
            getattr(args, f"{prefix}_evidence"),
            getattr(args, f"{prefix}_games"),
            args.candidate_games,
        )
        if error:
            print(f"{key}: {error}", file=sys.stderr)
            return 2
        reports[key] = report
        codes.append(code)
    verdict = "PROMOTE" if all(code == 0 for code in codes) else "REJECT"
    Path(args.report).write_text(
        json.dumps(
            {
                "schema_version": 1,
                "verdict": verdict,
                "comparisons": reports,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return 0 if verdict == "PROMOTE" else 3


if __name__ == "__main__":
    raise SystemExit(main())
'''


def write_panel(path: Path, own: float, rival: float = 50.0) -> None:
    rows = []
    for opponent in ("arlene", "apex"):
        for seed in (101, 102):
            for seat in (0, 1):
                scores = [rival, rival]
                scores[seat] = own
                rows.append(
                    {
                        "opponent": opponent,
                        "seed": seed,
                        "candidate_seat": seat,
                        "status": "complete",
                        "scores": scores,
                    }
                )
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def write_policy(path: Path, min_mean_own_delta: float) -> None:
    path.write_text(
        json.dumps(
            {
                "min_mean_own_delta": min_mean_own_delta,
                "min_median_own_delta": min_mean_own_delta,
                "min_mean_margin_delta": min_mean_own_delta,
                "min_positive_cell_fraction": 0.0,
                "min_positive_pair_fraction": 0.0,
                "max_result_regressions": 8,
                "max_baseline_win_regressions": 8,
                "max_new_losses": 8,
                "max_negative_opponent_strata": 2,
                "max_negative_seat_strata": 2,
                "min_worst_cell_own_delta": None,
                "require_any_change": False,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )


class MockedEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.state = self.root / "state"
        self.gate_dir = self.root / "fake-gate"
        self.gate_dir.mkdir()
        (self.gate_dir / "gate.py").write_text(STUB_GATE, encoding="utf-8")
        (self.gate_dir / "dual_predecessor_gate.py").write_text(
            STUB_DUAL_GATE,
            encoding="utf-8",
        )

        self.engine_id = self.root / "engine.json"
        self.engine_id.write_text(
            json.dumps({"engine": "stub-1.0"}),
            encoding="utf-8",
        )
        self.runner_id = self.root / "runner.json"
        self.runner_id.write_text(
            json.dumps({"runner": "stub-evaluator"}),
            encoding="utf-8",
        )
        self.control_games = self.root / "control.GAMES.jsonl"
        write_panel(self.control_games, own=100.0)
        self.control_artifact = self.root / "control.bin"
        self.control_artifact.write_bytes(b"frozen-control-bytes")
        self.land_artifact = self.root / "land.bin"
        self.land_artifact.write_bytes(b"land-bytes-different")

        config = {
            "schema_version": 1,
            "policy_version": "promotion-policy/v1",
            "engine": {
                "commit": "a" * 40,
                "identity_file": str(self.engine_id),
            },
            "runner": {
                "commit": "b" * 40,
                "identity_file": str(self.runner_id),
            },
            "slots": {
                "frozen_control": {
                    "name": "frozen-control",
                    "games": str(self.control_games),
                    "artifact_file": str(self.control_artifact),
                },
                "land": {
                    "name": "land",
                    "games": str(self.control_games),
                    "artifact_file": str(self.land_artifact),
                },
            },
        }
        self.config = self.root / "predecessors.json"
        self.config.write_text(
            json.dumps(config, sort_keys=True),
            encoding="utf-8",
        )

    def tearDown(self):
        self.tempdir.cleanup()

    def _cli(self, *argv: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [
                sys.executable,
                str(PROMOTE_PY),
                "--state-dir",
                str(self.state),
                *argv,
            ],
            capture_output=True,
            text=True,
            check=False,
        )

    def _run(self, *argv: str) -> subprocess.CompletedProcess:
        return self._cli(
            "run",
            *argv,
            "--predecessors",
            str(self.config),
            "--gate-dir",
            str(self.gate_dir),
        )

    def _submit(
        self,
        name: str,
        own: float,
        policy_delta: float,
        artifact_tag: str | None = None,
    ) -> str:
        candidate_games = self.root / f"{name}.GAMES.jsonl"
        write_panel(candidate_games, own=own)
        artifact = self.root / f"{name}.bin"
        artifact.write_bytes(f"candidate-{artifact_tag or name}".encode("utf-8"))
        policy = self.root / f"{name}.policy.json"
        write_policy(policy, policy_delta)
        process = self._cli(
            "submit",
            "--name",
            name,
            "--artifact",
            str(artifact),
            "--games",
            str(candidate_games),
            "--policy",
            str(policy),
            "--predecessors",
            str(self.config),
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        first = process.stdout.splitlines()[0]
        self.assertTrue(
            first.startswith("SUBMITTED") or first.startswith("DUPLICATE"),
            process.stdout,
        )
        return first.split()[1]

    def test_promote_path_end_to_end(self):
        submission = self._submit("good", own=110.0, policy_delta=5.0)
        process = self._run("--id", submission)
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertIn("PROMOTE", process.stdout)

        status = self._cli("status", submission)
        entry = json.loads(status.stdout)
        self.assertEqual(entry["status"], "passed")
        self.assertIsNotNone(entry["last_receipt"])

        verify = self._cli("receipt", submission, "--verify")
        self.assertEqual(verify.returncode, 0, verify.stdout)
        self.assertIn("OK", verify.stdout)

        raw = self._cli("receipt", submission)
        receipt = json.loads(raw.stdout)
        self.assertEqual(receipt["verdict"], "PROMOTE")
        self.assertEqual(len(receipt["comparisons"]), 2)
        self.assertEqual(
            {comparison["slot"] for comparison in receipt["comparisons"]},
            {"frozen_control", "land"},
        )
        self.assertTrue(
            all(
                comparison["verdict"] == "PROMOTE"
                for comparison in receipt["comparisons"]
            )
        )
        self.assertEqual(
            set(receipt["queue_pin"]["inputs"]),
            {
                "candidate_artifact",
                "candidate_games",
                "policy",
                "predecessor_config",
                "engine_identity",
                "runner_identity",
            },
        )
        self.assertEqual(
            receipt["extra"]["config_sha256"],
            receipt["queue_pin"]["inputs"]["predecessor_config"]["sha256"],
        )
        for comparison in receipt["comparisons"]:
            slot = comparison["slot"]
            provenance = receipt["predecessors"][slot]
            self.assertEqual(
                provenance["panel_id"],
                comparison["panel_id"],
            )

    def test_reject_then_rerun_keeps_hash_chain(self):
        submission = self._submit("weak", own=100.0, policy_delta=50.0)
        process = self._run("--id", submission)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("REJECT", process.stdout)
        entry = json.loads(self._cli("status", submission).stdout)
        self.assertEqual(entry["status"], "failed")
        first_receipt = entry["last_receipt"]
        self.assertIsNotNone(first_receipt)

        rerun = self._cli("rerun", submission)
        self.assertEqual(rerun.returncode, 0, rerun.stdout)
        process = self._run("--id", submission)
        self.assertNotEqual(process.returncode, 0)
        entry = json.loads(self._cli("status", submission).stdout)
        self.assertEqual(entry["status"], "failed")
        self.assertNotEqual(entry["last_receipt"], first_receipt)
        receipt = json.loads(self._cli("receipt", submission).stdout)
        self.assertEqual(receipt["verdict"], "REJECT")
        self.assertIsNotNone(
            receipt["integrity"]["prev_receipt_digest"],
        )
        verify = self._cli("receipt", submission, "--verify")
        self.assertEqual(verify.returncode, 0, verify.stdout)

    def test_fifo_and_dedupe_include_executable_bytes(self):
        first = self._submit("one", own=110.0, policy_delta=5.0)
        second = self._submit("two", own=110.0, policy_delta=5.0)
        duplicate = self._submit(
            "three",
            own=110.0,
            policy_delta=5.0,
            artifact_tag="one",
        )
        self.assertEqual(duplicate, first)

        listing = self._cli("list", "--status", "pending").stdout
        lines = [line for line in listing.splitlines() if line.startswith("pq-")]
        self.assertEqual(
            [line.split()[0] for line in lines],
            [first, second],
        )

        process = self._run("--all")
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        for submission in (first, second):
            entry = json.loads(self._cli("status", submission).stdout)
            self.assertEqual(entry["status"], "passed")


if __name__ == "__main__":
    unittest.main()
