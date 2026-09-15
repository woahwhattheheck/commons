#!/usr/bin/env python3
"""Authority-bound public-facade tests layered on the original fleet suite."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import ci_fleet_core_test_support as support
from host import ci_fleet as fleet


class FleetTests(support.FleetTests):
    def attempt(self, *args, **kwargs) -> dict:
        row = super().attempt(*args, **kwargs)
        row["report"]["execution"]["ignored_worktree_entries_at_start"] = 0
        return fleet.seal(row, "attempt_sha256")

    def authority(self, attempt: dict, *, plan: dict | None = None, changes=None) -> dict:
        plan = plan or self.plan
        row = {
            "schema": fleet.AUTHORITY_SCHEMA,
            "plan_sha256": plan["plan_sha256"],
            "attempt_sha256": attempt["attempt_sha256"],
            "provider": attempt["provenance"]["provider"],
            "execution_id": attempt["provenance"]["execution_id"],
            "source_sha": plan["source_sha"],
            "command_sha256": fleet.digest(attempt["command"]),
            "runtime": copy.deepcopy(plan["runtime"]),
            "runtime_sha256": plan["runtime_sha256"],
            "runner_inputs_sha256": fleet.digest(plan["runner_inputs"]),
            "raw_results_sha256": attempt["raw_results_sha256"],
            "report_sha256": fleet.digest(attempt["report"]),
        }
        if changes:
            row.update(copy.deepcopy(changes))
        return fleet.seal(row, "authority_sha256")

    def checked(self, plan: dict, attempts: list[dict]) -> dict:
        anchor = fleet.verify_plan_source(self.root, plan)
        latest: dict[int, dict] = {}
        for row in attempts:
            if not isinstance(row, dict) or type(row.get("shard_index")) is not int:
                continue
            current = latest.get(row["shard_index"])
            if current is None or row.get("attempt", 0) > current.get("attempt", 0):
                latest[row["shard_index"]] = row
        authorities = []
        for _, row in sorted(latest.items()):
            try:
                authorities.append(self.authority(row, plan=plan))
            except (KeyError, TypeError):
                pass
        return fleet.aggregate(
            plan,
            attempts,
            expected_plan_sha256=anchor,
            trusted_execution_authorities=authorities,
        )

    def test_plausible_provider_cannot_self_authorize_execution(self):
        attempts = [
            self.attempt(0, provider="github-actions", execution_id="run-100-job-a"),
            self.attempt(1, provider="github-actions", execution_id="run-100-job-b"),
        ]
        anchor = fleet.verify_plan_source(self.root, self.plan)
        result = fleet.aggregate(self.plan, attempts, expected_plan_sha256=anchor)
        self.assertEqual(result["status"], "UNVERIFIED")
        self.assertEqual(result["source_binding"], "coordinator-anchored")
        self.assertEqual(result["execution_binding"], "unverified")
        self.assertIn("cannot authorize PASSED", result["execution_authenticity"])

    def test_ignored_worktree_preflight_cannot_be_omitted_or_nonzero(self):
        anchor = fleet.verify_plan_source(self.root, self.plan)
        for defect in ("missing", "nonzero"):
            with self.subTest(defect=defect):
                attempts = [self.attempt(0), self.attempt(1)]
                execution = attempts[0]["report"]["execution"]
                if defect == "missing":
                    execution.pop("ignored_worktree_entries_at_start")
                else:
                    execution["ignored_worktree_entries_at_start"] = 1
                attempts[0] = fleet.seal(attempts[0], "attempt_sha256")
                authorities = [self.authority(row) for row in attempts]
                result = fleet.aggregate(
                    self.plan,
                    attempts,
                    expected_plan_sha256=anchor,
                    trusted_execution_authorities=authorities,
                )
                self.assertEqual(result["status"], "INVALID", result)
                self.assertTrue(any(
                    row["code"] == "INVALID_EXECUTION_PREFLIGHT"
                    for row in result["findings"]
                ))
                with self.assertRaises(fleet.FleetError):
                    fleet.inspect_attempt(self.plan, attempts[0])

    def test_authority_mismatches_fail_closed(self):
        attempts = [self.attempt(0), self.attempt(1)]
        anchor = fleet.verify_plan_source(self.root, self.plan)
        good = [self.authority(row) for row in attempts]
        self.assertEqual(
            fleet.aggregate(
                self.plan,
                attempts,
                expected_plan_sha256=anchor,
                trusted_execution_authorities=good,
            )["status"],
            "PASSED",
        )
        for field, value in (
            ("provider", "other-provider"),
            ("execution_id", "other-run"),
            ("source_sha", "a" * 40),
            ("command_sha256", "a" * 64),
            ("runtime_sha256", "a" * 64),
            ("runner_inputs_sha256", "a" * 64),
            ("raw_results_sha256", "a" * 64),
            ("report_sha256", "a" * 64),
        ):
            with self.subTest(field=field):
                bad = self.authority(attempts[0], changes={field: value})
                result = fleet.aggregate(
                    self.plan,
                    attempts,
                    expected_plan_sha256=anchor,
                    trusted_execution_authorities=[bad, good[1]],
                )
                self.assertEqual(result["status"], "INVALID", result)

        runtime = self.authority(attempts[0])
        runtime["runtime"]["node_version"] = "different"
        runtime = fleet.seal(runtime, "authority_sha256")
        self.assertEqual(
            fleet.aggregate(
                self.plan,
                attempts,
                expected_plan_sha256=anchor,
                trusted_execution_authorities=[runtime, good[1]],
            )["status"],
            "INVALID",
        )

    def test_cli_source_anchor_still_cannot_authenticate_execution(self):
        attempts = [self.attempt(0), self.attempt(1)]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            plan_path = root / "plan.json"
            plan_path.write_text(json.dumps(self.plan), encoding="utf-8")
            attempt_paths = []
            for index, attempt in enumerate(attempts):
                path = root / f"attempt-{index}.json"
                path.write_text(json.dumps(attempt), encoding="utf-8")
                attempt_paths.append(path)
            cli = Path(__file__).parent / "host/ci_fleet.py"
            argv = [
                sys.executable, "-B", str(cli), "aggregate",
                "--plan", str(plan_path),
                "--source-root", str(self.root),
            ]
            for path in attempt_paths:
                argv.extend(["--attempt", str(path)])
            result = subprocess.run(argv, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 1, result.stderr)
            parsed = json.loads(result.stdout)
            self.assertEqual(parsed["status"], "UNVERIFIED")
            self.assertEqual(parsed["execution_binding"], "unverified")


if __name__ == "__main__":
    import unittest
    unittest.main()
