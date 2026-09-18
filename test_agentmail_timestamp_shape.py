from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "agentmail_timestamp_shape",
    ROOT / "host" / "agentmail_adapter.py",
)
assert SPEC and SPEC.loader
agentmail = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agentmail)
NOW = "2026-09-02T01:30:00Z"


def unavailable() -> dict[str, object]:
    return {
        "build_order_id": agentmail.ORDER,
        "observed_at": NOW,
        "agentmail_connector_state": "UNAVAILABLE",
        "gmail_fallback_state": "UNAVAILABLE",
        "inbox": {
            "state": "NOT_ATTEMPTED",
            "occurred_at": None,
            "provider_inbox_id": None,
        },
        "outbound": {
            "state": "NOT_ATTEMPTED",
            "occurred_at": None,
            "provider_message_id": None,
            "payload_sha256": None,
        },
        "inbound": {
            "state": "NOT_ATTEMPTED",
            "occurred_at": None,
            "provider_message_id": None,
            "payload_sha256": None,
        },
    }


def complete() -> dict[str, object]:
    observation = unavailable()
    observation.update(
        {
            "agentmail_connector_state": "AVAILABLE",
            "gmail_fallback_state": "NOT_NEEDED",
            "inbox": {
                "state": "CREATED",
                "occurred_at": "2026-09-02T01:30:00.1Z",
                "provider_inbox_id": "inbox_01JTEST",
            },
            "outbound": {
                "state": "PROVIDER_ACCEPTED",
                "occurred_at": "2026-09-02T01:30:01.000001Z",
                "provider_message_id": "msg_out_01JTEST",
                "payload_sha256": "sha256:" + "1" * 64,
            },
            "inbound": {
                "state": "PROVIDER_OBSERVED",
                "occurred_at": "2026-09-02T01:30:02Z",
                "provider_message_id": "msg_in_01JTEST",
                "payload_sha256": "sha256:" + "2" * 64,
            },
        }
    )
    return observation


class AgentMailTimestampShapeTests(unittest.TestCase):
    def assert_invalid(self, value: object) -> None:
        with self.assertRaisesRegex(agentmail.AgentMailReceiptError, "invalid UTC timestamp"):
            agentmail._time(value)

    def test_extended_uppercase_utc_forms_are_preserved_exactly(self) -> None:
        for value in (
            "2026-09-02T01:30:00Z",
            "2026-09-02T01:30:00.0Z",
            "2026-09-02T01:30:00.123456789Z",
        ):
            with self.subTest(value=value):
                self.assertEqual(agentmail._time(value), value)

    def test_iso_extensions_are_not_canonical_utc_receipt_times(self) -> None:
        values = (
            "2026-09-02 01:30:00Z",
            "20260902T013000Z",
            "2026-W36-3T01:30:00Z",
            "2026-09-02X01:30:00Z",
            "2026-09-02T01:30:00,5Z",
            "2026-09-02T01:30Z",
            "2026-09-02T01:30:00+00:00Z",
        )
        for value in values:
            with self.subTest(value=value):
                self.assert_invalid(value)

    def test_case_whitespace_controls_and_unicode_digits_are_rejected(self) -> None:
        values = (
            "2026-09-02t01:30:00Z",
            "2026-09-02T01:30:00z",
            " 2026-09-02T01:30:00Z",
            "2026-09-02T01:30:00Z ",
            "2026-09-02T01:30:00Z\n",
            "2026-09-02T01:30:\x0000Z",
            "２０２６-09-02T01:30:00Z",
            "2026-09-02T01:30:00.１２Z",
        )
        for value in values:
            with self.subTest(value=repr(value)):
                self.assert_invalid(value)

    def test_calendar_and_clock_ranges_remain_checked(self) -> None:
        values = (
            "0000-09-02T01:30:00Z",
            "2025-02-29T01:30:00Z",
            "2026-13-02T01:30:00Z",
            "2026-09-31T01:30:00Z",
            "2026-09-02T24:00:00Z",
            "2026-09-02T01:60:00Z",
            "2026-09-02T01:30:60Z",
        )
        for value in values:
            with self.subTest(value=value):
                self.assert_invalid(value)

    def test_nullable_stage_time_accepts_only_none(self) -> None:
        self.assertIsNone(agentmail._time(None, nullable=True))
        for value in ("", " ", False, 0, [], {}):
            with self.subTest(value=repr(value)):
                with self.assertRaises(agentmail.AgentMailReceiptError):
                    agentmail._time(value, nullable=True)

    def test_observed_at_rejects_each_extension_form(self) -> None:
        for value in (
            "2026-09-02 01:30:00Z",
            "20260902T013000Z",
            "2026-W36-3T01:30:00Z",
            "2026-09-02T01:30:00,5Z",
        ):
            observation = unavailable()
            observation["observed_at"] = value
            with self.subTest(value=value), self.assertRaises(agentmail.AgentMailReceiptError):
                agentmail.project_receipt(observation)

    def test_each_stage_rejects_noncanonical_time(self) -> None:
        for name in ("inbox", "outbound", "inbound"):
            observation = complete()
            observation[name]["occurred_at"] = "2026-09-02 01:30:00Z"
            with self.subTest(name=name), self.assertRaises(agentmail.AgentMailReceiptError):
                agentmail.project_receipt(observation)

    def test_public_validator_rejects_noncanonical_receipt_time(self) -> None:
        receipt = agentmail.project_receipt(complete())
        for path in (
            ("observed_at",),
            ("inbox", "occurred_at"),
            ("outbound", "occurred_at"),
            ("inbound", "occurred_at"),
        ):
            changed = copy.deepcopy(receipt)
            target = changed if len(path) == 1 else changed[path[0]]
            target[path[-1]] = "2026-09-02 01:30:00Z"
            with self.subTest(path=path), self.assertRaises(agentmail.AgentMailReceiptError):
                agentmail.validate_public_receipt(changed)

    def test_valid_complete_projection_remains_round_trip_proven(self) -> None:
        observation = complete()
        receipt = agentmail.project_receipt(observation)
        agentmail.validate_public_receipt(receipt)
        self.assertEqual(receipt["terminal_state"], "ROUND_TRIP_PROVEN")
        self.assertEqual(receipt["observed_at"], NOW)
        for name in ("inbox", "outbound", "inbound"):
            self.assertEqual(receipt[name]["occurred_at"], observation[name]["occurred_at"])

    def test_cli_rejects_bad_time_without_echo_or_traceback(self) -> None:
        observation = unavailable()
        observation["observed_at"] = "PRIVATE-SENTINEL 2026-09-02 01:30:00Z"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observation.json"
            path.write_text(json.dumps(observation), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(ROOT / "host" / "agentmail_adapter.py"), str(path)],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, "")
        self.assertNotIn("PRIVATE-SENTINEL", result.stdout)
        self.assertEqual(
            json.loads(result.stdout),
            {
                "ok": False,
                "state": "RECEIPT_REJECTED",
                "error_type": "AgentMailReceiptError",
            },
        )


if __name__ == "__main__":
    unittest.main()
