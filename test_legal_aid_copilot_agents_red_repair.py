from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from commercial.legal_aid_copilot_agents import (
    AdoptionMetrics,
    ComparableEngagement,
    PartnerEvidence,
    Reference,
    Trainer,
    compile_delivery_pack,
)
from test_legal_aid_copilot_agents import good_adoption, good_eval, good_governance, good_partner


class DuplicateEvidenceRegressionTests(unittest.TestCase):
    def _trainer(self):
        return Trainer(
            name="Synthetic trainer",
            role="Lead",
            copilot_experience_summary="Synthetic only",
            availability_start=date(2026, 9, 25),
            availability_end=date(2026, 11, 30),
        )

    def test_duplicate_engagements_and_references_cannot_mint_teaming_ready(self):
        first_engagement = ComparableEngagement(
            client_label="Synthetic Client",
            scope="Copilot Studio training",
            outcome="Completed workshop",
            evidence_route="fixture://engagement/one",
        )
        semantic_duplicate_engagement = ComparableEngagement(
            client_label=" synthetic client ",
            scope="copilot studio training",
            outcome="completed workshop",
            evidence_route="FIXTURE://ENGAGEMENT/ONE",
        )
        first_reference = Reference(
            organization="Synthetic Org",
            contact_name="Synthetic Contact",
            contact_route="fixture://reference/one",
            engagement_summary="Synthetic reference",
        )
        semantic_duplicate_reference = Reference(
            organization=" synthetic org ",
            contact_name="synthetic contact",
            contact_route="FIXTURE://REFERENCE/ONE",
            engagement_summary="synthetic reference",
        )
        gate = PartnerEvidence(
            company_name="Synthetic Partner",
            company_profile="Synthetic profile",
            trainer=self._trainer(),
            comparable_engagements=(first_engagement, semantic_duplicate_engagement),
            references=(first_reference, semantic_duplicate_reference),
            subcontract_role="Training anchor",
            commercial_split_discussed=True,
            sample_agreement_available=True,
        ).proposal_gate()

        self.assertEqual(gate["status"], "HOLD")
        self.assertEqual(gate["valid_comparable_engagements"], 1)
        self.assertEqual(gate["valid_references"], 1)
        self.assertIn("duplicate_comparable_engagement_evidence", gate["blockers"])
        self.assertIn("duplicate_reference_evidence", gate["blockers"])
        self.assertIn("fewer_than_two_comparable_engagements", gate["blockers"])
        self.assertIn("fewer_than_two_valid_references", gate["blockers"])


class AdoptionRegressionTests(unittest.TestCase):
    def test_functioning_agent_cannot_exist_without_builder(self):
        with self.assertRaises(ValueError):
            AdoptionMetrics(
                invited_staff=0,
                trained_staff=0,
                builders=0,
                functioning_agents=1,
                evaluated_agents=1,
            ).result()

    def test_zero_training_and_zero_builders_remain_hold(self):
        result = AdoptionMetrics(
            invited_staff=0,
            trained_staff=0,
            builders=0,
            functioning_agents=0,
            evaluated_agents=0,
        ).result()
        self.assertEqual(result["buyer_outcome_status"], "HOLD")


class CliFailClosedRegressionTests(unittest.TestCase):
    def _run_path(self, path: Path, optimized: bool):
        command = [sys.executable]
        if optimized:
            command.append("-O")
        command.extend(["-m", "commercial.legal_aid_copilot_agents.cli", str(path)])
        return subprocess.run(command, check=False, capture_output=True, text=True)

    def _assert_controlled_hold(self, result):
        self.assertEqual(result.returncode, 2, msg=result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        pack = json.loads(result.stdout)
        self.assertEqual(pack["delivery_status"], "HOLD")

    def test_malformed_evidence_classes_fail_closed_normal_and_optimized(self):
        payloads = {
            "empty_object": "{}",
            "malformed_json": "{not-json",
            "wrong_nested_type": json.dumps({"partner": []}),
            "invalid_trainer_date": json.dumps(
                {
                    "partner": {
                        "trainer": {
                            "name": "Synthetic",
                            "role": "Lead",
                            "copilot_experience_summary": "Synthetic",
                            "availability_start": "not-a-date",
                            "availability_end": "2026-11-30",
                        }
                    }
                }
            ),
            "lone_surrogate_evidence": json.dumps(
                {
                    "governance": {"controls": {}, "notes": {"edge": "\ud800"}},
                    "adoption": {
                        "invited_staff": 0,
                        "trained_staff": 0,
                        "builders": 0,
                        "functioning_agents": 0,
                        "evaluated_agents": 0,
                    },
                }
            ),
        }
        for optimized in (False, True):
            for label, payload in payloads.items():
                with self.subTest(optimized=optimized, payload=label):
                    with tempfile.TemporaryDirectory() as temp_dir:
                        path = Path(temp_dir) / "evidence.json"
                        path.write_text(payload, encoding="utf-8")
                        self._assert_controlled_hold(self._run_path(path, optimized))

    def test_missing_input_resource_fails_closed_normal_and_optimized(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            missing = Path(temp_dir) / "missing.json"
            for optimized in (False, True):
                with self.subTest(optimized=optimized):
                    self._assert_controlled_hold(self._run_path(missing, optimized))


class ReceiptEvidenceBindingTests(unittest.TestCase):
    def test_passing_score_change_changes_receipt(self):
        first = compile_delivery_pack(
            partner=good_partner(),
            governance=good_governance(),
            evaluations=(good_eval(),),
            adoption=good_adoption(),
        )
        changed = compile_delivery_pack(
            partner=good_partner(),
            governance=good_governance(),
            evaluations=(good_eval(task_success=5),),
            adoption=good_adoption(),
        )
        self.assertEqual(first["evaluations"][0]["scores"]["task_success"], 4)
        self.assertEqual(changed["evaluations"][0]["scores"]["task_success"], 5)
        self.assertNotEqual(first["receipt_sha256"], changed["receipt_sha256"])


if __name__ == "__main__":
    unittest.main()
