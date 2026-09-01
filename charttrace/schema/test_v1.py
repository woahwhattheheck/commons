from dataclasses import FrozenInstanceError, fields
import unittest

from charttrace.schema.v1 import (
    COUNSEL_OR_CLINICIAN_REVIEW,
    EXTERNAL_AUTHORITY,
    INVESTIGATIVE_LEAD,
    RECORD_FACT,
    Citation,
    DateCertainty,
    EvidenceGrade,
    EvidenceObjectType,
    ForbiddenSemanticClaim,
    InvestigativeLead,
    RecordFact,
    RelevanceGrade,
    SchemaValidationError,
    TextSpan,
    find_forbidden_semantic_claims,
)


SOURCE_HASH = "a" * 64


class SchemaV1Tests(unittest.TestCase):
    def test_canonical_types_and_grades(self) -> None:
        self.assertEqual(
            [
                RECORD_FACT.value,
                EXTERNAL_AUTHORITY.value,
                INVESTIGATIVE_LEAD.value,
                COUNSEL_OR_CLINICIAN_REVIEW.value,
            ],
            [
                "RECORD_FACT",
                "EXTERNAL_AUTHORITY",
                "INVESTIGATIVE_LEAD",
                "COUNSEL_OR_CLINICIAN_REVIEW",
            ],
        )
        self.assertEqual(
            [grade.value for grade in EvidenceGrade],
            ["CLUE", "SUPPORTED", "CORROBORATED", "EXPLICIT"],
        )
        self.assertEqual(
            [grade.value for grade in RelevanceGrade],
            [
                "TENUOUS",
                "PLAUSIBLE",
                "MATERIAL_IF_CONFIRMED",
                "PRIORITY_REVIEW",
            ],
        )

    def test_atomic_fact_is_frozen_and_page_cited(self) -> None:
        citation = Citation(
            document="SYNTH-DOC-001",
            page=2,
            span_or_bbox=TextSpan(4, 15, "synthetic"),
            source_hash=SOURCE_HASH,
        )
        fact = RecordFact(
            fact_id="FACT-001",
            statement="A synthetic callback is documented.",
            citation=citation,
            domain="communication",
            care_phase="follow-up",
            event_date="2026-01-02",
            date_certainty=DateCertainty.EXACT,
        )
        self.assertIs(fact.object_type, EvidenceObjectType.RECORD_FACT)
        with self.assertRaises(FrozenInstanceError):
            fact.statement = "changed"  # type: ignore[misc]
        with self.assertRaises(SchemaValidationError):
            Citation(
                document="SYNTH-DOC-001",
                page=0,
                span_or_bbox=TextSpan(0, 1),
                source_hash=SOURCE_HASH,
            )

    def test_lead_has_every_owner_amendment_field(self) -> None:
        expected = {
            "lead_id",
            "neutral_title",
            "domain",
            "care_phase",
            "cited_observation",
            "hypothesis",
            "review_question",
            "supporting_facts",
            "counterevidence",
            "conflicts",
            "missing_records",
            "alternative_explanations",
            "source_universe_searched",
            "external_authorities",
            "jurisdiction_scope",
            "date_scope",
            "evidence_grade",
            "relevance_grade",
            "clinical_plausibility",
            "temporal_linkage",
            "peer_version",
            "model_version",
            "prompt_version",
            "policy_version",
            "review_history",
        }
        self.assertTrue(expected.issubset({field.name for field in fields(InvestigativeLead)}))
        lead = InvestigativeLead(
            lead_id="LEAD-001",
            neutral_title="Synthetic follow-up interval",
            domain="closed-loop follow-up",
            care_phase="follow-up",
            cited_observation="Two cited synthetic events have an interval.",
            hypothesis="The interval may warrant professional review.",
            review_question="What additional record would resolve the interval?",
            supporting_facts=("FACT-001",),
            counterevidence=("A callback is documented.",),
            conflicts=(),
            missing_records=("Synthetic scheduling ledger",),
            alternative_explanations=("Routine scheduling may explain the interval.",),
            source_universe_searched=("supplied synthetic notes",),
            external_authorities=(),
            jurisdiction_scope="SYNTHETIC",
            date_scope="2026-01",
            evidence_grade=EvidenceGrade.CLUE,
            relevance_grade=RelevanceGrade.PLAUSIBLE,
            clinical_plausibility="Requires clinician review.",
            temporal_linkage="Sequence only; no causal conclusion.",
            peer_version="peer-v1",
            model_version="LOCAL_RULES_ONLY_NO_EXTERNAL_MODEL",
            prompt_version="prompt-v1",
            policy_version="policy-v1",
            review_history=(),
        )
        self.assertEqual(lead.supporting_facts, ("FACT-001",))

    def test_forbidden_semantic_claims_fail_closed(self) -> None:
        samples = {
            "This proves malpractice.": ForbiddenSemanticClaim.MALPRACTICE,
            "The provider was negligent.": ForbiddenSemanticClaim.NEGLIGENCE,
            "The cause-of-death is known.": ForbiddenSemanticClaim.CAUSE_OF_DEATH,
            "A standard_of_care_breach occurred.": (
                ForbiddenSemanticClaim.STANDARD_OF_CARE_BREACH
            ),
            "The result was not disclosed.": ForbiddenSemanticClaim.NOT_DISCLOSED,
            "The patient-was-not-told.": (
                ForbiddenSemanticClaim.PATIENT_WAS_NOT_TOLD
            ),
        }
        for text, expected in samples.items():
            with self.subTest(text=text):
                self.assertIn(expected, find_forbidden_semantic_claims(text))
                with self.assertRaises(SchemaValidationError):
                    RecordFact(
                        fact_id="FACT-001",
                        statement=text,
                        citation=Citation(
                            document="SYNTH-DOC-001",
                            page=1,
                            span_or_bbox=TextSpan(0, len(text)),
                            source_hash=SOURCE_HASH,
                        ),
                        domain="synthetic",
                        care_phase="synthetic",
                    )


if __name__ == "__main__":
    unittest.main()
