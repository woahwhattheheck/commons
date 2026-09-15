from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
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

FIXTURE_NOW = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)
STALE_NOW = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)


def candidate():
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def verify_current_at(value, packet, when=FIXTURE_NOW):
    with patch.object(offboardmesh, "_now_utc", return_value=when):
        return offboardmesh.verify_current(value, packet)


class OffboardMeshTests(unittest.TestCase):
    def test_compile_is_deterministic(self):
        value = candidate()
        self.assertEqual(offboardmesh.compile_packet(value), offboardmesh.compile_packet(deepcopy(value)))

    def test_current_packet_verifies_against_verifier_owned_now(self):
        value = candidate()
        result = verify_current_at(value, offboardmesh.compile_packet(value))
        self.assertTrue(result["validCurrent"])
        self.assertTrue(result["currentEvidenceFresh"])
        self.assertFalse(result["externalSendAuthorized"])

    def test_historical_replay_verifies_same_candidate_without_current_claim(self):
        value = candidate()
        result = offboardmesh.verify_historical(value, offboardmesh.compile_packet(value))
        self.assertTrue(result["validHistorical"])
        self.assertFalse(result["externalSendAuthorized"])

    def test_stale_now_fresh_then_is_historical_not_current(self):
        value = candidate()
        packet = offboardmesh.compile_packet(value)
        current = verify_current_at(value, packet, STALE_NOW)
        historical = offboardmesh.verify_historical(value, packet)
        self.assertFalse(current["validCurrent"])
        self.assertFalse(current["currentEvidenceFresh"])
        self.assertTrue(historical["validHistorical"])

    def test_prior_plan_candidate_is_not_exact_historical_replay(self):
        old = candidate()
        packet = offboardmesh.compile_packet(old)
        new = deepcopy(old)
        new["planVersion"] = "PLAN-V4"
        self.assertFalse(verify_current_at(new, packet)["validCurrent"])
        self.assertFalse(offboardmesh.verify_historical(new, packet)["validHistorical"])

    def test_same_plan_mutation_is_neither_current_nor_historical(self):
        value = candidate()
        packet = offboardmesh.compile_packet(value)
        changed = deepcopy(value)
        changed["modelProposal"]["suggestions"][0]["summary"] = "Changed owner-review wording."
        self.assertFalse(verify_current_at(changed, packet)["validCurrent"])
        self.assertFalse(offboardmesh.verify_historical(changed, packet)["validHistorical"])

    def test_packet_tamper_fails_integrity(self):
        value = candidate()
        packet = offboardmesh.compile_packet(value)
        packet["tasks"][0]["executionAuthorized"] = True
        result = verify_current_at(value, packet)
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
        value = candidate()
        packet = offboardmesh.compile_packet(value)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "packet.json"
            path.write_text(json.dumps(packet), encoding="utf-8")
            with patch.object(offboardmesh, "_now_utc", return_value=FIXTURE_NOW), redirect_stdout(io.StringIO()):
                self.assertEqual(offboardmesh.main(["verify-current", str(EXAMPLE_PATH), str(path)]), 0)

    def test_cli_stale_now_fresh_then_fails_current_but_passes_historical(self):
        value = candidate()
        packet = offboardmesh.compile_packet(value)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "packet.json"
            path.write_text(json.dumps(packet), encoding="utf-8")
            with patch.object(offboardmesh, "_now_utc", return_value=STALE_NOW), redirect_stdout(io.StringIO()):
                self.assertEqual(offboardmesh.main(["verify-current", str(EXAMPLE_PATH), str(path)]), 2)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(offboardmesh.main(["verify-historical", str(EXAMPLE_PATH), str(path)]), 0)


if __name__ == "__main__":
    unittest.main()
