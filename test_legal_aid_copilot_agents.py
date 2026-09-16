from datetime import date
import unittest

from commercial.legal_aid_copilot_agents import (
    AdoptionMetrics,
    ComparableEngagement,
    EvaluationCase,
    GovernanceReview,
    PartnerEvidence,
    Reference,
    Trainer,
    compile_delivery_pack,
)


def good_partner(**overrides):
    trainer = Trainer(
        name="Synthetic Trainer",
        role="Lead trainer",
        copilot_experience_summary="Synthetic evidence used only for unit tests",
        availability_start=date(2026, 9, 25),
        availability_end=date(2026, 11, 30),
    )
    engagements = tuple(
        ComparableEngagement(
            client_label=f"Synthetic client {i}",
            scope="Synthetic Copilot Studio training engagement",
            outcome="Synthetic completed workshop",
            evidence_route=f"fixture://engagement/{i}",
        )
        for i in (1, 2)
    )
    refs = tuple(
        Reference(
            organization=f"Synthetic ref org {i}",
            contact_name=f"Synthetic contact {i}",
            contact_route=f"fixture://reference/{i}",
            engagement_summary="Synthetic reference for tests",
        )
        for i in (1, 2)
    )
    values = dict(
        company_name="Synthetic Training Partner",
        company_profile="Synthetic fixture; not a real credential",
        trainer=trainer,
        comparable_engagements=engagements,
        references=refs,
        subcontract_role="Training anchor with bounded TJLabs evaluation workshare",
        commercial_split_discussed=True,
        sample_agreement_available=True,
    )
    values.update(overrides)
    return PartnerEvidence(**values)


def good_governance(**changes):
    controls = {
        "approved_data_sources": True,
        "least_privilege_access": True,
        "human_escalation": True,
        "logging_and_audit": True,
        "retention_and_deletion": True,
    }
    controls.update(changes)
    return GovernanceReview(controls=controls)


def good_eval(case_id="case-001", **score_changes):
    scores = {
        "task_success": 4,
        "groundedness": 4,
        "permission_boundaries": 4,
        "safe_failure": 4,
        "human_handoff": 4,
    }
    scores.update(score_changes)
    return EvaluationCase(
        case_id=case_id,
        scores=scores,
        evidence_refs=(f"fixture://evidence/{case_id}",),
        observed_result="Synthetic observed result",
    )


def good_adoption(**changes):
    values = dict(
        invited_staff=20,
        trained_staff=18,
        builders=10,
        functioning_agents=1,
        evaluated_agents=1,
    )
    values.update(changes)
    return AdoptionMetrics(**values)


class ProposalGateTests(unittest.TestCase):
    def test_missing_partner_truth_holds_instead_of_inferring(self):
        gate = PartnerEvidence(company_name="", company_profile="", trainer=None).proposal_gate()
        self.assertEqual(gate["status"], "HOLD")
        self.assertIn("missing_company_name", gate["blockers"])
        self.assertIn("missing_or_invalid_named_trainer", gate["blockers"])
        self.assertIn("fewer_than_two_valid_references", gate["blockers"])

    def test_trainer_must_cover_entire_delivery_window(self):
        short = Trainer(
            name="Synthetic",
            role="Lead",
            copilot_experience_summary="Synthetic",
            availability_start=date(2026, 10, 5),
            availability_end=date(2026, 11, 1),
        )
        gate = good_partner(trainer=short).proposal_gate()
        self.assertEqual(gate["status"], "HOLD")
        self.assertIn("trainer_does_not_cover_delivery_window", gate["blockers"])

    def test_two_valid_engagements_and_references_are_required(self):
        partner = good_partner(
            comparable_engagements=good_partner().comparable_engagements[:1],
            references=good_partner().references[:1],
        )
        gate = partner.proposal_gate()
        self.assertIn("fewer_than_two_comparable_engagements", gate["blockers"])
        self.assertIn("fewer_than_two_valid_references", gate["blockers"])


class GovernanceAndEvaluationTests(unittest.TestCase):
    def test_governance_missing_control_holds(self):
        result = good_governance(logging_and_audit=False).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["missing_controls"], ["logging_and_audit"])

    def test_evaluation_requires_all_dimensions_and_evidence(self):
        case = EvaluationCase(case_id="x", scores={"task_success": 5}, evidence_refs=(), observed_result="observed")
        result = case.result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("missing_rubric_dimensions", result["blockers"])
        self.assertIn("missing_evidence_refs", result["blockers"])

    def test_below_threshold_score_holds(self):
        result = good_eval(permission_boundaries=2).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["below_threshold"], {"permission_boundaries": 2})

    def test_boolean_is_not_accepted_as_numeric_score(self):
        result = good_eval(task_success=True).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("invalid_rubric_scores", result["blockers"])

    def test_duplicate_case_ids_hold_delivery(self):
        pack = compile_delivery_pack(
            partner=good_partner(),
            governance=good_governance(),
            evaluations=(good_eval("dup"), good_eval("dup")),
            adoption=good_adoption(),
        )
        self.assertEqual(pack["delivery_status"], "HOLD")
        self.assertIn("duplicate_evaluation_case_ids", pack["delivery_blockers"])
        self.assertEqual(pack["duplicate_evaluation_case_ids"], ["dup"])


class AdoptionAndPackTests(unittest.TestCase):
    def test_at_least_one_functioning_agent_is_required(self):
        pack = compile_delivery_pack(
            partner=good_partner(),
            governance=good_governance(),
            evaluations=(good_eval(),),
            adoption=good_adoption(functioning_agents=0, evaluated_agents=0),
        )
        self.assertEqual(pack["delivery_status"], "HOLD")
        self.assertIn("functioning_agent_outcome_gate", pack["delivery_blockers"])

    def test_impossible_adoption_counts_raise(self):
        with self.assertRaises(ValueError):
            good_adoption(trained_staff=21).result()
        with self.assertRaises(ValueError):
            good_adoption(functioning_agents=0, evaluated_agents=1).result()

    def test_complete_synthetic_path_is_acceptance_ready(self):
        pack = compile_delivery_pack(
            partner=good_partner(),
            governance=good_governance(),
            evaluations=(good_eval("case-b"), good_eval("case-a")),
            adoption=good_adoption(),
        )
        self.assertEqual(pack["delivery_status"], "ACCEPTANCE_READY")
        self.assertEqual(pack["delivery_blockers"], [])
        self.assertEqual([row["case_id"] for row in pack["evaluations"]], ["case-a", "case-b"])
        self.assertEqual(len(pack["receipt_sha256"]), 64)

    def test_receipt_is_deterministic_and_changes_with_evidence(self):
        kwargs = dict(
            partner=good_partner(),
            governance=good_governance(),
            evaluations=(good_eval(),),
            adoption=good_adoption(),
        )
        first = compile_delivery_pack(**kwargs)
        second = compile_delivery_pack(**kwargs)
        self.assertEqual(first["receipt_sha256"], second["receipt_sha256"])
        changed = compile_delivery_pack(
            partner=good_partner(),
            governance=good_governance(),
            evaluations=(good_eval(task_success=5),),
            adoption=good_adoption(),
        )
        self.assertNotEqual(first["receipt_sha256"], changed["receipt_sha256"])


if __name__ == "__main__":
    unittest.main()
