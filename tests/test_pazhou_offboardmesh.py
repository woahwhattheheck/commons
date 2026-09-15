from __future__ import annotations

from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "competitions" / "pazhou_overseas_offboardmesh_2026" / "offboardmesh.py"
EXAMPLE_PATH = ROOT / "competitions" / "pazhou_overseas_offboardmesh_2026" / "example-candidate.json"

spec = importlib.util.spec_from_file_location("offboardmesh", MODULE_PATH)
assert spec and spec.loader
offboardmesh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offboardmesh)


def candidate():
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


class OffboardMeshTests(unittest.TestCase):
    def test_compile_is_deterministic(self):
        value = candidate()
        self.assertEqual(offboardmesh.compile_packet(value), offboardmesh.compile_packet(deepcopy(value)))

    def test_current_packet_verifies(self):
        value = candidate()
        result = offboardmesh.verify_packet(value, offboardmesh.compile_packet(value))
        self.assertTrue(result["validCurrent"])
        self.assertFalse(result["validHistorical"])
        self.assertFalse(result["externalSendAuthorized"])

    def test_prior_plan_is_historical_not_current(self):
        old = candidate()
        packet = offboardmesh.compile_packet(old)
        new = deepcopy(old)
        new["planVersion"] = "PLAN-V4"
        result = offboardmesh.verify_packet(new, packet)
        self.assertFalse(result["validCurrent"])
        self.assertTrue(result["validHistorical"])

    def test_same_plan_mutation_is_neither_current_nor_historical(self):
        value = candidate()
        packet = offboardmesh.compile_packet(value)
        changed = deepcopy(value)
        changed["modelProposal"]["suggestions"][0]["summary"] = "Changed owner-review wording."
        result = offboardmesh.verify_packet(changed, packet)
        self.assertFalse(result["validCurrent"])
        self.assertFalse(result["validHistorical"])

    def test_packet_tamper_fails_integrity(self):
        value = candidate()
        packet = offboardmesh.compile_packet(value)
        packet["tasks"][0]["executionAuthorized"] = True
        result = offboardmesh.verify_packet(value, packet)
        self.assertFalse(result["packetIntegrityValid"])
        self.assertFalse(result["validCurrent"])

    def test_all_authority_bits_are_false(self):
        packet = offboardmesh.compile_packet(candidate())
        self.assertTrue(packet["authority"])
        self.assertTrue(all(value is False for value in packet["authority"].values()))
        self.assertTrue(all(task["executionAuthorized"] is False for task in packet["tasks"]))

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

    def test_future_evidence_is_rejected(self):
        value = candidate()
        value["evidence"][0]["observedAt"] = "2026-09-10T12:00:01.000Z"
        with self.assertRaisesRegex(offboardmesh.OffboardMeshError, "FUTURE_EVIDENCE"):
            offboardmesh.compile_packet(value)

    def test_stale_evidence_is_rejected(self):
        value = candidate()
        value["evidence"][0]["observedAt"] = "2026-08-20T00:00:00.000Z"
        with self.assertRaisesRegex(offboardmesh.OffboardMeshError, "STALE_EVIDENCE"):
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

    def test_owner_supplied_evidence_is_required(self):
        value = candidate()
        value["evidence"][0]["ownerSupplied"] = False
        with self.assertRaisesRegex(offboardmesh.OffboardMeshError, "OWNER_SUPPLIED_EVIDENCE_REQUIRED"):
            offboardmesh.compile_packet(value)

    def test_cli_round_trip(self):
        value = candidate()
        packet = offboardmesh.compile_packet(value)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "packet.json"
            path.write_text(json.dumps(packet), encoding="utf-8")
            self.assertEqual(offboardmesh.main(["verify", str(EXAMPLE_PATH), str(path)]), 0)


if __name__ == "__main__":
    unittest.main()
