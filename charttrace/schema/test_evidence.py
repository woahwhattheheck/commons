import unittest

from charttrace.schema.evidence import (
    EvidenceGrade,
    EvidenceLayer,
    InvestigativeLead,
    RecordFact,
    RelevanceGrade,
    SourceCitation,
    to_primitive,
)


SHA = "a" * 64


class EvidenceSchemaTests(unittest.TestCase):
    def test_exact_citation_and_atomic_fact(self) -> None:
        citation = SourceCitation("doc-01", 3, SHA, span_start=12, span_end=25)
        fact = RecordFact("fact-01", "Synthetic callback documented.", citation)
        self.assertEqual(to_primitive(fact)["layer"], "RECORD_FACT")
        self.assertEqual(to_primitive(fact)["citation"]["page"], 3)

    def test_citation_requires_location_and_valid_hash(self) -> None:
        with self.assertRaises(ValueError):
            SourceCitation("doc-01", 1, SHA)
        with self.assertRaises(ValueError):
            SourceCitation("doc-01", 1, "not-a-hash", span_start=0, span_end=2)

    def test_lead_retains_counterevidence_and_provenance(self) -> None:
        lead = InvestigativeLead(
            lead_id="lead-01",
            title="Synthetic communication sequence",
            domain="communication",
            care_phase="follow-up",
            cited_observation="A cited synthetic note precedes a callback.",
            hypothesis="The sequence may warrant review.",
            review_question="Does the complete synthetic source set resolve the sequence?",
            supporting_fact_ids=("fact-01",),
            counterevidence_fact_ids=("fact-02",),
            conflict_ids=(),
            missing_records=("synthetic-index",),
            alternative_explanations=("documentation lag",),
            source_universe_searched=("synthetic-bundle-v1",),
            external_authority_ids=(),
            jurisdiction="synthetic",
            authority_date_scope="none",
            evidence_grade=EvidenceGrade.CLUE,
            relevance_grade=RelevanceGrade.TENUOUS,
            clinical_plausibility="unreviewed",
            temporal_linkage="sequence-only",
            peer_version="peer-v1",
            model_version="none",
            prompt_version="prompt-v1",
            policy_version="policy-v1",
        )
        primitive = to_primitive(lead)
        self.assertEqual(primitive["counterevidence_fact_ids"], ["fact-02"])
        self.assertEqual(primitive["layer"], EvidenceLayer.INVESTIGATIVE_LEAD.value)

    def test_lead_without_support_or_source_universe_fails_closed(self) -> None:
        common = dict(
            lead_id="lead-01", title="t", domain="d", care_phase="c",
            cited_observation="o", hypothesis="h", review_question="q",
            counterevidence_fact_ids=(), conflict_ids=(), missing_records=(),
            alternative_explanations=(), external_authority_ids=(),
            jurisdiction="synthetic", authority_date_scope="none",
            evidence_grade=EvidenceGrade.CLUE, relevance_grade=RelevanceGrade.TENUOUS,
            clinical_plausibility="unreviewed", temporal_linkage="unknown",
            peer_version="v", model_version="none", prompt_version="v", policy_version="v",
        )
        with self.assertRaises(ValueError):
            InvestigativeLead(supporting_fact_ids=(), source_universe_searched=("fixture",), **common)
        with self.assertRaises(ValueError):
            InvestigativeLead(supporting_fact_ids=("fact-01",), source_universe_searched=(), **common)


if __name__ == "__main__":
    unittest.main()
