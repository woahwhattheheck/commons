"""Exact packet verification tests."""

import copy
import unittest

from .engine import (
    CURRENT_PROCESS_UTC,
    HISTORICAL_INTEGRITY_ONLY,
    PacketVerificationError,
    compile_current,
    compile_packet,
    verify_current,
    verify_packet,
)
from .test_support import ready_fixture


class VerificationTests(unittest.TestCase):
    def test_exact_historical_packet_verifies(self) -> None:
        value = ready_fixture()
        receipt, markdown = compile_packet(value)
        self.assertEqual(receipt["evaluation_mode"], HISTORICAL_INTEGRITY_ONLY)
        self.assertTrue(verify_packet(value, receipt, markdown))

    def test_exact_current_packet_verifies(self) -> None:
        value = ready_fixture()
        receipt, markdown = compile_current(value)
        self.assertEqual(receipt["evaluation_mode"], CURRENT_PROCESS_UTC)
        self.assertTrue(verify_current(value, receipt, markdown))
        self.assertFalse(receipt["submission_ready"])

    def test_historical_packet_cannot_be_promoted_to_current(self) -> None:
        value = ready_fixture()
        receipt, markdown = compile_packet(value)
        with self.assertRaises(PacketVerificationError):
            verify_current(value, receipt, markdown)

    def test_tampered_receipt_rejected(self) -> None:
        value = ready_fixture()
        receipt, markdown = compile_packet(value)
        receipt = copy.deepcopy(receipt)
        receipt["status"] = "SUBMISSION_READY"
        receipt["submission_ready"] = True
        with self.assertRaises(PacketVerificationError):
            verify_packet(value, receipt, markdown)

    def test_tampered_evaluation_mode_rejected(self) -> None:
        value = ready_fixture()
        receipt, markdown = compile_packet(value)
        receipt = copy.deepcopy(receipt)
        receipt["evaluation_mode"] = CURRENT_PROCESS_UTC
        with self.assertRaises(PacketVerificationError):
            verify_packet(value, receipt, markdown)

    def test_tampered_markdown_rejected(self) -> None:
        value = ready_fixture()
        receipt, markdown = compile_packet(value)
        with self.assertRaises(PacketVerificationError):
            verify_packet(value, receipt, markdown + "tamper")

    def test_changed_input_rejected(self) -> None:
        value = ready_fixture()
        receipt, markdown = compile_packet(value)
        changed = copy.deepcopy(value)
        changed["owner_notes"].append("new note")
        with self.assertRaises(PacketVerificationError):
            verify_packet(changed, receipt, markdown)


if __name__ == "__main__":
    unittest.main()
