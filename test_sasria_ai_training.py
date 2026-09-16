import json
import subprocess
import sys
import unittest

from commercial.sasria_ai_training import (
    BuyerTechnicalScore,
    EvidenceRef,
    PaidWorkshare,
    PrimeCandidate,
    SubmissionAuthority,
    TrainingPathway,
    compile_readiness_pack,
)
from commercial.sasria_ai_training.core import REQUIRED_RETURNABLES, ROLE_GROUPS


def ref(label="Synthetic evidence", locator="fixture://evidence/1"):
    return EvidenceRef(label=label, locator=locator, note="Unit-test fixture only")


def good_prime(**changes):
    values = dict(
        legal_name="Synthetic South African Training Prime",
        company_profile_ref=ref("Company profile", "fixture://company/profile"),
        returnables={name: True for name in REQUIRED_RETURNABLES},
        framework_alignment=("NIST AI RMF",),
        framework_evidence=(ref("NIST alignment", "fixture://framework/nist"),),
        training_body_accreditation_ref=ref("Training body evidence", "fixture://accreditation"),
        recognized_certification_capability_ref=ref("Certification capability", "fixture://certification"),
        platform_access_12_months_ref=ref("Platform access proof", "fixture://platform"),
        regulated_environment_training_ref=ref("Regulated training", "fixture://regulated"),
        financial_services_training_ref=ref("Financial-services training", "fixture://financial"),
        facilitator_refs=(ref("Facilitator CV", "fixture://facilitator/1"),),
        reference_letter_refs=(ref("Reference letter", "fixture://reference/1"),),
        ai_trainings_last_3y=5,
    )
    values.update(changes)
    return PrimeCandidate(**values)


def good_score(**changes):
    scores = {
        "company_profile": 20,
        "project_proposal_and_training_methodology": 35,
        "training_personnel": 8,
        "key_personnel_cvs": 8,
        "reference_letters": 15,
    }
    scores.update(changes)
    return BuyerTechnicalScore(scores=scores, evidence_refs=(ref("Buyer score worksheet", "fixture://score"),))


def pathway(role):
    return TrainingPathway(
        role_group=role,
        learning_outcomes=(f"Outcome for {role}",),
        delivery_modes=("facilitated workshop", "hands-on lab"),
        evaluation_methods=("pre/post assessment", "scenario evidence rubric"),
        artefacts=("attendance record", "evaluation evidence pack"),
    )


def all_pathways():
    return tuple(pathway(role) for role in ROLE_GROUPS)


def good_workshare(**changes):
    values = dict(
        owner="TJLabs",
        deliverables=(
            "Responsible-AI evidence mapping",
            "role-pathway evaluation rubrics",
            "hands-on lab QA",
            "deterministic outcome evidence pack",
        ),
        acceptance_criteria=(
            "all agreed role pathways have testable evaluation criteria",
            "evidence pack verifies deterministically from supplied evidence",
        ),
        exclusions=(
            "South African procurement returns",
            "training accreditation or certification issuance",
            "buyer portal submission",
            "prime client references",
        ),
    )
    values.update(changes)
    return PaidWorkshare(**values)


def compile_good(authority=None, **changes):
    values = dict(
        prime=good_prime(),
        technical_score=good_score(),
        pathways=all_pathways(),
        workshare=good_workshare(),
        submission_authority=authority or SubmissionAuthority(),
    )
    values.update(changes)
    return compile_readiness_pack(**values)


class PrimeGateTests(unittest.TestCase):
    def test_missing_prime_truth_holds(self):
        gate = PrimeCandidate(
            legal_name="",
            company_profile_ref=None,
            returnables={},
        ).mandatory_gate()
        self.assertEqual(gate["status"], "HOLD")
        self.assertIn("missing_legal_name", gate["blockers"])
        self.assertIn("missing_required_returnables", gate["blockers"])
        self.assertIn("missing_training_body_accreditation_evidence", gate["blockers"])

    def test_missing_one_returnable_is_visible(self):
        returns = {name: True for name in REQUIRED_RETURNABLES}
        returns["csd_report"] = False
        gate = good_prime(returnables=returns).mandatory_gate()
        self.assertEqual(gate["status"], "HOLD")
        self.assertEqual(gate["missing_returnables"], ["csd_report"])

    def test_unrecognized_framework_does_not_pass(self):
        gate = good_prime(framework_alignment=("Synthetic Framework",)).mandatory_gate()
        self.assertEqual(gate["status"], "HOLD")
        self.assertIn("missing_recognized_ai_governance_framework_alignment", gate["blockers"])

    def test_training_count_is_evidence_not_eligibility_inference(self):
        gate = good_prime(ai_trainings_last_3y=2).mandatory_gate()
        self.assertEqual(gate["status"], "PRIME_MANDATORY_READY")
        self.assertIn("company_profile_may_not_reach_max_training_history_score", gate["warnings"])


class TechnicalScoreTests(unittest.TestCase):
    def test_scores_are_bounded_by_buyer_caps(self):
        result = good_score(company_profile=21).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("invalid_score:company_profile", result["blockers"])

    def test_boolean_is_not_a_numeric_score(self):
        result = good_score(training_personnel=True).result()
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("invalid_score:training_personnel", result["blockers"])

    def test_below_70_holds(self):
        result = BuyerTechnicalScore(
            scores={
                "company_profile": 10,
                "project_proposal_and_training_methodology": 20,
                "training_personnel": 5,
                "key_personnel_cvs": 5,
                "reference_letters": 10,
            },
            evidence_refs=(ref(),),
        ).result()
        self.assertEqual(result["total"], 50)
        self.assertIn("technical_score_below_70", result["blockers"])

    def test_scores_without_grounded_evidence_hold(self):
        result = BuyerTechnicalScore(scores=good_score().scores).result()
        self.assertIn("missing_score_evidence", result["blockers"])


class PathwayAndWorkshareTests(unittest.TestCase):
    def test_missing_role_pathway_holds(self):
        pack = compile_good(pathways=all_pathways()[:-1])
        self.assertEqual(pack["response_status"], "HOLD")
        self.assertIn("missing_role_pathways", pack["response_blockers"])

    def test_duplicate_role_pathway_holds(self):
        paths = all_pathways() + (pathway(ROLE_GROUPS[0]),)
        pack = compile_good(pathways=paths)
        self.assertIn("duplicate_role_pathways", pack["response_blockers"])

    def test_incomplete_pathway_holds(self):
        bad = TrainingPathway(
            role_group=ROLE_GROUPS[0],
            learning_outcomes=(),
            delivery_modes=("workshop",),
            evaluation_methods=("quiz",),
            artefacts=("attendance",),
        )
        paths = (bad,) + tuple(pathway(role) for role in ROLE_GROUPS[1:])
        pack = compile_good(pathways=paths)
        self.assertIn("pathway_content_gate", pack["response_blockers"])

    def test_workshare_must_remain_explicitly_paid(self):
        pack = compile_good(workshare=good_workshare(commercial_state="FREE_DISCOVERY"))
        self.assertIn("paid_workshare_gate", pack["response_blockers"])
        self.assertIn("unsupported_commercial_state", pack["paid_workshare"]["blockers"])


class SubmissionAndReceiptTests(unittest.TestCase):
    def test_response_can_be_ready_while_submission_authority_stays_hold(self):
        pack = compile_good()
        self.assertEqual(pack["response_status"], "RESPONSE_ASSEMBLY_READY")
        self.assertEqual(pack["submission_status"], "HOLD")
        self.assertEqual(pack["submission_authority"]["status"], "HOLD")

    def test_complete_synthetic_authority_path_is_submission_ready(self):
        pack = compile_good(
            authority=SubmissionAuthority(
                portal_account_confirmed=True,
                authorized_signatory_confirmed=True,
                prime_approved_submission=True,
            )
        )
        self.assertEqual(pack["response_status"], "RESPONSE_ASSEMBLY_READY")
        self.assertEqual(pack["submission_status"], "SUBMISSION_READY")
        self.assertEqual(len(pack["receipt_sha256"]), 64)

    def test_receipt_is_deterministic_and_changes_with_evidence(self):
        first = compile_good()
        second = compile_good()
        self.assertEqual(first["receipt_sha256"], second["receipt_sha256"])
        changed = compile_good(technical_score=good_score(reference_letters=16))
        self.assertNotEqual(first["receipt_sha256"], changed["receipt_sha256"])

    def test_receipt_handles_lone_surrogate_evidence(self):
        score = BuyerTechnicalScore(
            scores=good_score().scores,
            evidence_refs=(EvidenceRef(label="edge", locator="fixture://edge", note=chr(0xD800)),),
        )
        pack = compile_good(technical_score=score)
        self.assertEqual(len(pack["receipt_sha256"]), 64)

    def test_real_cli_hold_fixture_fails_closed_without_traceback(self):
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "commercial.sasria_ai_training.cli",
                "commercial/sasria_ai_training/example_hold.json",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 2, msg=result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        pack = json.loads(result.stdout)
        self.assertEqual(pack["response_status"], "HOLD")
        self.assertEqual(pack["submission_status"], "HOLD")
        self.assertIn("prime_mandatory_gate", pack["response_blockers"])
        self.assertEqual(len(pack["receipt_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
