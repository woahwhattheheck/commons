import copy
import json
import unittest
from pathlib import Path

import packet_gate as gate

ROOT = Path(__file__).resolve().parent


def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def requirement(matrix, rid):
    return next(row for row in matrix["requirements"] if row["id"] == rid)


class PacketGapInventoryTests(unittest.TestCase):
    def setUp(self):
        self.sources = load("sources.json")
        self.matrix = load("matrix.json")

    def test_deleting_required_forms_is_rejected(self):
        matrix = copy.deepcopy(self.matrix)
        matrix["requirements"] = [
            row for row in matrix["requirements"] if row["id"] != "required_forms"
        ]

        with self.assertRaisesRegex(
            gate.GateError,
            r"packet-required requirement set drift: .*required_forms",
        ):
            gate.build_receipt(self.sources, matrix)

    def test_reclassifying_references_is_rejected(self):
        matrix = copy.deepcopy(self.matrix)
        requirement(matrix, "references")["classification"] = "INFORMATIONAL"

        with self.assertRaisesRegex(
            gate.GateError,
            "packet-required requirement identity drift: references",
        ):
            gate.build_receipt(self.sources, matrix)

    def test_rewriting_packet_gap_text_is_rejected(self):
        matrix = copy.deepcopy(self.matrix)
        requirement(matrix, "insurance")["requirement"] = "No insurance evidence is needed."

        with self.assertRaisesRegex(
            gate.GateError,
            "packet-required requirement identity drift: insurance",
        ):
            gate.build_receipt(self.sources, matrix)

    def test_removing_packet_gap_source_binding_is_rejected(self):
        matrix = copy.deepcopy(self.matrix)
        requirement(matrix, "addenda_acknowledgement")["source_ids"] = []

        with self.assertRaisesRegex(
            gate.GateError,
            "packet-required requirement identity drift: addenda_acknowledgement",
        ):
            gate.build_receipt(self.sources, matrix)

    def test_unknown_packet_gap_cannot_expand_trusted_inventory(self):
        matrix = copy.deepcopy(self.matrix)
        matrix["requirements"].append(
            {
                "id": "invented_packet_gap",
                "classification": "MANDATORY",
                "state": "PACKET_REQUIRED",
                "source_ids": [],
                "requirement": "Caller-invented packet gap.",
            }
        )

        with self.assertRaisesRegex(
            gate.GateError,
            "untrusted packet-required requirement id: invented_packet_gap",
        ):
            gate.build_receipt(self.sources, matrix)

    def test_canonical_receipt_preserves_hold_and_full_gap_inventory(self):
        receipt = gate.build_receipt(self.sources, self.matrix)

        self.assertEqual(receipt["decision"], "HOLD_PACKET_REQUIRED")
        self.assertEqual(receipt["state"], "EVIDENCE_MATRIX_READY_PACKET_BLOCKED")
        self.assertEqual(len(receipt["packet_required_ids"]), 14)
        self.assertIn("required_forms", receipt["mandatory_packet_required_ids"])
        self.assertIn("references", receipt["mandatory_packet_required_ids"])
        self.assertIn("references", receipt["scoreable_packet_required_ids"])
        self.assertTrue(receipt["authorities"])
        self.assertTrue(all(value is False for value in receipt["authorities"].values()))
        self.assertTrue(gate.verify_receipt(receipt, self.sources, self.matrix))


if __name__ == "__main__":
    unittest.main()
