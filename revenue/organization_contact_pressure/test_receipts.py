from __future__ import annotations

from .test_support import *  # noqa: F401,F403


class ReceiptsTests(GateTestCase):
    def test_receipt_tamper_and_public_reseal_fail(self):
        receipt = self.fx.compile()
        tampered = dict(receipt)
        tampered["decision"] = gate.HOLD_DNR
        signed_without_sha = dict(tampered)
        signed_without_sha.pop("receipt_sha256")
        tampered["receipt_sha256"] = gate._sha256(gate._canonical_bytes(signed_without_sha))
        with self.assertRaises(gate.VerificationError):
            gate._verify_receipt_integrity_at(self.fx.receipt_bytes(tampered), root=self.root)


    def test_ready_receipt_verifies_current(self):
        receipt = self.fx.compile()
        result = gate._verify_receipt_current_at(self.fx.receipt_bytes(receipt), root=self.root, now=self.fx.now)
        self.assertEqual(receipt, result)


    def test_ready_receipt_expires(self):
        receipt = self.fx.compile()
        future = self.fx.now + timedelta(seconds=self.fx.policy["ready_validity_seconds"] + 1)
        with self.assertRaises(gate.VerificationError):
            gate._verify_receipt_current_at(self.fx.receipt_bytes(receipt), root=self.root, now=future)


    def test_ready_receipt_invalidated_by_ledger_generation_move(self):
        receipt = self.fx.compile()
        self.fx.write_ledger([self.fx.event("p-1", gate.EVENT_PROPOSED)], updated_at=self.fx.now)
        with self.assertRaisesRegex(gate.VerificationError, "ledger generation moved"):
            gate._verify_receipt_current_at(self.fx.receipt_bytes(receipt), root=self.root, now=self.fx.now)


    def test_hold_receipt_remains_historically_verifiable_after_drift(self):
        self.fx.write_ledger([self.fx.event("dnr-1", gate.EVENT_DNR)])
        receipt = self.fx.compile()
        self.assert_decision(gate.HOLD_DNR, receipt)
        self.fx.write_ledger([], updated_at=self.fx.now)
        result = gate._verify_receipt_current_at(
            self.fx.receipt_bytes(receipt), root=self.root, now=self.fx.now + timedelta(days=30)
        )
        self.assertEqual(receipt, result)
