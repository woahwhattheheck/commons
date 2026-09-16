import unittest

from commercial.sasria_ai_training import (
    BuyerTechnicalScore,
    EvidenceRef,
    PaidWorkshare,
    SubmissionAuthority,
    TrainingPathway,
)
from commercial.sasria_ai_training.core import TECHNICAL_SCORE_CAPS


class PublicApiFailClosedTests(unittest.TestCase):
    def test_non_string_evidence_note_is_rejected_without_crashing(self):
        scores = {name: cap for name, cap in TECHNICAL_SCORE_CAPS.items()}
        result = BuyerTechnicalScore(
            scores=scores,
            evidence_refs=(
                EvidenceRef(label="edge", locator="fixture://edge", note=123),  # type: ignore[arg-type]
            ),
        ).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("missing_score_evidence", result["blockers"])

    def test_non_string_workshare_owner_holds_without_crashing(self):
        result = PaidWorkshare(
            owner=123,  # type: ignore[arg-type]
            deliverables=("deliverable",),
            acceptance_criteria=("criterion",),
            exclusions=("exclusion",),
        ).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("missing_workshare_owner", result["blockers"])
        self.assertEqual(result["owner"], "")

    def test_non_string_role_group_holds_without_crashing(self):
        result = TrainingPathway(
            role_group=123,  # type: ignore[arg-type]
            learning_outcomes=("outcome",),
            delivery_modes=("workshop",),
            evaluation_methods=("assessment",),
            artefacts=("evidence pack",),
        ).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("unknown_role_group", result["blockers"])
        self.assertEqual(result["role_group"], "")

    def test_truthy_strings_do_not_create_submission_authority(self):
        result = SubmissionAuthority(
            portal_account_confirmed="yes",  # type: ignore[arg-type]
            authorized_signatory_confirmed="yes",  # type: ignore[arg-type]
            prime_approved_submission="yes",  # type: ignore[arg-type]
        ).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(
            result["blockers"],
            [
                "portal_account_not_confirmed",
                "authorized_signatory_not_confirmed",
                "prime_submission_approval_not_confirmed",
            ],
        )


if __name__ == "__main__":
    unittest.main()
