from datetime import date
import unittest

from commercial.legal_aid_copilot_agents import (
    ComparableEngagement,
    EvaluationCase,
    PartnerEvidence,
    Reference,
    Trainer,
)


class PublicApiFailClosedTests(unittest.TestCase):
    def test_truthy_strings_do_not_satisfy_boolean_teaming_evidence(self):
        trainer = Trainer(
            name="Synthetic trainer",
            role="Lead",
            copilot_experience_summary="Synthetic only",
            availability_start=date(2026, 9, 25),
            availability_end=date(2026, 11, 30),
        )
        engagements = tuple(
            ComparableEngagement(
                client_label=f"Synthetic client {i}",
                scope="Synthetic scope",
                outcome="Synthetic outcome",
                evidence_route=f"fixture://engagement/{i}",
            )
            for i in (1, 2)
        )
        references = tuple(
            Reference(
                organization=f"Synthetic org {i}",
                contact_name=f"Synthetic contact {i}",
                contact_route=f"fixture://reference/{i}",
                engagement_summary="Synthetic reference",
            )
            for i in (1, 2)
        )
        partner = PartnerEvidence(
            company_name="Synthetic partner",
            company_profile="Synthetic profile",
            trainer=trainer,
            comparable_engagements=engagements,
            references=references,
            subcontract_role="Training anchor",
            commercial_split_discussed="yes",  # type: ignore[arg-type]
            sample_agreement_available="yes",  # type: ignore[arg-type]
        )
        gate = partner.proposal_gate()
        self.assertEqual(gate["status"], "HOLD")
        self.assertIn("commercial_role_split_not_discussed", gate["blockers"])
        self.assertIn("sample_agreement_not_available", gate["blockers"])

    def test_non_string_observed_result_holds_without_crashing(self):
        case = EvaluationCase(
            case_id="edge",
            scores={
                "task_success": 4,
                "groundedness": 4,
                "permission_boundaries": 4,
                "safe_failure": 4,
                "human_handoff": 4,
            },
            evidence_refs=("fixture://edge",),
            observed_result=123,  # type: ignore[arg-type]
        )
        result = case.result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("missing_observed_result", result["blockers"])
        self.assertEqual(result["observed_result"], "")


if __name__ == "__main__":
    unittest.main()
