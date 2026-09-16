import copy
import hashlib
import inspect
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from host import scope_to_delivery as canonical_scope
from host import scope_to_delivery_time_gate as gate


def z(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def agreement(
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    accepted: datetime | None = None,
    status: str = "PRESENT",
):
    if start is None:
        start = z("2026-09-13T10:00:00Z")
    if end is None:
        end = z("2026-09-13T12:00:00Z")
    if accepted is None:
        accepted = z("2026-09-13T09:30:00Z")
    doc = {
        "schema_version": "commons-scope-agreement/v1",
        "kind": "SCOPE_AGREEMENT",
        "agreement_id": "agr-temporal-hostile-20260916-0001",
        "sku_id": "production-survival-sprint",
        "quote": {"currency": "USD", "amount": "15000.00"},
        "window": {"start": fmt(start), "end": fmt(end), "timezone": "UTC"},
        "buyer_ref": "buyer_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "intake_sentence": "Synthetic exact-byte temporal authority fixture.",
        "acceptance_rows": [
            {
                "id": "happy-path",
                "given": "Synthetic input",
                "when": "Run in window",
                "then": "Observe exact result",
                "evidence_required": ["public_ref", "sha256"],
            }
        ],
        "exclusions": ["credentials", "private-data"],
        "refund_choice": "REFUND_IF_MISS",
        "written_acceptance": {
            "status": status,
            "attestation": (
                "AUTHORIZED_OPERATOR_VERIFIED_EXACT_TERMS_ACCEPTANCE"
                if status == "PRESENT"
                else None
            ),
            "terms_digest": "0" * 64,
            "public_ref": (
                "revenue/scope_to_delivery/fixtures/synthetic-acceptance.txt"
                if status == "PRESENT"
                else None
            ),
            "accepted_at": fmt(accepted) if status == "PRESENT" else None,
        },
    }
    doc["written_acceptance"]["terms_digest"] = canonical_scope.terms_digest(doc)
    return doc


def dynamic_agreement(kind: str = "ready"):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    if kind == "ready":
        return agreement(start=now - timedelta(minutes=10), end=now + timedelta(minutes=10), accepted=now - timedelta(minutes=20))
    if kind == "expired":
        return agreement(start=now - timedelta(minutes=30), end=now - timedelta(minutes=20), accepted=now - timedelta(minutes=40))
    if kind == "future":
        return agreement(start=now + timedelta(minutes=20), end=now + timedelta(minutes=40), accepted=now - timedelta(minutes=10))
    if kind == "absent":
        return agreement(start=now - timedelta(minutes=10), end=now + timedelta(minutes=10), accepted=now - timedelta(minutes=20), status="ABSENT")
    raise AssertionError(kind)


def observations(*times: str, agreement_id: str = "agr-temporal-hostile-20260916-0001"):
    return {
        "schema_version": "commons-scope-observations/v1",
        "kind": "EXECUTION_OBSERVATIONS",
        "agreement_id": agreement_id,
        "observations": [
            {
                "observation_id": f"obs-{i:02d}-temporal",
                "kind": "WORK_STARTED",
                "row_id": None,
                "result": "UNMEASURED",
                "public_ref": None,
                "sha256": None,
                "observed_at": when,
                "note": "Synthetic chronology marker.",
            }
            for i, when in enumerate(times, 1)
        ],
    }


def raw(value, *, pretty=False):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
    ).encode()


def project(doc, obs=None):
    return canonical_scope.compose_project(
        doc,
        canonical_scope.load_json(canonical_scope.DEFAULT_CATALOG),
        canonical_scope.load_bindings(canonical_scope.DEFAULT_BINDINGS),
        obs,
        None,
    )


class TemporalGateTests(unittest.TestCase):
    def test_current_ready_requires_exact_bytes_process_clock_and_bound_project(self):
        doc = dynamic_agreement("ready")
        p = project(doc)
        out = gate.evaluate_current_bytes(raw(doc), None, canonical_project=p)
        self.assertEqual(out["state"], "TEMPORAL_PREREQUISITE_READY")
        self.assertTrue(out["current_work_authorized"])
        self.assertEqual(out["clock_authority"], "VERIFIER_PROCESS_UTC")
        self.assertTrue(out["raw_byte_provenance_verified"])
        self.assertTrue(out["canonical_scope_validated"])
        self.assertTrue(out["canonical_project_bound"])
        for key in (
            "external_action_authorized",
            "payment_authorized",
            "delivery_claim_authorized",
            "revenue_authorized",
        ):
            self.assertFalse(out[key])

    def test_authoritative_verifier_reconsumes_exact_ready_inputs(self):
        doc = dynamic_agreement("ready")
        p = project(doc)
        verdict = gate.verify_current_work_authority(raw(doc), None, canonical_project=p)
        self.assertTrue(verdict["valid"])
        self.assertTrue(verdict["current_work_authorized"])
        self.assertEqual(verdict["clock_authority"], "VERIFIER_PROCESS_UTC")

    def test_explicit_as_of_exact_bytes_is_historical_only(self):
        doc = agreement()
        p = project(doc)
        out = gate.evaluate_bytes(
            raw(doc),
            None,
            as_of=z("2026-09-13T11:00:00Z"),
            canonical_project=p,
        )
        self.assertEqual(out["temporal_state"], "TEMPORAL_PREREQUISITE_READY")
        self.assertEqual(out["state"], "HOLD_CALLER_TIME_UNVERIFIED")
        self.assertFalse(out["current_work_authorized"])
        self.assertEqual(out["clock_authority"], "CALLER_SUPPLIED_HISTORICAL_ONLY")

    def test_parsed_object_path_is_permanently_non_authoritative(self):
        doc = agreement()
        out = gate.evaluate(doc, None, as_of=z("2026-09-13T11:00:00Z"))
        self.assertEqual(out["state"], "HOLD_PARSED_OBJECT_UNVERIFIED")
        self.assertFalse(out["raw_byte_provenance_verified"])
        self.assertFalse(out["canonical_scope_validated"])
        self.assertFalse(out["canonical_project_bound"])
        self.assertFalse(out["current_work_authorized"])

    def test_expired_current_receipt_and_verifier_hold(self):
        doc = dynamic_agreement("expired")
        p = project(doc)
        receipt = gate.evaluate_current_bytes(raw(doc), None, canonical_project=p)
        self.assertEqual(receipt["state"], "HOLD_WINDOW_EXPIRED")
        self.assertFalse(receipt["current_work_authorized"])
        verdict = gate.verify_current_work_authority(raw(doc), None, canonical_project=p)
        self.assertFalse(verdict["valid"])
        self.assertFalse(verdict["current_work_authorized"])

    def test_not_started_current_verifier_holds(self):
        doc = dynamic_agreement("future")
        p = project(doc)
        verdict = gate.verify_current_work_authority(raw(doc), None, canonical_project=p)
        self.assertFalse(verdict["valid"])
        self.assertEqual(verdict["state"], "HOLD_WINDOW_NOT_STARTED")

    def test_nonpresent_current_verifier_holds(self):
        doc = dynamic_agreement("absent")
        p = project(doc)
        verdict = gate.verify_current_work_authority(raw(doc), None, canonical_project=p)
        self.assertFalse(verdict["valid"])
        self.assertEqual(verdict["state"], "HOLD_NO_PRESENT_ACCEPTANCE")

    def test_missing_project_holds_current_authority(self):
        doc = dynamic_agreement("ready")
        out = gate.evaluate_current_bytes(raw(doc), None, canonical_project=None)
        self.assertEqual(out["state"], "HOLD_CANONICAL_PROJECT_UNBOUND")
        self.assertFalse(out["current_work_authorized"])

    def test_binding_helper_is_explicit_integrity_only_on_expired_receipt(self):
        doc = dynamic_agreement("expired")
        p = project(doc)
        receipt = gate.evaluate_current_bytes(raw(doc), None, canonical_project=p)
        bound = gate.verify_project_binding_integrity(p, receipt)
        self.assertTrue(bound["integrity_valid"])
        self.assertFalse(bound["current_work_authority_verified"])
        self.assertEqual(bound["authority"], "INTEGRITY_ONLY_NOT_CURRENT_WORK")
        self.assertNotIn("valid", bound)

    def test_compat_binding_name_cannot_return_generic_authority_valid(self):
        doc = dynamic_agreement("expired")
        p = project(doc)
        receipt = gate.evaluate_current_bytes(raw(doc), None, canonical_project=p)
        bound = gate.verify_project_binding(p, receipt)
        self.assertTrue(bound["integrity_valid"])
        self.assertFalse(bound["current_work_authority_verified"])
        self.assertNotIn("valid", bound)

    def test_fabricated_self_sealed_receipt_is_at_most_integrity(self):
        doc = dynamic_agreement("expired")
        p = project(doc)
        core = {
            "schema_version": gate.SCHEMA_RECEIPT,
            "kind": "SCOPE_TO_DELIVERY_TEMPORAL_AUTHORITY",
            "agreement_id": doc["agreement_id"],
            "canonical_scope_validated": True,
            "canonical_project_bound": True,
            "canonical_project_sha256": gate.digest(p),
            "state": "TEMPORAL_PREREQUISITE_READY",
            "current_work_authorized": True,
        }
        fake = dict(core, receipt_sha256=gate.digest(core))
        bound = gate.verify_project_binding(p, fake)
        self.assertTrue(bound["integrity_valid"])
        self.assertFalse(bound["current_work_authority_verified"])
        self.assertNotIn("valid", bound)
        self.assertNotIn("receipt", inspect.signature(gate.verify_current_work_authority).parameters)

    def test_tampered_receipt_fails_integrity_check(self):
        doc = dynamic_agreement("ready")
        p = project(doc)
        receipt = gate.evaluate_current_bytes(raw(doc), None, canonical_project=p)
        receipt["state"] = "HOLD_WINDOW_EXPIRED"
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "receipt_sha256"):
            gate.verify_project_binding_integrity(p, receipt)

    def test_partial_same_id_temporal_b_is_rejected_by_canonical_scope(self):
        full = agreement()
        partial = {
            "schema_version": full["schema_version"],
            "kind": full["kind"],
            "agreement_id": full["agreement_id"],
            "window": full["window"],
            "written_acceptance": full["written_acceptance"],
        }
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "canonical scope"):
            gate.evaluate_bytes(
                raw(partial),
                None,
                as_of=z("2026-09-13T11:00:00Z"),
                canonical_project=project(full),
            )

    def test_complete_same_id_agreement_a_vs_temporal_b_project_mismatch(self):
        a = agreement()
        pa = project(a)
        b = copy.deepcopy(a)
        b["window"] = {
            "start": "2026-09-13T10:30:00Z",
            "end": "2026-09-13T11:30:00Z",
            "timezone": "UTC",
        }
        b["written_acceptance"]["terms_digest"] = canonical_scope.terms_digest(b)
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "does not bind"):
            gate.evaluate_bytes(
                raw(b),
                None,
                as_of=z("2026-09-13T11:00:00Z"),
                canonical_project=pa,
            )

    def test_same_agreement_observation_a_vs_b_project_mismatch(self):
        doc = agreement()
        oa = observations("2026-09-13T10:15:00Z")
        ob = observations("2026-09-13T10:25:00Z")
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "does not bind"):
            gate.evaluate_bytes(
                raw(doc),
                raw(ob),
                as_of=z("2026-09-13T11:00:00Z"),
                canonical_project=project(doc, oa),
            )

    def test_duplicate_json_key_rejected(self):
        good = raw(agreement())
        bad = good[:-1] + b',"agreement_id":"other"}'
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "duplicate JSON key"):
            gate.evaluate_bytes(
                bad,
                None,
                as_of=z("2026-09-13T11:00:00Z"),
                canonical_project=None,
            )

    def test_nonfinite_json_rejected(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "non-finite"):
            gate.strict_loads(b'{"x":NaN}', "x")

    def test_future_acceptance_rejected(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "acceptance is in"):
            gate.evaluate(
                agreement(),
                None,
                as_of=z("2026-09-13T09:00:00Z"),
            )

    def test_observation_before_acceptance_rejected(self):
        obs = observations("2026-09-13T09:00:00Z")
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "predates written acceptance"):
            gate.evaluate_bytes(
                raw(agreement()),
                raw(obs),
                as_of=z("2026-09-13T11:00:00Z"),
                canonical_project=project(agreement(), obs),
            )

    def test_observation_after_window_rejected(self):
        obs = observations("2026-09-13T12:00:01Z")
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "after contracted work window"):
            gate.evaluate_bytes(
                raw(agreement()),
                raw(obs),
                as_of=z("2026-09-13T13:00:00Z"),
                canonical_project=project(agreement(), obs),
            )

    def test_same_json_different_raw_bytes_stay_distinct_but_same_project(self):
        doc = agreement()
        p = project(doc)
        compact = gate.evaluate_bytes(
            raw(doc),
            None,
            as_of=z("2026-09-13T11:00:00Z"),
            canonical_project=p,
        )
        pretty = gate.evaluate_bytes(
            raw(doc, pretty=True),
            None,
            as_of=z("2026-09-13T11:00:00Z"),
            canonical_project=p,
        )
        self.assertEqual(
            compact["agreement_canonical_sha256"],
            pretty["agreement_canonical_sha256"],
        )
        self.assertNotEqual(
            compact["agreement_raw_sha256"], pretty["agreement_raw_sha256"]
        )
        self.assertEqual(
            compact["canonical_project_sha256"], pretty["canonical_project_sha256"]
        )

    def test_internal_raw_hash_cannot_be_overridden(self):
        doc = agreement()
        exact = raw(doc)
        out = gate.evaluate_bytes(
            exact,
            None,
            as_of=z("2026-09-13T11:00:00Z"),
            canonical_project=project(doc),
        )
        self.assertEqual(out["agreement_raw_sha256"], hashlib.sha256(exact).hexdigest())
        self.assertNotIn("agreement_raw_sha256", inspect.signature(gate.evaluate_bytes).parameters)

    def test_nonbytes_and_oversize_fail_closed(self):
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "exact bytes"):
            gate.evaluate_bytes(
                bytearray(raw(agreement())),
                None,
                as_of=z("2026-09-13T11:00:00Z"),
            )
        with self.assertRaisesRegex(gate.TemporalAuthorityError, "exceeds"):
            gate.evaluate_bytes(
                b" " * (gate.MAX_INPUT_BYTES + 1),
                None,
                as_of=z("2026-09-13T11:00:00Z"),
            )

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "requires O_NOFOLLOW")
    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            real = root / "a.json"
            link = root / "l.json"
            real.write_bytes(raw(agreement()))
            link.symlink_to(real)
            with self.assertRaisesRegex(gate.TemporalAuthorityError, "non-symlink"):
                gate.read_plain_bytes(link, "agreement")

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "requires O_NOFOLLOW")
    def test_file_byte_hash_exact(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "a.json"
            exact = raw(agreement(), pretty=True) + b"\n"
            path.write_bytes(exact)
            read = gate.read_plain_bytes(path, "agreement")
            out = gate.evaluate_bytes(
                read,
                None,
                as_of=z("2026-09-13T11:00:00Z"),
                canonical_project=project(agreement()),
            )
            self.assertEqual(
                out["agreement_raw_sha256"], hashlib.sha256(exact).hexdigest()
            )

    def test_historical_receipt_is_deterministic(self):
        doc = agreement()
        p = project(doc)
        first = gate.evaluate_bytes(
            raw(doc),
            None,
            as_of=z("2026-09-13T11:00:00Z"),
            canonical_project=p,
        )
        second = gate.evaluate_bytes(
            raw(copy.deepcopy(doc)),
            None,
            as_of=z("2026-09-13T11:00:00Z"),
            canonical_project=copy.deepcopy(p),
        )
        self.assertEqual(first, second)

    def test_current_public_surfaces_accept_no_caller_clock(self):
        for fn in (gate.evaluate_current_bytes, gate.verify_current_work_authority):
            params = inspect.signature(fn).parameters
            for forbidden in ("as_of", "now", "observed_at", "trusted_now", "evaluation_time"):
                self.assertNotIn(forbidden, params)

    def test_authoritative_verifier_accepts_no_receipt_object(self):
        params = inspect.signature(gate.verify_current_work_authority).parameters
        self.assertEqual(set(params), {"agreement_raw", "observations_raw", "canonical_project"})

    @unittest.skipUnless(hasattr(os, "O_NOFOLLOW"), "requires O_NOFOLLOW")
    def test_cli_uses_process_clock_and_requires_matching_project(self):
        doc = dynamic_agreement("ready")
        p = project(doc)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ap = root / "a.json"
            pp = root / "p.json"
            ap.write_bytes(raw(doc))
            pp.write_bytes(raw(p))
            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(gate.__file__)),
                    "--agreement",
                    str(ap),
                    "--project",
                    str(pp),
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload["current_work_authorized"])
            self.assertEqual(payload["clock_authority"], "VERIFIER_PROCESS_UTC")


if __name__ == "__main__":
    unittest.main()
