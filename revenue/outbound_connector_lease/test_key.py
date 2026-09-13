from __future__ import annotations

import hashlib
import json
import unittest

from revenue.outbound_connector_lease.key import (
    BRANCH_PREFIX,
    LeaseKeyError,
    _parse_json,
    compile_document,
    compile_key,
)


class LeaseKeyTests(unittest.TestCase):
    def test_deterministic_known_workday_seam(self):
        result = compile_key("workday.com", "uw-rfi-1255311")
        canonical = json.dumps(
            {
                "schema": "outbound-connector-lease/v1",
                "buyer_scope": "workday.com",
                "opportunity_scope": "uw-rfi-1255311",
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("ascii")
        expected = hashlib.sha256(canonical).hexdigest()
        self.assertEqual(result["seam_sha256"], expected)
        self.assertEqual(result["branch"], BRANCH_PREFIX + expected)

    def test_domain_normalization_is_case_trailing_dot_and_idna_stable(self):
        a = compile_key("ExAmPle.COM.", "cold")
        b = compile_key("example.com", "COLD")
        self.assertEqual(a, b)
        self.assertEqual(compile_key("BÜCHER.example", "cold")["buyer_scope"], "xn--bcher-kva.example")

    def test_opportunity_price_or_contact_is_not_implicitly_added(self):
        base = compile_key("example.com", "rfp-04254")
        self.assertEqual(base, compile_key("example.com", "RFP-04254"))
        self.assertNotEqual(base, compile_key("example.com", "rfp-04254-7500"))
        # The helper cannot infer semantic aliases; the skill forbids price/contact/version tokens.

    def test_cold_scope_is_one_org_level_seam(self):
        a = compile_key("example.com", "cold")
        b = compile_key("EXAMPLE.COM.", "COLD")
        self.assertEqual(a["branch"], b["branch"])

    def test_url_and_email_are_rejected_as_buyer_scope(self):
        for value in ("https://example.com", "person@example.com", "example.com/path", "localhost"):
            with self.subTest(value=value), self.assertRaises(LeaseKeyError):
                compile_key(value, "cold")

    def test_invalid_domain_labels_rejected(self):
        for value in ("-a.example", "a-.example", "a..example", "a_example.com"):
            with self.subTest(value=value), self.assertRaises(LeaseKeyError):
                compile_key(value, "cold")

    def test_opportunity_requires_machine_token(self):
        for value in ("", "price $5000", "human contact", "a" * 192):
            with self.subTest(value=value), self.assertRaises(LeaseKeyError):
                compile_key("example.com", value)

    def test_document_schema_and_exact_fields(self):
        doc = {
            "schema": "outbound-connector-lease/v1",
            "buyer_scope": "example.com",
            "opportunity_scope": "cold",
        }
        self.assertEqual(compile_document(doc), compile_key("example.com", "cold"))
        for mutation in (
            {**doc, "extra": 1},
            {**doc, "schema": "v2"},
            {"buyer_scope": "example.com", "opportunity_scope": "cold"},
        ):
            with self.assertRaises(LeaseKeyError):
                compile_document(mutation)

    def test_strict_json_duplicate_and_nonfinite_rejected(self):
        with self.assertRaises(LeaseKeyError):
            _parse_json('{"schema":"outbound-connector-lease/v1","buyer_scope":"example.com","buyer_scope":"evil.com","opportunity_scope":"cold"}')
        with self.assertRaises(LeaseKeyError):
            _parse_json('{"schema":"outbound-connector-lease/v1","buyer_scope":"example.com","opportunity_scope":"cold","x":NaN}')

    def test_bool_and_nonstring_rejected(self):
        for buyer, opportunity in ((True, "cold"), ("example.com", True), (1, "cold"), ("example.com", 1)):
            with self.assertRaises(LeaseKeyError):
                compile_key(buyer, opportunity)


if __name__ == "__main__":
    unittest.main()
