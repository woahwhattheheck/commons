from __future__ import annotations

import copy
import json
import math
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from coordination.connector_preflight.core import (
    PreflightError,
    compile_at,
    compile_current,
    strict_loads,
    verify_current,
    verify_integrity,
)

T0 = datetime(2026, 9, 14, 4, 40, 0, tzinfo=timezone.utc)
SHA_A = "a" * 64
SHA_B = "b" * 64
SHA_C = "c" * 64
SHA_D = "d" * 64


def base_input(*, claim: str = "NO_WRITE_RAIL", attempts: list[dict] | None = None) -> dict:
    return {
        "schema": "commons.connector-preflight/v1",
        "snapshot_id": "snapshot-20260914-001",
        "claim": claim,
        "captured_at": "2026-09-14T04:39:30Z",
        "policy": {
            "max_age_seconds": 3600,
            "required_actions": {
                "GitHub": ["create_branch"],
                "Slack": ["slack_send_message"],
            },
        },
        "discoveries": [
            {
                "request_id": "discovery-001",
                "requested_at": "2026-09-14T04:38:00Z",
                "completed_at": "2026-09-14T04:38:05Z",
                "paths": ["GitHub", "Slack"],
                "query": None,
                "complete": True,
                "actions": [
                    {"connector": "GitHub", "name": "fetch_file", "access": "READ"},
                    {"connector": "GitHub", "name": "create_branch", "access": "WRITE"},
                    {"connector": "Slack", "name": "slack_read_channel", "access": "READ"},
                    {"connector": "Slack", "name": "slack_send_message", "access": "WRITE"},
                ],
                "evidence_sha256": SHA_A,
            }
        ],
        "attempts": attempts or [],
    }


def attempt(
    attempt_id: str,
    connector: str,
    action: str,
    result: str,
    *,
    access: str = "WRITE",
    discovery: str = "discovery-001",
    at: str = "2026-09-14T04:39:00Z",
    digest: str = SHA_B,
) -> dict:
    return {
        "attempt_id": attempt_id,
        "operation_id": f"operation-{attempt_id}",
        "discovery_request_id": discovery,
        "connector": connector,
        "action": action,
        "access": access,
        "attempted_at": at,
        "result": result,
        "error_code": None if result == "SUCCESS" else result.lower(),
        "evidence_sha256": digest,
    }


class StrictJsonTests(unittest.TestCase):
    def test_duplicate_key_rejected(self):
        with self.assertRaisesRegex(PreflightError, "duplicate JSON key"):
            strict_loads('{"a":1,"a":2}')

    def test_nonfinite_rejected(self):
        with self.assertRaisesRegex(PreflightError, "non-finite"):
            strict_loads('{"a":NaN}')

    def test_bad_json_rejected(self):
        with self.assertRaisesRegex(PreflightError, "invalid JSON"):
            strict_loads('{')


class EvaluationTests(unittest.TestCase):
    def test_discovery_only_requires_write_attempt_for_blocker(self):
        bundle = compile_at(base_input(), T0)
        self.assertEqual("WRITE_ATTEMPT_REQUIRED", bundle["packet"]["overall_state"])
        self.assertFalse(bundle["packet"]["work_blocked_claim_supported"])
        self.assertTrue(all(row["state"] == "WRITE_ATTEMPT_REQUIRED" for row in bundle["packet"]["connectors"]))

    def test_capability_report_exposes_actions_without_attempt(self):
        bundle = compile_at(base_input(claim="CAPABILITY_REPORT"), T0)
        self.assertEqual("WRITE_ACTIONS_EXPOSED", bundle["packet"]["overall_state"])
        self.assertTrue(all(row["state"] == "WRITE_ACTIONS_EXPOSED" for row in bundle["packet"]["connectors"]))

    def test_both_write_successes_confirm_rails(self):
        raw = base_input(
            attempts=[
                attempt("attempt-github-001", "GitHub", "create_branch", "SUCCESS"),
                attempt("attempt-slack-001", "Slack", "slack_send_message", "SUCCESS", digest=SHA_C),
            ]
        )
        bundle = compile_at(raw, T0)
        self.assertEqual("WRITE_RAIL_CONFIRMED", bundle["packet"]["overall_state"])
        self.assertFalse(bundle["packet"]["work_blocked_claim_supported"])
        self.assertTrue(all(row["state"] == "WRITE_RAIL_CONFIRMED" for row in bundle["packet"]["connectors"]))

    def test_unavailable_write_attempts_support_blocker(self):
        raw = base_input(
            attempts=[
                attempt("attempt-github-001", "GitHub", "create_branch", "UNAVAILABLE"),
                attempt("attempt-slack-001", "Slack", "slack_send_message", "UNAVAILABLE", digest=SHA_C),
            ]
        )
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("BLOCKER_SUPPORTED", packet["overall_state"])
        self.assertTrue(packet["work_blocked_claim_supported"])

    def test_rate_limit_does_not_support_absence(self):
        raw = base_input(
            attempts=[
                attempt("attempt-github-001", "GitHub", "create_branch", "RATE_LIMITED"),
                attempt("attempt-slack-001", "Slack", "slack_send_message", "RATE_LIMITED", digest=SHA_C),
            ]
        )
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("WRITE_ACTIONS_EXPOSED", packet["overall_state"])
        self.assertFalse(packet["work_blocked_claim_supported"])
        self.assertTrue(all("WRITE_FAILURE_DOES_NOT_PROVE_RAIL_ABSENCE" in row["reasons"] for row in packet["connectors"]))

    def test_read_403_does_not_disprove_write(self):
        raw = base_input(
            attempts=[
                attempt("attempt-github-read", "GitHub", "fetch_file", "RATE_LIMITED", access="READ"),
                attempt("attempt-github-write", "GitHub", "create_branch", "SUCCESS", digest=SHA_C),
                attempt("attempt-slack-write", "Slack", "slack_send_message", "SUCCESS", digest=SHA_D),
            ]
        )
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("WRITE_RAIL_CONFIRMED", packet["overall_state"])
        github = next(row for row in packet["connectors"] if row["connector"] == "GitHub")
        self.assertIn("READ_FAILURE_DOES_NOT_PROVE_WRITE_ABSENCE", github["reasons"])

    def test_filtered_first_pass_not_qualified(self):
        raw = base_input()
        raw["discoveries"][0]["query"] = "send"
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("NOT_DISCOVERED", packet["overall_state"])
        self.assertFalse(packet["work_blocked_claim_supported"])

    def test_empty_string_query_is_filtered(self):
        raw = base_input()
        raw["discoveries"][0]["query"] = "x"
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("NOT_DISCOVERED", packet["overall_state"])

    def test_incomplete_discovery_not_qualified(self):
        raw = base_input()
        raw["discoveries"][0]["complete"] = False
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("NOT_DISCOVERED", packet["overall_state"])

    def test_missing_one_connector_path_not_qualified(self):
        raw = base_input()
        raw["discoveries"][0]["paths"] = ["GitHub"]
        raw["discoveries"][0]["actions"] = [
            row for row in raw["discoveries"][0]["actions"] if row["connector"] == "GitHub"
        ]
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("NOT_DISCOVERED", packet["overall_state"])

    def test_complete_read_only_catalog_supports_blocker(self):
        raw = base_input()
        raw["discoveries"][0]["actions"] = [
            {"connector": "GitHub", "name": "fetch_file", "access": "READ"},
            {"connector": "Slack", "name": "slack_read_channel", "access": "READ"},
        ]
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("BLOCKER_SUPPORTED", packet["overall_state"])
        self.assertTrue(packet["work_blocked_claim_supported"])

    def test_auth_required_does_not_prove_absence(self):
        raw = base_input(
            attempts=[
                attempt("attempt-github-001", "GitHub", "create_branch", "AUTH_REQUIRED"),
                attempt("attempt-slack-001", "Slack", "slack_send_message", "AUTH_REQUIRED", digest=SHA_C),
            ]
        )
        packet = compile_at(raw, T0)["packet"]
        self.assertFalse(packet["work_blocked_claim_supported"])

    def test_success_wins_over_earlier_failure(self):
        raw = base_input(
            attempts=[
                attempt("attempt-github-old", "GitHub", "create_branch", "RATE_LIMITED", at="2026-09-14T04:38:30Z"),
                attempt("attempt-github-new", "GitHub", "create_branch", "SUCCESS", at="2026-09-14T04:39:10Z", digest=SHA_C),
                attempt("attempt-slack-new", "Slack", "slack_send_message", "SUCCESS", digest=SHA_D),
            ]
        )
        self.assertEqual("WRITE_RAIL_CONFIRMED", compile_at(raw, T0)["packet"]["overall_state"])

    def test_attempt_unknown_action_holds(self):
        raw = base_input(attempts=[attempt("attempt-github-001", "GitHub", "create_file", "SUCCESS")])
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("HOLD", packet["overall_state"])
        self.assertIn("ATTEMPT_ACTION_UNDISCOVERED_attempt-github-001", packet["reasons"])

    def test_attempt_missing_discovery_holds(self):
        raw = base_input(attempts=[attempt("attempt-github-001", "GitHub", "create_branch", "SUCCESS", discovery="missing-disc")])
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("HOLD", packet["overall_state"])
        self.assertIn("ATTEMPT_DISCOVERY_MISSING_attempt-github-001", packet["reasons"])

    def test_attempt_before_discovery_holds(self):
        raw = base_input(attempts=[attempt("attempt-github-001", "GitHub", "create_branch", "SUCCESS", at="2026-09-14T04:37:59Z")])
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("HOLD", packet["overall_state"])
        self.assertIn("ATTEMPT_BEFORE_DISCOVERY_attempt-github-001", packet["reasons"])

    def test_changed_action_access_across_discoveries_holds(self):
        raw = base_input()
        second = copy.deepcopy(raw["discoveries"][0])
        second["request_id"] = "discovery-002"
        second["requested_at"] = "2026-09-14T04:38:10Z"
        second["completed_at"] = "2026-09-14T04:38:15Z"
        second["evidence_sha256"] = SHA_C
        next(row for row in second["actions"] if row["name"] == "create_branch")["access"] = "READ"
        raw["discoveries"].append(second)
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("HOLD", packet["overall_state"])
        self.assertTrue(any(reason.startswith("ACTION_ACCESS_CONFLICT_GitHub_create_branch") for reason in packet["reasons"]))

    def test_authority_flags_are_all_false(self):
        authority = compile_at(base_input(), T0)["packet"]["authority"]
        self.assertTrue(authority)
        self.assertTrue(all(value is False for value in authority.values()))

    def test_input_order_invariant(self):
        raw = base_input(
            attempts=[
                attempt("attempt-github-001", "GitHub", "create_branch", "SUCCESS"),
                attempt("attempt-slack-001", "Slack", "slack_send_message", "SUCCESS", digest=SHA_C),
            ]
        )
        reversed_raw = copy.deepcopy(raw)
        reversed_raw["discoveries"][0]["actions"].reverse()
        reversed_raw["attempts"].reverse()
        self.assertEqual(
            json.dumps(compile_at(raw, T0), sort_keys=True),
            json.dumps(compile_at(reversed_raw, T0), sort_keys=True),
        )


class StructuralHostileTests(unittest.TestCase):
    def test_duplicate_action_identity_rejected(self):
        raw = base_input()
        raw["discoveries"][0]["actions"].append(copy.deepcopy(raw["discoveries"][0]["actions"][0]))
        with self.assertRaisesRegex(PreflightError, "duplicate action identity"):
            compile_at(raw, T0)

    def test_duplicate_attempt_id_rejected(self):
        a = attempt("attempt-github-001", "GitHub", "create_branch", "SUCCESS")
        raw = base_input(attempts=[a, {**a, "operation_id": "operation-other"}])
        with self.assertRaisesRegex(PreflightError, "duplicate attempt_id"):
            compile_at(raw, T0)

    def test_duplicate_operation_id_rejected(self):
        a = attempt("attempt-github-001", "GitHub", "create_branch", "SUCCESS")
        b = attempt("attempt-slack-001", "Slack", "slack_send_message", "SUCCESS")
        b["operation_id"] = a["operation_id"]
        with self.assertRaisesRegex(PreflightError, "duplicate operation_id"):
            compile_at(base_input(attempts=[a, b]), T0)

    def test_bool_not_int(self):
        raw = base_input()
        raw["policy"]["max_age_seconds"] = True
        with self.assertRaisesRegex(PreflightError, "expected integer"):
            compile_at(raw, T0)

    def test_future_snapshot_rejected(self):
        raw = base_input()
        raw["captured_at"] = "2026-09-14T04:40:01Z"
        with self.assertRaisesRegex(PreflightError, "future"):
            compile_at(raw, T0)

    def test_stale_snapshot_rejected(self):
        raw = base_input()
        raw["policy"]["max_age_seconds"] = 10
        with self.assertRaisesRegex(PreflightError, "stale"):
            compile_at(raw, T0)

    def test_noncanonical_timestamp_rejected(self):
        raw = base_input()
        raw["captured_at"] = "2026-09-14T04:39:30+00:00"
        with self.assertRaisesRegex(PreflightError, "canonical"):
            compile_at(raw, T0)

    def test_bad_sha_rejected(self):
        raw = base_input()
        raw["discoveries"][0]["evidence_sha256"] = "A" * 64
        with self.assertRaisesRegex(PreflightError, "invalid format"):
            compile_at(raw, T0)

    def test_unknown_top_key_rejected(self):
        raw = base_input()
        raw["extra"] = "nope"
        with self.assertRaisesRegex(PreflightError, "key mismatch"):
            compile_at(raw, T0)

    def test_action_connector_must_be_requested(self):
        raw = base_input()
        raw["discoveries"][0]["paths"] = ["GitHub"]
        with self.assertRaisesRegex(PreflightError, "not requested"):
            compile_at(raw, T0)

    def test_attempt_after_capture_rejected(self):
        raw = base_input(attempts=[attempt("attempt-github-001", "GitHub", "create_branch", "SUCCESS", at="2026-09-14T04:39:31Z")])
        with self.assertRaisesRegex(PreflightError, "after snapshot capture"):
            compile_at(raw, T0)


class VerificationTests(unittest.TestCase):
    def test_exact_integrity_valid(self):
        raw = base_input()
        bundle = compile_at(raw, T0)
        self.assertTrue(verify_integrity(raw, bundle))

    def test_packet_tamper_invalid(self):
        raw = base_input()
        bundle = compile_at(raw, T0)
        bundle["packet"]["overall_state"] = "BLOCKER_SUPPORTED"
        self.assertFalse(verify_integrity(raw, bundle))

    def test_markdown_tamper_invalid(self):
        raw = base_input()
        bundle = compile_at(raw, T0)
        bundle["markdown"] += "tamper"
        self.assertFalse(verify_integrity(raw, bundle))

    def test_receipt_reseal_invalid(self):
        raw = base_input()
        bundle = compile_at(raw, T0)
        bundle["packet"]["reasons"] = ["FORGED"]
        bundle["packet_sha256"] = "0" * 64
        bundle["receipt"]["packet_sha256"] = "0" * 64
        self.assertFalse(verify_integrity(raw, bundle))

    def test_input_drift_invalid(self):
        raw = base_input()
        bundle = compile_at(raw, T0)
        changed = copy.deepcopy(raw)
        changed["snapshot_id"] = "snapshot-20260914-002"
        self.assertFalse(verify_integrity(changed, bundle))

    def test_current_valid_while_semantics_same(self):
        raw = base_input()
        bundle = compile_at(raw, T0, mode="CURRENT")
        result = verify_current(raw, bundle, clock=lambda: T0 + timedelta(seconds=10))
        self.assertTrue(result["integrity_valid"])
        self.assertTrue(result["current_valid"])

    def test_current_invalid_after_staleness(self):
        raw = base_input()
        raw["policy"]["max_age_seconds"] = 60
        bundle = compile_at(raw, T0, mode="CURRENT")
        result = verify_current(raw, bundle, clock=lambda: T0 + timedelta(seconds=61))
        self.assertTrue(result["integrity_valid"])
        self.assertFalse(result["current_valid"])
        self.assertEqual("STALE_OR_INVALID", result["current_state"])


class CliTests(unittest.TestCase):
    def test_cli_compile_and_verify(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.json"
            bundle_path = Path(tmp) / "bundle.json"
            input_path.write_text(json.dumps(base_input()), encoding="utf-8")
            env = {**os.environ, "PYTHONPATH": str(root)}
            compile_proc = subprocess.run(
                [sys.executable, "-m", "coordination.connector_preflight.cli", "compile", str(input_path), str(bundle_path)],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, compile_proc.returncode, compile_proc.stderr)
            verify_proc = subprocess.run(
                [sys.executable, "-m", "coordination.connector_preflight.cli", "verify", str(input_path), str(bundle_path)],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, verify_proc.returncode, verify_proc.stderr)

    def test_output_overwrite_refused(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.json"
            output_path = Path(tmp) / "bundle.json"
            input_path.write_text(json.dumps(base_input()), encoding="utf-8")
            output_path.write_text("occupied", encoding="utf-8")
            env = {**os.environ, "PYTHONPATH": str(root)}
            proc = subprocess.run(
                [sys.executable, "-m", "coordination.connector_preflight.cli", "compile", str(input_path), str(output_path)],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, proc.returncode)
            self.assertEqual("occupied", output_path.read_text(encoding="utf-8"))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_output_symlink_refused(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.json"
            target_path = Path(tmp) / "target.json"
            output_path = Path(tmp) / "bundle.json"
            input_path.write_text(json.dumps(base_input()), encoding="utf-8")
            target_path.write_text("safe", encoding="utf-8")
            output_path.symlink_to(target_path)
            env = {**os.environ, "PYTHONPATH": str(root)}
            proc = subprocess.run(
                [sys.executable, "-m", "coordination.connector_preflight.cli", "compile", str(input_path), str(output_path)],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, proc.returncode)
            self.assertEqual("safe", target_path.read_text(encoding="utf-8"))

    @unittest.skipUnless(hasattr(os, "symlink"), "symlink unavailable")
    def test_input_symlink_refused(self):
        root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            real_input = Path(tmp) / "real.json"
            input_path = Path(tmp) / "input.json"
            output_path = Path(tmp) / "bundle.json"
            real_input.write_text(json.dumps(base_input()), encoding="utf-8")
            input_path.symlink_to(real_input)
            env = {**os.environ, "PYTHONPATH": str(root)}
            proc = subprocess.run(
                [sys.executable, "-m", "coordination.connector_preflight.cli", "compile", str(input_path), str(output_path)],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, proc.returncode)
            self.assertFalse(output_path.exists())


if __name__ == "__main__":
    unittest.main()
