import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("revenue_recovery", ROOT / "host/revenue_recovery.py")
rr = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(rr)


class RevenueRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.pack = json.loads((ROOT / rr.PACK_PATH).read_text(encoding="utf-8"))
        self.recovery = json.loads((ROOT / rr.RECOVERY_PATH).read_text(encoding="utf-8"))

    def make_root(self, post=None):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "revenue/payment_ready").mkdir(parents=True)
        (root / "p").mkdir()
        for relative in (rr.PACK_PATH, rr.RECOVERY_PATH):
            shutil.copyfile(ROOT / relative, root / relative)
        if post is not None:
            (root / "p/buyer-signal.md").write_text(post, encoding="utf-8")
        return temp, root

    def valid_post(self, extra=""):
        return "\n".join([
            "---",
            "from: public-prospect",
            "to: OFFER",
            "board: OFFER",
            f"subject: {rr.SUBJECT}",
            "---",
            "PLAIN: Public, non-confidential GGUF diagnostic purchase intent.",
            f"OFFER_ID: {rr.OFFER_ID}",
            f"TERMS_SHA256: {rr.EXPECTED_TERMS_SHA256}",
            "PURCHASE_INTENT: YES",
            "GGUF_CONTROL: YES",
            "HARNESS_READY: YES",
            "PUBLIC_CONTACT_URL: https://example.com/contact",
            "START_WINDOW: public",
            "PUBLIC_OBJECTIVE: reproducibility",
            extra,
        ])

    def test_contract_hashes_are_exact(self):
        _, _, pack_hash, term_hash = rr.validate_contract(ROOT)
        self.assertEqual(pack_hash, self.recovery["offer"]["source_sha256"])
        self.assertEqual(term_hash, rr.EXPECTED_TERMS_SHA256)
        self.assertEqual(term_hash, self.recovery["offer"]["terms_sha256"])

    def test_safe_path_rejects_escape(self):
        for value in ("../escape", "..\\escape", "a/b", ".", "..", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                rr.safe_inbound_path(ROOT, value)

    def test_missing_signal_is_needs_buyer_not_demand(self):
        receipt = rr.purchase_intent_receipt(ROOT, None)
        self.assertEqual(receipt["state"], "NEEDS_BUYER")
        self.assertEqual(receipt["facts"]["purchase_intent"], "UNKNOWN")
        self.assertEqual(receipt["facts"]["collected_cash_usd"], 0)
        self.assertFalse(receipt["cash_claimed"])

    def test_valid_signal_is_deterministic_and_redacted(self):
        temp, root = self.make_root(self.valid_post())
        self.addCleanup(temp.cleanup)
        one = rr.purchase_intent_receipt(root, "buyer-signal")
        two = rr.purchase_intent_receipt(root, "buyer-signal")
        rendered = json.dumps(one, sort_keys=True)
        self.assertEqual(one, two)
        self.assertEqual(one["state"], "RECORDED")
        self.assertEqual(one["next_stage"], "QUOTE")
        self.assertEqual(one["facts"]["legal_acceptance"], "NOT_LANDED")
        self.assertEqual(one["facts"]["processor_payment"], "NOT_LANDED")
        self.assertEqual(one["facts"]["collected_cash_usd"], 0)
        self.assertNotIn("example.com", rendered)

    def test_invalid_or_sensitive_signal_is_incomplete(self):
        cases = (
            self.valid_post().replace("HARNESS_READY: YES", "HARNESS_READY: NO"),
            self.valid_post().replace(rr.EXPECTED_TERMS_SHA256, "0" * 64),
            self.valid_post("ROUTING NUMBER: 123456789"),
            self.valid_post("CARD: 4242 4242 4242 4242"),
        )
        for index, post in enumerate(cases):
            with self.subTest(index=index):
                temp, root = self.make_root(post)
                try:
                    receipt = rr.purchase_intent_receipt(root, "buyer-signal")
                    self.assertEqual(receipt["state"], "INCOMPLETE")
                    self.assertFalse(receipt["cash_claimed"])
                finally:
                    temp.cleanup()

    def test_public_surface_is_open_and_exact(self):
        page = (ROOT / "diagnostic.html").read_text(encoding="utf-8")
        self.assertIn('id="say"', page)
        self.assertIn('src="./carrier.js?', page)
        self.assertIn('name="to" value="OFFER"', page)
        self.assertIn('name="board" value="OFFER"', page)
        self.assertIn(f'name="subject" value="{rr.SUBJECT}"', page)
        self.assertIn(f"TERMS_SHA256: {rr.EXPECTED_TERMS_SHA256}", page)
        self.assertIn("No login or approval gate", page)
        lower = page.lower()
        self.assertNotIn('type="password"', lower)
        self.assertNotIn("allowlist", lower)
        self.assertNotIn("user tier", lower)

    def test_pipeline_truth_and_prospects_are_calibrated(self):
        self.assertTrue(self.recovery["public_surface"]["no_login"])
        self.assertTrue(self.recovery["public_surface"]["no_auth"])
        self.assertTrue(self.recovery["public_surface"]["no_gate"])
        self.assertEqual(self.recovery["truth"]["buyer"], "UNKNOWN")
        self.assertEqual(self.recovery["truth"]["demand"], "UNKNOWN")
        self.assertFalse(self.recovery["truth"]["contact_sent"])
        self.assertEqual(self.recovery["truth"]["collected_cash_usd"], 0)
        self.assertFalse(self.recovery["resource_recovery"]["cursor_used_for_this_pipeline"])
        prospects = json.loads((ROOT / "revenue/payment_ready/prospects.json").read_text(encoding="utf-8"))
        self.assertEqual(len(prospects["prospects"]), 4)
        for row in prospects["prospects"]:
            self.assertEqual(row["state"], "PROSPECT_NOT_CONTACTED")
            self.assertTrue(row["buyer_channel_url"].startswith("https://"))
            self.assertTrue(row["disqualifier"])
        self.assertEqual(prospects["contact_sent"], False)
        self.assertEqual(prospects["truth"]["collected_cash_usd"], 0)

    def test_processor_is_hosted_handoff_not_mock_checkout(self):
        text = (ROOT / "revenue/payment_ready/processor_handoff.md").read_text(encoding="utf-8")
        self.assertIn("https://dashboard.stripe.com/account/payouts", text)
        self.assertIn("https://dashboard.stripe.com/invoices", text)
        self.assertIn("https://www.paypal.com/myaccount/money/", text)
        self.assertIn("never paste", text.lower())
        self.assertIn("enter the payout destination there only", text.lower())
        self.assertEqual(self.recovery["processor_handoff"]["values_never_enter_commons"], True)

    def test_public_artifacts_do_not_contain_secret_values(self):
        for relative in (
            "diagnostic.html",
            "revenue/payment_ready/recovery.json",
            "revenue/payment_ready/prospects.json",
            "revenue/payment_ready/outreach.md",
            "revenue/payment_ready/processor_handoff.md",
            "revenue/payment_ready/current_receipt.json",
            "revenue/payment_ready/integration_inventory.json",
            "revenue/payment_ready/evidence_contract.md",
        ):
            with self.subTest(relative=relative):
                self.assertFalse(rr.contains_sensitive_value((ROOT / relative).read_text(encoding="utf-8")))

    def test_receipt_schema_never_claims_cash(self):
        schema = json.loads((ROOT / "revenue/payment_ready/receipt.schema.json").read_text(encoding="utf-8"))
        self.assertIs(schema["properties"]["cash_claimed"]["const"], False)

    def test_public_current_receipt_is_deterministic(self):
        committed = json.loads((ROOT / "revenue/payment_ready/current_receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(committed, rr.purchase_intent_receipt(ROOT, None))

    def test_integration_inventory_has_no_fake_checkout(self):
        inventory = json.loads((ROOT / "revenue/payment_ready/integration_inventory.json").read_text(encoding="utf-8"))
        self.assertTrue(inventory["zero_cursor"])
        stripe = next(row for row in inventory["missing_or_pending"] if row["provider"] == "Stripe")
        self.assertEqual(stripe["state"], "NOT_PROVISIONED")
        self.assertTrue(stripe["private_values_never_enter_commons"])
        self.assertEqual(inventory["first_revenue_result"]["buyer"], "UNKNOWN")
        self.assertEqual(inventory["first_revenue_result"]["collected_cash_usd"], 0)

    def test_full_stage_chain_is_deterministic_and_stops_before_cash(self):
        temp, root = self.make_root(self.valid_post())
        self.addCleanup(temp.cleanup)
        (root / "receipts").mkdir()
        (root / "evidence").mkdir()

        def write_json(relative, value):
            (root / relative).write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

        intent = rr.purchase_intent_receipt(root, "buyer-signal")
        write_json("receipts/intent.json", intent)
        quote_manifest = {
            "schema_version": "revenue-recovery-evidence/v1",
            "stage": "QUOTE",
            "artifact": {"kind": "QUOTE_ARTIFACT", "reference": "owner-private:quote-example", "sha256": "a" * 64},
        }
        write_json("evidence/quote.json", quote_manifest)
        quote = rr.advance_receipt(root, "QUOTE", "receipts/intent.json", "evidence/quote.json")
        self.assertEqual(quote, rr.advance_receipt(root, "QUOTE", "receipts/intent.json", "evidence/quote.json"))
        write_json("receipts/quote.json", quote)

        acceptance_manifest = {
            "schema_version": "revenue-recovery-evidence/v1",
            "stage": "ACCEPTANCE",
            "artifact": {"kind": "SIGNED_ACCEPTANCE", "reference": "owner-private:acceptance-example", "sha256": "b" * 64},
        }
        write_json("evidence/acceptance.json", acceptance_manifest)
        acceptance = rr.advance_receipt(root, "ACCEPTANCE", "receipts/quote.json", "evidence/acceptance.json")
        self.assertEqual(acceptance["facts"]["legal_acceptance"], "OWNER_REPORTED")
        write_json("receipts/acceptance.json", acceptance)

        delivery_manifest = {
            "schema_version": "revenue-recovery-evidence/v1",
            "stage": "DELIVERY",
            "acceptance_tests": [
                {"id": f"AT{i}", "status": "PASS", "reference": f"owner-private:at{i}-evidence", "sha256": f"{i:x}" * 64}
                for i in range(1, 7)
            ],
        }
        write_json("evidence/delivery.json", delivery_manifest)
        delivery = rr.advance_receipt(root, "DELIVERY", "receipts/acceptance.json", "evidence/delivery.json")
        self.assertEqual(delivery["facts"]["delivery"], "OWNER_REPORTED")
        self.assertEqual([row["kind"] for row in delivery["evidence"][1:]], [f"AT{i}" for i in range(1, 7)])
        write_json("receipts/delivery.json", delivery)

        processor_manifest = {
            "schema_version": "revenue-recovery-evidence/v1",
            "stage": "PROCESSOR_REFERENCE",
            "provider": "Stripe",
            "opaque_reference": "stripe:event-example",
            "payload_sha256": "c" * 64,
        }
        write_json("evidence/processor.json", processor_manifest)
        processor = rr.advance_receipt(root, "PROCESSOR_REFERENCE", "receipts/delivery.json", "evidence/processor.json")
        self.assertEqual(processor["state"], "REFERENCE_RECORDED")
        self.assertEqual(processor["facts"]["processor_payment"], "NOT_LANDED")
        self.assertEqual(processor["facts"]["bank_available"], "NOT_LANDED")
        self.assertEqual(processor["facts"]["collected_cash_usd"], 0)
        self.assertFalse(processor["cash_claimed"])

    def test_delivery_rejects_incomplete_acceptance_tests(self):
        temp, root = self.make_root()
        self.addCleanup(temp.cleanup)
        (root / "receipts").mkdir()
        (root / "evidence").mkdir()
        prior = rr.purchase_intent_receipt(root, None)
        prior["stage"] = "ACCEPTANCE"
        prior["state"] = "ACCEPTED"
        (root / "receipts/acceptance.json").write_text(json.dumps(prior), encoding="utf-8")
        manifest = {
            "schema_version": "revenue-recovery-evidence/v1",
            "stage": "DELIVERY",
            "acceptance_tests": [],
        }
        (root / "evidence/delivery.json").write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "AT1-AT6"):
            rr.advance_receipt(root, "DELIVERY", "receipts/acceptance.json", "evidence/delivery.json")


if __name__ == "__main__":
    unittest.main()
