import unittest
import unc_ap_ai as m

H = "a" * 64
K = "b" * 64

def src(bound=True):
    return {
        "buyer": m.BUYER,
        "solicitation_id": m.SOLICITATION_ID,
        "first_party_url": m.FIRST_PARTY_URL,
        "status": "OPEN",
        "observed_at": "2026-09-17T21:15:00-04:00",
        "offer_due_at": "2026-09-25T12:00:00-04:00",
        "exact_current_bytes_sha256": H if bound else None,
        "addenda_complete": bound,
    }

def invoice():
    return {
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
        "integration": {
            "request_sha256": H,
            "ack_sha256": K,
            "effect_key": "invoice:INV-001",
            "retry_effect_key": "invoice:INV-001",
            "effect_count": 1,
            "retry_count": 1,
        },
        "audit_events": [
            "received", "extracted", "validated", "matched",
            "routing_started", "routing_completed", "erp_staged",
        ],
    }

def vendor():
    return {
        "name": "Example AP Partner",
        "ap_automation_evidence": "retained AP automation evidence",
        "peoplesoft_evidence": "retained PeopleSoft integration evidence",
        "route": "research-only descriptor",
        "researched_at": "2026-09-17T21:15:00-04:00",
    }

class TestCompiler(unittest.TestCase):
    def ev(self, value=None):
        return m.evaluate_invoice_case(value or invoice(), extraction_threshold_basis_points=9900)

    def test_strict_json(self):
        with self.assertRaises(m.ContractError):
            m.load_strict_json('{"a":1,"a":2}')
        with self.assertRaises(m.ContractError):
            m.load_strict_json('{"x":NaN}')

    def test_source_states(self):
        self.assertEqual(m.compile_source(src(False))["state"], "HOLD_SOURCE_BYTES")
        self.assertEqual(m.compile_source(src())["state"], "SOURCE_BOUND")
        expired = src()
        expired["observed_at"] = expired["offer_due_at"]
        self.assertEqual(m.compile_source(expired)["state"], "HOLD_DEADLINE")

    def test_pass(self):
        self.assertEqual(self.ev()["disposition"], "PASS")
        self.assertEqual(self.ev()["receipt_sha256"], self.ev()["receipt_sha256"])

    def test_hostile_cases(self):
        value = invoice()
        value["duplicate_seen"] = True
        self.assertEqual(self.ev(value)["disposition"], "HOLD_DUPLICATE")
        value = invoice()
        value["extraction_fields_correct"] = 98
        self.assertEqual(self.ev(value)["disposition"], "HOLD_EXTRACTION")
        value = invoice()
        value["extracted_supplier_id"] = "SUP-X"
        self.assertEqual(self.ev(value)["disposition"], "HOLD_SUPPLIER")
        value = invoice()
        value["extracted_amount_cents"] += 1
        self.assertEqual(self.ev(value)["disposition"], "HOLD_AMOUNT")
        value = invoice()
        value["receipt_amount_cents"] = None
        self.assertEqual(self.ev(value)["disposition"], "HOLD_MATCH")
        value = invoice()
        value["routing_signoff_present"] = False
        self.assertEqual(self.ev(value)["disposition"], "HOLD_ROUTING_SIGNOFF")
        value = invoice()
        value["integration"]["effect_count"] = 2
        self.assertEqual(self.ev(value)["disposition"], "HOLD_INTEGRATION")
        value = invoice()
        value["integration"]["retry_effect_key"] = "different"
        self.assertEqual(self.ev(value)["disposition"], "HOLD_INTEGRATION")
        value = invoice()
        value["audit_events"].remove("validated")
        self.assertEqual(self.ev(value)["disposition"], "HOLD_AUDIT")

    def test_exact_integer(self):
        value = invoice()
        value["expected_amount_cents"] = True
        with self.assertRaises(m.ContractError):
            self.ev(value)

    def test_internal_only_bundle(self):
        out = m.compile_bundle(src(), [invoice()], [vendor()])
        self.assertEqual(out["state"], "INTERNAL_WORKSHARE_READY")
        self.assertTrue(all(v is False for v in out["authority"].values()))
        self.assertFalse(out["partners"][0]["outbound_authorized"])
        held = m.compile_bundle(src(False), [invoice()], [vendor()])
        self.assertEqual(held["state"], "HOLD_SOURCE_BYTES")

if __name__ == "__main__":
    unittest.main()
