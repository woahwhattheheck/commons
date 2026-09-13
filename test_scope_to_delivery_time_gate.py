import copy
import hashlib
import inspect
import json
import os
import tempfile
import unittest
from datetime import datetime
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


def raw(value, *, pretty=False):
    if pretty:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode()
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def eval_bytes(doc=None, obs=None, *, as_of="2026-09-13T11:00:00Z"):
    doc = agreement() if doc is None else doc
    return gate.evaluate_bytes(raw(doc), None if obs is None else raw(obs), as_of=z(as_of))


class TemporalGateTests(unittest.TestCase):
    def test_current_window_is_ready_but_never_external_authority(self):
        out = eval_bytes(obs=observations("2026-09-13T10:15:00Z"))
        self.assertEqual(out["state"], "TEMPORAL_PREREQUISITE_READY")
        self.assertTrue(out["current_work_authorized"])
        self.assertTrue(out["raw_byte_provenance_verified"])
        self.assertEqual(out["provenance_mode"], "EXACT_RAW_BYTES_VERIFIED")
        for key in ("external_action_authorized", "payment_authorized", "delivery_claim_authorized", "revenue_authorized"):
            self.assertFalse(out[key])

    def test_parsed_object_path_is_fail_closed_for_current_work(self):
        out = gate.evaluate(agreement(), observations("2026-09-13T10:15:00Z"), as_of=z("2026-09-13T11:00:00Z"))
        self.assertEqual(out["state"], "HOLD_RAW_PROVENANCE_UNVERIFIED")
        self.assertFalse(out["current_work_authorized"])
        self.assertFalse(out["raw_byte_provenance_verified"])
        self.assertIsNone(out["agreement_raw_sha256"])
        self.assertIsNone(out["observations_raw_sha256"])
        self.assertEqual(out["provenance_mode"], "CANONICAL_OBJECT_ONLY")
        self.assertNotIn("agreement_raw_sha256", inspect.signature(gate.evaluate).parameters)

    def test_expired_window_holds_new_work_but_preserves_historical_chronology(self):
        out = eval_bytes(obs=observations("2026-09-13T10:15:00Z", "2026-09-13T11:50:00Z"), as_of="2026-09-13T13:00:00Z")
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
        out = eval_bytes(doc=doc, obs=obs, as_of="2026-09-13T10:00:00Z")
        self.assertEqual(out["state"], "HOLD_WINDOW_EXPIRED")
        self.assertFalse(out["current_work_authorized"])
        self.assertTrue(out["historical_evidence_temporally_admissible"])
        self.assertTrue(out["raw_byte_provenance_verified"])
        self.assertTrue(out["canonical_scope_validation_still_required"])

    def test_window_not_started_holds(self):
        out = eval_bytes(as_of="2026-09-13T09:45:00Z")
        self.assertEqual(out["state"], "HOLD_WINDOW_NOT_STARTED")
        self.assertFalse(out["current_work_authorized"])

    def test_non_present_acceptance_holds(self):
        doc = agreement(); doc["written_acceptance"] = {"status": "ABSENT", "accepted_at": None}
        out = eval_bytes(doc=doc)
        self.assertEqual(out["state"], "HOLD_NO_PRESENT_ACCEPTANCE")

    def test_future_acceptance_rejected(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "acceptance is in"):
            eval_bytes(as_of="2026-09-13T09:00:00Z")

    def test_acceptance_after_window_rejected(self):
        doc = agreement(); doc["written_acceptance"]["accepted_at"] = "2026-09-13T12:01:00Z"
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "after the contracted window"):
            eval_bytes(doc=doc, as_of="2026-09-13T13:00:00Z")

    def test_observation_before_acceptance_rejected(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "predates written acceptance"):
            eval_bytes(obs=observations("2026-09-13T09:00:00Z"))

    def test_observation_before_window_rejected(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "predates contracted work window"):
            eval_bytes(obs=observations("2026-09-13T09:45:00Z"))

    def test_observation_after_window_rejected(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "after contracted work window"):
            eval_bytes(obs=observations("2026-09-13T12:00:01Z"), as_of="2026-09-13T13:00:00Z")

    def test_future_observation_rejected(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "verifier's future"):
            eval_bytes(obs=observations("2026-09-13T11:30:00Z"))

    def test_duplicate_json_keys_rejected_by_byte_authority(self):
        good = raw(agreement())
        bad = good[:-1] + b',"agreement_id":"other"}'
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "duplicate JSON key"):
            gate.evaluate_bytes(bad, None, as_of=z("2026-09-13T11:00:00Z"))

    def test_receipt_is_deterministic_and_input_bound(self):
        first = eval_bytes(obs=observations("2026-09-13T10:15:00Z"))
        second = eval_bytes(doc=copy.deepcopy(agreement()), obs=copy.deepcopy(observations("2026-09-13T10:15:00Z")))
        self.assertEqual(first, second)
        changed = agreement(); changed["agreement_id"] = "agr-temporal-hostile-0002"
        other_obs = observations("2026-09-13T10:15:00Z"); other_obs["agreement_id"] = changed["agreement_id"]
        third = eval_bytes(doc=changed, obs=other_obs)
        self.assertNotEqual(first["receipt_sha256"], third["receipt_sha256"])

    def test_same_json_different_bytes_have_same_canonical_but_distinct_raw_digest(self):
        doc = agreement(); obs = observations("2026-09-13T10:15:00Z")
        compact = gate.evaluate_bytes(raw(doc), raw(obs), as_of=z("2026-09-13T11:00:00Z"))
        pretty = gate.evaluate_bytes(raw(doc, pretty=True), raw(obs, pretty=True), as_of=z("2026-09-13T11:00:00Z"))
        self.assertEqual(compact["agreement_canonical_sha256"], pretty["agreement_canonical_sha256"])
        self.assertEqual(compact["observations_canonical_sha256"], pretty["observations_canonical_sha256"])
        self.assertNotEqual(compact["agreement_raw_sha256"], pretty["agreement_raw_sha256"])
        self.assertNotEqual(compact["observations_raw_sha256"], pretty["observations_raw_sha256"])

    def test_byte_authority_derives_hashes_internally_and_cannot_pair_payload_a_with_digest_b(self):
        a = raw(agreement())
        b_doc = agreement(); b_doc["agreement_id"] = "agr-temporal-hostile-9999"
        b = raw(b_doc)
        obs_a = raw(observations("2026-09-13T10:15:00Z"))
        obs_b_obj = observations("2026-09-13T10:15:00Z")
        obs_b_obj["observations"][0]["observation_id"] = "obs-different"
        obs_b = raw(obs_b_obj)
        out = gate.evaluate_bytes(a, obs_a, as_of=z("2026-09-13T11:00:00Z"))
        self.assertEqual(out["agreement_raw_sha256"], hashlib.sha256(a).hexdigest())
        self.assertNotEqual(out["agreement_raw_sha256"], hashlib.sha256(b).hexdigest())
        self.assertEqual(out["observations_raw_sha256"], hashlib.sha256(obs_a).hexdigest())
        self.assertNotEqual(out["observations_raw_sha256"], hashlib.sha256(obs_b).hexdigest())

    def test_byte_authority_rejects_nonbytes_and_oversize_before_parse(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "exact bytes"):
            gate.evaluate_bytes(bytearray(raw(agreement())), None, as_of=z("2026-09-13T11:00:00Z"))
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "exceeds"):
            gate.evaluate_bytes(b" " * (gate.MAX_INPUT_BYTES + 1), None, as_of=z("2026-09-13T11:00:00Z"))

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "requires O_NOFOLLOW")
    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); real = root / "agreement.json"; link = root / "link.json"
            real.write_text(json.dumps(agreement()), encoding="utf-8"); link.symlink_to(real)
            with self.assertRaisesRegex(gate.TemporalAuthorityError, "non-symlink"):
                gate.read_plain_bytes(link, "agreement")

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "requires O_NOFOLLOW")
    def test_file_byte_path_receipt_hashes_exact_bytes_read(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "agreement.json"
            exact = raw(agreement(), pretty=True) + b"\n"
            path.write_bytes(exact)
            read = gate.read_plain_bytes(path, "agreement")
            out = gate.evaluate_bytes(read, None, as_of=z("2026-09-13T11:00:00Z"))
            self.assertEqual(out["agreement_raw_sha256"], hashlib.sha256(exact).hexdigest())
            self.assertTrue(out["current_work_authorized"])


if __name__ == "__main__":
    unittest.main()
