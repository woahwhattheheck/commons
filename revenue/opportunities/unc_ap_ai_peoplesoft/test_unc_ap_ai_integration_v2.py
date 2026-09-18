import unittest

import unc_ap_ai as m


def invoice():
    value = {
        "invoice_id": "INV-001",
        "supplier_id": "SUP-7",
        "extracted_supplier_id": "SUP-7",
        "expected_amount_cents": 12500,
        "extracted_amount_cents": 12500,
        "match_mode": "THREE_WAY",
        "purchase_order_amount_cents": 12500,
        "receipt_amount_cents": 12500,
        "routing_signoff_needed": True,
        "routing_signoff_present": True,
        "extraction_fields_total": 100,
        "extraction_fields_correct": 100,
        "duplicate_seen": False,
        "integration": {},
        "audit_events": [
            "received", "extracted", "validated", "matched",
            "routing_started", "routing_completed", "erp_staged",
        ],
    }
    value["integration"] = m.expected_integration_evidence(value)
    return value


class IntegrationBindingTests(unittest.TestCase):
    def ev(self, value=None):
        return m.evaluate_invoice_case(
            value or invoice(), extraction_threshold_basis_points=9900
        )

    def test_correlated_generation_passes(self):
        out = self.ev()
        self.assertEqual(out["disposition"], "PASS")
        self.assertFalse(out["provider_ack_independently_authenticated"])

    def test_effect_key_is_invoice_bound(self):
        value = invoice()
        value["integration"]["effect_key"] = "invoice:INV-999"
        self.assertEqual(self.ev(value)["disposition"], "HOLD_INTEGRATION")

    def test_request_digest_is_case_bound(self):
        value = invoice()
        value["integration"]["request_sha256"] = "a" * 64
        self.assertEqual(self.ev(value)["disposition"], "HOLD_INTEGRATION")

    def test_ack_digest_is_request_and_effect_bound(self):
        value = invoice()
        value["integration"]["ack_sha256"] = "b" * 64
        self.assertEqual(self.ev(value)["disposition"], "HOLD_INTEGRATION")

    def test_retry_and_effect_count_are_checked(self):
        value = invoice()
        value["integration"]["retry_effect_key"] = "invoice:OTHER"
        self.assertEqual(self.ev(value)["disposition"], "HOLD_INTEGRATION")
        value = invoice()
        value["integration"]["effect_count"] = 2
        self.assertEqual(self.ev(value)["disposition"], "HOLD_INTEGRATION")

    def test_business_holds_remain(self):
        cases = [
            ("duplicate_seen", True, "HOLD_DUPLICATE"),
            ("extraction_fields_correct", 98, "HOLD_EXTRACTION"),
            ("extracted_supplier_id", "SUP-X", "HOLD_SUPPLIER"),
            ("extracted_amount_cents", 12501, "HOLD_AMOUNT"),
            ("receipt_amount_cents", None, "HOLD_MATCH"),
            ("routing_signoff_present", False, "HOLD_ROUTING_SIGNOFF"),
        ]
        for field, bad, expected in cases:
            value = invoice()
            value[field] = bad
            value["integration"] = m.expected_integration_evidence(value)
            with self.subTest(field=field):
                self.assertEqual(self.ev(value)["disposition"], expected)

    def test_bool_does_not_alias_money_integer(self):
        value = invoice()
        value["expected_amount_cents"] = True
        with self.assertRaises(m.ContractError):
            self.ev(value)


if __name__ == "__main__":
    unittest.main()
