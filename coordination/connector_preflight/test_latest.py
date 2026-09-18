from __future__ import annotations

import copy
import importlib
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from coordination.connector_preflight import (
    PreflightError,
    compile_at,
    compile_current,
    verify_current,
)
from coordination.connector_preflight import core
from coordination.connector_preflight.latest import (
    _compile_current_at,
    read_json_file,
)
from coordination.connector_preflight.test_preflight import (
    SHA_C,
    SHA_D,
    T0,
    attempt,
    base_input,
)


def _stat_clone(info, **changes):
    fields = {
        "st_mode": info.st_mode,
        "st_dev": info.st_dev,
        "st_ino": info.st_ino,
        "st_nlink": info.st_nlink,
        "st_size": info.st_size,
        "st_mtime_ns": info.st_mtime_ns,
        "st_ctime_ns": info.st_ctime_ns,
    }
    fields.update(changes)
    return SimpleNamespace(**fields)


class LatestDiscoveryTests(unittest.TestCase):
    def _second(self, raw):
        second = copy.deepcopy(raw["discoveries"][0])
        second["request_id"] = "discovery-002"
        second["requested_at"] = "2026-09-14T04:38:10Z"
        second["completed_at"] = "2026-09-14T04:38:15Z"
        second["evidence_sha256"] = SHA_C
        raw["discoveries"].append(second)
        return second

    def test_latest_complete_discovery_controls_catalog(self):
        raw = base_input()
        second = self._second(raw)
        second["actions"] = [
            {"connector": "GitHub", "name": "fetch_file", "access": "READ"},
            {"connector": "Slack", "name": "slack_read_channel", "access": "READ"},
        ]
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("HOLD", packet["overall_state"])
        self.assertFalse(packet["work_blocked_claim_supported"])
        self.assertIn(
            "CALLER_EVIDENCE_CANNOT_SUPPORT_NO_WRITE_RAIL",
            packet["reasons"],
        )

    def test_old_success_does_not_confirm_new_discovery(self):
        raw = base_input(
            attempts=[
                attempt(
                    "attempt-github-old",
                    "GitHub",
                    "create_branch",
                    "SUCCESS",
                )
            ]
        )
        self._second(raw)
        packet = compile_at(raw, T0)["packet"]
        github = next(
            row
            for row in packet["connectors"]
            if row["connector"] == "GitHub"
        )
        self.assertEqual("WRITE_ATTEMPT_REQUIRED", github["state"])
        self.assertEqual("WRITE_ATTEMPT_REQUIRED", packet["overall_state"])

    def test_same_time_latest_catalog_conflict_holds(self):
        raw = base_input()
        second = copy.deepcopy(raw["discoveries"][0])
        second["request_id"] = "discovery-002"
        second["evidence_sha256"] = SHA_C
        second["actions"] = [
            {"connector": "GitHub", "name": "fetch_file", "access": "READ"},
            {"connector": "Slack", "name": "slack_read_channel", "access": "READ"},
        ]
        raw["discoveries"].append(second)
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("HOLD", packet["overall_state"])
        self.assertIn(
            "LATEST_DISCOVERY_CATALOG_CONFLICT",
            packet["reasons"],
        )

    def test_other_write_action_prevents_read_only_blocker(self):
        raw = base_input()
        raw["discoveries"][0]["actions"] = [
            {"connector": "GitHub", "name": "fetch_file", "access": "READ"},
            {"connector": "GitHub", "name": "create_issue", "access": "WRITE"},
            {"connector": "Slack", "name": "slack_read_channel", "access": "READ"},
        ]
        packet = compile_at(raw, T0)["packet"]
        github = next(
            row
            for row in packet["connectors"]
            if row["connector"] == "GitHub"
        )
        self.assertEqual("WRITE_ATTEMPT_REQUIRED", github["state"])
        self.assertFalse(packet["work_blocked_claim_supported"])

    def test_successful_unlisted_write_confirms_rail(self):
        raw = base_input(
            attempts=[
                attempt(
                    "attempt-github-issue",
                    "GitHub",
                    "create_issue",
                    "SUCCESS",
                ),
                attempt(
                    "attempt-slack-send",
                    "Slack",
                    "slack_send_message",
                    "SUCCESS",
                    digest=SHA_D,
                ),
            ]
        )
        github_action = next(
            row
            for row in raw["discoveries"][0]["actions"]
            if row["name"] == "create_branch"
        )
        github_action["name"] = "create_issue"
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("WRITE_RAIL_CONFIRMED", packet["overall_state"])
        self.assertFalse(packet["work_blocked_claim_supported"])

    def test_unattempted_other_write_prevents_blocker(self):
        raw = base_input(
            attempts=[
                attempt(
                    "attempt-github-branch",
                    "GitHub",
                    "create_branch",
                    "UNAVAILABLE",
                ),
                attempt(
                    "attempt-slack-send",
                    "Slack",
                    "slack_send_message",
                    "UNAVAILABLE",
                    digest=SHA_D,
                ),
            ]
        )
        raw["discoveries"][0]["actions"].append(
            {
                "connector": "GitHub",
                "name": "create_issue",
                "access": "WRITE",
            }
        )
        packet = compile_at(raw, T0)["packet"]
        github = next(
            row
            for row in packet["connectors"]
            if row["connector"] == "GitHub"
        )
        self.assertFalse(github["blocker_supported"])
        self.assertEqual("WRITE_ATTEMPT_REQUIRED", github["state"])
        self.assertFalse(packet["work_blocked_claim_supported"])

    def test_same_time_conflicting_write_results_hold(self):
        raw = base_input(
            attempts=[
                attempt(
                    "attempt-github-a",
                    "GitHub",
                    "create_branch",
                    "SUCCESS",
                ),
                attempt(
                    "attempt-github-b",
                    "GitHub",
                    "create_branch",
                    "UNAVAILABLE",
                    digest=SHA_D,
                ),
            ]
        )
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("HOLD", packet["overall_state"])
        self.assertIn(
            "LATEST_ATTEMPT_CONFLICT_GitHub_create_branch",
            packet["reasons"],
        )

    def test_public_current_clock_injection_is_impossible(self):
        raw = base_input()
        bundle = _compile_current_at(raw, T0)
        with self.assertRaises(TypeError):
            compile_current(raw, clock=lambda: T0)
        with self.assertRaises(TypeError):
            verify_current(raw, bundle, clock=lambda: T0)

    def test_public_compile_at_cannot_select_current_mode(self):
        raw = base_input()
        with self.assertRaises(TypeError):
            compile_at(raw, T0, mode="CURRENT")
        with self.assertRaises(TypeError):
            core.compile_at(raw, T0, mode="CURRENT")
        bundle = compile_at(raw, T0)
        self.assertEqual(
            "HISTORICAL_INTEGRITY_ONLY",
            bundle["packet"]["evaluation_mode"],
        )
        self.assertEqual(
            "HISTORICAL_INTEGRITY_ONLY",
            core.compile_at(raw, T0)["packet"]["evaluation_mode"],
        )

    def test_public_current_paths_use_process_owned_clock(self):
        raw = base_input()
        with patch(
            "coordination.connector_preflight.core.utc_now",
            return_value=T0,
        ):
            bundle = compile_current(raw)
            result = verify_current(raw, bundle)
        self.assertEqual(
            "CURRENT",
            bundle["packet"]["evaluation_mode"],
        )
        self.assertTrue(result["current_valid"])

    def test_fresh_wrapper_cannot_launder_old_read_only_discovery(self):
        raw = base_input()
        raw["policy"]["max_age_seconds"] = 60
        raw["captured_at"] = "2026-09-14T04:39:55Z"
        raw["discoveries"][0]["requested_at"] = "2026-09-14T03:00:00Z"
        raw["discoveries"][0]["completed_at"] = "2026-09-14T03:00:05Z"
        raw["discoveries"][0]["actions"] = [
            {"connector": "GitHub", "name": "fetch_file", "access": "READ"},
            {"connector": "Slack", "name": "slack_read_channel", "access": "READ"},
        ]
        packet = _compile_current_at(raw, T0)["packet"]
        self.assertEqual("HOLD", packet["overall_state"])
        self.assertFalse(packet["work_blocked_claim_supported"])
        self.assertIn("CONTROLLING_DISCOVERY_STALE", packet["reasons"])

    def test_fresh_wrapper_cannot_launder_old_write_evidence(self):
        raw = base_input(
            attempts=[
                attempt(
                    "attempt-github-old",
                    "GitHub",
                    "create_branch",
                    "SUCCESS",
                    at="2026-09-14T03:00:10Z",
                ),
                attempt(
                    "attempt-slack-old",
                    "Slack",
                    "slack_send_message",
                    "SUCCESS",
                    at="2026-09-14T03:00:11Z",
                    digest=SHA_D,
                ),
            ]
        )
        raw["policy"]["max_age_seconds"] = 60
        raw["captured_at"] = "2026-09-14T04:39:55Z"
        raw["discoveries"][0]["requested_at"] = "2026-09-14T03:00:00Z"
        raw["discoveries"][0]["completed_at"] = "2026-09-14T03:00:05Z"
        packet = _compile_current_at(raw, T0)["packet"]
        self.assertEqual("HOLD", packet["overall_state"])
        self.assertFalse(packet["work_blocked_claim_supported"])
        self.assertIn("CONTROLLING_DISCOVERY_STALE", packet["reasons"])
        self.assertIn(
            "LATEST_WRITE_ATTEMPT_STALE_GitHub_create_branch",
            packet["reasons"],
        )
        self.assertIn(
            "LATEST_WRITE_ATTEMPT_STALE_Slack_slack_send_message",
            packet["reasons"],
        )

    def test_host_age_ceiling_cannot_be_widened_by_input(self):
        raw = base_input(claim="CAPABILITY_REPORT")
        raw["policy"]["max_age_seconds"] = 7 * 24 * 3600
        raw["captured_at"] = "2026-09-14T04:39:55Z"
        raw["discoveries"][0]["requested_at"] = "2026-09-14T02:00:00Z"
        raw["discoveries"][0]["completed_at"] = "2026-09-14T02:00:05Z"
        packet = _compile_current_at(raw, T0)["packet"]
        self.assertEqual("HOLD", packet["overall_state"])
        self.assertIn("CONTROLLING_DISCOVERY_STALE", packet["reasons"])

    def test_newer_failure_overrides_older_success(self):
        raw = base_input(
            attempts=[
                attempt(
                    "attempt-github-old",
                    "GitHub",
                    "create_branch",
                    "SUCCESS",
                    at="2026-09-14T04:38:30Z",
                ),
                attempt(
                    "attempt-github-new",
                    "GitHub",
                    "create_branch",
                    "UNAVAILABLE",
                    at="2026-09-14T04:39:10Z",
                    digest=SHA_C,
                ),
                attempt(
                    "attempt-slack-old",
                    "Slack",
                    "slack_send_message",
                    "SUCCESS",
                    at="2026-09-14T04:38:31Z",
                    digest=SHA_C,
                ),
                attempt(
                    "attempt-slack-new",
                    "Slack",
                    "slack_send_message",
                    "UNAVAILABLE",
                    at="2026-09-14T04:39:11Z",
                    digest=SHA_D,
                ),
            ]
        )
        packet = compile_at(raw, T0)["packet"]
        self.assertEqual("HOLD", packet["overall_state"])
        self.assertFalse(packet["work_blocked_claim_supported"])
        self.assertTrue(
            all(
                row["state"] == "WRITE_ATTEMPT_FAILED"
                for row in packet["connectors"]
            )
        )
        self.assertFalse(
            any(
                row["state"] == "WRITE_RAIL_CONFIRMED"
                for row in packet["connectors"]
            )
        )

    def test_policy_overlay_reload_is_idempotent(self):
        import coordination.connector_preflight.latest as latest

        importlib.reload(latest)
        packet = latest.compile_at(base_input(), T0)["packet"]
        self.assertEqual("WRITE_ATTEMPT_REQUIRED", packet["overall_state"])

    @unittest.skipUnless(hasattr(os, "mkfifo"), "FIFO unavailable")
    def test_fifo_input_rejected_without_waiting_for_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            fifo = Path(tmp) / "input.fifo"
            os.mkfifo(fifo)
            with self.assertRaisesRegex(PreflightError, "regular file"):
                read_json_file(fifo)

    def test_input_generation_change_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_text("{}", encoding="utf-8")
            original = os.stat(path)
            changed = _stat_clone(
                original,
                st_mtime_ns=original.st_mtime_ns + 1,
            )
            with patch(
                "coordination.connector_preflight.latest.os.fstat",
                side_effect=[original, changed],
            ):
                with self.assertRaisesRegex(
                    PreflightError,
                    "generation changed",
                ):
                    read_json_file(path)

    def test_input_pathname_replacement_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "input.json"
            path.write_text("{}", encoding="utf-8")
            original = os.stat(path)
            replacement = _stat_clone(
                original,
                st_ino=original.st_ino + 1,
            )
            with patch(
                "coordination.connector_preflight.latest.os.fstat",
                side_effect=[original, original],
            ), patch(
                "coordination.connector_preflight.latest.os.stat",
                return_value=replacement,
            ):
                with self.assertRaisesRegex(
                    PreflightError,
                    "pathname was replaced",
                ):
                    read_json_file(path)


if __name__ == "__main__":
    unittest.main()
