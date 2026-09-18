from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import inspect
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "competitions" / "pazhou_overseas_offboardmesh_2026" / "offboardmesh.py"
EXAMPLE_PATH = ROOT / "competitions" / "pazhou_overseas_offboardmesh_2026" / "example-candidate.json"

spec = importlib.util.spec_from_file_location("offboardmesh", MODULE_PATH)
assert spec and spec.loader
offboardmesh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offboardmesh)


def candidate():
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _windowed_candidate(requested: datetime, closeout: datetime):
    value = candidate()
    value["requestedAt"] = _iso(requested)
    value["requestedCloseoutAt"] = _iso(closeout)
    value["modelProposal"]["generatedAt"] = _iso(requested + timedelta(minutes=1))
    for index, evidence in enumerate(value["evidence"], start=1):
        evidence["observedAt"] = _iso(requested - timedelta(minutes=index))
    return value


def current_candidate():
    now = datetime.now(timezone.utc)
    return _windowed_candidate(now - timedelta(minutes=5), now + timedelta(hours=1))


def historical_candidate():
    requested = datetime(2000, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
    return _windowed_candidate(requested, requested + timedelta(days=10))


class ForgedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        forged = datetime(2000, 1, 11, 12, 0, 0, tzinfo=timezone.utc)
        return forged if tz is None else forged.astimezone(tz)


class OffboardMeshTests(unittest.TestCase):
    def test_compile_is_deterministic(self):
        value = candidate()
        self.assertEqual(offboardmesh.compile_packet(value), offboardmesh.compile_packet(deepcopy(value)))

    def test_current_packet_verifies_against_captured_process_clock(self):
        value = current_candidate()
        result = offboardmesh.verify_current(value, offboardmesh.compile_packet(value))
        self.assertTrue(result["validCurrent"])
        self.assertTrue(result["currentEvidenceFresh"])
        self.assertFalse(result["externalSendAuthorized"])

    def test_public_current_verifier_has_no_evaluation_time_parameter(self):
        self.assertEqual(list(inspect.signature(offboardmesh.verify_current).parameters), ["candidate", "packet"])

    def test_historical_replay_verifies_same_candidate_without_current_claim(self):
        value = historical_candidate()
        result = offboardmesh.verify_historical(value, offboardmesh.compile_packet(value))
        self.assertTrue(result["validHistorical"])
        self.assertFalse(result["externalSendAuthorized"])

    def test_stale_now_fresh_then_is_historical_not_current(self):
        value = historical_candidate()
        packet = offboardmesh.compile_packet(value)
        current = offboardmesh.verify_current(value, packet)
        historical = offboardmesh.verify_historical(value, packet)
        self.assertFalse(current["validCurrent"])
        self.assertFalse(current["currentEvidenceFresh"])
        self.assertTrue(historical["validHistorical"])

    def test_rebinding_now_helper_cannot_regain_current(self):
        value = historical_candidate()
        packet = offboardmesh.compile_packet(value)
        forged = datetime(2000, 1, 11, 12, 0, 0, tzinfo=timezone.utc)
        with patch.object(offboardmesh, "_now_utc", return_value=forged, create=True):
            result = offboardmesh.verify_current(value, packet)
        self.assertFalse(result["validCurrent"])
        self.assertFalse(result["currentEvidenceFresh"])

    def test_rebinding_native_datetime_cannot_regain_current(self):
        value = historical_candidate()
        packet = offboardmesh.compile_packet(value)
        with patch.object(offboardmesh, "_NATIVE_DATETIME", ForgedDateTime):
            result = offboardmesh.verify_current(value, packet)
        self.assertFalse(result["validCurrent"])
        self.assertFalse(result["currentEvidenceFresh"])

    def test_rebinding_max_evidence_age_cannot_regain_current(self):
        value = historical_candidate()
        packet = offboardmesh.compile_packet(value)
        with patch.object(offboardmesh, "_MAX_EVIDENCE_AGE_SECONDS", 10**18):
            result = offboardmesh.verify_current(value, packet)
        self.assertFalse(result["validCurrent"])
        self.assertFalse(result["currentEvidenceFresh"])

    def test_rebinding_currentness_helper_cannot_regain_current(self):
        value = historical_candidate()
        packet = offboardmesh.compile_packet(value)
        with patch.object(offboardmesh, "_is_current", return_value=True, create=True):
            result = offboardmesh.verify_current(value, packet)
        self.assertFalse(result["validCurrent"])
        self.assertFalse(result["currentEvidenceFresh"])

    def test_prior_plan_candidate_is_not_exact_historical_replay(self):
        old = current_candidate()
        packet = offboardmesh.compile_packet(old)
        new = deepcopy(old)
        new["planVersion"] = "PLAN-V4"
        self.assertFalse(offboardmesh.verify_current(new, packet)["validCurrent"])
        self.assertFalse(offboardmesh.verify_historical(new, packet)["validHistorical"])

    def test_same_plan_mutation_is_neither_current_nor_historical(self):
        value = current_candidate()
        packet = offboardmesh.compile_packet(value)
        changed = deepcopy(value)
        changed["modelProposal"]["suggestions"][0]["summary"] = "Changed owner-review wording."
        self.assertFalse(offboardmesh.verify_current(changed, packet)["validCurrent"])
        self.assertFalse(offboardmesh.verify_historical(changed, packet)["validHistorical"])

    def test_packet_tamper_fails_integrity(self):
        value = current_candidate()
        packet = offboardmesh.compile_packet(value)
        packet["tasks"][0]["executionAuthorized"] = True
        result = offboardmesh.verify_current(value, packet)
        self.assertFalse(result["packetIntegrityValid"])
        self.assertFalse(result["validCurrent"])

    def test_all_authority_bits_are_false(self):
        packet = offboardmesh.compile_packet(candidate())
        self.assertTrue(packet["authority"])
        self.assertTrue(all(value is False for value in packet["authority"].values()))
        self.assertTrue(all(task["executionAuthorized"] is False for task in packet["tasks"]))
        self.assertTrue(all(task["reviewState"] == "OWNER_REVIEW_REQUIRED" for task in packet["tasks"]))

    def test_caller_owner_assertion_does_not_mint_owner_provenance(self):
        value = candidate()
        value["evidence"][0]["ownerSupplied"] = True
        packet = offboardmesh.compile_packet(value)
        self.assertFalse(packet["truth"]["ownerEvidenceBound"])
        self.assertTrue(packet["truth"]["evidenceDigestBound"])
        self.assertEqual(packet["truth"]["evidenceProvenance"], "CALLER_ASSERTED_UNVERIFIED")

        not_claimed = candidate()
        not_claimed["evidence"][0]["ownerSupplied"] = False
        second = offboardmesh.compile_packet(not_claimed)
        self.assertFalse(second["truth"]["ownerEvidenceBound"])
        self.assertEqual(second["truth"]["evidenceProvenance"], "CALLER_ASSERTED_UNVERIFIED")

    def test_owner_supplied_assertion_must_be_boolean(self):
        value = candidate()
        value["evidence"][0]["ownerSupplied"] = "yes"
        with self.assertRaisesRegex(offboardmesh.OffboardMeshError, "OWNER_SUPPLIED_ASSERTION_INVALID"):
            offboardmesh.compile_packet(value)

    def test_non_proposal_model_state_is_rejected(self):
        value = candidate()
        value["modelProposal"]["suggestions"][0]["proposedState"] = "EXECUTE"
        with self.assertRaisesRegex(offboardmesh.OffboardMeshError, "MODEL_STATE_MUST_BE_PROPOSAL_ONLY"):
            offboardmesh.compile_packet(value)

    def test_unknown_evidence_ref_is_rejected(self):
        value = candidate()
        value["modelProposal"]["suggestions"][0]["evidenceRefs"] = ["EV-NOT-THERE"]
        with self.assertRaisesRegex(offboardmesh.OffboardMeshError, "UNKNOWN_EVIDENCE_REF"):
            offboardmesh.compile_packet(value)

    def test_duplicate_task_id_is_rejected(self):
        value = candidate()
        value["modelProposal"]["suggestions"].append(deepcopy(value["modelProposal"]["suggestions"][0]))
        with self.assertRaisesRegex(offboardmesh.OffboardMeshError, "DUPLICATE_TASK_ID"):
            offboardmesh.compile_packet(value)

    def test_duplicate_evidence_id_is_rejected(self):
        value = candidate()
        value["evidence"].append(deepcopy(value["evidence"][0]))
        with self.assertRaisesRegex(offboardmesh.OffboardMeshError, "DUPLICATE_EVIDENCE_ID"):
            offboardmesh.compile_packet(value)

    def test_future_evidence_is_rejected_at_request_boundary(self):
        value = candidate()
        value["evidence"][0]["observedAt"] = "2026-09-10T12:00:01.000Z"
        with self.assertRaisesRegex(offboardmesh.OffboardMeshError, "FUTURE_EVIDENCE"):
            offboardmesh.compile_packet(value)

    def test_stale_evidence_is_rejected_at_request_boundary(self):
        value = candidate()
        value["evidence"][0]["observedAt"] = "2026-08-20T00:00:00.000Z"
        with self.assertRaisesRegex(offboardmesh.OffboardMeshError, "STALE_EVIDENCE_AT_REQUEST"):
            offboardmesh.compile_packet(value)

    def test_contact_shaped_source_ref_is_rejected(self):
        value = candidate()
        value["evidence"][0]["sourceRef"] = "ops@example.com"
        with self.assertRaisesRegex(offboardmesh.OffboardMeshError, "OPAQUE_REF_REQUIRED|CONTACT_OR_SECRET_SHAPED_REF"):
            offboardmesh.compile_packet(value)

    def test_secret_shaped_ref_is_rejected(self):
        value = candidate()
        value["evidence"][0]["sourceRef"] = "OWNER-SECRET-TOKEN-001"
        with self.assertRaisesRegex(offboardmesh.OffboardMeshError, "CONTACT_OR_SECRET_SHAPED_REF"):
            offboardmesh.compile_packet(value)

    def test_summary_contact_route_is_rejected(self):
        value = candidate()
        value["modelProposal"]["suggestions"][0]["summary"] = "Send result to https://example.com/hook"
        with self.assertRaisesRegex(offboardmesh.OffboardMeshError, "CONTACT_ROUTE_IN_SUMMARY"):
            offboardmesh.compile_packet(value)

    def test_unsupported_action_is_rejected(self):
        value = candidate()
        value["modelProposal"]["suggestions"][0]["actionClass"] = "DELETE_EVERYTHING"
        with self.assertRaisesRegex(offboardmesh.OffboardMeshError, "ACTION_CLASS_UNSUPPORTED"):
            offboardmesh.compile_packet(value)

    def test_cli_current_round_trip(self):
        value = current_candidate()
        packet = offboardmesh.compile_packet(value)
        with tempfile.TemporaryDirectory() as td:
            candidate_path = Path(td) / "candidate.json"
            packet_path = Path(td) / "packet.json"
            candidate_path.write_text(json.dumps(value), encoding="utf-8")
            packet_path.write_text(json.dumps(packet), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(offboardmesh.main(["verify-current", str(candidate_path), str(packet_path)]), 0)

    def test_cli_stale_now_fresh_then_fails_current_but_passes_historical(self):
        value = historical_candidate()
        packet = offboardmesh.compile_packet(value)
        with tempfile.TemporaryDirectory() as td:
            candidate_path = Path(td) / "candidate.json"
            packet_path = Path(td) / "packet.json"
            candidate_path.write_text(json.dumps(value), encoding="utf-8")
            packet_path.write_text(json.dumps(packet), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(offboardmesh.main(["verify-current", str(candidate_path), str(packet_path)]), 2)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(offboardmesh.main(["verify-historical", str(candidate_path), str(packet_path)]), 0)


if __name__ == "__main__":
    unittest.main()
