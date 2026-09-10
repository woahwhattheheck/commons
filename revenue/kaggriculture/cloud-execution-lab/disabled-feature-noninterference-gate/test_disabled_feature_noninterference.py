#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import copy
import io
import json
import math
import tempfile
import unittest
from pathlib import Path

import disabled_feature_noninterference as gate


PREDECESSOR = """\
class SpatialTempo:
    def transform(self, selected, state):
        if self._continue_weed(state):
            return selected
        if not self.pathing and not self.tempo:
            return selected
        return selected
"""

W0_REPAIR = """\
class SpatialTempo:
    def transform(self, selected, state):
        if (self.pathing or self.tempo) and self._continue_weed(state):
            return selected
        if not self.pathing and not self.tempo:
            return selected
        return selected
"""

EARLY_RETURN = """\
class SpatialTempo:
    def transform(self, selected, state):
        if not self.pathing and not self.tempo:
            return selected
        if self._continue_weed(state):
            return selected
        return selected
"""


def digest(character: str) -> str:
    return "sha256:" + character * 64


class GateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source_relative = "src/spatial_tempo.py"
        (self.root / "src").mkdir()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_source(self, text: str) -> bytes:
        data = text.encode("utf-8")
        (self.root / self.source_relative).write_bytes(data)
        return data

    def contract(
        self,
        text: str,
        *,
        expected: str,
        effects: list[dict[str, str]] | None = None,
    ) -> dict[str, object]:
        data = self.write_source(text)
        return {
            "schema_version": 1,
            "claim_id": "TEST-DISABLED-NONINTERFERENCE",
            "source": {
                "path": self.source_relative,
                "git_blob_sha1": gate.git_blob_sha1(data),
            },
            "target": {"class": "SpatialTempo", "method": "transform"},
            "disabled_bindings": {"self.pathing": False, "self.tempo": False},
            "protected_effects": effects
            or [{"kind": "call", "target": "self._continue_weed"}],
            "expected_verdict": expected,
        }

    def evidence(self) -> dict[str, object]:
        arm = {
            "action_digest": digest("a"),
            "transition_digest": digest("b"),
            "banks": [102918, 101269],
            "reward": 102918,
            "state": {"day": 800, "inventory": [0, 1, 2]},
        }
        return {
            "schema_version": 1,
            "claim_id": "TEST-SPENT-TRACE-IDENTITY",
            "expected_verdict": "PASS",
            "expected_case_ids": ["seed-2609097303-seat-1"],
            "cases": [
                {
                    "case_id": "seed-2609097303-seat-1",
                    "baseline": copy.deepcopy(arm),
                    "disabled": copy.deepcopy(arm),
                }
            ],
        }


class SourceAuditTests(GateTestCase):
    def test_exact_predecessor_is_blocked(self) -> None:
        receipt = gate.audit_source(self.root, self.contract(PREDECESSOR, expected="BLOCK"))
        self.assertEqual("BLOCK", receipt["observed_verdict"])
        self.assertTrue(receipt["expectation_met"])
        self.assertEqual("REACHABLE_PROTECTED_CALL", receipt["findings"][0]["code"])

    def test_w0_short_circuit_repair_passes(self) -> None:
        receipt = gate.audit_source(self.root, self.contract(W0_REPAIR, expected="PASS"))
        self.assertEqual("PASS", receipt["observed_verdict"])
        self.assertEqual([], receipt["findings"])

    def test_dominating_early_return_passes(self) -> None:
        receipt = gate.audit_source(self.root, self.contract(EARLY_RETURN, expected="PASS"))
        self.assertEqual("PASS", receipt["observed_verdict"])

    def test_one_flag_or_guard_does_not_short_circuit(self) -> None:
        source = """\
class SpatialTempo:
    def transform(self, selected, state):
        if self.pathing or self._continue_weed(state):
            return selected
        return selected
"""
        receipt = gate.audit_source(self.root, self.contract(source, expected="BLOCK"))
        self.assertEqual("BLOCK", receipt["observed_verdict"])

    def test_false_left_and_short_circuits(self) -> None:
        source = """\
class SpatialTempo:
    def transform(self, selected, state):
        if self.pathing and self._continue_weed(state):
            return selected
        return selected
"""
        receipt = gate.audit_source(self.root, self.contract(source, expected="PASS"))
        self.assertEqual("PASS", receipt["observed_verdict"])

    def test_nested_else_fallthrough_is_blocked(self) -> None:
        source = """\
class SpatialTempo:
    def transform(self, selected, state):
        if not self.pathing:
            if self.tempo:
                return selected
        else:
            return selected
        self._continue_weed(state)
        return selected
"""
        receipt = gate.audit_source(self.root, self.contract(source, expected="BLOCK"))
        self.assertEqual("BLOCK", receipt["observed_verdict"])

    def test_call_in_condition_is_blocked(self) -> None:
        source = """\
class SpatialTempo:
    def transform(self, selected, state):
        if self._continue_weed(state) and not self.pathing:
            return selected
        return selected
"""
        receipt = gate.audit_source(self.root, self.contract(source, expected="BLOCK"))
        self.assertEqual("REACHABLE_PROTECTED_CALL", receipt["findings"][0]["code"])

    def test_protected_effect_in_finally_is_blocked(self) -> None:
        source = """\
class SpatialTempo:
    def transform(self, selected, state):
        try:
            return selected
        finally:
            self._continue_weed(state)
"""
        receipt = gate.audit_source(self.root, self.contract(source, expected="BLOCK"))
        codes = {item["code"] for item in receipt["findings"]}
        self.assertIn("PROTECTED_EFFECT_IN_FINALLY", codes)

    def test_protected_write_before_guard_is_blocked(self) -> None:
        source = """\
class SpatialTempo:
    def transform(self, selected, state):
        self._weed_state = state
        if not self.pathing and not self.tempo:
            return selected
        return selected
"""
        effects = [{"kind": "write", "target": "self._weed_state"}]
        receipt = gate.audit_source(
            self.root, self.contract(source, expected="BLOCK", effects=effects)
        )
        self.assertEqual("REACHABLE_PROTECTED_WRITE", receipt["findings"][0]["code"])

    def test_binding_mutation_is_blocked(self) -> None:
        source = """\
class SpatialTempo:
    def transform(self, selected, state):
        self.pathing = True
        return selected
"""
        receipt = gate.audit_source(self.root, self.contract(source, expected="BLOCK"))
        self.assertEqual("DISABLED_BINDING_MUTATION", receipt["findings"][0]["code"])

    def test_callable_alias_is_blocked(self) -> None:
        source = """\
class SpatialTempo:
    def transform(self, selected, state):
        callback = self._continue_weed
        if not self.pathing and not self.tempo:
            return selected
        return callback(state)
"""
        receipt = gate.audit_source(self.root, self.contract(source, expected="BLOCK"))
        codes = {item["code"] for item in receipt["findings"]}
        self.assertIn("PROTECTED_CALLABLE_ALIAS", codes)

    def test_dynamic_getattr_is_blocked(self) -> None:
        source = """\
class SpatialTempo:
    def transform(self, selected, state):
        return getattr(self, "_continue_weed")(state)
"""
        receipt = gate.audit_source(self.root, self.contract(source, expected="BLOCK"))
        codes = {item["code"] for item in receipt["findings"]}
        self.assertIn("DYNAMIC_PROTECTED_CALL", codes)

    def test_source_drift_fails_closed(self) -> None:
        contract = self.contract(W0_REPAIR, expected="PASS")
        (self.root / self.source_relative).write_text(W0_REPAIR + "\n# drift\n", encoding="utf-8")
        with self.assertRaisesRegex(gate.GateError, "source drift"):
            gate.audit_source(self.root, contract)

    def test_duplicate_effect_contract_is_rejected(self) -> None:
        effect = {"kind": "call", "target": "self._continue_weed"}
        contract = self.contract(W0_REPAIR, expected="PASS", effects=[effect, effect])
        with self.assertRaisesRegex(gate.GateError, "duplicate protected effect"):
            gate.audit_source(self.root, contract)

    def test_non_false_binding_is_rejected(self) -> None:
        contract = self.contract(W0_REPAIR, expected="PASS")
        contract["disabled_bindings"]["self.pathing"] = True  # type: ignore[index]
        with self.assertRaisesRegex(gate.GateError, "must be the boolean false"):
            gate.audit_source(self.root, contract)

    def test_duplicate_target_class_is_rejected(self) -> None:
        source = W0_REPAIR + "\n" + W0_REPAIR
        with self.assertRaisesRegex(gate.GateError, "exactly one top-level class"):
            gate.audit_source(self.root, self.contract(source, expected="PASS"))

    def test_receipt_is_deterministic(self) -> None:
        contract = self.contract(PREDECESSOR, expected="BLOCK")
        first = gate.audit_source(self.root, contract)
        second = gate.audit_source(self.root, contract)
        self.assertEqual(gate.canonical_bytes(first), gate.canonical_bytes(second))

    def test_expected_mismatch_returns_nonzero(self) -> None:
        contract = self.contract(PREDECESSOR, expected="PASS")
        contract_path = self.root / "contract.json"
        output = self.root / "receipt.json"
        contract_path.write_text(json.dumps(contract), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = gate.main(
                [
                    "source",
                    "--repo-root",
                    str(self.root),
                    "--contract",
                    str(contract_path),
                    "--output",
                    str(output),
                    "--expect",
                    "PASS",
                ]
            )
        self.assertEqual(1, code)
        self.assertEqual("BLOCK", json.loads(output.read_text())["observed_verdict"])

    def test_cli_expectation_cannot_disagree_with_contract(self) -> None:
        contract = self.contract(PREDECESSOR, expected="BLOCK")
        contract_path = self.root / "contract.json"
        output = self.root / "receipt.json"
        contract_path.write_text(json.dumps(contract), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            code = gate.main(
                [
                    "source",
                    "--repo-root",
                    str(self.root),
                    "--contract",
                    str(contract_path),
                    "--output",
                    str(output),
                    "--expect",
                    "PASS",
                ]
            )
        self.assertEqual(2, code)
        self.assertFalse(output.exists())


class TraceAuditTests(GateTestCase):
    def test_identical_spent_trace_passes(self) -> None:
        receipt = gate.audit_trace(self.evidence())
        self.assertEqual("PASS", receipt["observed_verdict"])
        self.assertTrue(receipt["cases"][0]["identical"])

    def test_action_divergence_blocks(self) -> None:
        evidence = self.evidence()
        evidence["cases"][0]["disabled"]["action_digest"] = digest("c")  # type: ignore[index]
        receipt = gate.audit_trace(evidence)
        self.assertEqual("BLOCK", receipt["observed_verdict"])
        self.assertIn("$.action_digest", receipt["findings"][0]["paths"])

    def test_transition_divergence_blocks(self) -> None:
        evidence = self.evidence()
        evidence["cases"][0]["disabled"]["transition_digest"] = digest("c")  # type: ignore[index]
        receipt = gate.audit_trace(evidence)
        self.assertIn("$.transition_digest", receipt["findings"][0]["paths"])

    def test_bank_divergence_blocks(self) -> None:
        evidence = self.evidence()
        evidence["cases"][0]["disabled"]["banks"][0] -= 1  # type: ignore[index]
        receipt = gate.audit_trace(evidence)
        self.assertIn("$.banks[0]", receipt["findings"][0]["paths"])

    def test_reward_divergence_blocks(self) -> None:
        evidence = self.evidence()
        evidence["cases"][0]["disabled"]["reward"] = 0  # type: ignore[index]
        receipt = gate.audit_trace(evidence)
        self.assertIn("$.reward", receipt["findings"][0]["paths"])

    def test_missing_case_is_rejected(self) -> None:
        evidence = self.evidence()
        evidence["cases"] = []
        with self.assertRaisesRegex(gate.GateError, "missing cases"):
            gate.audit_trace(evidence)

    def test_unexpected_case_is_rejected(self) -> None:
        evidence = self.evidence()
        extra = copy.deepcopy(evidence["cases"][0])  # type: ignore[index]
        extra["case_id"] = "unexpected"
        evidence["cases"].append(extra)  # type: ignore[union-attr]
        with self.assertRaisesRegex(gate.GateError, "unexpected cases"):
            gate.audit_trace(evidence)

    def test_duplicate_case_is_rejected(self) -> None:
        evidence = self.evidence()
        evidence["cases"].append(copy.deepcopy(evidence["cases"][0]))  # type: ignore[index,union-attr]
        with self.assertRaisesRegex(gate.GateError, "duplicate case_id"):
            gate.audit_trace(evidence)

    def test_nonfinite_value_is_rejected(self) -> None:
        evidence = self.evidence()
        evidence["cases"][0]["baseline"]["reward"] = math.nan  # type: ignore[index]
        with self.assertRaisesRegex(gate.GateError, "non-finite"):
            gate.audit_trace(evidence)

    def test_malformed_digest_is_rejected(self) -> None:
        evidence = self.evidence()
        evidence["cases"][0]["baseline"]["action_digest"] = "abc"  # type: ignore[index]
        with self.assertRaisesRegex(gate.GateError, "must be sha256"):
            gate.audit_trace(evidence)

    def test_missing_required_arm_field_is_rejected(self) -> None:
        evidence = self.evidence()
        del evidence["cases"][0]["disabled"]["banks"]  # type: ignore[index]
        with self.assertRaisesRegex(gate.GateError, "missing keys: banks"):
            gate.audit_trace(evidence)

    def test_output_alias_is_rejected(self) -> None:
        evidence = self.evidence()
        evidence_path = self.root / "evidence.json"
        evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
        receipt = gate.audit_trace(evidence)
        with self.assertRaisesRegex(gate.GateError, "aliases protected input"):
            gate.write_receipt(evidence_path, receipt, (evidence_path,))

    def test_trace_receipt_is_deterministic(self) -> None:
        evidence = self.evidence()
        self.assertEqual(
            gate.canonical_bytes(gate.audit_trace(evidence)),
            gate.canonical_bytes(gate.audit_trace(evidence)),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
