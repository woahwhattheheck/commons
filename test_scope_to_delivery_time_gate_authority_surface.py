import inspect
import unittest
from datetime import datetime

from host import scope_to_delivery_time_authority as authority
from host import scope_to_delivery_time_gate as gate


def z(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def temporal_agreement():
    return {
        "schema_version": "commons-scope-agreement/v1",
        "kind": "SCOPE_AGREEMENT",
        "agreement_id": "agr-authority-surface-20260916",
        "window": {
            "start": "2026-09-13T10:00:00Z",
            "end": "2026-09-13T12:00:00Z",
            "timezone": "UTC",
        },
        "written_acceptance": {
            "status": "PRESENT",
            "accepted_at": "2026-09-13T09:30:00Z",
        },
    }


class AuthoritySurfaceTests(unittest.TestCase):
    def test_no_historical_helper_accepts_raw_authority_claims(self):
        forbidden = {
            "agreement_raw_sha256",
            "observations_raw_sha256",
            "raw_byte_provenance_verified",
            "canonical_scope_validated",
            "canonical_project_bound",
            "canonical_project_sha256",
            "current_work_authorized",
        }
        offenders = {}
        for name, value in vars(authority).items():
            if not inspect.isfunction(value) or value.__module__ != authority.__name__:
                continue
            if name in {
                "evaluate_bytes",
                "evaluate_current_bytes",
                "verify_current_work_authority",
            }:
                continue
            overlap = forbidden.intersection(inspect.signature(value).parameters)
            if overlap:
                offenders[name] = sorted(overlap)
        self.assertEqual(offenders, {})

    def test_current_authority_surfaces_have_no_caller_clock_or_receipt(self):
        current = inspect.signature(gate.evaluate_current_bytes).parameters
        verify = inspect.signature(gate.verify_current_work_authority).parameters
        for params in (current, verify):
            for name in (
                "as_of",
                "now",
                "trusted_now",
                "evaluation_time",
                "observed_at",
            ):
                self.assertNotIn(name, params)
        self.assertNotIn("receipt", verify)

    def test_historical_fact_helpers_cannot_emit_authority(self):
        facts = authority._temporal_facts(
            temporal_agreement(),
            None,
            as_of=z("2026-09-13T11:00:00Z"),
        )
        forbidden_fields = {
            "agreement_raw_sha256",
            "observations_raw_sha256",
            "raw_byte_provenance_verified",
            "provenance_mode",
            "canonical_scope_validated",
            "canonical_project_bound",
            "canonical_project_sha256",
            "current_work_authorized",
            "receipt_sha256",
        }
        self.assertTrue(forbidden_fields.isdisjoint(facts))
        base = authority._receipt_base(facts, state=facts["state"])
        self.assertTrue(forbidden_fields.isdisjoint(base))

    def test_public_parsed_evaluate_is_permanently_fail_closed(self):
        receipt = gate.evaluate(
            temporal_agreement(),
            None,
            as_of=z("2026-09-13T11:00:00Z"),
        )
        self.assertEqual(receipt["state"], "HOLD_PARSED_OBJECT_UNVERIFIED")
        self.assertIsNone(receipt["agreement_raw_sha256"])
        self.assertIsNone(receipt["observations_raw_sha256"])
        self.assertFalse(receipt["raw_byte_provenance_verified"])
        self.assertFalse(receipt["canonical_scope_validated"])
        self.assertFalse(receipt["canonical_project_bound"])
        self.assertFalse(receipt["current_work_authorized"])

    def test_explicit_time_byte_evaluator_is_hard_false_for_current_work(self):
        source = inspect.getsource(gate.evaluate_bytes)
        self.assertIn('"current_work_authorized": False', source)
        self.assertIn("CALLER_SUPPLIED_HISTORICAL_ONLY", source)

    def test_binding_helper_name_is_truth_narrowed_to_integrity_only(self):
        source = inspect.getsource(gate.verify_project_binding)
        self.assertIn("verify_project_binding_integrity", source)
        self.assertNotIn('"valid"', source)

    def test_current_evaluator_source_has_no_gate_semantic_global_calls(self):
        source = inspect.getsource(gate.evaluate_current_bytes)
        for forbidden in (
            "_temporal_facts(",
            "_historical_project(",
            "_receipt_base(",
            "_exact_facts(",
            "canonical_scope.",
        ):
            self.assertNotIn(forbidden, source)
        self.assertIn("canonical_project_from_fresh_process", source)

    def test_wrapper_points_at_isolated_authority_kernel(self):
        self.assertIs(gate.evaluate_current_bytes, authority.evaluate_current_bytes)
        self.assertIs(
            gate.verify_current_work_authority,
            authority.verify_current_work_authority,
        )


if __name__ == "__main__":
    unittest.main()
