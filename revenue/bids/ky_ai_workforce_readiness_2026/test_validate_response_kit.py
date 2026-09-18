from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from validate_response_kit import (  # noqa: E402
    REQUIRED_GATE_IDS,
    evaluate_manifest,
    load_manifest_text,
)


class ResponseKitValidatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.current = load_manifest_text((HERE / "readiness_manifest.json").read_text(encoding="utf-8"))

    def test_current_manifest_is_hold(self) -> None:
        result = evaluate_manifest(copy.deepcopy(self.current))
        self.assertEqual(result.status, "HOLD")
        states = {gate.gate_id: gate.state for gate in result.gates}
        self.assertEqual(states["source_freshness"], "RESOLVED")
        self.assertEqual(states["partner_legal_role_and_consent"], "OPEN")
        self.assertEqual(states["commercial_model_and_approved_prices"], "DRAFTED")

    def test_all_resolved_with_real_evidence_is_ready(self) -> None:
        payload = copy.deepcopy(self.current)
        for gate in payload["gates"]:
            gate["state"] = "RESOLVED"
            gate["evidence"] = f"verified evidence receipt for {gate['id']}"
        self.assertEqual(evaluate_manifest(payload).status, "READY")

    def test_missing_gate_is_invalid(self) -> None:
        payload = copy.deepcopy(self.current)
        payload["gates"] = payload["gates"][:-1]
        with self.assertRaisesRegex(ValueError, "missing required gate"):
            evaluate_manifest(payload)

    def test_extra_gate_is_invalid(self) -> None:
        payload = copy.deepcopy(self.current)
        payload["gates"].append(
            {"id": "invented_gate", "mandatory": True, "state": "OPEN", "evidence": ""}
        )
        with self.assertRaisesRegex(ValueError, "unexpected gate"):
            evaluate_manifest(payload)

    def test_duplicate_gate_id_is_invalid(self) -> None:
        payload = copy.deepcopy(self.current)
        payload["gates"].append(copy.deepcopy(payload["gates"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate gate id"):
            evaluate_manifest(payload)

    def test_duplicate_json_key_is_invalid(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            load_manifest_text('{"schema_version":1,"schema_version":1,"gates":[]}')

    def test_resolved_without_evidence_is_invalid(self) -> None:
        payload = copy.deepcopy(self.current)
        gate = payload["gates"][2]
        gate["state"] = "RESOLVED"
        gate["evidence"] = ""
        with self.assertRaisesRegex(ValueError, "requires evidence"):
            evaluate_manifest(payload)

    def test_open_with_pseudo_evidence_is_invalid(self) -> None:
        payload = copy.deepcopy(self.current)
        gate = payload["gates"][2]
        gate["evidence"] = "someone probably agreed"
        with self.assertRaisesRegex(ValueError, "OPEN must not carry pseudo-evidence"):
            evaluate_manifest(payload)

    def test_resolved_placeholder_is_invalid(self) -> None:
        payload = copy.deepcopy(self.current)
        gate = payload["gates"][2]
        gate["state"] = "RESOLVED"
        gate["evidence"] = "[OPEN] replace with partner consent"
        with self.assertRaisesRegex(ValueError, "placeholder token"):
            evaluate_manifest(payload)

    def test_invalid_state_is_rejected(self) -> None:
        payload = copy.deepcopy(self.current)
        payload["gates"][0]["state"] = "MAYBE"
        with self.assertRaisesRegex(ValueError, "invalid state"):
            evaluate_manifest(payload)

    def test_nonmandatory_required_gate_is_rejected(self) -> None:
        payload = copy.deepcopy(self.current)
        payload["gates"][0]["mandatory"] = False
        with self.assertRaisesRegex(ValueError, "mandatory=true"):
            evaluate_manifest(payload)

    def test_manifest_contains_exact_contract_set(self) -> None:
        self.assertEqual({gate["id"] for gate in self.current["gates"]}, REQUIRED_GATE_IDS)


if __name__ == "__main__":
    unittest.main()
