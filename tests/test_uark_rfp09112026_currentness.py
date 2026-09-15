from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "revenue" / "uark_rfp09112026_cmmc" / "qualifier.py"
FIXTURE_PATH = ROOT / "revenue" / "uark_rfp09112026_cmmc" / "synthetic_candidate.json"

SPEC = importlib.util.spec_from_file_location(
    "uark_rfp09112026_currentness", MODULE_PATH
)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


def fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def utc(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


class UarkRfp09112026CurrentnessTests(unittest.TestCase):
    def test_fixture_remains_ready_at_captured_generation(self) -> None:
        packet = mod.compile_qualification(fixture())
        self.assertEqual(packet["decision"]["status"], "TEAMING_READY")
        self.assertTrue(mod.verify_packet(packet))

    def test_evaluation_before_source_capture_holds(self) -> None:
        value = fixture()
        value["evaluated_at_utc"] = "2026-09-15T00:57:59Z"
        packet = mod.compile_qualification(value)
        self.assertEqual(packet["decision"]["status"], "HOLD")
        self.assertIn(
            "EVALUATION_PRECEDES_SOURCE_CAPTURE",
            packet["decision"]["blockers"],
        )
        self.assertTrue(mod.verify_packet(packet))

    def test_frozen_generation_holds_after_addendum_recheck_boundary(self) -> None:
        value = fixture()
        value["evaluated_at_utc"] = mod.ADDENDUM_RECHECK_BOUNDARY_UTC
        packet = mod.compile_qualification(value)
        self.assertEqual(packet["decision"]["status"], "HOLD")
        self.assertIn(
            "POST_ADDENDUM_SOURCE_RECHECK_REQUIRED",
            packet["decision"]["blockers"],
        )
        self.assertTrue(mod.verify_packet(packet))

    def test_production_compile_ignores_backdated_input(self) -> None:
        value = fixture()
        value["evaluated_at_utc"] = "2000-01-01T00:00:00Z"
        packet = mod.compile_production(
            value,
            now=utc(mod.PROPOSAL_DEADLINE_UTC),
        )
        self.assertEqual(
            packet["evaluated_at_utc"],
            mod.PROPOSAL_DEADLINE_UTC,
        )
        self.assertEqual(packet["decision"]["status"], "NO_BID")
        self.assertIn(
            "PROPOSAL_DEADLINE_PASSED",
            packet["decision"]["blockers"],
        )

    def test_current_verify_rejects_predeadline_ready_after_deadline(self) -> None:
        packet = mod.compile_qualification(fixture())
        with self.assertRaisesRegex(mod.InputError, "no longer current"):
            mod.verify_packet_current(
                packet,
                now=utc(mod.PROPOSAL_DEADLINE_UTC),
            )

    def test_current_verify_rejects_future_evaluation(self) -> None:
        packet = mod.compile_qualification(fixture())
        before_capture = utc("2026-09-15T00:00:00Z")
        with self.assertRaisesRegex(mod.InputError, "ahead of trusted"):
            mod.verify_packet_current(packet, now=before_capture)

    def test_receipt_recomputation_covers_currentness_blockers(self) -> None:
        packet = mod.compile_qualification(fixture())
        forged = copy.deepcopy(packet)
        forged["decision"]["blockers"].append(
            "POST_ADDENDUM_SOURCE_RECHECK_REQUIRED"
        )
        unsigned_decision = copy.deepcopy(forged["decision"])
        unsigned_decision.pop("decision_receipt_sha256")
        forged["decision"]["decision_receipt_sha256"] = mod.sha256_obj(
            unsigned_decision
        )
        unsigned_packet = copy.deepcopy(forged)
        unsigned_packet.pop("packet_receipt_sha256")
        forged["packet_receipt_sha256"] = mod.sha256_obj(unsigned_packet)
        with self.assertRaisesRegex(mod.InputError, "semantic verification"):
            mod.verify_packet(forged)


if __name__ == "__main__":
    unittest.main()
