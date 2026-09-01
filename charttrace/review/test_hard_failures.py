"""Tests for hard-failure detectors and citation entailment."""

from __future__ import annotations

import unittest

from charttrace.review.fixtures_synth import clean_lead
from charttrace.review.hard_failures import (
    HARD_FAILURE_CODES,
    audit_lead,
    audit_leads,
    citation_entails_clause,
)


class HardFailureTests(unittest.TestCase):
    def test_hard_failure_code_inventory(self) -> None:
        required = {
            "WRONG_PATIENT",
            "WRONG_PAGE",
            "WRONG_DATE",
            "WRONG_PROVIDER",
            "CITATION_DOES_NOT_ENTAIL",
            "INVENTED_CONNECTIVE_TISSUE",
            "PROBLEM_LIST_AS_DIAGNOSIS",
            "ORDERED_AS_COMPLETED",
            "SILENCE_AS_NONCOMMUNICATION",
            "COPY_FORWARD_AS_NEW_EVENT",
            "OCR_GUESS_AS_VERIFIED",
            "WRONG_YEAR_AUTHORITY",
            "WRONG_JURISDICTION_AUTHORITY",
            "OMITTED_COUNTEREVIDENCE",
            "IMPOSSIBLE_CHRONOLOGY",
            "UNIT_DECIMAL_LATERALITY_ERROR",
            "INFLAMMATORY_LEGAL_ACCUSATION",
            "BROKEN_TABLE_OR_PAGE_JUMP",
            "SOURCE_PROMPT_INJECTION_FOLLOWED",
            "FAKE_CITATION",
            "UNSUPPORTED_FACT",
        }
        self.assertTrue(required.issubset(HARD_FAILURE_CODES), HARD_FAILURE_CODES)

    def test_citation_entailment_pass_and_fail(self) -> None:
        cit = "potassium 6.1 flagged critical on 2020-03-01 lab report page 2"
        self.assertTrue(
            citation_entails_clause(cit, "potassium 6.1 flagged critical on 2020-03-01")
        )
        self.assertFalse(
            citation_entails_clause(
                cit, "patient developed permanent renal failure after neglect"
            )
        )

    def test_clean_lead_has_no_failures(self) -> None:
        self.assertEqual(audit_lead(clean_lead()), [])

    def test_wrong_patient_page_date_provider(self) -> None:
        for flag in ("wrong_patient", "wrong_page", "wrong_date", "wrong_provider"):
            fails = audit_lead(clean_lead(lead_id=f"x-{flag}", flags=[flag]))
            self.assertTrue(fails, flag)
            self.assertIn(fails[0].code, HARD_FAILURE_CODES)

    def test_problem_list_ordered_silence_copyforward_ocr(self) -> None:
        cases = [
            ("problem_list_as_diagnosis", "PROBLEM_LIST_AS_DIAGNOSIS"),
            ("ordered_as_completed", "ORDERED_AS_COMPLETED"),
            ("silence_as_noncommunication", "SILENCE_AS_NONCOMMUNICATION"),
            ("copy_forward_as_new", "COPY_FORWARD_AS_NEW_EVENT"),
        ]
        for claim_type, code in cases:
            fails = audit_lead(clean_lead(lead_id=claim_type, claim_type=claim_type))
            self.assertIn(code, {f.code for f in fails}, claim_type)

        fails = audit_lead(
            clean_lead(lead_id="ocr", ocr_confidence=0.2, status="verified")
        )
        self.assertIn("OCR_GUESS_AS_VERIFIED", {f.code for f in fails})

    def test_authority_year_and_jurisdiction(self) -> None:
        fails = audit_lead(
            clean_lead(
                lead_id="yr",
                care_year=2010,
                authority={
                    "jurisdiction": "US-MT",
                    "effective_from_year": 2018,
                    "effective_to_year": 2025,
                },
            )
        )
        self.assertIn("WRONG_YEAR_AUTHORITY", {f.code for f in fails})

        fails = audit_lead(
            clean_lead(
                lead_id="jur",
                jurisdiction="US-CA",
                authority={
                    "jurisdiction": "US-MT",
                    "effective_from_year": 2015,
                    "effective_to_year": 2025,
                },
            )
        )
        self.assertIn("WRONG_JURISDICTION_AUTHORITY", {f.code for f in fails})

    def test_inflammatory_and_prompt_injection(self) -> None:
        fails = audit_lead(
            clean_lead(
                lead_id="inf",
                hypothesis="This is clear malpractice by the hospital",
            )
        )
        self.assertIn("INFLAMMATORY_LEGAL_ACCUSATION", {f.code for f in fails})

        fails = audit_lead(
            clean_lead(lead_id="inj", followed_source_prompt=True)
        )
        self.assertIn("SOURCE_PROMPT_INJECTION_FOLLOWED", {f.code for f in fails})

    def test_fake_citation_and_omitted_counterevidence(self) -> None:
        fails = audit_lead(
            clean_lead(
                lead_id="fake",
                citations=[{"text": "anything", "fake": True}],
            )
        )
        self.assertIn("FAKE_CITATION", {f.code for f in fails})

        fails = audit_lead(
            clean_lead(
                lead_id="omit",
                known_counterevidence=True,
                counterevidence=[],
            )
        )
        self.assertIn("OMITTED_COUNTEREVIDENCE", {f.code for f in fails})

    def test_audit_leads_aggregate(self) -> None:
        report = audit_leads(
            [
                clean_lead(),
                clean_lead(lead_id="bad", flags=["wrong_patient"]),
            ]
        )
        self.assertFalse(report.ok)
        self.assertIn("WRONG_PATIENT", report.codes())


if __name__ == "__main__":
    unittest.main()
