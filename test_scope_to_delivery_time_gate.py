import copy
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from host import scope_to_delivery_time_gate as gate


def z(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def agreement():
    return {
        "schema_version": "commons-scope-agreement/v1",
        "kind": "SCOPE_AGREEMENT",
        "agreement_id": "agr-temporal-hostile-0001",
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


def observations(*times: str):
    return {
        "schema_version": "commons-scope-observations/v1",
        "kind": "EXECUTION_OBSERVATIONS",
        "agreement_id": "agr-temporal-hostile-0001",
        "observations": [
            {"observation_id": f"obs-{i:02d}", "observed_at": when}
            for i, when in enumerate(times, 1)
        ],
    }


class TemporalGateTests(unittest.TestCase):
    def test_current_window_is_ready_but_never_external_authority(self):
        out = gate.evaluate(agreement(), observations("2026-09-13T10:15:00Z"), as_of=z("2026-09-13T11:00:00Z"))
        self.assertEqual(out["state"], "TEMPORAL_PREREQUISITE_READY")
        self.assertTrue(out["current_work_authorized"])
        for key in ("external_action_authorized", "payment_authorized", "delivery_claim_authorized", "revenue_authorized"):
            self.assertFalse(out[key])

    def test_expired_window_holds_new_work_but_preserves_historical_chronology(self):
        out = gate.evaluate(agreement(), observations("2026-09-13T10:15:00Z", "2026-09-13T11:50:00Z"), as_of=z("2026-09-13T13:00:00Z"))
        self.assertEqual(out["state"], "HOLD_WINDOW_EXPIRED")
        self.assertFalse(out["current_work_authorized"])
        self.assertTrue(out["historical_evidence_temporally_admissible"])

    def test_aug28_historical_delivery_is_not_current_work_authority(self):
        doc = agreement()
        doc["agreement_id"] = "agr-synthetic-production-survival-20260828-01"
        doc["window"] = {
            "start": "2026-08-28T13:00:00-04:00",
            "end": "2026-08-28T21:00:00-04:00",
            "timezone": "America/New_York",
        }
        doc["written_acceptance"] = {
            "status": "PRESENT",
            "accepted_at": "2026-08-28T12:00:00-04:00",
        }
        obs = {
            "schema_version": "commons-scope-observations/v1",
            "kind": "EXECUTION_OBSERVATIONS",
            "agreement_id": doc["agreement_id"],
            "observations": [
                {"observation_id": "obs-work-started-20260828-01", "observed_at": "2026-08-28T13:05:00-04:00"},
                {"observation_id": "obs-receipt-20260828-01", "observed_at": "2026-08-28T15:00:00-04:00"},
            ],
        }
        out = gate.evaluate(doc, obs, as_of=z("2026-09-13T10:00:00Z"))
        self.assertEqual(out["state"], "HOLD_WINDOW_EXPIRED")
        self.assertFalse(out["current_work_authorized"])
        self.assertTrue(out["historical_evidence_temporally_admissible"])
        self.assertTrue(out["canonical_scope_validation_still_required"])

    def test_window_not_started_holds(self):
        out = gate.evaluate(agreement(), None, as_of=z("2026-09-13T09:45:00Z"))
        self.assertEqual(out["state"], "HOLD_WINDOW_NOT_STARTED")
        self.assertFalse(out["current_work_authorized"])

    def test_non_present_acceptance_holds(self):
        doc = agreement()
        doc["written_acceptance"] = {"status": "ABSENT", "accepted_at": None}
        out = gate.evaluate(doc, None, as_of=z("2026-09-13T11:00:00Z"))
        self.assertEqual(out["state"], "HOLD_NO_PRESENT_ACCEPTANCE")

    def test_future_acceptance_rejected(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "acceptance is in"):
            gate.evaluate(agreement(), None, as_of=z("2026-09-13T09:00:00Z"))

    def test_acceptance_after_window_rejected(self):
        doc = agreement()
        doc["written_acceptance"]["accepted_at"] = "2026-09-13T12:01:00Z"
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "after the contracted window"):
            gate.evaluate(doc, None, as_of=z("2026-09-13T13:00:00Z"))

    def test_observation_before_acceptance_rejected(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "predates written acceptance"):
            gate.evaluate(agreement(), observations("2026-09-13T09:00:00Z"), as_of=z("2026-09-13T11:00:00Z"))

    def test_observation_before_window_rejected(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "predates contracted work window"):
            gate.evaluate(agreement(), observations("2026-09-13T09:45:00Z"), as_of=z("2026-09-13T11:00:00Z"))

    def test_observation_after_window_rejected(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "after contracted work window"):
            gate.evaluate(agreement(), observations("2026-09-13T12:00:01Z"), as_of=z("2026-09-13T13:00:00Z"))

    def test_future_observation_rejected(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "verifier's future"):
            gate.evaluate(agreement(), observations("2026-09-13T11:30:00Z"), as_of=z("2026-09-13T11:00:00Z"))

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "duplicate JSON key"):
            gate.strict_loads(b'{"a":1,"a":2}', "x")

    def test_receipt_is_deterministic_and_input_bound(self):
        first = gate.evaluate(agreement(), observations("2026-09-13T10:15:00Z"), as_of=z("2026-09-13T11:00:00Z"))
        second = gate.evaluate(copy.deepcopy(agreement()), copy.deepcopy(observations("2026-09-13T10:15:00Z")), as_of=z("2026-09-13T11:00:00Z"))
        self.assertEqual(first, second)
        changed = agreement()
        changed["agreement_id"] = "agr-temporal-hostile-0002"
        other_obs = observations("2026-09-13T10:15:00Z")
        other_obs["agreement_id"] = changed["agreement_id"]
        third = gate.evaluate(changed, other_obs, as_of=z("2026-09-13T11:00:00Z"))
        self.assertNotEqual(first["receipt_sha256"], third["receipt_sha256"])

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "requires O_NOFOLLOW")
    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real = root / "agreement.json"
            link = root / "link.json"
            real.write_text(json.dumps(agreement()), encoding="utf-8")
            link.symlink_to(real)
            with self.assertRaisesRegex(gate.TemporalAuthorityError, "non-symlink"):
                gate.read_plain_json(link, "agreement")


if __name__ == "__main__":
    unittest.main()
