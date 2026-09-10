# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


def read_json(name: str):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def inner_receipt(payload: dict) -> str:
    body = dict(payload)
    claimed = body.pop("receipt_sha256")
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    actual = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    if actual != claimed:
        raise AssertionError(f"receipt mismatch: {actual} != {claimed}")
    return actual


class DurableReceiptTests(unittest.TestCase):
    def test_source_packet_receipt_closes_exact_preimage(self):
        row = read_json("SOURCE-PACKET-WITNESS.json")
        self.assertEqual(inner_receipt(row), "b7d213b1e70d570f282be944373dca9afdb23446848b521a6dca6ff69c8dc985")
        self.assertEqual(row["packet_sha256"], "f68792bf7f0fb269864ef4ab25967292e2d4cd03439dbc5c52b98dfcebd1b728")
        self.assertEqual(row["member_sha256"]["l01_mechanics.py"], "65fc1841f6d00b6db78e2eb88d98e9e7b05053502e0de527bce1f1a60fbe9691")
        self.assertEqual(row["manifest_base"]["sha256"], "a055fd56ca5821208096f37787f77dbdddc2f65c14c24132d6e219a05e6f02ba")
        self.assertEqual(row["l01_main_tape"], "7015cc00acfa4922")

    def test_official_engine_receipt_closes_execution_witness(self):
        row = read_json("L01-DAY0-ENGINE-WITNESS.json")
        self.assertEqual(inner_receipt(row), "5fb0abf33b2ffd1930fc1fd41e68511b6a74d9c4b5ef9e1139d9410212577d45")
        self.assertEqual(row["control"]["shed"], {"WHEAT": 13})
        self.assertEqual(row["shipped"]["shed"], {"WHEAT": 2})
        self.assertEqual(row["control_minus_shipped_wheat"], 11)
        issues = row["source_certificate"]["issues"]
        self.assertEqual(sum(issue["code"] == "unsupported_product" for issue in issues), 5)

    def test_panel_receipt_preserves_every_negative_cell(self):
        row = read_json("L01-DAY0-PANEL.json")
        self.assertEqual(inner_receipt(row), "a42d8c409c1bd69e2719331960707473bdfcdb43cf145e8d2ef0d8f73fb332da")
        self.assertEqual(row["cells"], 8)
        self.assertEqual(row["games"], 16)
        self.assertEqual(row["changed_action_cells"], 8)
        self.assertEqual(row["new_losses"], 8)
        self.assertEqual(row["lost_wins"], 8)
        self.assertEqual(row["margin_delta"]["negative"], 8)
        self.assertEqual(row["margin_delta"]["positive"], 0)
        self.assertEqual(row["margin_delta"]["mean"], -16688.25)
        self.assertTrue(all(pair["control_outcome"] == "W" for pair in row["pairs"]))
        self.assertTrue(all(pair["shipped_outcome"] == "L" for pair in row["pairs"]))
        self.assertTrue(all(pair["margin_delta"] < 0 for pair in row["pairs"]))

    def test_positive_own_mean_is_not_misreported_as_strength(self):
        row = read_json("L01-DAY0-PANEL.json")
        self.assertGreater(row["own_delta"]["mean"], 0)
        self.assertLess(row["margin_delta"]["mean"], 0)
        self.assertEqual(row["new_losses"], row["cells"])

    def test_carrier_receipt_binds_every_payload_file(self):
        receipt = read_json("RECEIPT.json")
        inner_receipt(receipt)
        for relative, expected in receipt["files"].items():
            with self.subTest(relative=relative):
                data = (HERE / relative).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
