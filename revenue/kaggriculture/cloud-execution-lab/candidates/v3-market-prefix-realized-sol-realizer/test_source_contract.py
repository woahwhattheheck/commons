# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from source_contract import load_json


class SourceContractTests(unittest.TestCase):
    def test_duplicate_json_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text('{"x":1,"x":2}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                load_json(path)

    def test_source_contract_declares_action_excluding_state_phase(self):
        data = load_json(Path(__file__).with_name("SOURCE.json"))
        self.assertEqual(
            data["invariants"]["state_receipt_phase"],
            "post interpreter with submitted actions excluded",
        )
        self.assertEqual(data["invariants"]["expected_candidate_actions"], 719)


if __name__ == "__main__":
    unittest.main()
