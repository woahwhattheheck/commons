import unittest

from commercial.sasria_ai_training import (
    BuyerTechnicalScore,
    EvidenceRef,
    PaidWorkshare,
    PrimeCandidate,
    SubmissionAuthority,
    TrainingPathway,
)
from commercial.sasria_ai_training.core import TECHNICAL_SCORE_CAPS


class PublicApiFailClosedTests(unittest.TestCase):
    def test_non_string_evidence_note_is_rejected_without_crashing(self):
        scores = {name: cap for name, cap in TECHNICAL_SCORE_CAPS.items()}
        result = BuyerTechnicalScore(
            scores=scores,
            evidence_refs=(EvidenceRef(label="edge", locator="fixture://edge", note=123),),  # type: ignore[arg-type]
        ).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("missing_score_evidence", result["blockers"])

    def test_non_mapping_public_inputs_hold_without_crashing(self):
        prime = PrimeCandidate(
            legal_name="Synthetic",
            company_profile_ref=EvidenceRef("profile", "fixture://profile"),
            returnables=None,  # type: ignore[arg-type]
            framework_alignment=None,  # type: ignore[arg-type]
        ).mandatory_gate()
        self.assertEqual(prime["status"], "HOLD")
        self.assertIn("invalid_returnables_mapping", prime["blockers"])
        score = BuyerTechnicalScore(scores=None).result()  # type: ignore[arg-type]
        self.assertEqual(score["status"], "HOLD")
        self.assertIn("invalid_scores_mapping", score["blockers"])

    def test_non_string_workshare_owner_holds_without_crashing(self):
        result = PaidWorkshare(
            owner=123,  # type: ignore[arg-type]
            deliverables=("deliverable",), acceptance_criteria=("criterion",), exclusions=("exclusion",),
        ).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("missing_workshare_owner", result["blockers"])

    def test_non_string_role_group_holds_without_crashing(self):
        result = TrainingPathway(
            role_group=123,  # type: ignore[arg-type]
            learning_outcomes=("outcome",), delivery_modes=("workshop",),
            evaluation_methods=("assessment",), artefacts=("evidence pack",),
        ).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("unknown_role_group", result["blockers"])

    def test_truthy_strings_and_literal_true_are_candidate_assertions_only(self):
        strings = SubmissionAuthority(
            portal_account_confirmed="yes",  # type: ignore[arg-type]
            authorized_signatory_confirmed="yes",  # type: ignore[arg-type]
            prime_approved_submission="yes",  # type: ignore[arg-type]
        ).result()
        self.assertEqual(strings["status"], "HOLD")
        self.assertIn("trusted_submission_authority_not_bound", strings["blockers"])
        self.assertFalse(any(strings["candidate_assertions"].values()))
        literal = SubmissionAuthority(True, True, True).result()
        self.assertEqual(literal["status"], "HOLD")
        self.assertTrue(all(literal["candidate_assertions"].values()))
        self.assertEqual(literal["blockers"], ["trusted_submission_authority_not_bound"])


if __name__ == "__main__":
    unittest.main()
