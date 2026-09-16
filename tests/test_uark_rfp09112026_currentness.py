from __future__ import annotations

import copy
import importlib.util
import inspect
import json
import unittest
from datetime import datetime, timedelta, timezone
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


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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

    def test_current_api_has_no_caller_time_or_clock_parameters(self) -> None:
        self.assertEqual(
            list(inspect.signature(mod.compile_production).parameters),
            ["intake"],
        )
        self.assertEqual(
            list(inspect.signature(mod.verify_packet_current).parameters),
            ["packet"],
        )
        with self.assertRaises(TypeError):
            mod.compile_production(fixture(), now=utc("2000-01-01T00:00:00Z"))
        packet = mod.compile_qualification(fixture())
        with self.assertRaises(TypeError):
            mod.verify_packet_current(packet, clock=lambda: utc("2000-01-01T00:00:00Z"))

    def test_production_compile_ignores_backdated_input_and_uses_live_process_time(self) -> None:
        value = fixture()
        value["evaluated_at_utc"] = "2000-01-01T00:00:00Z"
        before = datetime.now(timezone.utc).replace(microsecond=0)
        packet = mod.compile_production(value)
        after = datetime.now(timezone.utc).replace(microsecond=0)
        observed = utc(packet["evaluated_at_utc"])
        self.assertGreaterEqual(observed, before)
        self.assertLessEqual(observed, after)
        self.assertNotEqual(packet["evaluated_at_utc"], value["evaluated_at_utc"])
        self.assertTrue(mod.verify_packet_current(packet))

    def test_post_import_clock_and_parser_global_rebinding_cannot_backdate_current(self) -> None:
        value = fixture()
        value["evaluated_at_utc"] = "2000-01-01T00:00:00Z"
        before = datetime.now(timezone.utc).replace(microsecond=0)

        original_datetime = mod.datetime
        original_timezone = mod.timezone
        original_dt = mod._dt
        original_normalize = mod._normalize_aware_utc
        original_utc_text = mod._utc_text
        original_compile = mod.compile_qualification
        original_verify = mod.verify_packet
        try:
            class BackdatedDateTime:
                @classmethod
                def now(cls, *_args, **_kwargs):
                    return utc("2000-01-01T00:00:00Z")

            mod.datetime = BackdatedDateTime
            mod.timezone = object()
            mod._dt = lambda _value: utc("2000-01-01T00:00:00Z")
            mod._normalize_aware_utc = lambda _value: utc("2000-01-01T00:00:00Z")
            mod._utc_text = lambda _value: "2000-01-01T00:00:00Z"
            mod.compile_qualification = lambda _value: (_ for _ in ()).throw(
                AssertionError("CURRENT must retain its compiler dependency")
            )
            mod.verify_packet = lambda _value: (_ for _ in ()).throw(
                AssertionError("CURRENT must retain its verifier dependency")
            )

            packet = mod.compile_production(value)
            observed = utc(packet["evaluated_at_utc"])
            self.assertGreaterEqual(observed, before)
            self.assertNotEqual(packet["evaluated_at_utc"], "2000-01-01T00:00:00Z")
            self.assertTrue(mod.verify_packet_current(packet))
        finally:
            mod.datetime = original_datetime
            mod.timezone = original_timezone
            mod._dt = original_dt
            mod._normalize_aware_utc = original_normalize
            mod._utc_text = original_utc_text
            mod.compile_qualification = original_compile
            mod.verify_packet = original_verify

    def test_current_verify_rejects_future_evaluation(self) -> None:
        value = fixture()
        future = datetime.now(timezone.utc) + timedelta(days=1)
        value["evaluated_at_utc"] = utc_text(future)
        packet = mod.compile_qualification(value)
        with self.assertRaisesRegex(mod.InputError, "ahead of trusted"):
            mod.verify_packet_current(packet)

    def test_historical_deadline_semantics_remain_explicit_time_replay_only(self) -> None:
        value = fixture()
        value["evaluated_at_utc"] = mod.PROPOSAL_DEADLINE_UTC
        packet = mod.compile_qualification(value)
        self.assertEqual(packet["decision"]["status"], "NO_BID")
        self.assertIn(
            "PROPOSAL_DEADLINE_PASSED",
            packet["decision"]["blockers"],
        )
        self.assertTrue(mod.verify_packet(packet))

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
