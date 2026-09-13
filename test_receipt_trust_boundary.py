import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from revenue.receipt_trust_boundary import (
    CONTRACT_SCHEMA,
    TrustError,
    attach_integrity_digest,
    bind_external_commitment,
    canonical_bytes,
    inspect_receipt,
    load_json_bytes,
    sha256_value,
    validate_contract_shape,
    verify_contract,
)
from revenue.receipt_trust_boundary.cli import main


def honest_receipt():
    return attach_integrity_digest({
        "product": "COMMERCIAL_ACCEPTANCE_BRIDGE",
        "schema_version": 1,
        "state": "HUMAN_CLOSING_READY",
        "authorities": {
            "recognized_revenue": False,
            "payment_or_charge": False,
        },
    })


def forged_paid_receipt():
    # This is the exact failure class the package must classify as integrity-only:
    # the fabricator controls both the semantics and the recomputed self-digest.
    return attach_integrity_digest({
        "product": "NOT_THE_BRIDGE",
        "schema_version": 999,
        "state": "PAID",
        "authorities": {
            "recognized_revenue": True,
            "payment_or_charge": True,
        },
    })


def contract():
    return {
        "schema": CONTRACT_SCHEMA,
        "contract_id": "commercial-acceptance-evidence-only-demo/v1",
        "required_top_level_keys": [
            "authorities", "product", "receipt_sha256", "schema_version", "state"
        ],
        "allowed_top_level_keys": [
            "authorities", "product", "receipt_sha256", "schema_version", "state"
        ],
        "rules": [
            {"path": ["product"], "op": "equals", "value": "COMMERCIAL_ACCEPTANCE_BRIDGE"},
            {"path": ["schema_version"], "op": "equals", "value": 1},
            {"path": ["state"], "op": "in", "values": ["NO_CURRENT_ACCEPTANCE", "HUMAN_CLOSING_READY"]},
            {"path": ["authorities", "recognized_revenue"], "op": "equals", "value": False},
            {"path": ["authorities", "payment_or_charge"], "op": "equals", "value": False},
        ],
    }


class ReceiptTrustTests(unittest.TestCase):
    def test_honest_self_digest_is_integrity_only(self):
        result = inspect_receipt(honest_receipt())
        self.assertEqual(result["status"], "INTEGRITY_ONLY")
        self.assertTrue(result["self_digest_matches"])
        self.assertFalse(result["external_commitment_verified"])
        self.assertFalse(result["source_authenticity_verified"])
        self.assertFalse(result["buyer_acceptance_verified"])
        self.assertFalse(result["recognized_revenue_verified"])

    def test_forged_paid_self_digest_never_becomes_authority(self):
        result = inspect_receipt(forged_paid_receipt())
        self.assertEqual(result["status"], "INTEGRITY_ONLY")
        self.assertTrue(result["self_digest_matches"])
        self.assertFalse(result["payment_verified"])
        self.assertFalse(result["recognized_revenue_verified"])
        self.assertFalse(result["source_authenticity_verified"])

    def test_self_digest_tamper_without_rehash_is_detected(self):
        receipt = honest_receipt()
        receipt["state"] = "PAID"
        result = inspect_receipt(receipt)
        self.assertEqual(result["status"], "INTEGRITY_UNPROVEN")
        self.assertFalse(result["self_digest_matches"])

    def test_full_rehash_forgery_fails_old_external_commitment(self):
        original = honest_receipt()
        frozen = original["receipt_sha256"]
        forged = copy.deepcopy(original)
        forged["state"] = "PAID"
        forged["authorities"]["recognized_revenue"] = True
        forged = attach_integrity_digest(forged)
        self.assertTrue(inspect_receipt(forged)["self_digest_matches"])
        with self.assertRaisesRegex(TrustError, "external receipt commitment mismatch"):
            bind_external_commitment(forged, frozen)

    def test_matching_external_commitment_is_named_commitment_bound_only(self):
        receipt = honest_receipt()
        result = bind_external_commitment(receipt, receipt["receipt_sha256"])
        self.assertEqual(result["status"], "EXTERNAL_COMMITMENT_BOUND")
        self.assertTrue(result["external_commitment_verified"])
        self.assertTrue(result["trust_root_supplied_by_caller"])
        self.assertFalse(result["semantic_contract_verified"])
        self.assertFalse(result["source_authenticity_verified"])
        self.assertFalse(result["buyer_acceptance_verified"])

    def test_malformed_external_commitment_is_rejected(self):
        with self.assertRaisesRegex(TrustError, "lowercase SHA-256"):
            bind_external_commitment(honest_receipt(), "ABC")

    def test_contract_bound_success_remains_non_authorizing(self):
        receipt = honest_receipt()
        rules = contract()
        expected_contract = sha256_value(validate_contract_shape(rules))
        result = verify_contract(
            receipt, receipt["receipt_sha256"], rules, expected_contract
        )
        self.assertEqual(result["status"], "EXTERNAL_COMMITMENT_AND_CONTRACT_BOUND")
        self.assertTrue(result["external_commitment_verified"])
        self.assertTrue(result["semantic_contract_verified"])
        self.assertTrue(result["external_contract_commitment_verified"])
        self.assertFalse(result["source_authenticity_verified"])
        self.assertFalse(result["buyer_acceptance_verified"])
        self.assertFalse(result["contract_execution_verified"])
        self.assertFalse(result["payment_verified"])
        self.assertFalse(result["recognized_revenue_verified"])

    def test_forged_paid_fails_honest_contract_even_with_its_own_receipt_commitment(self):
        receipt = forged_paid_receipt()
        rules = contract()
        expected_contract = sha256_value(validate_contract_shape(rules))
        with self.assertRaisesRegex(TrustError, "contract rule 0 failed"):
            verify_contract(receipt, receipt["receipt_sha256"], rules, expected_contract)

    def test_forged_contract_fails_frozen_contract_commitment(self):
        receipt = honest_receipt()
        rules = contract()
        frozen = sha256_value(validate_contract_shape(rules))
        forged = copy.deepcopy(rules)
        forged["rules"][3]["value"] = True
        with self.assertRaisesRegex(TrustError, "external contract commitment mismatch"):
            verify_contract(receipt, receipt["receipt_sha256"], forged, frozen)

    def test_unknown_receipt_top_level_key_fails_contract(self):
        receipt = honest_receipt()
        receipt["surprise"] = "smuggled"
        receipt = attach_integrity_digest(receipt)
        rules = contract()
        with self.assertRaisesRegex(TrustError, "contract-unknown keys"):
            verify_contract(
                receipt,
                receipt["receipt_sha256"],
                rules,
                sha256_value(validate_contract_shape(rules)),
            )

    def test_missing_required_receipt_key_fails_contract(self):
        receipt = honest_receipt()
        receipt.pop("authorities")
        receipt = attach_integrity_digest(receipt)
        rules = contract()
        with self.assertRaisesRegex(TrustError, "missing contract keys"):
            verify_contract(
                receipt,
                receipt["receipt_sha256"],
                rules,
                sha256_value(validate_contract_shape(rules)),
            )

    def test_missing_nested_path_fails_contract(self):
        receipt = honest_receipt()
        del receipt["authorities"]["payment_or_charge"]
        receipt = attach_integrity_digest(receipt)
        rules = contract()
        with self.assertRaisesRegex(TrustError, "contract path missing"):
            verify_contract(
                receipt,
                receipt["receipt_sha256"],
                rules,
                sha256_value(validate_contract_shape(rules)),
            )

    def test_bool_does_not_alias_integer_rule(self):
        receipt = honest_receipt()
        receipt["schema_version"] = True
        receipt = attach_integrity_digest(receipt)
        rules = contract()
        with self.assertRaisesRegex(TrustError, "contract rule 1 failed"):
            verify_contract(
                receipt,
                receipt["receipt_sha256"],
                rules,
                sha256_value(validate_contract_shape(rules)),
            )

    def test_integer_does_not_alias_float_rule(self):
        receipt = honest_receipt()
        rules = contract()
        rules["rules"][1]["value"] = 1.0
        expected = sha256_value(validate_contract_shape(rules))
        with self.assertRaisesRegex(TrustError, "contract rule 1 failed"):
            verify_contract(receipt, receipt["receipt_sha256"], rules, expected)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(TrustError, "duplicate JSON key"):
            load_json_bytes(b'{"state":"A","state":"B"}')

    def test_nonfinite_json_numbers_rejected(self):
        for raw in (b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e9999}'):
            with self.subTest(raw=raw):
                with self.assertRaises(TrustError):
                    load_json_bytes(raw)

    def test_contract_shape_rejects_unsupported_operation(self):
        rules = contract()
        rules["rules"][0]["op"] = "regex"
        with self.assertRaisesRegex(TrustError, "unsupported"):
            validate_contract_shape(rules)

    def test_contract_shape_requires_receipt_digest_key(self):
        rules = contract()
        rules["allowed_top_level_keys"].remove("receipt_sha256")
        rules["required_top_level_keys"].remove("receipt_sha256")
        with self.assertRaisesRegex(TrustError, "must include receipt_sha256"):
            validate_contract_shape(rules)

    def test_contract_value_set_rejects_typed_duplicates_only(self):
        rules = contract()
        rules["rules"][2]["values"] = [1, 1]
        with self.assertRaisesRegex(TrustError, "contains duplicates"):
            validate_contract_shape(rules)
        rules["rules"][2]["values"] = [1, 1.0, True]
        normalized = validate_contract_shape(rules)
        self.assertEqual(normalized["rules"][2]["values"], [1, 1.0, True])

    def test_contract_hash_is_order_invariant(self):
        rules = contract()
        reversed_rules = dict(reversed(list(rules.items())))
        self.assertEqual(
            sha256_value(validate_contract_shape(rules)),
            sha256_value(validate_contract_shape(reversed_rules)),
        )

    def test_receipt_self_digest_is_key_order_invariant(self):
        receipt = honest_receipt()
        reversed_receipt = dict(reversed(list(receipt.items())))
        self.assertEqual(receipt["receipt_sha256"], inspect_receipt(reversed_receipt)["receipt_sha256"])
        self.assertTrue(inspect_receipt(reversed_receipt)["self_digest_matches"])

    def test_cli_rejects_symlinked_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            real = base / "receipt.json"
            link = base / "receipt-link.json"
            real.write_bytes(canonical_bytes(honest_receipt()))
            link.symlink_to(real)
            self.assertEqual(main(["inspect", str(link)]), 2)

    def test_cli_inspect_forgery_says_integrity_only(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "forged.json"
            path.write_bytes(canonical_bytes(forged_paid_receipt()))
            rfd, wfd = os.pipe()
            saved = os.dup(1)
            try:
                os.dup2(wfd, 1)
                os.close(wfd)
                rc = main(["inspect", str(path)])
                os.dup2(saved, 1)
                raw = os.read(rfd, 100000)
            finally:
                try:
                    os.dup2(saved, 1)
                except OSError:
                    pass
                os.close(saved)
                os.close(rfd)
            self.assertEqual(rc, 0)
            result = json.loads(raw)
            self.assertEqual(result["status"], "INTEGRITY_ONLY")
            self.assertFalse(result["recognized_revenue_verified"])

    def test_cli_verify_honest_contract(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            receipt = honest_receipt()
            rules = contract()
            receipt_path = base / "receipt.json"
            contract_path = base / "contract.json"
            receipt_path.write_bytes(canonical_bytes(receipt))
            contract_path.write_bytes(canonical_bytes(rules))
            rc = main([
                "verify",
                str(receipt_path),
                "--expected-receipt-sha256", receipt["receipt_sha256"],
                "--contract", str(contract_path),
                "--expected-contract-sha256", sha256_value(validate_contract_shape(rules)),
            ])
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
