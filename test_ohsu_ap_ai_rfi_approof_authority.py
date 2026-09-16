from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

import revenue.ohsu_ap_ai_rfi_approof.approof as public_api
import revenue.ohsu_ap_ai_rfi_approof.authority_api as authority_api
import revenue.ohsu_ap_ai_rfi_approof.common as common_module
import revenue.ohsu_ap_ai_rfi_approof.engine as engine_module

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "revenue" / "ohsu_ap_ai_rfi_approof" / "fixture.json"
AUTHORITY_MODULES = (public_api, authority_api, common_module, engine_module)


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class APProofAuthorityBoundaryTests(unittest.TestCase):
    def assert_hard_false(self, projection):
        self.assertTrue(projection["authority"])
        self.assertTrue(all(value is False for value in projection["authority"].values()))
        for row in projection["oracle_shadow_rows"]:
            self.assertIs(row["posting_authorized"], False)
            self.assertEqual(row["mode"], "SHADOW_ONLY")
            self.assertIsNone(row["oracle_ebs_transaction_id"])

    def test_every_importable_authority_view_is_immutable(self):
        for module in AUTHORITY_MODULES:
            with self.subTest(module=module.__name__):
                with self.assertRaises(TypeError):
                    module.AUTHORITY["payment_authorized"] = True

    def test_rebinding_every_authority_name_cannot_promote_effects(self):
        packet = load_fixture()
        originals = [(module, module.AUTHORITY) for module in AUTHORITY_MODULES]
        malicious = {
            "oracle_ebs_write_authorized": True,
            "invoice_approval_authorized": True,
            "payment_authorized": True,
            "supplier_contact_authorized": True,
            "buyer_submission_authorized": True,
            "contract_award_claimed": True,
            "revenue_claimed": True,
        }
        try:
            for module, _ in originals:
                module.AUTHORITY = dict(malicious)

            # Both advertised and importable engine entrypoints are sealed to
            # the same code-owned all-false authority generation.
            public_projection = public_api.compile_packet(packet)
            engine_projection = engine_module.compile_packet(packet)
            authority_projection = authority_api.compile_packet(packet)
            for projection in (
                public_projection,
                engine_projection,
                authority_projection,
            ):
                self.assert_hard_false(projection)
                self.assertEqual(projection, public_projection)

            self.assertTrue(public_api.verify_projection(packet, public_projection))
            self.assertTrue(engine_module.verify_projection(packet, public_projection))
            self.assertTrue(authority_api.verify_projection(packet, public_projection))

            promoted = copy.deepcopy(public_projection)
            for key in promoted["authority"]:
                promoted["authority"][key] = True
            for row in promoted["oracle_shadow_rows"]:
                row["posting_authorized"] = True
            self.assertFalse(public_api.verify_projection(packet, promoted))
            self.assertFalse(engine_module.verify_projection(packet, promoted))
            self.assertFalse(authority_api.verify_projection(packet, promoted))
        finally:
            for module, original in originals:
                module.AUTHORITY = original

    def test_public_authority_replacement_does_not_change_projection_digest(self):
        packet = load_fixture()
        before = public_api.compile_packet(packet)
        original = public_api.AUTHORITY
        try:
            public_api.AUTHORITY = {"payment_authorized": True}
            after = public_api.compile_packet(packet)
        finally:
            public_api.AUTHORITY = original
        self.assertEqual(before["projection_sha256"], after["projection_sha256"])
        self.assertEqual(before, after)
        self.assert_hard_false(after)


if __name__ == "__main__":
    unittest.main()
