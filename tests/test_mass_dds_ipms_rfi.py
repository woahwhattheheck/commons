import copy
import json
import unittest
from pathlib import Path

from opportunities.mass_dds_ipms_rfi.compiler import CompileError, compile_packet, verify_bundle

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "opportunities" / "mass_dds_ipms_rfi" / "example_input.json"


def load():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def evidence(doc, eid, subject, source_id="src.notice.header.20260915", claim="verified"):
    doc["evidence"].append({
        "id": eid,
        "subject": subject,
        "source_id": source_id,
        "claim": claim,
        "observed_at": "2026-09-15T07:50:00Z",
    })


def make_ready():
    d = load()
    d["company"] = {"legal_name": "Example Vendor LLC", "contact_name": "Example Contact", "contact_email": "contact@example.invalid", "product_name": "Evidence Example"}
    for src in d["sources"]:
        if src["source_class"] == "BUYER_ATTACHMENT":
            src["sha256"] = "a" * 64 if src["id"].endswith("rfi") else "b" * 64
    for att in d["required_attachments"]:
        att["available"] = True
    for cap in d["capabilities"]:
        cap["state"] = "NOT_SUPPORTED"
    for row in d["privacy"]:
        evidence(d, "ev." + row["id"], row["id"])
        row["value"] = "EVIDENCED_POSTURE"
        row["evidence_refs"] = ["ev." + row["id"]]
    for row in d["architecture"]:
        evidence(d, "ev." + row["id"], row["id"])
        row["state"] = "EVIDENCED"
        row["evidence_refs"] = ["ev." + row["id"]]
    for row in d["compatibility"]:
        row["state"] = "NOT_SUPPORTED"
    d["tco"] = {
        "currency": "USD",
        "components": [
            {"id": "tco.implementation", "category": "IMPLEMENTATION", "period": "ONE_TIME", "years": 1, "low_cents": 1000000, "high_cents": 1500000, "source": "OWNER_INPUT"},
            {"id": "tco.recurring", "category": "RECURRING", "period": "ANNUAL", "years": 5, "low_cents": 200000, "high_cents": 300000, "source": "VENDOR_INPUT"},
        ],
        "declared_five_year_low": 2000000,
        "declared_five_year_high": 3000000,
    }
    for q in d["questions"]:
        q["state"] = "ANSWERED"
        q["answer"] = "Evidence-bound answer supplied for test fixture."
    return d


class TestMassDDSCompiler(unittest.TestCase):
    def assert_bad(self, doc, needle):
        with self.assertRaises(CompileError) as ctx:
            compile_packet(doc)
        self.assertIn(needle, str(ctx.exception))

    def test_incomplete_example_holds(self):
        response, receipt = compile_packet(load())
        self.assertEqual(response["readiness"], "HOLD")
        self.assertIn("MISSING_REQUIRED_ATTACHMENT:att.rfi", response["blockers"])
        self.assertFalse(response["authority"]["provider_submission"])
        verify_bundle(load(), response, receipt)

    def test_ready_fixture_is_response_draft_ready(self):
        response, receipt = compile_packet(make_ready())
        self.assertEqual(response["readiness"], "RESPONSE_DRAFT_READY")
        self.assertEqual(response["blockers"], [])
        self.assertEqual(response["five_year_tco"]["low_cents"], 2000000)
        self.assertEqual(response["five_year_tco"]["high_cents"], 3000000)
        verify_bundle(make_ready(), response, receipt)

    def test_deterministic_replay(self):
        a = compile_packet(make_ready())
        b = compile_packet(make_ready())
        self.assertEqual(a, b)

    def test_unknown_root_field_rejected(self):
        d = load(); d["surprise"] = 1
        self.assert_bad(d, "root:keys")

    def test_bool_int_alias_rejected(self):
        d = make_ready(); d["tco"]["components"][0]["low_cents"] = True
        self.assert_bad(d, "integer_required")

    def test_duplicate_source_id_rejected(self):
        d = load(); d["sources"].append(copy.deepcopy(d["sources"][0]))
        self.assert_bad(d, "sources:duplicate_id")

    def test_duplicate_capability_id_rejected(self):
        d = load(); d["capabilities"].append(copy.deepcopy(d["capabilities"][0]))
        self.assert_bad(d, "capabilities:duplicate_id")

    def test_malformed_hash_rejected(self):
        d = load(); d["sources"][0]["sha256"] = "abc"
        self.assert_bad(d, "invalid_sha256")

    def test_naive_time_rejected(self):
        d = load(); d["sources"][0]["observed_at"] = "2026-09-15T07:45:00"
        self.assert_bad(d, "timezone_required")

    def test_future_source_rejected(self):
        d = load(); d["sources"][0]["observed_at"] = "2026-09-16T07:45:00Z"
        self.assert_bad(d, "future_observation")

    def test_published_after_observed_rejected(self):
        d = load(); d["sources"][0]["published_at"] = "2026-09-15T07:59:00Z"
        self.assert_bad(d, "published_after_observed")

    def test_secondary_source_cannot_control(self):
        d = load(); d["sources"][0]["source_class"] = "SECONDARY_REFERENCE"
        self.assert_bad(d, "secondary_cannot_control")

    def test_current_amendment_must_control(self):
        d = load(); d["sources"][0]["source_class"] = "AMENDMENT"; d["sources"][0]["authority"] = "SECONDARY"
        self.assert_bad(d, "current_amendment_must_control")

    def test_evidence_transplant_rejected(self):
        d = load(); evidence(d, "ev.cap", "different-subject")
        d["capabilities"][0]["state"] = "SUPPORTED"; d["capabilities"][0]["evidence_refs"] = ["ev.cap"]
        self.assert_bad(d, "evidence_transplant")

    def test_affirmative_capability_needs_evidence(self):
        d = load(); d["capabilities"][0]["state"] = "SUPPORTED"
        self.assert_bad(d, "affirmative_without_evidence")

    def test_known_privacy_needs_evidence(self):
        d = load(); d["privacy"][0]["value"] = "NOT_USED"
        self.assert_bad(d, "known_without_evidence")

    def test_all_privacy_ids_required(self):
        d = load(); d["privacy"].pop()
        self.assert_bad(d, "privacy:required_ids")

    def test_facial_recognition_contradiction(self):
        d = load()
        evidence(d, "ev.face-cap", "cap.facial-recognition")
        d["capabilities"][1]["state"] = "SUPPORTED"; d["capabilities"][1]["evidence_refs"] = ["ev.face-cap"]
        evidence(d, "ev.face-policy", "facial_recognition")
        d["privacy"][0]["value"] = "NOT_USED"; d["privacy"][0]["evidence_refs"] = ["ev.face-policy"]
        self.assert_bad(d, "facial_recognition_contradiction")

    def test_tco_mismatch_rejected(self):
        d = make_ready(); d["tco"]["declared_five_year_high"] += 1
        self.assert_bad(d, "declared_total_mismatch")

    def test_tco_low_gt_high_rejected(self):
        d = make_ready(); d["tco"]["components"][0]["low_cents"] = 1600000
        self.assert_bad(d, "low_gt_high")

    def test_one_time_years_rejected(self):
        d = make_ready(); d["tco"]["components"][0]["years"] = 2
        self.assert_bad(d, "one_time_years")

    def test_annual_over_five_rejected(self):
        d = make_ready(); d["tco"]["components"][1]["years"] = 6
        self.assert_bad(d, "annual_years_gt_5")

    def test_available_attachment_requires_hash(self):
        d = load(); d["required_attachments"][0]["available"] = True
        self.assert_bad(d, "available_without_hash")

    def test_stale_controlling_source_holds(self):
        d = make_ready(); d["evaluation_time"] = "2026-09-30T08:00:00Z"
        response, _ = compile_packet(d)
        self.assertEqual(response["readiness"], "HOLD")
        self.assertTrue(any(x.startswith("STALE_CONTROLLING_SOURCE:") for x in response["blockers"]))

    def test_missing_company_field_holds(self):
        d = make_ready(); d["company"]["product_name"] = None
        response, _ = compile_packet(d)
        self.assertIn("MISSING_COMPANY_FIELD:product_name", response["blockers"])

    def test_unknown_capability_holds(self):
        d = make_ready(); d["capabilities"][0]["state"] = "UNKNOWN"
        response, _ = compile_packet(d)
        self.assertIn("UNKNOWN_CAPABILITY:cap.video-analytics", response["blockers"])

    def test_unknown_privacy_holds(self):
        d = make_ready(); row = d["privacy"][0]; row["value"] = "UNKNOWN"; row["evidence_refs"] = []
        response, _ = compile_packet(d)
        self.assertIn("UNKNOWN_PRIVACY_FACT:facial_recognition", response["blockers"])

    def test_missing_required_response_holds(self):
        d = make_ready(); d["questions"][0]["state"] = "OWNER_INPUT_REQUIRED"; d["questions"][0]["answer"] = None
        response, _ = compile_packet(d)
        self.assertIn("MISSING_REQUIRED_RESPONSE:q.company", response["blockers"])

    def test_receipt_tamper_rejected(self):
        d = make_ready(); response, receipt = compile_packet(d); receipt["readiness"] = "HOLD"
        with self.assertRaises(CompileError):
            verify_bundle(d, response, receipt)

    def test_response_tamper_rejected(self):
        d = make_ready(); response, receipt = compile_packet(d); response["readiness"] = "HOLD"
        with self.assertRaises(CompileError):
            verify_bundle(d, response, receipt)

    def test_markdown_preserves_authority_ceiling(self):
        response, _ = compile_packet(load())
        self.assertIn("does not submit, sign, price-bind, contact the buyer", response["markdown"])


if __name__ == "__main__":
    unittest.main()
