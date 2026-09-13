from __future__ import annotations

import copy

from .acceptance import EXPECTED_HOLD_COUNTS, packet, run_acceptance
from .gate import HOLD_STATUS, READY_STATUS, ReadinessError, canonical_json, verify_readiness_package
from .test_support import BatchReadinessTestBase


class BatchReadinessTestsA(BatchReadinessTestBase):

    def test_ready_control(self):
            compiled = self.compile()
            self.assertEqual(READY_STATUS, compiled["receipt"]["status"])
            self.assertEqual([], compiled["receipt"]["holds"])
            self.assertTrue(verify_readiness_package(compiled)["valid"])
    def test_exact_retry_is_byte_stable(self):
            raw = packet(2); expected = self.compile(raw)
            raw["events"].append(copy.deepcopy(raw["events"][0]))
            self.assertEqual(canonical_json(expected), canonical_json(self.compile(raw)))
    def test_event_order_is_invariant(self):
            raw = packet(3); expected = self.compile(raw)
            raw["events"] = list(reversed(raw["events"]))
            self.assertEqual(canonical_json(expected), canonical_json(self.compile(raw)))
    def test_changed_same_event_id_fails(self):
            raw = packet(4); changed = copy.deepcopy(raw["events"][0]); changed["payload"]["formulationRevision"] = "FORM-X"; raw["events"].append(changed)
            with self.assertRaisesRegex(ReadinessError, "EVENT_ID_CONFLICT"): self.compile(raw)
    def test_unknown_event_kind_fails(self):
            raw = packet(5); raw["events"][0]["kind"] = "MAGIC_RELEASE"
            with self.assertRaisesRegex(ReadinessError, "UNKNOWN_EVENT_KIND"): self.compile(raw)
    def test_future_evidence_fails(self):
            raw = packet(6); raw["events"][1]["observedAt"] = "2026-09-13T11:00:00Z"
            with self.assertRaisesRegex(ReadinessError, "FUTURE_EVIDENCE"): self.compile(raw)
    def test_formulation_mismatch_holds(self):
            raw = packet(7); raw["events"][0]["payload"]["formulationRevision"] = "FORM-OLD"
            self.assertIn("FORMULATION_REVISION_MISMATCH", self.hold_codes(self.compile(raw)))
    def test_line_revision_mismatch_holds(self):
            raw = packet(8); raw["events"][0]["payload"]["lineRevision"] = "LINE-OLD"
            self.assertIn("LINE_REVISION_MISMATCH", self.hold_codes(self.compile(raw)))