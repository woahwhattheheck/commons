"""Exact packet verification tests."""

import copy
import unittest

from .engine import PacketVerificationError, compile_packet, verify_packet
from .test_support import ready_fixture

class VerificationTests(unittest.TestCase):
    def test_exact_packet_verifies(self) -> None:
        value = ready_fixture()
        receipt, markdown = compile_packet(value)
        self.assertTrue(verify_packet(value, receipt, markdown))

    def test_tampered_receipt_rejected(self) -> None:
        value = ready_fixture()
        receipt, markdown = compile_packet(value)
        receipt = copy.deepcopy(receipt)
        receipt["status"] = "SUBMISSION_READY"
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


