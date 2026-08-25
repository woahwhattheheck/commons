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
        base = Path(temp.name)
        root = base / "commons"
        private = base / "private-evidence"
        (root / "revenue/payment_ready").mkdir(parents=True)
        (root / "p").mkdir()
        private.mkdir()
        for relative in (rr.PACK_PATH, rr.RECOVERY_PATH):
            shutil.copyfile(ROOT / relative, root / relative)
        if post is not None:
            (root / "p/buyer-signal.md").write_text(post, encoding="utf-8")
        return temp, root, private

    def write_private_artifact(self, private, relative, value):
        path = private / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
        return rr.sha256_file(path)

    def write_private_json(self, private, relative, value):
        path = private / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

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

    def test_pack_hash_is_canonical_across_lf_and_crlf(self):
        source = (ROOT / rr.PACK_PATH).read_text(encoding="utf-8")
        normalized = source.replace("\r\n", "\n").replace("\r", "\n")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lf_path = root / "pack-lf.json"
            crlf_path = root / "pack-crlf.json"
            lf_path.write_bytes(normalized.encode("utf-8"))
            crlf_path.write_bytes(normalized.replace("\n", "\r\n").encode("utf-8"))
            self.assertEqual(rr.sha256_canonical_text_file(lf_path), self.recovery["offer"]["source_sha256"])
            self.assertEqual(rr.sha256_canonical_text_file(crlf_path), self.recovery["offer"]["source_sha256"])

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
        temp, root, _ = self.make_root(self.valid_post())
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
                temp, root, _ = self.make_root(post)
                try:
                    receipt = rr.purchase_intent_receipt(root, "buyer-signal")
                    self.assertEqual(receipt["state"], "INCOMPLETE")
                    self.assertFalse(receipt["cash_claimed"])
                finally:
                    temp.cleanup()

    def assert_sensitive_signal_is_incomplete(self, extra):
        temp, root, _ = self.make_root(self.valid_post(extra))
        try:
            receipt = rr.purchase_intent_receipt(root, "buyer-signal")
            self.assertEqual(receipt["state"], "INCOMPLETE")
            self.assertFalse(receipt["cash_claimed"])
        finally:
            temp.cleanup()

    def test_x_url_embedded_secret_is_incomplete(self):
        self.assert_sensitive_signal_is_incomplete(
            "PUBLIC_CONTACT_URL: https://example.com/contact?token=sk_live_ABC123"
        )

    def test_y_plain_password_is_incomplete(self):
        self.assert_sensitive_signal_is_incomplete("PASSWORD: hunter2")

    def test_z_model_bytes_are_incomplete(self):
        self.assert_sensitive_signal_is_incomplete("MODEL_BYTES: payload")

    def test_private_contact_fields_are_incomplete(self):
        for value in (
            "CUSTOMER_EMAIL: private@example.com",
            "PRIVATE_CONTACT: private@example.com",
            "CUSTOMER_PHONE: +1-212-555-0199",
            "CUSTOMER_NAME: Jane Doe",
            "STREET_ADDRESS: 123 Main Street",
            "CONTACT: private@example.com",
            '\"CUSTOMER_EMAIL\": \"private@example.com\"',
        ):
            with self.subTest(value=value):
                self.assert_sensitive_signal_is_incomplete(value)

    def test_public_contact_url_is_not_a_private_contact_field(self):
        self.assertFalse(rr.contains_sensitive_value("PUBLIC_CONTACT_URL: https://example.com/contact"))

    def test_public_surface_is_open_and_exact(self):
        page = (ROOT / "diagnostic.html").read_text(encoding="utf-8")
        self.assertIn('id="say"', page)
        self.assertIn('src="./carrier.js?', page)
        self.assertIn('name="to" value="OFFER"', page)
        self.assertIn('name="board" value="OFFER"', page)
        self.assertIn(f'name="subject" value="{rr.SUBJECT}"', page)
        self.assertIn(f"TERMS_SHA256: {rr.EXPECTED_TERMS_SHA256}", page)
        self.assertIn("after NDA and SOW signing", page)
        self.assertIn("$6,000 before customer file exchange; after NDA and SOW signing", page)
        self.assertNotIn("before customer file exchange, after NDA and SOW signing", page)
        self.assertIn("event.stopImmediatePropagation()", page)
        self.assertIn("(?:model|gguf)[_ -]?bytes", page)
        self.assertIn("private[_ -]?contact", page)
        self.assertIn('data-no-from-memory="true"', page)
        self.assertLess(page.index("event.stopImmediatePropagation()"), page.index('src="./carrier.js?'))
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
        self.assertEqual(schema["properties"]["facts"]["properties"]["collected_cash_usd"]["const"], 0)

    def test_false_cash_claim_rejects_positive_previous_cash(self):
        temp, root, private = self.make_root()
        self.addCleanup(temp.cleanup)
        (root / "receipts").mkdir()
        prior = rr.purchase_intent_receipt(root, None)
        prior["stage"] = "PURCHASE_INTENT"
        prior["state"] = "RECORDED"
        prior["facts"]["collected_cash_usd"] = 1
        (root / "receipts/intent.json").write_text(json.dumps(prior), encoding="utf-8")
        manifest = {
            "schema_version": "revenue-recovery-evidence/v1",
            "stage": "QUOTE",
            "artifact": {
                "kind": "QUOTE_ARTIFACT",
                "reference": "owner-private:quote-example",
                "file": "quote.bin",
                "sha256": self.write_private_artifact(private, "quote.bin", b"quote"),
            },
        }
        self.write_private_json(private, "quote.json", manifest)
        with self.assertRaisesRegex(ValueError, "collected_cash_usd"):
            rr.advance_receipt(root, "QUOTE", "receipts/intent.json", private, "quote.json")

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
        temp, root, private = self.make_root(self.valid_post())
        self.addCleanup(temp.cleanup)
        (root / "receipts").mkdir()

        def write_json(relative, value):
            (root / relative).write_text(json.dumps(value, sort_keys=True), encoding="utf-8")

        intent = rr.purchase_intent_receipt(root, "buyer-signal")
        write_json("receipts/intent.json", intent)
        quote_digest = self.write_private_artifact(private, "quote.bin", b"private quote bytes")
        quote_manifest = {
            "schema_version": "revenue-recovery-evidence/v1",
            "stage": "QUOTE",
            "artifact": {
                "kind": "QUOTE_ARTIFACT",
                "reference": "owner-private:quote-example",
                "file": "quote.bin",
                "sha256": quote_digest,
            },
        }
        self.write_private_json(private, "quote.json", quote_manifest)
        quote = rr.advance_receipt(root, "QUOTE", "receipts/intent.json", private, "quote.json")
        self.assertEqual(quote, rr.advance_receipt(root, "QUOTE", "receipts/intent.json", private, "quote.json"))
        self.assertNotIn(str(private), json.dumps(quote))
        self.assertNotIn("quote.json", json.dumps(quote))
        write_json("receipts/quote.json", quote)

        acceptance_digest = self.write_private_artifact(private, "signed-acceptance.bin", b"signed acceptance")
        acceptance_manifest = {
            "schema_version": "revenue-recovery-evidence/v1",
            "stage": "ACCEPTANCE",
            "artifact": {
                "kind": "SIGNED_ACCEPTANCE",
                "reference": "owner-private:acceptance-example",
                "file": "signed-acceptance.bin",
                "sha256": acceptance_digest,
            },
        }
        self.write_private_json(private, "acceptance.json", acceptance_manifest)
        acceptance = rr.advance_receipt(root, "ACCEPTANCE", "receipts/quote.json", private, "acceptance.json")
        self.assertEqual(acceptance["facts"]["legal_acceptance"], "OWNER_REPORTED")
        write_json("receipts/acceptance.json", acceptance)

        test_rows = []
        for i in range(1, 7):
            relative = f"at{i}.bin"
            test_rows.append({
                "id": f"AT{i}",
                "status": "PASS",
                "reference": f"owner-private:at{i}-evidence",
                "file": relative,
                "sha256": self.write_private_artifact(private, relative, f"AT{i}".encode("ascii")),
            })
        delivery_manifest = {
            "schema_version": "revenue-recovery-evidence/v1",
            "stage": "DELIVERY",
            "acceptance_tests": test_rows,
        }
        self.write_private_json(private, "delivery.json", delivery_manifest)
        delivery = rr.advance_receipt(root, "DELIVERY", "receipts/acceptance.json", private, "delivery.json")
        self.assertEqual(delivery["facts"]["delivery"], "OWNER_REPORTED")
        self.assertEqual([row["kind"] for row in delivery["evidence"][1:]], [f"AT{i}" for i in range(1, 7)])
        write_json("receipts/delivery.json", delivery)

        processor_digest = self.write_private_artifact(private, "processor.json", b"private processor payload")
        processor_manifest = {
            "schema_version": "revenue-recovery-evidence/v1",
            "stage": "PROCESSOR_REFERENCE",
            "provider": "Stripe",
            "opaque_reference": "stripe:event-example",
            "payload_file": "processor.json",
            "payload_sha256": processor_digest,
        }
        self.write_private_json(private, "processor-manifest.json", processor_manifest)
        processor = rr.advance_receipt(root, "PROCESSOR_REFERENCE", "receipts/delivery.json", private, "processor-manifest.json")
        self.assertEqual(processor["state"], "REFERENCE_RECORDED")
        self.assertEqual(processor["facts"]["processor_payment"], "NOT_LANDED")
        self.assertEqual(processor["facts"]["bank_available"], "NOT_LANDED")
        self.assertEqual(processor["facts"]["collected_cash_usd"], 0)
        self.assertFalse(processor["cash_claimed"])

    def test_delivery_rejects_incomplete_acceptance_tests(self):
        temp, root, private = self.make_root()
        self.addCleanup(temp.cleanup)
        (root / "receipts").mkdir()
        prior = rr.purchase_intent_receipt(root, None)
        prior["stage"] = "ACCEPTANCE"
        prior["state"] = "ACCEPTED"
        (root / "receipts/acceptance.json").write_text(json.dumps(prior), encoding="utf-8")
        manifest = {
            "schema_version": "revenue-recovery-evidence/v1",
            "stage": "DELIVERY",
            "acceptance_tests": [],
        }
        self.write_private_json(private, "delivery.json", manifest)
        with self.assertRaisesRegex(ValueError, "AT1-AT6"):
            rr.advance_receipt(root, "DELIVERY", "receipts/acceptance.json", private, "delivery.json")

    def test_private_evidence_root_is_disjoint_and_paths_cannot_escape(self):
        temp, root, private = self.make_root()
        self.addCleanup(temp.cleanup)
        (root / "owner-private").mkdir()
        (root / "owner-private/manifest.json").write_text("{}", encoding="utf-8")
        (private / "manifest.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "outside the Commons root"):
            rr.safe_external_evidence_file(root, root / "owner-private", "manifest.json")
        with self.assertRaisesRegex(ValueError, "may not contain"):
            rr.safe_external_evidence_file(root, root.parent, "private-evidence/manifest.json")
        with self.assertRaisesRegex(ValueError, "stay inside"):
            rr.safe_external_evidence_file(root, private, "../escape.json")

    def test_private_artifact_digest_is_measured_not_trusted(self):
        temp, root, private = self.make_root(self.valid_post())
        self.addCleanup(temp.cleanup)
        (root / "receipts").mkdir()
        intent = rr.purchase_intent_receipt(root, "buyer-signal")
        (root / "receipts/intent.json").write_text(json.dumps(intent), encoding="utf-8")
        self.write_private_artifact(private, "quote.bin", b"real bytes")
        manifest = {
            "schema_version": "revenue-recovery-evidence/v1",
            "stage": "QUOTE",
            "artifact": {
                "kind": "QUOTE_ARTIFACT",
                "reference": "owner-private:quote-example",
                "file": "quote.bin",
                "sha256": "a" * 64,
            },
        }
        self.write_private_json(private, "quote.json", manifest)
        with self.assertRaisesRegex(ValueError, "does not match"):
            rr.advance_receipt(root, "QUOTE", "receipts/intent.json", private, "quote.json")


if __name__ == "__main__":
    unittest.main()
