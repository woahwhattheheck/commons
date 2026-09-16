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
        self.assertIn("EVALUATION_PRECEDES_SOURCE_CAPTURE", packet["decision"]["blockers"])
        self.assertTrue(mod.verify_packet(packet))

    def test_frozen_generation_holds_after_addendum_recheck_boundary(self) -> None:
        value = fixture()
        value["evaluated_at_utc"] = mod.ADDENDUM_RECHECK_BOUNDARY_UTC
        packet = mod.compile_qualification(value)
        self.assertEqual(packet["decision"]["status"], "HOLD")
        self.assertIn("POST_ADDENDUM_SOURCE_RECHECK_REQUIRED", packet["decision"]["blockers"])
        self.assertTrue(mod.verify_packet(packet))

    def test_current_api_has_no_caller_time_or_clock_parameters(self) -> None:
        self.assertEqual(list(inspect.signature(mod.compile_production).parameters), ["intake"])
        self.assertEqual(list(inspect.signature(mod.verify_packet_current).parameters), ["packet"])
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

    def test_post_import_clock_and_public_function_rebinding_cannot_backdate_current(self) -> None:
        value = fixture()
        value["evaluated_at_utc"] = "2000-01-01T00:00:00Z"
        before = datetime.now(timezone.utc).replace(microsecond=0)
        originals = (
            mod.datetime, mod.timezone, mod._dt, mod._normalize_aware_utc,
            mod._utc_text, mod.compile_qualification, mod.verify_packet,
        )
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
                AssertionError("CURRENT must retain private compiler semantics")
            )
            mod.verify_packet = lambda _value: (_ for _ in ()).throw(
                AssertionError("CURRENT must retain private verifier semantics")
            )
            packet = mod.compile_production(value)
            observed = utc(packet["evaluated_at_utc"])
            self.assertGreaterEqual(observed, before)
            self.assertNotEqual(packet["evaluated_at_utc"], "2000-01-01T00:00:00Z")
            self.assertTrue(mod.verify_packet_current(packet))
        finally:
            (
                mod.datetime, mod.timezone, mod._dt, mod._normalize_aware_utc,
                mod._utc_text, mod.compile_qualification, mod.verify_packet,
            ) = originals

    def test_current_semantics_ignore_public_and_core_authority_graph_mutation(self) -> None:
        authority = copy.deepcopy(mod._core.AUTHORITY)
        expected_source = copy.deepcopy(mod._core.EXPECTED_SOURCE_GENERATION)
        proposal_deadline = mod._core.PROPOSAL_DEADLINE_UTC
        question_deadline = mod._core.QUESTION_DEADLINE_UTC
        try:
            # Facade AUTHORITY aliases the public historical core. Mutation here is
            # exactly the predecessor that minted contact authority on the RED head.
            mod.AUTHORITY["partner_contact_authorized"] = True
            mod.AUTHORITY["buyer_contact_authorized"] = True
            mod._core.EXPECTED_SOURCE_GENERATION["rfp_page_count"] = 999_999
            mod._core.PROPOSAL_DEADLINE_UTC = "2000-01-01T00:00:00Z"
            mod._core.QUESTION_DEADLINE_UTC = "2000-01-01T00:00:00Z"

            packet = mod.compile_production(fixture())
            self.assertFalse(packet["decision"]["authority"]["partner_contact_authorized"])
            self.assertFalse(packet["decision"]["authority"]["buyer_contact_authorized"])
            self.assertEqual(packet["rfp_number"], "09112026")
            self.assertEqual(packet["proposal_deadline_utc"], "2026-10-16T19:30:00Z")
            self.assertEqual(packet["question_deadline_utc"], "2026-09-25T22:00:00Z")
            self.assertEqual(packet["source_generation"]["rfp_page_count"], 31)
            self.assertTrue(mod.verify_packet_current(packet))
        finally:
            mod._core.AUTHORITY.clear()
            mod._core.AUTHORITY.update(authority)
            mod._core.EXPECTED_SOURCE_GENERATION.clear()
            mod._core.EXPECTED_SOURCE_GENERATION.update(expected_source)
            mod._core.PROPOSAL_DEADLINE_UTC = proposal_deadline
            mod._core.QUESTION_DEADLINE_UTC = question_deadline

    def test_current_verify_ignores_public_core_mutation_between_compile_and_verify(self) -> None:
        packet = mod.compile_production(fixture())
        authority = copy.deepcopy(mod._core.AUTHORITY)
        expected_source = copy.deepcopy(mod._core.EXPECTED_SOURCE_GENERATION)
        proposal_deadline = mod._core.PROPOSAL_DEADLINE_UTC
        try:
            mod._core.AUTHORITY["partner_contact_authorized"] = True
            mod._core.EXPECTED_SOURCE_GENERATION["rfp_page_count"] = 888
            mod._core.PROPOSAL_DEADLINE_UTC = "2000-01-01T00:00:00Z"
            self.assertTrue(mod.verify_packet_current(packet))
        finally:
            mod._core.AUTHORITY.clear()
            mod._core.AUTHORITY.update(authority)
            mod._core.EXPECTED_SOURCE_GENERATION.clear()
            mod._core.EXPECTED_SOURCE_GENERATION.update(expected_source)
            mod._core.PROPOSAL_DEADLINE_UTC = proposal_deadline

    def test_current_verify_rejects_dict_subclass_generation_switch(self) -> None:
        good = mod.compile_production(fixture())
        forged = copy.deepcopy(good)
        forged["internal_workshare_target_usd"] = 999_999
        forged["packet_receipt_sha256"] = "0" * 64

        class SwapOnFifthRead(dict):
            def __init__(self, first, second):
                super().__init__(first)
                self.second = second
                self.reads = 0

            def __getitem__(self, key):
                self.reads += 1
                if self.reads == 5:
                    self.clear()
                    self.update(self.second)
                return super().__getitem__(key)

        hostile = SwapOnFifthRead(good, forged)
        with self.assertRaisesRegex(mod.InputError, "non-exact JSON value type"):
            mod.verify_packet_current(hostile)
        self.assertEqual(hostile["internal_workshare_target_usd"], good["internal_workshare_target_usd"])

    def test_current_compile_rejects_dict_subclass_input_hooks(self) -> None:
        class HostileDict(dict):
            pass

        with self.assertRaisesRegex(mod.InputError, "non-exact JSON value type"):
            mod.compile_production(HostileDict(fixture()))

    def test_current_verify_rejects_future_evaluation(self) -> None:
        value = fixture()
        future = datetime.now(timezone.utc) + timedelta(days=1)
        value["evaluated_at_utc"] = utc_text(future)
        packet = mod.compile_qualification(value)
        with self.assertRaisesRegex(mod.InputError, "ahead of trusted"):
            mod.verify_packet_current(packet)

    def test_owner_renderer_is_current_and_historical_renderer_is_visibly_labeled(self) -> None:
        packet = mod.compile_production(fixture())
        current = mod.render_markdown(packet)
        self.assertIn("CURRENT qualification", current)
        self.assertIn("CURRENT AUTHORITY CHECK PASSED", current)

        historical = mod.render_markdown_historical(packet)
        self.assertIn("historical qualification snapshot", historical)
        self.assertIn("HISTORICAL / INTEGRITY ONLY", historical)
        self.assertIn("NOT CURRENT AUTHORITY", historical)

    def test_current_renderer_rejects_future_historical_packet(self) -> None:
        value = fixture()
        value["evaluated_at_utc"] = utc_text(datetime.now(timezone.utc) + timedelta(days=1))
        packet = mod.compile_qualification(value)
        historical = mod.render_markdown_historical(packet)
        self.assertIn("HISTORICAL / INTEGRITY ONLY", historical)
        with self.assertRaisesRegex(mod.InputError, "ahead of trusted"):
            mod.render_markdown(packet)

    def test_historical_deadline_semantics_remain_explicit_time_replay_only(self) -> None:
        value = fixture()
        value["evaluated_at_utc"] = mod.PROPOSAL_DEADLINE_UTC
        packet = mod.compile_qualification(value)
        self.assertEqual(packet["decision"]["status"], "NO_BID")
        self.assertIn("PROPOSAL_DEADLINE_PASSED", packet["decision"]["blockers"])
        self.assertTrue(mod.verify_packet(packet))

    def test_receipt_recomputation_covers_currentness_blockers(self) -> None:
        packet = mod.compile_qualification(fixture())
        forged = copy.deepcopy(packet)
        forged["decision"]["blockers"].append("POST_ADDENDUM_SOURCE_RECHECK_REQUIRED")
        unsigned_decision = copy.deepcopy(forged["decision"])
        unsigned_decision.pop("decision_receipt_sha256")
        forged["decision"]["decision_receipt_sha256"] = mod.sha256_obj(unsigned_decision)
        unsigned_packet = copy.deepcopy(forged)
        unsigned_packet.pop("packet_receipt_sha256")
        forged["packet_receipt_sha256"] = mod.sha256_obj(unsigned_packet)
        with self.assertRaisesRegex(mod.InputError, "semantic verification"):
            mod.verify_packet(forged)


if __name__ == "__main__":
    unittest.main()
