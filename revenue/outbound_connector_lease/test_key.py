from __future__ import annotations

import contextlib
import hashlib
import io
import json
import unittest

from revenue.outbound_connector_lease.key import (
    BRANCH_PREFIX,
    REPLY_BRANCH_PREFIX,
    REPLY_SCHEMA,
    LeaseKeyError,
    _parse_json,
    compile_document,
    compile_key,
    compile_reply_key,
    main,
)


def cold():
    return {"kind": "cold"}


def external(authority="uiowa.edu", ident="1255311"):
    return {"kind": "external", "authority": authority, "id": ident}


def reply(provider="gmail", event_id="1a09b2e381d7fa0e"):
    return {"kind": "reply", "provider": provider, "event_id": event_id}


class LeaseKeyTests(unittest.TestCase):
    def test_deterministic_known_workday_external_seam_unchanged(self):
        result = compile_key("workday.com", external())
        canonical = json.dumps(
            {
                "schema": "outbound-connector-lease/v1",
                "buyer_scope": "workday.com",
                "opportunity": {"kind": "external", "authority": "uiowa.edu", "id": "1255311"},
            }, sort_keys=True, separators=(",", ":")
        ).encode("ascii")
        expected = hashlib.sha256(canonical).hexdigest()
        self.assertEqual(result["seam_sha256"], expected)
        self.assertEqual(result["branch"], BRANCH_PREFIX + expected)
        self.assertEqual(result["schema"], "outbound-connector-lease/v1")

    def test_domain_and_external_authority_normalization(self):
        a = compile_key("ExAmPle.COM.", external("Issuer.EXAMPLE.", "RFP-04254"))
        b = compile_key("example.com", external("issuer.example", "rfp-04254"))
        self.assertEqual(a, b)
        self.assertEqual(compile_key("BÜCHER.example", cold())["buyer_scope"], "xn--bcher-kva.example")

    def test_price_contact_route_cannot_enter_external_schema(self):
        base = external("lacsd.org", "04254")
        for field in ("price", "recipient", "route", "draft", "subject"):
            mutated = {**base, field: "variant"}
            with self.subTest(field=field), self.assertRaises(LeaseKeyError):
                compile_key("ghd.com", mutated)

    def test_external_id_is_stable_across_case(self):
        self.assertEqual(
            compile_key("ghd.com", external("lacsd.org", "RFP-04254")),
            compile_key("GHD.COM.", external("LACSD.ORG", "rfp-04254")),
        )

    def test_cold_scope_is_exact_and_org_level(self):
        self.assertEqual(compile_key("example.com", cold()), compile_key("EXAMPLE.COM.", {"kind": "COLD"}))
        with self.assertRaises(LeaseKeyError):
            compile_key("example.com", {"kind": "cold", "campaign": "x"})

    def test_reply_v2_binds_provider_event_only_across_buyer_aliases(self):
        direct = compile_reply_key("GMAIL", "ABC123")
        via_a = compile_key("uwo.ca", reply("gmail", "abc123"))
        via_b = compile_key("westernu.ca", reply("GMAIL", "ABC123"))
        self.assertEqual(direct, via_a)
        self.assertEqual(via_a, via_b)
        self.assertEqual(via_a["schema"], REPLY_SCHEMA)
        self.assertNotIn("buyer_scope", via_a)
        self.assertEqual(via_a["branch"], REPLY_BRANCH_PREFIX + via_a["seam_sha256"])

    def test_reply_v2_distinguishes_provider_or_event(self):
        base = compile_reply_key("gmail", "abc123")
        self.assertNotEqual(base["branch"], compile_reply_key("gmail", "abc124")["branch"])
        self.assertNotEqual(base["branch"], compile_reply_key("slack", "abc123")["branch"])

    def test_reply_schema_rejects_contact_route_and_buyer_fields(self):
        base = reply()
        for field in ("recipient", "route", "draft", "subject", "buyer_scope"):
            with self.subTest(field=field), self.assertRaises(LeaseKeyError):
                compile_key("example.com", {**base, field: "variant"})
        doc = {"schema": REPLY_SCHEMA, "provider": "gmail", "event_id": "abc123", "buyer_scope": "example.com"}
        with self.assertRaises(LeaseKeyError):
            compile_document(doc)

    def test_legacy_v1_reply_document_migrates_to_reply_v2(self):
        legacy = {
            "schema": "outbound-connector-lease/v1",
            "buyer_scope": "example.com",
            "opportunity": reply("gmail", "abc123"),
        }
        self.assertEqual(compile_document(legacy), compile_reply_key("gmail", "abc123"))

    def test_reply_v2_document_exact_fields(self):
        doc = {"schema": REPLY_SCHEMA, "provider": "gmail", "event_id": "abc123"}
        self.assertEqual(compile_document(doc), compile_reply_key("gmail", "abc123"))
        with self.assertRaises(LeaseKeyError):
            compile_document({**doc, "extra": 1})

    def test_reply_cli_does_not_accept_buyer_scope(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = main([
                "--buyer-scope", "example.com",
                "--reply-provider", "gmail",
                "--reply-event-id", "abc123",
            ])
        self.assertEqual(rc, 2)
        self.assertIn("buyer-scope is forbidden for reply mode", err.getvalue())

    def test_reply_cli_without_buyer_scope_emits_v2(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = main(["--reply-provider", "gmail", "--reply-event-id", "abc123"])
        self.assertEqual(rc, 0)
        payload = json.loads(out.getvalue())
        self.assertEqual(payload, compile_reply_key("gmail", "abc123"))

    def test_url_and_email_are_rejected_as_domains(self):
        for value in ("https://example.com", "person@example.com", "example.com/path", "localhost"):
            with self.subTest(value=value), self.assertRaises(LeaseKeyError):
                compile_key(value, cold())
        for value in ("https://issuer.example", "x@issuer.example", "issuer.example/path"):
            with self.subTest(value=value), self.assertRaises(LeaseKeyError):
                compile_key("example.com", external(value, "123"))

    def test_invalid_domain_labels_rejected(self):
        for value in ("-a.example", "a-.example", "a..example", "a_example.com"):
            with self.subTest(value=value), self.assertRaises(LeaseKeyError):
                compile_key(value, cold())

    def test_machine_ids_reject_free_text_and_price_punctuation(self):
        for value in ("", "price $5000", "human contact", "a" * 192):
            with self.subTest(value=value), self.assertRaises(LeaseKeyError):
                compile_key("example.com", external("issuer.example", value))

    def test_opportunity_kind_exact_fields(self):
        with self.assertRaises(LeaseKeyError): compile_key("example.com", {"kind": "external", "authority": "x.example"})
        with self.assertRaises(LeaseKeyError): compile_key("example.com", {"kind": "reply", "provider": "gmail"})
        with self.assertRaises(LeaseKeyError): compile_key("example.com", {"kind": "unknown"})

    def test_v1_document_schema_and_exact_fields(self):
        doc = {"schema": "outbound-connector-lease/v1", "buyer_scope": "example.com", "opportunity": cold()}
        self.assertEqual(compile_document(doc), compile_key("example.com", cold()))
        for mutation in ({**doc, "extra": 1}, {**doc, "schema": "not-a-schema"}, {"buyer_scope": "example.com", "opportunity": cold()}):
            with self.assertRaises(LeaseKeyError): compile_document(mutation)

    def test_strict_json_duplicate_and_nonfinite_rejected(self):
        with self.assertRaises(LeaseKeyError):
            _parse_json('{"schema":"outbound-connector-lease/v1","buyer_scope":"example.com","buyer_scope":"evil.com","opportunity":{"kind":"cold"}}')
        with self.assertRaises(LeaseKeyError):
            _parse_json('{"schema":"outbound-connector-lease/v1","buyer_scope":"example.com","opportunity":{"kind":"cold"},"x":NaN}')

    def test_bool_and_nonstring_rejected(self):
        for buyer, opportunity in ((True, cold()), (1, cold()), ("example.com", True), ("example.com", {"kind": True})):
            with self.assertRaises(LeaseKeyError): compile_key(buyer, opportunity)
        for provider, event_id in ((True, "abc"), ("gmail", True), ("", "abc"), ("gmail", "")):
            with self.assertRaises(LeaseKeyError): compile_reply_key(provider, event_id)


if __name__ == "__main__":
    unittest.main()