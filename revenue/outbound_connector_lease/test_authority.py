from __future__ import annotations

import copy
import json
import unittest

from revenue.outbound_connector_lease.authority import (
    STATE,
    SeamAuthorityError,
    admit_compiled_seam,
    admit_json,
)
from revenue.outbound_connector_lease.key import LeaseKeyError, compile_key
from revenue.outbound_mutex.lease import lead_key as legacy_lead_key


def cold(scope: str = "example.com"):
    return compile_key(scope, {"kind": "cold"})


def external(scope: str = "prime.example", authority: str = "issuer.example", ident: str = "rfp-04254"):
    return compile_key(
        scope,
        {"kind": "external", "authority": authority, "id": ident},
    )


def legacy(opportunity: str = "Acme / $199 diagnostic"):
    return {
        "version": 1,
        "key": legacy_lead_key(
            opportunity=opportunity,
            channel="email",
            destination="buyer@example.com",
        ),
        "opportunity": opportunity,
        "channel": "email",
        "destination_sha256": "0" * 64,
        "holder": "Z-Test",
        "state": "active",
        "acquired_at": "2026-09-14T03:00:00Z",
        "expires_at": "2026-09-14T03:30:00Z",
        "provider_snapshot": "1" * 64,
        "generation": 1,
        "released_at": None,
        "release_reason": None,
        "sent_at": None,
        "send_receipt_sha256": None,
    }


class CanonicalSeamAuthorityTests(unittest.TestCase):
    def test_canonical_cold_seam_is_admitted_but_never_send_authority(self):
        receipt = admit_compiled_seam(cold())
        self.assertEqual(receipt["state"], STATE)
        self.assertFalse(receipt["external_send_authorized"])
        self.assertFalse(receipt["legacy_mutex_accepted"])
        self.assertTrue(receipt["atomic_branch_create_required"])
        self.assertTrue(receipt["provider_reread_required"])

    def test_canonical_external_seam_round_trips(self):
        candidate = external()
        receipt = admit_json(json.dumps(candidate, sort_keys=True))
        self.assertEqual(receipt["branch"], candidate["branch"])
        self.assertEqual(receipt["seam_sha256"], candidate["seam_sha256"])

    def test_same_org_cold_outreach_cannot_split_by_recipient_or_offer(self):
        # Recipient/price/draft do not exist in the schema at all.  Every cold
        # outreach attempt for this organization compiles to the same seam.
        first = cold("Example.COM.")
        second = cold("example.com")
        self.assertEqual(first, second)
        for field in ("recipient", "price", "route", "draft", "subject", "campaign"):
            with self.subTest(field=field), self.assertRaises(LeaseKeyError):
                compile_key("example.com", {"kind": "cold", field: "alias"})

    def test_external_contact_price_route_aliases_have_no_schema_slot(self):
        baseline = external()
        for field in ("recipient", "price", "route", "draft", "subject"):
            mutated = {
                "kind": "external",
                "authority": "issuer.example",
                "id": "rfp-04254",
                field: "variant",
            }
            with self.subTest(field=field), self.assertRaises(LeaseKeyError):
                compile_key("prime.example", mutated)
        self.assertEqual(baseline, external("PRIME.EXAMPLE.", "ISSUER.EXAMPLE.", "RFP-04254"))

    def test_legacy_free_form_aliases_reproduce_parallel_key_bug(self):
        a = legacy_lead_key(
            opportunity="SigNoz / $2,500 survival proof",
            channel="email",
            destination="dev@signoz.io",
        )
        b = legacy_lead_key(
            opportunity="signoz agent reliability pilot",
            channel="email",
            destination="dev@signoz.io",
        )
        self.assertNotEqual(a, b)

    def test_legacy_active_document_is_rejected(self):
        with self.assertRaisesRegex(SeamAuthorityError, "legacy revenue/outbound_mutex"):
            admit_compiled_seam(legacy())

    def test_legacy_sent_document_is_still_rejected_as_production_seam(self):
        candidate = legacy()
        candidate.update(
            state="sent",
            sent_at="2026-09-14T03:10:00Z",
            send_receipt_sha256="2" * 64,
        )
        with self.assertRaisesRegex(SeamAuthorityError, "non-authoritative"):
            admit_compiled_seam(candidate)

    def test_tampered_branch_is_rejected(self):
        candidate = cold()
        candidate["branch"] += "-alias"
        with self.assertRaisesRegex(SeamAuthorityError, "canonical recomputation"):
            admit_compiled_seam(candidate)

    def test_tampered_digest_is_rejected(self):
        candidate = cold()
        candidate["seam_sha256"] = "0" * 64
        with self.assertRaisesRegex(SeamAuthorityError, "canonical recomputation"):
            admit_compiled_seam(candidate)

    def test_extra_compiled_field_is_rejected(self):
        candidate = {**cold(), "recipient": "buyer@example.com"}
        with self.assertRaisesRegex(SeamAuthorityError, "exact schema"):
            admit_compiled_seam(candidate)

    def test_schema_downgrade_is_rejected(self):
        candidate = cold()
        candidate["schema"] = "outbound-mutex/v1"
        with self.assertRaisesRegex(SeamAuthorityError, "schema must"):
            admit_compiled_seam(candidate)

    def test_duplicate_json_key_is_rejected(self):
        good = cold()
        raw = (
            '{"schema":"outbound-connector-lease/v1",'
            '"schema":"outbound-mutex/v1",'
            f'"buyer_scope":{json.dumps(good["buyer_scope"])},'
            f'"opportunity":{json.dumps(good["opportunity"])},'
            f'"seam_sha256":{json.dumps(good["seam_sha256"])},'
            f'"branch":{json.dumps(good["branch"])}' + "}"
        )
        with self.assertRaises(SeamAuthorityError):
            admit_json(raw)

    def test_plain_dict_only(self):
        class Sneaky(dict):
            pass

        with self.assertRaisesRegex(SeamAuthorityError, "plain JSON object"):
            admit_compiled_seam(Sneaky(cold()))


if __name__ == "__main__":
    unittest.main()
