import importlib.util
import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE = ROOT / "revenue" / "mmsd_ai_governance" / "qualification.py"
spec = importlib.util.spec_from_file_location("mmsd_qualification", MODULE)
q = importlib.util.module_from_spec(spec)
spec.loader.exec_module(q)

D = "a" * 64


def evidence(status="CONFIRMED", n="x"):
    return {
        "status": status,
        "evidence_ref": f"evidence-{n}",
        "evidence_digest": D,
        "note": f"truth-bound evidence note {n}",
    }


def request(status="CONFIRMED"):
    return {
        "schema_version": q.SCHEMA,
        "opportunity_id": "MMSD-AI-GOVERNANCE-RFP-20260913",
        "compiled_at": "2026-09-13T10:20:00Z",
        "gates": {name: evidence(status, name) for name in q.REQUIRED_GATES},
    }


class QualificationTests(unittest.TestCase):
    def assert_code(self, fn, text):
        with self.assertRaises(q.QualificationError) as ctx:
            fn()
        self.assertIn(text, str(ctx.exception))

    def test_all_confirmed_is_owner_review_not_submission(self):
        pkg = q.compile_readiness(request())
        self.assertEqual(pkg["receipt"]["status"], q.READY)
        self.assertTrue(all(v is False for v in pkg["receipt"]["authorities"].values()))

    def test_unknown_holds(self):
        r = request()
        r["gates"]["official_pdf_obtained"] = evidence("UNKNOWN", "pdf")
        pkg = q.compile_readiness(r)
        self.assertEqual(pkg["receipt"]["status"], q.HOLD)
        self.assertIn("UNKNOWN:official_pdf_obtained", pkg["receipt"]["reason_codes"])

    def test_nonhard_failed_gate_holds(self):
        r = request()
        r["gates"]["price_authorized"] = evidence("FAILED", "price")
        self.assertEqual(q.compile_readiness(r)["receipt"]["status"], q.HOLD)

    def test_hard_reference_failure_is_no_go(self):
        r = request()
        r["gates"]["references_satisfied"] = evidence("FAILED", "refs")
        pkg = q.compile_readiness(r)
        self.assertEqual(pkg["receipt"]["status"], q.NO_GO)
        self.assertIn("HARD_GATE_FAILED:references_satisfied", pkg["receipt"]["reason_codes"])

    def test_hard_insurance_failure_is_no_go(self):
        r = request()
        r["gates"]["insurance_satisfied_or_bindable"] = evidence("FAILED", "insurance")
        self.assertEqual(q.compile_readiness(r)["receipt"]["status"], q.NO_GO)

    def test_hard_scope_failure_is_no_go(self):
        r = request()
        r["gates"]["technical_scope_supported"] = evidence("FAILED", "scope")
        self.assertEqual(q.compile_readiness(r)["receipt"]["status"], q.NO_GO)

    def test_hard_capacity_failure_is_no_go(self):
        r = request()
        r["gates"]["delivery_capacity_supported"] = evidence("FAILED", "capacity")
        self.assertEqual(q.compile_readiness(r)["receipt"]["status"], q.NO_GO)

    def test_exact_request_keys(self):
        r = request(); r["extra"] = True
        self.assert_code(lambda: q.compile_readiness(r), "exact keys")

    def test_exact_gate_set(self):
        r = request(); del r["gates"]["price_authorized"]
        self.assert_code(lambda: q.compile_readiness(r), "exact keys")

    def test_exact_evidence_keys(self):
        r = request(); r["gates"]["price_authorized"]["secret"] = "x"
        self.assert_code(lambda: q.compile_readiness(r), "exact keys")

    def test_invalid_status(self):
        r = request(); r["gates"]["price_authorized"]["status"] = "READY"
        self.assert_code(lambda: q.compile_readiness(r), "invalid")

    def test_invalid_digest(self):
        r = request(); r["gates"]["price_authorized"]["evidence_digest"] = "abc"
        self.assert_code(lambda: q.compile_readiness(r), "sha256")

    def test_schema_mismatch(self):
        r = request(); r["schema_version"] = "other"
        self.assert_code(lambda: q.compile_readiness(r), "mismatch")

    def test_opportunity_mismatch(self):
        r = request(); r["opportunity_id"] = "other"
        self.assert_code(lambda: q.compile_readiness(r), "mismatch")

    def test_timezone_required(self):
        r = request(); r["compiled_at"] = "2026-09-13T10:20:00"
        self.assert_code(lambda: q.compile_readiness(r), "timezone")

    def test_timestamp_normalizes_to_utc(self):
        r = request(); r["compiled_at"] = "2026-09-13T06:20:00-04:00"
        pkg = q.compile_readiness(r)
        self.assertEqual(pkg["request"]["compiled_at"], "2026-09-13T10:20:00Z")

    def test_deterministic_same_request(self):
        self.assertEqual(q.compile_readiness(request()), q.compile_readiness(request()))

    def test_gate_order_does_not_change_digest(self):
        a = request(); b = request()
        b["gates"] = dict(reversed(list(b["gates"].items())))
        self.assertEqual(q.compile_readiness(a)["receipt"]["request_digest"], q.compile_readiness(b)["receipt"]["request_digest"])

    def test_evidence_change_changes_digest(self):
        a = q.compile_readiness(request())
        b = request(); b["gates"]["price_authorized"]["note"] = "different truthful note"
        b = q.compile_readiness(b)
        self.assertNotEqual(a["receipt"]["request_digest"], b["receipt"]["request_digest"])

    def test_verify_valid_package(self):
        pkg = q.compile_readiness(request())
        result = q.verify_package(pkg)
        self.assertTrue(result["valid"])
        self.assertEqual(result["status"], q.READY)

    def test_verify_receipt_tamper_fails(self):
        pkg = q.compile_readiness(request())
        pkg["receipt"]["status"] = "SUBMITTED"
        self.assert_code(lambda: q.verify_package(pkg), "mismatch")

    def test_verify_authority_tamper_fails(self):
        pkg = q.compile_readiness(request())
        pkg["receipt"]["authorities"]["submit_proposal"] = True
        self.assert_code(lambda: q.verify_package(pkg), "mismatch")

    def test_verify_payload_tamper_fails(self):
        pkg = q.compile_readiness(request())
        pkg["request"]["gates"]["price_authorized"]["note"] = "tampered"
        self.assert_code(lambda: q.verify_package(pkg), "mismatch")

    def test_package_exact_keys(self):
        pkg = q.compile_readiness(request()); pkg["extra"] = 1
        self.assert_code(lambda: q.verify_package(pkg), "exact keys")

    def test_not_applicable_can_be_resolved(self):
        r = request(); r["gates"]["insurance_requirement_verified"] = evidence("NOT_APPLICABLE", "insurance-na")
        self.assertEqual(q.compile_readiness(r)["receipt"]["status"], q.READY)

    def test_multiple_unknowns_are_sorted(self):
        r = request()
        r["gates"]["price_authorized"] = evidence("UNKNOWN", "price")
        r["gates"]["official_pdf_obtained"] = evidence("UNKNOWN", "pdf")
        reasons = q.compile_readiness(r)["receipt"]["reason_codes"]
        self.assertEqual(reasons, sorted(reasons))

    def test_example_truthfully_holds(self):
        example = json.loads((ROOT / "revenue" / "mmsd_ai_governance" / "example_qualification.json").read_text())
        pkg = q.compile_readiness(example)
        self.assertEqual(pkg["receipt"]["status"], q.HOLD)
        self.assertFalse(pkg["receipt"]["authorities"]["contact_buyer"])

    def test_unknown_is_not_treated_as_failure(self):
        r = request(); r["gates"]["references_satisfied"] = evidence("UNKNOWN", "refs")
        pkg = q.compile_readiness(r)
        self.assertEqual(pkg["receipt"]["status"], q.HOLD)
        self.assertFalse(any(code.startswith("HARD_GATE_FAILED") for code in pkg["receipt"]["reason_codes"]))

    def test_failed_unknown_mixture_prefers_no_go_if_hard(self):
        r = request()
        r["gates"]["references_satisfied"] = evidence("FAILED", "refs")
        r["gates"]["official_pdf_obtained"] = evidence("UNKNOWN", "pdf")
        pkg = q.compile_readiness(r)
        self.assertEqual(pkg["receipt"]["status"], q.NO_GO)
        self.assertEqual(pkg["receipt"]["reason_codes"], ["HARD_GATE_FAILED:references_satisfied"])

    def test_empty_text_rejected(self):
        r = request(); r["gates"]["price_authorized"]["note"] = "   "
        self.assert_code(lambda: q.compile_readiness(r), "invalid length")

    def test_boolean_does_not_pass_as_text(self):
        r = request(); r["gates"]["price_authorized"]["evidence_ref"] = True
        self.assert_code(lambda: q.compile_readiness(r), "text required")


if __name__ == "__main__":
    unittest.main()
