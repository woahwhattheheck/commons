from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.outbound_send_guard.relationship_census import (
    CensusError, evaluate, evaluate_bytes, sign_census, strict_loads, verify_receipt,
)

KEY = b"k" * 32
ROUTE_A = "a" * 64
ROUTE_B = "b" * 64
RECORD = "c" * 64


def request(worker="Z-Solstice"):
    return {
        "schema": "relationship-census-request/v1",
        "target_scope": "funto-network",
        "current_worker": worker,
        "as_of": "2026-09-14T02:30:00Z",
        "max_snapshot_age_seconds": 3600,
        "coverage_required_from": "2026-09-01T00:00:00Z",
        "expected_provider": "gmail",
        "expected_key_id": "gmail-export-v1",
        "route_sha256": [ROUTE_A, ROUTE_B],
    }


def census_core(state="ACTIVE_OWNER", owner="Z-Solstice", generation=3):
    event = "SENT" if state != "UNSEEN" else "NONE"
    def route(r):
        if event == "NONE":
            return {"target_scope": "funto-network", "route_sha256": r, "event_kind": "NONE", "event_at": None, "provider_record_sha256": None, "owner": None, "owner_generation": 0}
        return {"target_scope": "funto-network", "route_sha256": r, "event_kind": event, "event_at": "2026-09-13T21:20:00Z", "provider_record_sha256": RECORD, "owner": owner, "owner_generation": generation}
    return {
        "schema": "relationship-census/v1",
        "target_scope": "funto-network",
        "provider": "gmail",
        "snapshot_id": "gmail-snapshot-20260914-0229",
        "snapshot_at": "2026-09-14T02:29:00Z",
        "coverage_started_at": "2026-08-01T00:00:00Z",
        "complete": True,
        "relationship": {"state": state, "owner": owner if state != "UNSEEN" else None, "generation": generation if state != "UNSEEN" else 0},
        "routes": [route(ROUTE_A), route(ROUTE_B)],
        "transfer": None,
    }


def signed(**kwargs):
    return sign_census(census_core(**kwargs), KEY, "gmail-export-v1")


class RelationshipCensusTests(unittest.TestCase):
    def test_current_owner_holds(self):
        receipt = evaluate(request(), signed(), KEY)
        self.assertEqual(receipt["decision"], "CUSTODY_HELD")
        self.assertFalse(receipt["external_send_authorized"])
        self.assertTrue(verify_receipt(receipt))

    def test_unseen_is_clear_but_never_send_authority(self):
        receipt = evaluate(request(), signed(state="UNSEEN", owner=None, generation=0), KEY)
        self.assertEqual(receipt["decision"], "CUSTODY_CLEAR")
        self.assertFalse(receipt["external_send_authorized"])

    def test_other_owner_holds(self):
        receipt = evaluate(request(), signed(owner="Z-Dedekind"), KEY)
        self.assertEqual((receipt["decision"], receipt["reason"]), ("HOLD", "OWNED_BY_OTHER"))

    def test_invalid_attestation_holds(self):
        c = signed()
        c["relationship"]["generation"] = 4
        receipt = evaluate(request(), c, KEY)
        self.assertEqual((receipt["decision"], receipt["reason"]), ("HOLD", "ATTESTATION_INVALID"))

    def test_key_id_mismatch_holds_before_authority(self):
        c = signed()
        c["attestation"]["key_id"] = "wrong-export-v1"
        receipt = evaluate(request(), c, KEY)
        self.assertEqual(receipt["reason"], "ATTESTATION_KEY_ID_MISMATCH")
        self.assertFalse(receipt["attestation_valid"])

    def test_cross_target_route_transplant_holds_even_when_resigned(self):
        core = census_core()
        core["routes"][1]["target_scope"] = "other-buyer"
        c = sign_census(core, KEY, "gmail-export-v1")
        receipt = evaluate(request(), c, KEY)
        self.assertEqual(receipt["reason"], "CROSS_TARGET_ROUTE_TRANSPLANT")

    def test_target_mismatch_holds(self):
        core = census_core()
        core["target_scope"] = "other-buyer"
        c = sign_census(core, KEY, "gmail-export-v1")
        self.assertEqual(evaluate(request(), c, KEY)["reason"], "TARGET_SCOPE_MISMATCH")

    def test_stale_snapshot_holds(self):
        core = census_core()
        core["snapshot_at"] = "2026-09-13T00:00:00Z"
        c = sign_census(core, KEY, "gmail-export-v1")
        self.assertEqual(evaluate(request(), c, KEY)["reason"], "CENSUS_STALE")

    def test_future_snapshot_holds(self):
        core = census_core()
        core["snapshot_at"] = "2026-09-14T03:00:00Z"
        c = sign_census(core, KEY, "gmail-export-v1")
        self.assertEqual(evaluate(request(), c, KEY)["reason"], "CENSUS_FROM_FUTURE")

    def test_incomplete_holds(self):
        core = census_core(); core["complete"] = False
        c = sign_census(core, KEY, "gmail-export-v1")
        self.assertEqual(evaluate(request(), c, KEY)["reason"], "CENSUS_INCOMPLETE")

    def test_shallow_coverage_holds(self):
        core = census_core(); core["coverage_started_at"] = "2026-09-10T00:00:00Z"
        c = sign_census(core, KEY, "gmail-export-v1")
        self.assertEqual(evaluate(request(), c, KEY)["reason"], "COVERAGE_TOO_SHALLOW")

    def test_missing_requested_route_holds(self):
        core = census_core(); core["routes"] = core["routes"][:1]
        c = sign_census(core, KEY, "gmail-export-v1")
        self.assertEqual(evaluate(request(), c, KEY)["reason"], "REQUESTED_ROUTE_NOT_COVERED")

    def test_dnr_always_holds(self):
        c = signed(state="DNR", owner="Z-Solstice", generation=3)
        self.assertEqual(evaluate(request(), c, KEY)["reason"], "DNR")

    def test_hard_bounce_always_holds(self):
        c = signed(state="HARD_BOUNCE", owner="Z-Solstice", generation=3)
        self.assertEqual(evaluate(request(), c, KEY)["reason"], "HARD_BOUNCE")

    def test_waiting_reply_owner_holds_custody(self):
        c = signed(state="WAITING_REPLY")
        self.assertEqual(evaluate(request(), c, KEY)["decision"], "CUSTODY_HELD")

    def test_transfer_requires_proof(self):
        c = signed(state="TRANSFERRED")
        self.assertEqual(evaluate(request(), c, KEY)["reason"], "TRANSFER_PROOF_MISSING")

    def test_valid_owner_transfer(self):
        core = census_core(state="TRANSFERRED", owner="Z-Solstice", generation=4)
        for row in core["routes"]:
            row["owner_generation"] = 4
        core["transfer"] = {
            "schema": "relationship-transfer/v1", "target_scope": "funto-network", "transfer_id": "funto-transfer-4",
            "from_owner": "Z-Dedekind", "to_owner": "Z-Solstice", "from_generation": 3, "to_generation": 4,
            "release_actor": "Z-Dedekind", "release_role": "owner", "released_at": "2026-09-14T02:20:00Z",
            "accepted_by": "Z-Solstice", "accepted_at": "2026-09-14T02:21:00Z",
        }
        c = sign_census(core, KEY, "gmail-export-v1")
        receipt = evaluate(request(), c, KEY)
        self.assertEqual((receipt["decision"], receipt["reason"]), ("CUSTODY_HELD", "TRANSFER_VALID"))

    def test_transfer_rejects_wrong_acceptor(self):
        core = census_core(state="TRANSFERRED", owner="Z-Solstice", generation=4)
        core["transfer"] = {
            "schema": "relationship-transfer/v1", "target_scope": "funto-network", "transfer_id": "funto-transfer-4",
            "from_owner": "Z-Dedekind", "to_owner": "Z-Solstice", "from_generation": 3, "to_generation": 4,
            "release_actor": "Z-Dedekind", "release_role": "owner", "released_at": "2026-09-14T02:20:00Z",
            "accepted_by": "Z-Other", "accepted_at": "2026-09-14T02:21:00Z",
        }
        c = sign_census(core, KEY, "gmail-export-v1")
        self.assertEqual(evaluate(request(), c, KEY)["reason"], "TRANSFER_ACCEPTANCE_NOT_NEW_OWNER")

    def test_admin_transfer_release_is_allowed(self):
        core = census_core(state="TRANSFERRED", owner="Z-Solstice", generation=4)
        core["transfer"] = {
            "schema": "relationship-transfer/v1", "target_scope": "funto-network", "transfer_id": "funto-transfer-4",
            "from_owner": "Z-Dedekind", "to_owner": "Z-Solstice", "from_generation": 3, "to_generation": 4,
            "release_actor": "Root-Operator", "release_role": "admin", "released_at": "2026-09-14T02:20:00Z",
            "accepted_by": "Z-Solstice", "accepted_at": "2026-09-14T02:21:00Z",
        }
        c = sign_census(core, KEY, "gmail-export-v1")
        self.assertEqual(evaluate(request(), c, KEY)["decision"], "CUSTODY_HELD")

    def test_raw_byte_custody_differs_for_whitespace(self):
        r = request(); c = signed()
        rb1 = json.dumps(r, sort_keys=True, separators=(",", ":")).encode()
        rb2 = json.dumps(r, sort_keys=True, indent=2).encode()
        cb = json.dumps(c, sort_keys=True, separators=(",", ":")).encode()
        one = evaluate_bytes(rb1, cb, KEY); two = evaluate_bytes(rb2, cb, KEY)
        self.assertEqual(one["request_object_sha256"], two["request_object_sha256"])
        self.assertNotEqual(one["byte_custody"]["request_sha256"], two["byte_custody"]["request_sha256"])

    def test_duplicate_keys_rejected(self):
        with self.assertRaises(CensusError):
            strict_loads(b'{"x":1,"x":2}')

    def test_nonfinite_rejected(self):
        with self.assertRaises(CensusError):
            strict_loads(b'{"x":NaN}')

    def test_receipt_tamper_rejected(self):
        receipt = evaluate(request(), signed(), KEY)
        receipt["decision"] = "CUSTODY_CLEAR"
        with self.assertRaises(CensusError):
            verify_receipt(receipt)

    def test_receipt_never_contains_raw_owner(self):
        receipt = evaluate(request(), signed(owner="Z-Solstice"), KEY)
        encoded = json.dumps(receipt)
        self.assertNotIn("Z-Solstice", encoded)
        self.assertNotIn("Z-Dedekind", encoded)

    def test_wrong_secret_holds(self):
        receipt = evaluate(request(), signed(), b"z" * 32)
        self.assertEqual(receipt["reason"], "ATTESTATION_INVALID")

    def test_short_secret_rejected(self):
        with self.assertRaises(CensusError):
            evaluate(request(), signed(), b"short")

    def test_cli_atomic_output_and_alias_rejection(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            req = root / "request.json"; cen = root / "census.json"; out = root / "receipt.json"
            req.write_text(json.dumps(request()), encoding="utf-8")
            cen.write_text(json.dumps(signed()), encoding="utf-8")
            env = dict(os.environ, RELATIONSHIP_CENSUS_KEY="k" * 32)
            cmd = [sys.executable, "-m", "tools.outbound_send_guard.relationship_census", "--request", str(req), "--census", str(cen), "--out", str(out)]
            ok = subprocess.run(cmd, cwd=Path(__file__).resolve().parents[2], env=env, capture_output=True, text=True)
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertTrue(verify_receipt(json.loads(out.read_text())))
            alias = subprocess.run([sys.executable, "-m", "tools.outbound_send_guard.relationship_census", "--request", str(req), "--census", str(cen), "--out", str(req)], cwd=Path(__file__).resolve().parents[2], env=env, capture_output=True, text=True)
            self.assertEqual(alias.returncode, 2)


if __name__ == "__main__":
    unittest.main()
