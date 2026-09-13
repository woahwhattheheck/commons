from __future__ import annotations

import copy
import unittest

from . import BridgeError, build_scope_bridge, verify_scope_bridge
from .fixtures import (
    NOW, ONE, OWNER_KEY, VERIFY_KEY, agreement_validator, bundle, canonical, catalog, contract,
    contract_verifier, digest, schedule, verification,
)


class BridgeTests(unittest.TestCase):
    def bad(self, fn, *args, **kwargs):
        with self.assertRaises(BridgeError):
            fn(*args, **kwargs)

    def test_happy_bridge_and_roundtrip(self):
        c = contract(); receipt = verification(c); out = bundle(c, receipt)
        self.assertEqual(out["bridge_receipt"]["state"], "SCOPE_AGREEMENT_READY")
        self.assertEqual(out["agreement"]["window"], {key: schedule()[key] for key in ("start", "end", "timezone")})
        self.assertEqual(out["agreement"]["written_acceptance"]["accepted_at"], schedule()["accepted_at"])
        self.assertIn(c["offer_sha256"], out["agreement"]["intake_sentence"])
        self.assertIn(ONE, out["agreement"]["acceptance_rows"][0]["given"])
        self.assertFalse(out["bridge_receipt"]["authority"]["payment_collected"])
        self.assertEqual(verify_scope_bridge(
            out, c, OWNER_KEY, VERIFY_KEY, catalog=catalog(), trusted_now=NOW,
            contract_verifier=contract_verifier, agreement_validator=agreement_validator,
        ), out)

    def test_deterministic(self):
        self.assertEqual(canonical(bundle()), canonical(bundle()))

    def test_buyer_ref_is_opaque_derivative(self):
        out = bundle(); self.assertNotEqual(out["agreement"]["buyer_ref"], contract()["offer"]["buyer_ref"])
        self.assertRegex(out["agreement"]["buyer_ref"], r"^buyer_[0-9a-f]{64}$")

    def test_opportunity_must_already_be_catalog_sku(self):
        c = contract(); c["offer"]["opportunity_id"] = "not-a-catalog-sku"; c["offer_sha256"] = digest(c["offer"]); c["buyer_acceptance"]["offer_sha256"] = c["offer_sha256"]
        self.bad(bundle, c, verification(c))

    def test_catalog_price_drift(self):
        self.bad(bundle, cat=catalog("14999.99"))

    def test_catalog_currency_drift(self):
        self.bad(bundle, cat=catalog("15000.00", "EUR"))

    def test_duplicate_catalog_sku(self):
        cat = catalog(); cat["listings"].append(copy.deepcopy(cat["listings"][0])); self.bad(bundle, cat=cat)

    def test_malformed_deliverable_evidence(self):
        c = contract(); c["offer"]["deliverables"][0]["evidence_sha256"] = "nope"; self.bad(bundle, c, verification(c))

    def test_validator_mutation(self):
        def mutating(value, _catalog):
            value = copy.deepcopy(value); value["refund_choice"] = "REFUND_IF_MISS"; return value
        c = contract(); receipt = verification(c)
        self.bad(build_scope_bridge, c, receipt, OWNER_KEY, VERIFY_KEY, catalog=catalog(), trusted_now=NOW, contract_verifier=contract_verifier, agreement_validator=mutating)

    def test_bridge_receipt_tamper(self):
        c = contract(); out = bundle(c); out["bridge_receipt"]["sku_id"] = "gguf-diagnostic-10d-12k"
        self.bad(verify_scope_bridge, out, c, OWNER_KEY, VERIFY_KEY, catalog=catalog(), trusted_now=NOW, contract_verifier=contract_verifier, agreement_validator=agreement_validator)

    def test_bridge_authority_escalation(self):
        c = contract(); out = bundle(c); out["bridge_receipt"]["authority"]["revenue_recognized"] = True
        core = {key: value for key, value in out["bridge_receipt"].items() if key != "bridge_sha256"}; out["bridge_receipt"]["bridge_sha256"] = digest(core)
        self.bad(verify_scope_bridge, out, c, OWNER_KEY, VERIFY_KEY, catalog=catalog(), trusted_now=NOW, contract_verifier=contract_verifier, agreement_validator=agreement_validator)

    def test_agreement_tamper(self):
        c = contract(); out = bundle(c); out["agreement"]["quote"]["amount"] = "1.00"
        self.bad(verify_scope_bridge, out, c, OWNER_KEY, VERIFY_KEY, catalog=catalog(), trusted_now=NOW, contract_verifier=contract_verifier, agreement_validator=agreement_validator)


if __name__ == "__main__":
    unittest.main()
