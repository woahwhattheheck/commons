import json
from pathlib import Path
import subprocess
import sys
import tempfile
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
        deliverables=("Responsible-AI evidence mapping", "role-pathway evaluation rubrics"),
        acceptance_criteria=("all agreed outputs trace to supplied evidence",),
        exclusions=("South African procurement returns", "buyer portal submission"),
    )
    values.update(changes)
    return PaidWorkshare(**values)


def compile_good(authority=None, **changes):
    values = dict(
        prime=good_prime(), technical_score=good_score(), pathways=all_pathways(),
        workshare=good_workshare(), submission_authority=authority or SubmissionAuthority(),
    )
    values.update(changes)
    return compile_readiness_pack(**values)


class ReadinessTests(unittest.TestCase):
    def test_missing_prime_truth_holds(self):
        gate = PrimeCandidate(legal_name="", company_profile_ref=None, returnables={}).mandatory_gate()
        self.assertEqual(gate["status"], "HOLD")
        self.assertIn("missing_required_returnables", gate["blockers"])

    def test_invalid_returnables_public_api_holds_without_crash(self):
        gate = PrimeCandidate(legal_name="x", company_profile_ref=ref(), returnables=None).mandatory_gate()  # type: ignore[arg-type]
        self.assertEqual(gate["status"], "HOLD")
        self.assertIn("invalid_returnables_mapping", gate["blockers"])

    def test_score_caps_boolean_and_threshold(self):
        self.assertIn("invalid_score:company_profile", good_score(company_profile=21).result()["blockers"])
        self.assertIn("invalid_score:training_personnel", good_score(training_personnel=True).result()["blockers"])
        low = BuyerTechnicalScore(
            scores={"company_profile": 10, "project_proposal_and_training_methodology": 20, "training_personnel": 5, "key_personnel_cvs": 5, "reference_letters": 10},
            evidence_refs=(ref(),),
        ).result()
        self.assertEqual(low["total"], 50)
        self.assertIn("technical_score_below_70", low["blockers"])

    def test_pathway_and_paid_workshare_gates(self):
        missing = compile_good(pathways=all_pathways()[:-1])
        self.assertIn("missing_role_pathways", missing["response_blockers"])
        dup = compile_good(pathways=all_pathways() + (pathway(ROLE_GROUPS[0]),))
        self.assertIn("duplicate_role_pathways", dup["response_blockers"])
        free = compile_good(workshare=good_workshare(commercial_state="FREE_DISCOVERY"))
        self.assertIn("paid_workshare_gate", free["response_blockers"])

    def test_response_ready_does_not_mean_submission_ready(self):
        pack = compile_good()
        self.assertEqual(pack["response_status"], "RESPONSE_ASSEMBLY_READY")
        self.assertEqual(pack["submission_status"], "HOLD")
        self.assertIn("trusted_submission_authority_not_bound", pack["submission_authority"]["blockers"])

    def test_caller_true_true_true_cannot_mint_submission_authority(self):
        pack = compile_good(authority=SubmissionAuthority(True, True, True))
        self.assertEqual(pack["response_status"], "RESPONSE_ASSEMBLY_READY")
        self.assertEqual(pack["submission_status"], "HOLD")
        self.assertEqual(pack["submission_authority"]["status"], "HOLD")
        self.assertTrue(all(pack["submission_authority"]["candidate_assertions"].values()))
        self.assertIn("trusted_submission_authority_not_bound", pack["submission_authority"]["blockers"])

    def test_receipt_is_deterministic_and_evidence_sensitive(self):
        first, second = compile_good(), compile_good()
        self.assertEqual(first["receipt_sha256"], second["receipt_sha256"])
        changed = compile_good(technical_score=good_score(reference_letters=16))
        self.assertNotEqual(first["receipt_sha256"], changed["receipt_sha256"])

    def test_real_cli_hold_fixture_is_controlled(self):
        for optimized in (False, True):
            command = [sys.executable] + (["-O"] if optimized else []) + [
                "-m", "commercial.sasria_ai_training.cli", "commercial/sasria_ai_training/example_hold.json"
            ]
            result = subprocess.run(command, check=False, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, msg=result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            pack = json.loads(result.stdout)
            self.assertEqual(pack["submission_status"], "HOLD")

    def test_hostile_valid_json_shapes_are_rc2_no_traceback_no_outputs(self):
        hostiles = [
            {"prime": {"returnables": []}},
            {"prime": {"framework_alignment": True}},
            {"training_pathways": None},
        ]
        for payload in hostiles:
            for optimized in (False, True):
                with self.subTest(payload=payload, optimized=optimized), tempfile.TemporaryDirectory() as td:
                    td_path = Path(td)
                    source = td_path / "input.json"
                    json_out = td_path / "out.json"
                    md_out = td_path / "out.md"
                    source.write_text(json.dumps(payload), encoding="utf-8")
                    command = [sys.executable] + (["-O"] if optimized else []) + [
                        "-m", "commercial.sasria_ai_training.cli", str(source),
                        "--json-out", str(json_out), "--markdown-out", str(md_out),
                    ]
                    result = subprocess.run(command, check=False, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 2, msg=result.stderr)
                    self.assertIn("INPUT_ERROR:", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertEqual(result.stdout, "")
                    self.assertFalse(json_out.exists())
                    self.assertFalse(md_out.exists())


if __name__ == "__main__":
    unittest.main()
