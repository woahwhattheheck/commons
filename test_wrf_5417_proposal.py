from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MODULE_PATH = ROOT / "revenue" / "wrf_5417_camera_ai" / "validate.py"
spec = importlib.util.spec_from_file_location("wrf_5417_validate", MODULE_PATH)
assert spec is not None and spec.loader is not None
validate_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_mod)


class ProposalGateTests(unittest.TestCase):
    def setUp(self):
        self.ledger = json.loads((MODULE_PATH.parent / "gate_ledger.json").read_text(encoding="utf-8"))

    def test_current_carrier_validates(self):
        validate_mod.validate()

    def test_repository_cannot_self_green_submission(self):
        changed = copy.deepcopy(self.ledger)
        changed["portal_submission"] = "READY"
        with self.assertRaises(validate_mod.ValidationError):
            validate_mod._validate_ledger(changed)

    def test_repository_cannot_claim_external_authority(self):
        changed = copy.deepcopy(self.ledger)
        changed["authority"]["proposal_submitted"] = True
        with self.assertRaises(validate_mod.ValidationError):
            validate_mod._validate_ledger(changed)

    def test_required_owner_gate_cannot_be_marked_verified(self):
        changed = copy.deepcopy(self.ledger)
        for gate in changed["gates"]:
            if gate["id"] == "minimum_contribution":
                gate["state"] = "VERIFIED"
                break
        with self.assertRaises(validate_mod.ValidationError):
            validate_mod._validate_ledger(changed)

    def test_sensitive_identifier_patterns_are_rejected(self):
        for text in (
            "taxpayer identification number: 123456789",
            "TIN=123456789",
            "12-3456789",
            "123-45-6789",
        ):
            matched = any(pattern.search(text) for pattern in validate_mod._FORBIDDEN_PATTERNS.values())
            self.assertTrue(matched, text)


if __name__ == "__main__":
    unittest.main()
