#!/usr/bin/env python3
import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MODULE_PATH = ROOT / "host" / "scope_to_delivery.py"
SPEC = importlib.util.spec_from_file_location("scope_to_delivery", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ScopeToDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.catalog = load("revenue/outcome_commerce/catalog.json")
        self.bindings = MODULE.load_bindings()
        self.accepted = load("revenue/scope_to_delivery/fixtures/accepted_agreement.json")
        self.unaccepted = load("revenue/scope_to_delivery/fixtures/unaccepted_agreement.json")
        self.observations = load("revenue/scope_to_delivery/fixtures/accepted_observations.json")
        self.incomplete = load("revenue/scope_to_delivery/fixtures/incomplete_observations.json")
        self.payment = load("revenue/scope_to_delivery/fixtures/payment_authorized.json")
        self.payment_absent = load("revenue/scope_to_delivery/fixtures/payment_absent.json")
        self.payment_bank = load("revenue/scope_to_delivery/fixtures/payment_bank_available.json")

    def project(self, agreement, observations=None, payment=None):
        return MODULE.compose_project(agreement, self.catalog, self.bindings, observations, payment)

    def test_catalog_lists_every_canonical_sku_and_does_not_mint_cash(self):
        view = MODULE.compose_catalog(self.catalog, self.bindings)
        ids = [item["id"] for item in view["listings"]]
        self.assertEqual(len(ids), 17)
        self.assertIn("same-day-agent-survival-proof", ids)
        self.assertIn("sku-muhlnickel-titan-20260826", ids)
        self.assertIn("sku-muhlnickel-attested-inference", ids)
        self.assertIn("sku-muhlnickel-generated-token-capacity", ids)
        self.assertEqual(view["funnel_truth"]["accepted_scopes"], 0)
        self.assertEqual(view["funnel_truth"]["paid_deliveries"], 0)
        self.assertEqual(view["funnel_truth"]["collected_cash_usd"], "0.00")
        survival = next(item for item in view["listings"] if item["id"] == "same-day-agent-survival-proof")
        self.assertEqual(survival["amount"], "2500.00")
        self.assertEqual(survival["acceptance_row_count"], 4)

    def test_json_fixtures_reject_floating_point(self):
        for path in (ROOT / "revenue" / "scope_to_delivery").rglob("*.json"):
            MODULE.load_json(path)

    def test_unaccepted_agreement_stays_draft_and_does_not_deliver(self):
        project = self.project(self.unaccepted, payment=self.payment_absent)
        self.assertEqual(project["agreement_state"], "WRITTEN_INTAKE")
        self.assertEqual(project["sow"]["lock"], "DRAFT_SOW")
        self.assertEqual(project["work_packet"]["state"], "NOT_ISSUED")
        self.assertEqual(project["execution_status"]["status"], "NOT_STARTED")
        self.assertFalse(project["delivery_receipt"]["delivered"])
        self.assertEqual(project["delivery_receipt"]["delivery_state"], "NOT_DELIVERED")
        self.assertEqual(project["invoice"]["state"], "NOT_ISSUED")
        self.assertFalse(project["payment_state"]["cash_claimed"])
        self.assertIn("No written PRESENT acceptance", project["handoff"]["gaps"][0])

    def test_accepted_without_observations_locks_sow_but_does_not_invent_work(self):
        project = self.project(self.accepted)
        self.assertEqual(project["agreement_state"], "ACCEPTED")
        self.assertEqual(project["sow"]["lock"], "LOCKED_SOW")
        self.assertEqual(project["work_packet"]["state"], "ISSUED")
        self.assertEqual(len(project["work_packet"]["acceptance_rows"]), 4)
        self.assertEqual(project["execution_status"]["status"], "NOT_STARTED")
        self.assertFalse(project["delivery_receipt"]["delivered"])
        self.assertEqual(project["evidence_bundle"]["unmeasured_rows"], [
            "happy-path", "failure-or-stop-path", "rollback-or-reset", "durable-receipt",
        ])

    def test_complete_synthetic_run_delivers_without_claiming_bank_cash(self):
        project = self.project(self.accepted, self.observations, self.payment)
        self.assertEqual(project["execution_status"]["status"], "PASS")
        self.assertTrue(project["evidence_bundle"]["complete"])
        self.assertTrue(project["delivery_receipt"]["delivered"])
        self.assertEqual(project["invoice"]["state"], "ISSUED")
        self.assertEqual(project["payment_state"]["payment_truth"]["authorization"], "CONFIRMED")
        self.assertEqual(project["payment_state"]["payment_truth"]["settlement"], "UNMEASURED")
        self.assertFalse(project["payment_state"]["cash_claimed"])
        self.assertIn("Cash is not BANK_AVAILABLE", " ".join(project["handoff"]["gaps"]))
        self.assertNotIn("testimonial", project["handoff"])
        self.assertNotIn("testimonial", project)

    def test_authorization_does_not_prove_delivery_on_incomplete_rows(self):
        project = self.project(self.accepted, self.incomplete, self.payment)
        self.assertEqual(project["execution_status"]["status"], "SUBMITTED")
        self.assertFalse(project["delivery_receipt"]["delivered"])
        self.assertIn("failure-or-stop-path", project["delivery_receipt"]["missing_rows"])
        self.assertEqual(project["invoice"]["state"], "ISSUED")
        self.assertEqual(project["payment_state"]["payment_truth"]["authorization"], "CONFIRMED")

    def test_bank_available_claims_cash_but_still_does_not_invent_delivery(self):
        project = self.project(self.accepted, self.incomplete, self.payment_bank)
        self.assertTrue(project["payment_state"]["cash_claimed"])
        self.assertFalse(project["delivery_receipt"]["delivered"])
        self.assertTrue(project["delivery_receipt"]["payment_does_not_prove_delivery"])

    def test_digest_mismatch_is_rejected(self):
        changed = copy.deepcopy(self.accepted)
        changed["intake_sentence"] += " extra"
        with self.assertRaisesRegex(MODULE.PipelineError, "terms_digest"):
            MODULE.validate_agreement(changed, self.catalog)

    def test_wrong_catalog_amount_is_rejected(self):
        changed = copy.deepcopy(self.accepted)
        changed["quote"]["amount"] = "2499.00"
        changed["written_acceptance"]["terms_digest"] = MODULE.terms_digest(changed)
        with self.assertRaisesRegex(MODULE.PipelineError, "catalog total"):
            MODULE.validate_agreement(changed, self.catalog)

    def test_sensitive_and_party_fields_are_rejected(self):
        changed = copy.deepcopy(self.accepted)
        changed["customer_email"] = "buyer@example.com"
        with self.assertRaisesRegex(MODULE.PipelineError, "forbidden"):
            MODULE.validate_agreement(changed, self.catalog)
        changed = copy.deepcopy(self.accepted)
        changed["testimonial"] = "Great work"
        with self.assertRaisesRegex(MODULE.PipelineError, "forbidden"):
            MODULE.validate_agreement(changed, self.catalog)

    def test_float_json_is_rejected(self):
        path = ROOT / "revenue" / "scope_to_delivery" / "fixtures" / "accepted_agreement.json"
        original = path.read_text(encoding="utf-8")
        try:
            path.write_text(original.replace('"2500.00"', "2500.00"), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.PipelineError, "floating point"):
                MODULE.load_json(path)
        finally:
            path.write_text(original, encoding="utf-8")

    def test_sow_never_fills_party_names(self):
        sow = self.project(self.accepted)["sow"]
        self.assertEqual(sow["parties"]["buyer"], "REDACTED_PUBLIC")
        self.assertEqual(sow["parties"]["emails"], "NOT_ON_PUBLIC_MAIN")
        self.assertEqual(sow["parties"]["addresses"], "NOT_ON_PUBLIC_MAIN")
        serialized = json.dumps(sow).lower()
        self.assertNotIn("@", serialized)
        self.assertNotIn("example.com", serialized)

    def test_pass_rows_without_work_started_are_submitted_not_pass(self):
        observations = copy.deepcopy(self.observations)
        observations["observations"] = [
            item for item in observations["observations"] if item["kind"] != "WORK_STARTED"
        ]
        project = self.project(self.accepted, observations)
        self.assertEqual(project["execution_status"]["status"], "SUBMITTED")
        self.assertFalse(project["delivery_receipt"]["delivered"])

    def test_cli_project_matches_library_and_evidence_hashes(self):
        import subprocess
        result = subprocess.run(
            [
                "python3", "host/scope_to_delivery.py", "project",
                "--agreement", "revenue/scope_to_delivery/fixtures/accepted_agreement.json",
                "--observations", "revenue/scope_to_delivery/fixtures/accepted_observations.json",
                "--payment", "revenue/scope_to_delivery/fixtures/payment_authorized.json",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["delivery_receipt"]["delivered"], True)
        self.assertEqual(payload["payment_state"]["cash_claimed"], False)
        happy = (ROOT / "revenue/scope_to_delivery/fixtures/synthetic-happy-path.txt").read_bytes()
        digest = __import__("hashlib").sha256(happy).hexdigest()
        item = next(row for row in payload["evidence_bundle"]["items"] if row["row_id"] == "happy-path")
        self.assertEqual(item["sha256"], digest)

    def test_checked_in_project_fixtures_match_composer(self):
        complete = self.project(self.accepted, self.observations, self.payment)
        stored = load("revenue/scope_to_delivery/fixtures/project-accepted-complete.json")
        self.assertEqual(complete["delivery_receipt"]["delivered"], stored["delivery_receipt"]["delivered"])
        self.assertEqual(complete["execution_status"]["status"], stored["execution_status"]["status"])
        self.assertEqual(complete["payment_state"]["cash_claimed"], stored["payment_state"]["cash_claimed"])
        unaccepted = self.project(self.unaccepted, payment=self.payment_absent)
        stored_open = load("revenue/scope_to_delivery/fixtures/project-unaccepted.json")
        self.assertEqual(unaccepted["sow"]["lock"], stored_open["sow"]["lock"])
        self.assertFalse(stored_open["delivery_receipt"]["delivered"])

    def test_strongest_sku_bindings_exist(self):
        required = {
            "same-day-agent-survival-proof",
            "production-survival-sprint",
            "gguf-diagnostic-10d-12k",
            "white-box-gguf-pilot-30d",
            "ho-issue-to-pr",
            "ho-meeting-packet",
            "ho-security-questionnaire",
            "ho-pixel-pack",
            "sku-muhlnickel-titan-20260826",
        }
        self.assertTrue(required.issubset(self.bindings["skus"]))

    def test_sponsorship_exclusions_do_not_collocate_claim_with_gate(self):
        skus = self.bindings["skus"]
        self.assertEqual(
            skus["sku-tip-20260826"]["out_of_scope"],
            ["membership", "gated-entitlement", "private-buyer-data-on-main"],
        )
        self.assertEqual(
            skus["sku-seat-20260826"]["out_of_scope"],
            ["claim-purchase", "gated-entitlement", "from-equals-payment"],
        )
        self.assertEqual(
            skus["sku-monthly-tip-20260826"]["out_of_scope"],
            ["seat", "claim", "gated-entitlement"],
        )
        view = load("revenue/scope_to_delivery/fixtures/catalog-view.json")
        by_id = {item["id"]: item for item in view["listings"]}
        self.assertEqual(
            by_id["sku-seat-20260826"]["out_of_scope"],
            skus["sku-seat-20260826"]["out_of_scope"],
        )
        self.assertEqual(
            by_id["sku-monthly-tip-20260826"]["out_of_scope"],
            skus["sku-monthly-tip-20260826"]["out_of_scope"],
        )
        self.assertEqual(
            by_id["sku-tip-20260826"]["out_of_scope"],
            skus["sku-tip-20260826"]["out_of_scope"],
        )


if __name__ == "__main__":
    unittest.main()
