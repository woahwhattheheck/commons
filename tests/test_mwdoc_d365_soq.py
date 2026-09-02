from __future__ import annotations

import copy
import csv
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKET_DIR = ROOT / "revenue" / "mwdoc_d365_soq"
SPEC = importlib.util.spec_from_file_location(
    "mwdoc_builder", ROOT / "scripts" / "build_mwdoc_d365_soq.py"
)
builder = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(builder)


class MWDOCPartnerPacketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = json.loads((PACKET_DIR / "source.json").read_text(encoding="utf-8"))
        cls.packet = json.loads((PACKET_DIR / "readiness.json").read_text(encoding="utf-8"))
        cls.schema = json.loads((PACKET_DIR / "readiness.schema.json").read_text(encoding="utf-8"))

    def test_compile_twice_is_byte_identical_and_committed(self):
        first = builder.artifacts(copy.deepcopy(self.source))
        second = builder.artifacts(copy.deepcopy(self.source))
        self.assertEqual(first, second)
        for name, content in first.items():
            self.assertEqual((PACKET_DIR / name).read_text(encoding="utf-8"), content)

    def test_write_compile_twice_is_identical(self):
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            builder.write_outputs(PACKET_DIR / "source.json", Path(left))
            builder.write_outputs(PACKET_DIR / "source.json", Path(right))
            for name in builder.OUTPUTS:
                self.assertEqual((Path(left) / name).read_bytes(), (Path(right) / name).read_bytes())

    def test_machine_schema_and_required_contract(self):
        required = set(self.schema["required"])
        self.assertTrue(required.issubset(self.packet))
        self.assertEqual(self.packet["schema"], "commons-mwdoc-d365-readiness/v2")
        self.assertEqual(self.schema["properties"]["schema"]["const"], self.packet["schema"])
        self.assertEqual(self.schema["properties"]["id"]["const"], self.packet["id"])

    def test_scores_reconcile_exactly(self):
        expected = {
            "HSO": 50,
            "RSM US LLP": 45,
            "Hitachi Solutions America": 40,
            "Consultadd Public Services": 27.5,
        }
        actual = {target["company"]: target["computed_score"] for target in self.packet["targets"]}
        self.assertEqual(actual, expected)
        for target in self.packet["targets"]:
            self.assertEqual(
                target["computed_score"],
                builder.score_target(target, self.packet["score_weights"]),
            )

    def test_every_target_fails_closed_on_mandatory_evidence(self):
        for target in self.packet["targets"]:
            self.assertEqual(target["status"], "PRIME_GATE_FAIL_CLOSED")
            self.assertIn("NOT_VERIFIED", target["mandatory_gates"].values())
        self.assertEqual(
            self.packet["decision"],
            "NO_GO_AS_PRIME; PROVISIONAL_PARTNER_RESEARCH_ONLY; CONDITIONAL_SUBCONTRACTOR_ONLY",
        )

    def test_missing_partner_gcc_or_references_never_promotes(self):
        mutated = copy.deepcopy(self.source)
        target = mutated["targets"][0]
        for key in (
            "microsoft_partner_good_standing",
            "gcc_moderate_ppac",
            "two_public_agency_support_references",
        ):
            target["evidence"][key]["state"] = "NOT_VERIFIED"
        built = builder.build_packet(mutated)
        self.assertEqual(built["targets"][0]["status"], "PRIME_GATE_FAIL_CLOSED")

    def test_two_reference_slots_require_owner_private_evidence(self):
        slots = self.packet["reference_slots"]
        self.assertEqual([slot["slot"] for slot in slots], [1, 2])
        for slot in slots:
            self.assertEqual(slot["status"], "OWNER_PRIVATE_EVIDENCE_REQUIRED")
            self.assertFalse(slot["public_contact_data"])
            self.assertTrue(slot["requirements"])
            self.assertFalse(any(slot["requirements"].values()))

    def test_reference_promotion_without_receipts_is_rejected(self):
        mutated = copy.deepcopy(self.source)
        mutated["reference_slots"][0]["requirements"]["owner_private_receipt_id"] = True
        with self.assertRaises(builder.PacketError):
            builder.validate_source(mutated)

    def test_outreach_is_one_truthful_unauthorized_draft(self):
        draft = self.packet["outreach_draft"]
        self.assertEqual(draft["state"], "DRAFT_ONLY")
        self.assertEqual(draft["authorization"], "NO_SEND_AUTHORIZATION")
        self.assertEqual(draft["teaming_claim"], "NO_TEAMING_CLAIM")
        self.assertEqual(draft["target_company"], "HSO")
        self.assertIn("not claiming prime eligibility", " ".join(draft["body"]).lower())
        self.assertFalse(self.packet["truth_flags"]["external_outreach"])

    def test_narrow_role_is_nonproduction_and_prime_controlled(self):
        scope = self.packet["proposed_subcontract_scope"]
        self.assertEqual(
            scope["label"],
            "NARROW_NON_PRODUCTION_AP_TO_REPORT_REGRESSION_RECONCILIATION",
        )
        text = " ".join(scope["inclusions"] + scope["exclusions"]).lower()
        self.assertIn("non-production", text)
        self.assertIn("prime retains", text)
        self.assertIn("no production access", text)

    def test_rate_values_are_blank_and_invention_is_rejected(self):
        with (PACKET_DIR / "rate-sheet-template.csv").open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        self.assertEqual(len(rows), 4)
        for row in rows:
            self.assertEqual(row["status"], "OWNER_RATE_REQUIRED")
            self.assertFalse(row["hourly_rate_usd"])
            self.assertFalse(row["prepaid_block_hours"])
            self.assertFalse(row["prepaid_block_price_usd"])
        mutated = copy.deepcopy(self.source)
        mutated["rate_sheet"]["rows"][0]["hourly_rate"] = 1
        with self.assertRaises(builder.PacketError):
            builder.validate_source(mutated)

    def test_agreement_checklist_is_not_acceptance_or_legal_advice(self):
        checklist = self.packet["agreement_checklist"]
        self.assertEqual(checklist["status"], "OWNER_AND_COUNSEL_REVIEW_REQUIRED")
        self.assertIn("not legal advice", checklist["disclaimer"])
        self.assertGreaterEqual(len(checklist["items"]), 8)

    def test_official_sources_are_dated_https_and_boundary_qualified(self):
        for item in self.packet["official_sources"]:
            self.assertTrue(item["url"].startswith("https://"))
            self.assertRegex(item["observed_on"], r"^\d{4}-\d{2}-\d{2}$")
            self.assertTrue(item["claim"])
            self.assertTrue(item["boundary"])

    def test_start_date_conflict_requires_addendum(self):
        schedule = self.packet["schedule"]
        self.assertEqual(schedule["required_content_start"], "2026-10-26")
        self.assertEqual(schedule["evaluation_start"], "2026-09-21")
        self.assertEqual(schedule["start_discrepancy_state"], "ADDENDUM_REQUIRED")

    def test_false_external_action_or_cash_claim_is_rejected(self):
        for key in self.source["truth_flags"]:
            mutated = copy.deepcopy(self.source)
            mutated["truth_flags"][key] = True
            with self.assertRaises(builder.PacketError):
                builder.validate_source(mutated)

    def test_public_coordinate_secret_and_token_fabrication_are_rejected(self):
        probes = (
            "person" + "@" + "example.invalid",
            "555" + "-111-" + "2222",
            "api_key" + "=" + "abcdef123456",
        )
        for probe in probes:
            mutated = copy.deepcopy(self.source)
            mutated["purpose"] = probe
            with self.assertRaises(builder.PacketError):
                builder.validate_source(mutated)

    def test_public_outputs_have_no_contact_coordinates_or_secret_values(self):
        public = "\n".join(
            (PACKET_DIR / name).read_text(encoding="utf-8")
            for name in ("README.md", "readiness.html", "readiness.json", "rate-sheet-template.csv")
        )
        self.assertIsNone(builder.EMAIL_RE.search(public))
        self.assertIsNone(builder.PHONE_RE.search(public))
        self.assertIsNone(builder.SECRET_RE.search(public))

    def test_static_handoff_has_no_login_form_or_script(self):
        html = (PACKET_DIR / "readiness.html").read_text(encoding="utf-8").lower()
        for forbidden in ("<form", "<script", "type=\"password\"", "sign in", "log in"):
            self.assertNotIn(forbidden, html)
        self.assertIn("no_external_action", (PACKET_DIR / "readiness.json").read_text(encoding="utf-8").lower())

    def test_no_invented_send_submission_award_or_cash_state(self):
        flags = self.packet["truth_flags"]
        self.assertTrue(flags)
        self.assertFalse(any(flags.values()))
        self.assertEqual(self.packet["transport_state"], "NO_EXTERNAL_ACTION")
        self.assertEqual(self.packet["reference_gate_status"], "OWNER_PRIVATE_EVIDENCE_REQUIRED")


if __name__ == "__main__":
    unittest.main()
