from dataclasses import FrozenInstanceError, fields
import unittest

from charttrace.schema.v1 import (
    COUNSEL_OR_CLINICIAN_REVIEW,
    COUNTEREVIDENCE,
    EXTERNAL_AUTHORITY,
    HYPOTHESIS,
    INVESTIGATIVE_LEAD,
    MISSING_PROOF,
    OBSERVATION,
    RECORD_FACT,
    Authority,
    AuthorityReviewStatus,
    Citation,
    Counterevidence,
    DateCertainty,
    DuplicateIdError,
    EvidenceGrade,
    EvidenceObjectType,
    ExternalAuthority,
    Fact,
    ForbiddenSemanticClaim,
    Hypothesis,
    InvestigativeLead,
    MissingProof,
    Observation,
    OrphanCitationError,
    RecordFact,
    RelevanceGrade,
    SchemaValidationError,
    TextSpan,
    assert_citations_resolve,
    assert_unique_ids,
    find_forbidden_semantic_claims,
    parse_relevance_grade,
    to_primitive,
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
            ["WEAK", "SUBTLE", "OBVIOUS"],
        )
        with self.assertRaises(SchemaValidationError):
            parse_relevance_grade("MATERIAL_IF_CONFIRMED")
        self.assertIs(parse_relevance_grade("obvious"), RelevanceGrade.OBVIOUS)

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
            relevance_grade=RelevanceGrade.SUBTLE,
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
            "The patient was never told.": ForbiddenSemanticClaim.NEVER_TOLD,
            "No follow-up occurred after the result.": (
                ForbiddenSemanticClaim.NO_FOLLOW_UP_OCCURRED
            ),
            "The finding was not found anywhere.": (
                ForbiddenSemanticClaim.NOT_FOUND_ANYWHERE
            ),
            "This is actionable.": ForbiddenSemanticClaim.ACTIONABLE,
            "The case value is unknown.": ForbiddenSemanticClaim.CASE_VALUE,
            "A standard of care discussion.": (
                ForbiddenSemanticClaim.STANDARD_OF_CARE_BREACH
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

    def _citation(self, page: int = 1) -> Citation:
        return Citation(
            document="SYNTH-DOC-001",
            page=page,
            span_or_bbox=TextSpan(0, 8, "synthetic"),
            source_hash=SOURCE_HASH,
        )

    def test_typed_work_order_objects_and_aliases(self) -> None:
        observation = Observation(
            observation_id="OBS-001",
            statement="A synthetic observation is documented.",
            citation=self._citation(),
            domain="communication",
            care_phase="follow-up",
        )
        fact = Fact(
            fact_id="FACT-001",
            statement="A synthetic fact is documented.",
            citation=self._citation(),
            domain="communication",
            care_phase="follow-up",
        )
        hypothesis = Hypothesis(
            hypothesis_id="HYP-001",
            statement="The observation may warrant review.",
            cited_observations=("OBS-001",),
            citation=self._citation(),
        )
        authority = Authority(
            authority_id="AUTH-001",
            authority_type="regulation",
            issuer="Synthetic Authority",
            jurisdiction="SYNTHETIC",
            effective_from="2025-01-01",
            effective_to=None,
            care_date_match=True,
            primary_url="https://example.invalid/authority",
            pinpoint="section-1",
            retrieval_date="2026-09-01",
            supported_proposition="Context for a synthetic review.",
            supersession=None,
            review_status=AuthorityReviewStatus.CONTEXT_ONLY,
        )
        counter = Counterevidence(
            counterevidence_id="CTR-001",
            statement="A callback is documented.",
            counters="HYP-001",
            citation=self._citation(2),
        )
        missing = MissingProof(
            missing_proof_id="MISS-001",
            statement="Scheduling ledger is absent.",
            needed_for="HYP-001",
            citation=self._citation(),
        )
        self.assertIs(observation.object_type, EvidenceObjectType.OBSERVATION)
        self.assertIs(fact.object_type, EvidenceObjectType.RECORD_FACT)
        self.assertIs(hypothesis.object_type, EvidenceObjectType.HYPOTHESIS)
        self.assertIs(authority.object_type, EvidenceObjectType.EXTERNAL_AUTHORITY)
        self.assertIs(counter.object_type, EvidenceObjectType.COUNTEREVIDENCE)
        self.assertIs(missing.object_type, EvidenceObjectType.MISSING_PROOF)
        self.assertIs(Fact, RecordFact)
        self.assertIs(Authority, ExternalAuthority)
        self.assertEqual(
            [
                OBSERVATION.value,
                HYPOTHESIS.value,
                COUNTEREVIDENCE.value,
                MISSING_PROOF.value,
            ],
            ["OBSERVATION", "HYPOTHESIS", "COUNTEREVIDENCE", "MISSING_PROOF"],
        )
        graph = (observation, fact, hypothesis, authority, counter, missing)
        assert_unique_ids(graph)
        assert_citations_resolve(
            graph,
            known_source_hashes=(SOURCE_HASH,),
            known_documents=("SYNTH-DOC-001",),
        )

    def test_duplicate_id_and_orphan_citation_fail_closed(self) -> None:
        observation = Observation(
            observation_id="OBS-001",
            statement="A synthetic observation is documented.",
            citation=self._citation(),
            domain="communication",
            care_phase="follow-up",
        )
        duplicate = Observation(
            observation_id="OBS-001",
            statement="A second synthetic observation.",
            citation=self._citation(),
            domain="communication",
            care_phase="follow-up",
        )
        with self.assertRaises(DuplicateIdError):
            assert_unique_ids((observation, duplicate))

        hypothesis = Hypothesis(
            hypothesis_id="HYP-001",
            statement="The observation may warrant review.",
            cited_observations=("OBS-MISSING",),
            citation=self._citation(),
        )
        with self.assertRaises(OrphanCitationError):
            assert_citations_resolve(
                (observation, hypothesis),
                known_source_hashes=(SOURCE_HASH,),
                known_documents=("SYNTH-DOC-001",),
            )

        orphan_cite = Observation(
            observation_id="OBS-002",
            statement="A synthetic observation with a missing source.",
            citation=Citation(
                document="MISSING-DOC",
                page=1,
                span_or_bbox=TextSpan(0, 8, "synthetic"),
                source_hash="b" * 64,
            ),
            domain="communication",
            care_phase="follow-up",
        )
        with self.assertRaises(OrphanCitationError):
            assert_citations_resolve(
                (orphan_cite,),
                known_source_hashes=(SOURCE_HASH,),
                known_documents=("SYNTH-DOC-001",),
            )

    def test_citation_exposes_source_sha256_and_span_fields(self) -> None:
        citation = Citation.from_span(
            document_id="SYNTH-DOC-001",
            page=3,
            source_sha256=SOURCE_HASH,
            span_start=4,
            span_end=12,
            quote="callback",
        )
        self.assertEqual(citation.source_hash, SOURCE_HASH)
        self.assertEqual(citation.source_sha256, SOURCE_HASH)
        self.assertEqual(citation.document_id, "SYNTH-DOC-001")
        primitive = to_primitive(citation)
        self.assertEqual(primitive["source_sha256"], SOURCE_HASH)
        self.assertEqual(primitive["document_id"], "SYNTH-DOC-001")
        self.assertEqual(primitive["span_start"], 4)
        self.assertEqual(primitive["span_end"], 12)

    def test_context_only_authority_allows_offline_locator_without_url(self) -> None:
        authority = ExternalAuthority(
            authority_id="AUTH-OFFLINE",
            authority_type="regulation",
            issuer="Synthetic Authority Pack",
            jurisdiction="SYNTHETIC",
            effective_from="2025-01-01",
            effective_to=None,
            care_date_match=False,
            primary_url="",
            pinpoint="pack:syn-auth-001#section-1",
            retrieval_date="2026-09-01",
            supported_proposition="Context for a synthetic review.",
            supersession=None,
            review_status=AuthorityReviewStatus.CONTEXT_ONLY,
            offline_locator="local-authority-pack:syn-auth-001",
        )
        self.assertEqual(authority.primary_url, "")
        self.assertEqual(
            authority.offline_locator, "local-authority-pack:syn-auth-001"
        )
        self.assertIs(authority.review_status, AuthorityReviewStatus.CONTEXT_ONLY)
        with self.assertRaisesRegex(
            SchemaValidationError, "primary_url or offline_locator"
        ):
            ExternalAuthority(
                authority_id="AUTH-EMPTY",
                authority_type="regulation",
                issuer="Synthetic Authority Pack",
                jurisdiction="SYNTHETIC",
                effective_from="2025-01-01",
                effective_to=None,
                care_date_match=False,
                primary_url="",
                pinpoint="pack:syn-auth-empty#section-1",
                retrieval_date="2026-09-01",
                supported_proposition="Context for a synthetic review.",
                supersession=None,
                review_status=AuthorityReviewStatus.CONTEXT_ONLY,
                offline_locator="",
            )


if __name__ == "__main__":
    unittest.main()
