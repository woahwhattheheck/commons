from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "competitions" / "pazhou_overseas_offboardmesh_2026" / "offboardmesh.py"
EXAMPLE_PATH = ROOT / "competitions" / "pazhou_overseas_offboardmesh_2026" / "example-candidate.json"

spec = importlib.util.spec_from_file_location("offboardmesh_binding", MODULE_PATH)
assert spec and spec.loader
offboardmesh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(offboardmesh)

FIXTURE_NOW = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)


def candidate():
    return json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))


def reseal(packet):
    unsigned = {k: v for k, v in packet.items() if k != "receiptSha256"}
    packet["receiptSha256"] = offboardmesh._digest(unsigned)
    return packet


class OffboardMeshCompilerBindingTests(unittest.TestCase):
    def assert_forgery_rejected(self, mutate):
        value = candidate()
        packet = offboardmesh.compile_packet(value)
        mutate(packet)
        reseal(packet)
        historical = offboardmesh.verify_historical(value, packet)
        with patch.object(offboardmesh, "_now_utc", return_value=FIXTURE_NOW):
            current = offboardmesh.verify_current(value, packet)
        self.assertTrue(historical["packetIntegrityValid"])
        self.assertTrue(current["packetIntegrityValid"])
        self.assertFalse(historical["compilerProjectionMatches"])
        self.assertFalse(current["compilerProjectionMatches"])
        self.assertFalse(historical["validHistorical"])
        self.assertFalse(current["validCurrent"])

    def test_recomputed_receipt_cannot_forge_task_summary(self):
        self.assert_forgery_rejected(lambda packet: packet["tasks"][0].__setitem__("summary", "FORGED OWNER-REVIEW CONTENT"))

    def test_recomputed_receipt_cannot_forge_task_owner(self):
        self.assert_forgery_rejected(lambda packet: packet["tasks"][0].__setitem__("ownerRef", "OWNER-FORGED"))

    def test_recomputed_receipt_cannot_forge_task_evidence_refs(self):
        self.assert_forgery_rejected(lambda packet: packet["tasks"][0].__setitem__("evidenceRefs", ["EV-FORGED-001"]))

    def test_recomputed_receipt_cannot_forge_binding_digest_or_count(self):
        def mutate(packet):
            packet["bindings"]["tasksSha256"] = "0" * 64
            packet["bindings"]["taskCount"] += 7
            packet["bindings"]["evidenceCount"] += 3
        self.assert_forgery_rejected(mutate)

    def test_recomputed_receipt_cannot_forge_source_fields(self):
        def mutate(packet):
            packet["source"]["requestedAt"] = "2026-09-10T11:59:59.000Z"
            packet["source"]["sourceModelRef"] = "MODEL-FORGED"
        self.assert_forgery_rejected(mutate)

    def test_exact_compiler_output_is_correspondent(self):
        value = candidate()
        packet = offboardmesh.compile_packet(value)
        historical = offboardmesh.verify_historical(value, deepcopy(packet))
        with patch.object(offboardmesh, "_now_utc", return_value=FIXTURE_NOW):
            current = offboardmesh.verify_current(value, deepcopy(packet))
        self.assertTrue(historical["compilerProjectionMatches"])
        self.assertTrue(current["compilerProjectionMatches"])
        self.assertTrue(historical["validHistorical"])
        self.assertTrue(current["validCurrent"])


if __name__ == "__main__":
    unittest.main()
