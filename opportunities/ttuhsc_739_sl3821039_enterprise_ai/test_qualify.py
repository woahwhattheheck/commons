from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import qualify  # noqa: E402
from revenue.pursuit_evidence_bridge import bridge  # noqa: E402


def envelope() -> dict:
    return {
        "source_ledger": json.loads((HERE / "source_ledger.json").read_text(encoding="utf-8")),
        "submission_manifest": json.loads((HERE / "submission_manifest.json").read_text(encoding="utf-8")),
        "vault": None,
    }


class CurrentQualificationTests(unittest.TestCase):
    def test_repo_pinned_ttuhsc_bytes_are_truthful_hold(self):
        result = qualify.evaluate_current(envelope())
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("FIRST_PARTY_PACKET_BYTES_NOT_RETAINED", result["reason_codes"])
        self.assertIn("ALL_ADDENDA_NOT_RETAINED", result["reason_codes"])
        self.assertIn("VAULT_ROOTS_NOT_PINNED", result["reason_codes"])
        self.assertFalse(result["external_submission_authorized"])
        self.assertTrue(all(value is False for value in result["authority"].values()))

    def test_rejected_old_positive_packet_cannot_enter_current_gate(self):
        old_shape = {
            "schema": "tjlabs.ttuhsc-739-sl3821039-qualification/v1",
            "as_of": "2026-09-14T04:00:00Z",
            "source": {}, "organization": {}, "proposal": {}, "references": [],
            "team": {}, "security": {}, "commercial": {}, "route": "PRIME",
        }
        with self.assertRaisesRegex(qualify.QualificationError, "keys invalid"):
            qualify.evaluate_current(old_shape)

    def test_caller_clock_deadline_and_expected_roots_are_not_inputs(self):
        for extra in (
            "as_of", "deadline_utc", "route", "expected_source_sha256",
            "expected_manifest_sha256", "owner_approved", "final_price_owner_approved",
        ):
            with self.subTest(extra=extra):
                candidate = envelope()
                candidate[extra] = "caller-controlled"
                with self.assertRaisesRegex(qualify.QualificationError, "keys invalid"):
                    qualify.evaluate_current(candidate)

    def test_source_ledger_drift_is_rejected_not_downgraded_to_assertion(self):
        candidate = envelope()
        candidate["source_ledger"] = deepcopy(candidate["source_ledger"])
        candidate["source_ledger"]["observed_at_utc"] = "2026-09-14T03:49:59Z"
        with self.assertRaisesRegex(qualify.QualificationError, "source_ledger root mismatch"):
            qualify.evaluate_current(candidate)

    def test_submission_manifest_drift_is_rejected(self):
        candidate = envelope()
        candidate["submission_manifest"] = deepcopy(candidate["submission_manifest"])
        candidate["submission_manifest"]["commercial"]["final_price_owner_approved"] = True
        with self.assertRaisesRegex(qualify.QualificationError, "submission_manifest root mismatch"):
            qualify.evaluate_current(candidate)

    def test_runtime_vault_cannot_supply_unpinned_roots(self):
        candidate = envelope()
        candidate["vault"] = {"authority": {}, "registry": {}, "query": {}, "bundle": {}}
        with self.assertRaisesRegex(qualify.QualificationError, "cannot self-authorize"):
            qualify.evaluate_current(candidate)

    def test_binding_pins_exact_source_manifest_and_deadline(self):
        _, bindings = bridge._load_binding_registry()
        binding = bindings[qualify.BINDING_ID]
        self.assertEqual(binding["opportunity_id"], "739-SL3821039")
        self.assertEqual(binding["deadline_utc"], "2026-09-21T21:30:00Z")
        self.assertEqual(binding["source_ledger_sha256"], "3d2af64d5c4c9547e3c35f7095606e0be16c6628d78dfc1de7a9c8d1eb20d729")
        self.assertEqual(binding["submission_manifest_sha256"], "3b199b5ceb4e8f1d7a5a72a46267d57d7333c8c2acc2b97f2ac8d738cf4713f3")
        self.assertIsNone(binding["vault_authority_sha256"])
        self.assertIsNone(binding["vault_registry_sha256"])
        self.assertIsNone(binding["vault_query_sha256"])

    def test_deadline_is_repo_pinned_and_expiry_is_process_evaluation_input(self):
        registry_sha, bindings = bridge._load_binding_registry()
        binding = bindings[qualify.BINDING_ID]
        candidate = envelope()
        after = datetime(2026, 9, 21, 21, 30, 0, tzinfo=timezone.utc)
        result = bridge._evaluate_at(
            binding, registry_sha, candidate["source_ledger"],
            candidate["submission_manifest"], None, after,
        )
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("PROPOSAL_DEADLINE_EXPIRED", result["reason_codes"])
        with self.assertRaises(TypeError):
            qualify.evaluate_current(candidate, evaluated_at=after)  # type: ignore[call-arg]

    def test_gate_never_translates_evidence_status_into_route_or_submission_authority(self):
        result = qualify.evaluate_current(envelope())
        rendered = json.dumps(result, sort_keys=True)
        self.assertNotIn("PRIME_READY", rendered)
        self.assertNotIn("TEAMING_READY", rendered)
        self.assertFalse(result["external_submission_authorized"])


if __name__ == "__main__":
    unittest.main()
