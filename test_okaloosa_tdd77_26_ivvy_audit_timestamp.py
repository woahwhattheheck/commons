#!/usr/bin/env python3
"""Hostile proof that Okaloosa source-audit freshness metadata is immutable."""
from __future__ import annotations

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKET_ROOT = ROOT / "revenue" / "okaloosa_tdd77_26_ivvy"
VALIDATOR_PATH = PACKET_ROOT / "validate_packet.py"
LEDGER_PATH = PACKET_ROOT / "source_ledger.json"


def _load_validator():
    spec = importlib.util.spec_from_file_location("okaloosa_packet_validator_audit", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Okaloosa packet validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = _load_validator()


class OkaloosaSourceAuditTimestampGuard(unittest.TestCase):
    def setUp(self) -> None:
        self.packet = validator.load_packet(LEDGER_PATH)

    def test_reviewed_source_audit_timestamp_is_accepted(self) -> None:
        result = validator.validate_packet(copy.deepcopy(self.packet))
        self.assertEqual(result["status"], "OK")

    def test_future_dated_source_audit_timestamp_is_rejected(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet["last_source_audit_utc"] = "2099-01-01T00:00:00Z"
        with self.assertRaisesRegex(validator.PacketError, "last_source_audit_utc changed"):
            validator.validate_packet(packet)

    def test_missing_source_audit_timestamp_is_rejected(self) -> None:
        packet = copy.deepcopy(self.packet)
        packet.pop("last_source_audit_utc", None)
        with self.assertRaisesRegex(validator.PacketError, "root key set changed"):
            validator.validate_packet(packet)


if __name__ == "__main__":
    unittest.main()
