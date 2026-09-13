import inspect
import unittest
from datetime import datetime

from host import scope_to_delivery_time_gate as gate


def z(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def temporal_agreement():
    return {
        "schema_version": "commons-scope-agreement/v1",
        "kind": "SCOPE_AGREEMENT",
        "agreement_id": "agr-authority-surface-20260913",
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


class ParsedAuthoritySurfaceTests(unittest.TestCase):
    def test_no_parsed_helper_accepts_authority_minting_parameters(self):
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
        for name, value in vars(gate).items():
            if not inspect.isfunction(value) or value.__module__ != gate.__name__:
                continue
            if name == "evaluate_bytes":
                continue
            overlap = forbidden.intersection(inspect.signature(value).parameters)
            if overlap:
                offenders[name] = sorted(overlap)
        self.assertEqual(offenders, {})

    def test_parsed_fact_helpers_cannot_emit_authority(self):
        facts = gate._temporal_facts(
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
        base = gate._receipt_base(facts, state=facts["state"])
        self.assertTrue(forbidden_fields.isdisjoint(base))

    def test_public_parsed_evaluate_is_permanently_fail_closed(self):
        receipt = gate.evaluate(
            temporal_agreement(),
            None,
            as_of=z("2026-09-13T11:00:00Z"),
        )
        self.assertEqual(receipt["state"], "HOLD_RAW_PROVENANCE_UNVERIFIED")
        self.assertIsNone(receipt["agreement_raw_sha256"])
        self.assertIsNone(receipt["observations_raw_sha256"])
        self.assertFalse(receipt["raw_byte_provenance_verified"])
        self.assertFalse(receipt["canonical_scope_validated"])
        self.assertFalse(receipt["canonical_project_bound"])
        self.assertFalse(receipt["current_work_authorized"])


if __name__ == "__main__":
    unittest.main()
