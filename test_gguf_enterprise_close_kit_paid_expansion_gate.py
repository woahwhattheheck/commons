from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULE = ROOT / "revenue" / "gguf_enterprise_close_kit" / "close_kit.py"
INTAKE = ROOT / "revenue" / "gguf_enterprise_close_kit" / "sample_intake.json"
EVIDENCE = ROOT / "revenue" / "gguf_enterprise_close_kit" / "sample_evidence.json"

spec = importlib.util.spec_from_file_location("gguf_close_kit_paid_expansion_gate_test", MODULE)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class GgufPaidExpansionGateTests(unittest.TestCase):
    def test_at_complete_m1_only_packet_cannot_promote_paid_expansion(self) -> None:
        intake = load(INTAKE)
        intake["mode"] = "CUSTOMER_PRIVATE"
        intake["scope"]["data_classification"] = "PRIVATE_CUSTOMER_CONTROLLED"
        for key in intake["customer_readiness"]:
            intake["customer_readiness"][key] = True
        intake["evidence_refs"] = {
            "nda_sha256": "2" * 64,
            "sow_sha256": "3" * 64,
            "m1_sha256": "4" * 64,
        }

        packet = mod.compile_packet(intake, load(EVIDENCE))

        self.assertEqual(packet["terminal_state"], "READY_FOR_OWNER_M2_ACCEPTANCE_REVIEW")
        self.assertTrue(packet["acceptance"]["all_at1_at6_evidence_complete"])
        self.assertEqual(packet["milestones"]["M1"], "OWNER_REPORTED_EVIDENCE_PRESENT")
        self.assertEqual(packet["milestones"]["M2"], "READY_FOR_OWNER_ACCEPTANCE_REVIEW")
        self.assertFalse(packet["acceptance"]["legal_acceptance_claimed"])
        self.assertFalse(packet["expansion"]["white_box_30d_discussion_ready"])
        self.assertFalse(packet["expansion"]["expansion_accepted"])
        self.assertTrue(all(value is False for value in packet["authority"].values()))
        self.assertFalse(packet["truth"]["build_is_payment"])
        self.assertFalse(packet["truth"]["build_is_revenue"])
        mod.verify_packet(packet)


if __name__ == "__main__":
    unittest.main()
