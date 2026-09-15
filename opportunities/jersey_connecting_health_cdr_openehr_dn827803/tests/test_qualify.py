from __future__ import annotations

import copy
import inspect
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import qualify


class Tests(unittest.TestCase):
    def setUp(self):
        self.source_raw = (ROOT / "sources.json").read_bytes()
        self.manifest_raw = (ROOT / "fixtures/public_hold.json").read_bytes()
        self.source = qualify.load_json_bytes(self.source_raw, "source")
        self.manifest = qualify.load_json_bytes(self.manifest_raw, "manifest")

    def run_case(self, source=None, manifest=None, raw=None, pack=None):
        return qualify.evaluate(
            copy.deepcopy(self.manifest if manifest is None else manifest),
            copy.deepcopy(self.source if source is None else source),
            self.source_raw if raw is None else raw,
            tender_pack_bytes=pack,
        )

    def test_public_fixture_remains_truthful_hold(self):
        result = self.run_case()
        self.assertEqual("HOLD_TENDER_PACK_REQUIRED", result.state)
        self.assertEqual(3, result.exit_code)
        self.assertEqual("HOLD", result.payload["bridge_status"])
        self.assertEqual(qualify.BINDING_ID, result.payload["binding_id"])
        self.assertTrue(result.payload["legacy_ready_authority_retired"])
        self.assertFalse(result.payload["tender_submission_authorized"])
        self.assertFalse(result.payload["external_submission_authorized"])
        self.assertTrue(all(value is False for value in result.payload["action_authority"].values()))

    def test_current_time_is_process_owned_not_manifest_time(self):
        before = datetime.now(timezone.utc).replace(microsecond=0)
        result = self.run_case()
        after = datetime.now(timezone.utc).replace(microsecond=0)
        evaluated = datetime.strptime(result.payload["evaluated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        self.assertLessEqual(before, evaluated)
        self.assertLessEqual(evaluated, after)
        self.assertNotEqual(self.manifest["evaluated_at"], result.payload["evaluated_at"])

    def test_route_switch_cannot_self_authorize(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["route"] = "PRIME_CDR"
        with self.assertRaisesRegex(qualify.QualificationError, "BRIDGE_AUTHORITY_REJECTED:submission_manifest root mismatch"):
            self.run_case(manifest=manifest)

    def test_partner_false_to_true_cannot_self_authorize(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["partner_prime_confirmed"] = True
        with self.assertRaisesRegex(qualify.QualificationError, "BRIDGE_AUTHORITY_REJECTED:submission_manifest root mismatch"):
            self.run_case(manifest=manifest)

    def test_caller_time_change_cannot_self_authorize(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["evaluated_at"] = "2026-09-01T00:00:00Z"
        with self.assertRaisesRegex(qualify.QualificationError, "BRIDGE_AUTHORITY_REJECTED:submission_manifest root mismatch"):
            self.run_case(manifest=manifest)

    def test_source_generation_mutation_rejected(self):
        source = copy.deepcopy(self.source)
        source["checked_at"] = "2026-09-15T00:00:00+00:00"
        raw = (json.dumps(source, sort_keys=True, separators=(",", ":")) + "\n").encode()
        with self.assertRaisesRegex(qualify.QualificationError, "BRIDGE_AUTHORITY_REJECTED:source_ledger root mismatch"):
            self.run_case(source=source, raw=raw)

    def test_source_raw_must_describe_supplied_source(self):
        source = copy.deepcopy(self.source)
        source["checked_at"] = "2026-09-15T00:00:00+00:00"
        with self.assertRaisesRegex(qualify.QualificationError, "SOURCE_RAW_OBJECT_MISMATCH"):
            self.run_case(source=source)

    def test_legacy_tender_pack_bytes_are_not_authority(self):
        with self.assertRaisesRegex(qualify.QualificationError, "LEGACY_TENDER_PACK_BYTES_NOT_AUTHORITY"):
            self.run_case(pack=b"synthetic pack bytes\n")

    def test_legacy_surface_has_no_as_of_or_trusted_time_parameter(self):
        parameters = inspect.signature(qualify.evaluate).parameters
        self.assertNotIn("as_of", parameters)
        self.assertNotIn("trusted_as_of", parameters)
        self.assertEqual({"manifest", "source", "source_raw", "tender_pack_bytes"}, set(parameters))

    def test_even_future_bridge_evidence_ready_maps_to_hold(self):
        synthetic = {
            "status": "OPPORTUNITY_EVIDENCE_READY",
            "reason_codes": [],
            "external_submission_authorized": False,
            "authority": {"proposal_submission": False, "revenue_claim": False},
        }
        self.assertEqual("HOLD_LEGACY_QUALIFIER_RETIRED", qualify._legacy_state(synthetic))

    def test_bridge_authority_escalation_fails_closed(self):
        synthetic = {
            "status": "HOLD",
            "reason_codes": ["TENDER_PACK_NOT_ACQUIRED"],
            "external_submission_authorized": False,
            "authority": {"proposal_submission": True},
        }
        with self.assertRaisesRegex(qualify.QualificationError, "ACTION_AUTHORITY_ESCALATION"):
            qualify._legacy_state(synthetic)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(qualify.QualificationError, "DUPLICATE_JSON_KEY:a"):
            qualify.load_json_bytes(b'{"a":1,"a":2}', "x")

    def test_diagnostic_output_is_create_exclusive(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "receipt.json"
            qualify._write_exclusive(target, b"one\n")
            self.assertEqual(b"one\n", target.read_bytes())
            with self.assertRaises(FileExistsError):
                qualify._write_exclusive(target, b"two\n")
            self.assertEqual(b"one\n", target.read_bytes())


if __name__ == "__main__":
    unittest.main()
