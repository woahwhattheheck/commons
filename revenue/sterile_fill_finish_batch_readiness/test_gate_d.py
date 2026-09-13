from __future__ import annotations

import copy

from .acceptance import EXPECTED_HOLD_COUNTS, packet, run_acceptance
from .gate import HOLD_STATUS, READY_STATUS, ReadinessError, canonical_json, verify_readiness_package
from .test_support import BatchReadinessTestBase


class BatchReadinessTestsD(BatchReadinessTestBase):

    def test_verifier_rejects_payload_tamper(self):
            compiled = self.compile(packet(25)); compiled["payload"]["policy"]["approvedLineRevision"] = "LINE-X"
            with self.assertRaises(ReadinessError): verify_readiness_package(compiled)
    def test_verifier_rejects_receipt_tamper(self):
            compiled = self.compile(packet(26)); compiled["receipt"]["status"] = HOLD_STATUS
            with self.assertRaisesRegex(ReadinessError, "RECEIPT_MISMATCH"): verify_readiness_package(compiled)
    def test_verifier_rejects_summary_tamper(self):
            compiled = self.compile(packet(27)); compiled["summaryMarkdown"] += "\nforged"
            with self.assertRaisesRegex(ReadinessError, "SUMMARY_MISMATCH"): verify_readiness_package(compiled)
    def test_secret_key_rejected(self):
            raw = packet(28); raw["events"][0]["payload"]["apiKey"] = "not-even-a-real-key"
            with self.assertRaisesRegex(ReadinessError, "SECRET_OR_PII_KEY"): self.compile(raw)
    def test_email_shaped_text_rejected(self):
            raw = packet(29); raw["events"][1]["payload"]["evidenceRef"] = "operator@example.com"
            with self.assertRaisesRegex(ReadinessError, "PII_SHAPED_TEXT"): self.compile(raw)
    def test_bool_is_not_integer(self):
            raw = packet(30); raw["policy"]["environmentMaxAgeHours"] = True
            with self.assertRaisesRegex(ReadinessError, "INTEGER_REQUIRED"): self.compile(raw)
    def test_authority_ceiling_is_all_false(self):
            compiled = self.compile(packet(31)); self.assertTrue(compiled["receipt"]["authorities"]); self.assertFalse(any(compiled["receipt"]["authorities"].values()))
    def test_acceptance_180_packets(self):
            result = run_acceptance(); self.assertEqual(180, result["packets"]); self.assertEqual(144, result["ready"]); self.assertEqual(36, result["held"]); self.assertEqual(EXPECTED_HOLD_COUNTS, result["holdCounts"]); self.assertTrue(result["allOfflineVerified"]); self.assertTrue(result["retryByteStable"]); self.assertTrue(result["orderInvariant"])