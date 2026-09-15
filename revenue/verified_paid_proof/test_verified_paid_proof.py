import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
from revenue.verified_paid_proof.verified_paid_proof import ProofError, compile_proof, strict_json_loads


def permission(granted=False, *refs):
    return {"granted": granted, "evidence_refs": list(refs)}


def base_record():
    return {
        "schema_version": 1,
        "engagement_id": "eng.synthetic.001",
        "customer": {"display_name": "Synthetic Buyer", "logo_ref": "evidence:logo:1"},
        "payment": {
            "status": "SETTLED",
            "amount_minor": 9000,
            "currency": "USD",
            "currency_decimals": 2,
            "settled_at": "2026-09-14T18:00:00-04:00",
            "evidence_refs": ["stripe:pi_synthetic_1"],
        },
        "delivery": {
            "status": "ACCEPTED",
            "accepted_at": "2026-09-14T18:30:00-04:00",
            "evidence_refs": ["email:synthetic-acceptance-1"],
        },
        "quote": {"text": "The bounded artifact met the requested acceptance checks.", "evidence_ref": "email:synthetic-quote-1"},
        "outcomes": [
            {
                "claim": "Buyer confirmed the requested acceptance checks passed.",
                "evidence_refs": ["email:synthetic-acceptance-1"],
                "publication_permission": permission(False),
            }
        ],
        "permissions": {
            "public_proof": permission(False),
            "payment_fact": permission(False),
            "customer_identity": permission(False),
            "logo": permission(False),
            "exact_amount": permission(False),
            "delivery_acceptance": permission(False),
            "quote": permission(False),
        },
        "revocation": {"revoked": False, "evidence_refs": []},
    }


class PaidProofTests(unittest.TestCase):
    def test_payment_only_never_implies_satisfaction(self):
        record = base_record()
        record["delivery"] = {"status": "NOT_DELIVERED", "accepted_at": None, "evidence_refs": []}
        record["quote"] = {"text": None, "evidence_ref": None}
        record["outcomes"] = []
        proof = compile_proof(record).proof
        self.assertEqual(proof["status"], "PRIVATE_VERIFIED")
        rendered = json.dumps(proof).lower()
        self.assertNotIn("satisfied", rendered)
        self.assertNotIn("recommend", rendered)

    def test_accepted_delivery_no_public_permission_stays_private(self):
        proof = compile_proof(base_record()).proof
        self.assertEqual(proof["status"], "PRIVATE_VERIFIED")
        self.assertIsNone(proof["public_projection"]["delivery_accepted"])

    def test_public_anonymous_withholds_identity_amount_quote_logo(self):
        record = base_record()
        record["permissions"]["public_proof"] = permission(True, "email:permission:public")
        record["permissions"]["payment_fact"] = permission(True, "email:permission:payment")
        proof = compile_proof(record).proof
        self.assertEqual(proof["status"], "PUBLIC_ANONYMOUS")
        projection = proof["public_projection"]
        self.assertTrue(projection["customer"].startswith("anonymous-customer-"))
        self.assertIsNone(projection["exact_amount"])
        self.assertIsNone(projection["quote"])
        self.assertIsNone(projection["logo_ref"])
        public_blob = json.dumps(projection)
        self.assertNotIn("Synthetic Buyer", public_blob)
        self.assertNotIn(record["engagement_id"], public_blob)
        self.assertTrue(projection["proof_id"].startswith("proof-"))

    def test_public_named_requires_independent_scopes(self):
        record = base_record()
        for scope in ("public_proof", "payment_fact", "customer_identity", "logo", "exact_amount", "delivery_acceptance", "quote"):
            record["permissions"][scope] = permission(True, f"email:permission:{scope}")
        record["outcomes"][0]["publication_permission"] = permission(True, "email:permission:outcome")
        compiled = compile_proof(record)
        self.assertEqual(compiled.proof["status"], "PUBLIC_NAMED")
        projection = compiled.proof["public_projection"]
        self.assertEqual(projection["customer"], "Synthetic Buyer")
        self.assertEqual(projection["exact_amount"], "USD 90.00")
        self.assertTrue(projection["delivery_accepted"])
        self.assertEqual(projection["quote"], record["quote"]["text"])
        self.assertEqual(len(projection["outcomes"]), 1)

    def test_quote_requires_source_pair(self):
        record = base_record()
        record["quote"]["evidence_ref"] = None
        with self.assertRaises(ProofError):
            compile_proof(record)

    def test_granted_quote_permission_requires_quote(self):
        record = base_record()
        record["quote"] = {"text": None, "evidence_ref": None}
        record["permissions"]["quote"] = permission(True, "email:permission:quote")
        with self.assertRaises(ProofError):
            compile_proof(record)

    def test_outcome_requires_evidence(self):
        record = base_record()
        record["outcomes"][0]["evidence_refs"] = []
        with self.assertRaises(ProofError):
            compile_proof(record)

    def test_outcome_without_permission_is_withheld(self):
        record = base_record()
        record["permissions"]["public_proof"] = permission(True, "email:permission:public")
        record["permissions"]["payment_fact"] = permission(True, "email:permission:payment")
        proof = compile_proof(record).proof
        self.assertEqual(proof["public_projection"]["outcomes"], [])
        self.assertTrue(any(item.startswith("outcome:") for item in proof["withheld"]))

    def test_revocation_forces_hold(self):
        record = base_record()
        record["permissions"]["public_proof"] = permission(True, "email:permission:public")
        record["permissions"]["payment_fact"] = permission(True, "email:permission:payment")
        record["revocation"] = {"revoked": True, "evidence_refs": ["email:revocation:1"]}
        proof = compile_proof(record).proof
        self.assertEqual(proof["status"], "HOLD")
        self.assertIn("publication_permission_revoked", proof["blockers"])

    def test_bool_is_not_integer_amount(self):
        record = base_record()
        record["payment"]["amount_minor"] = True
        with self.assertRaises(ProofError):
            compile_proof(record)

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ProofError):
            strict_json_loads('{"schema_version":1,"schema_version":1}')

    def test_float_money_rejected(self):
        text = json.dumps(base_record()).replace('"amount_minor": 9000', '"amount_minor": 90.0')
        with self.assertRaises(ProofError):
            strict_json_loads(text)

    def test_negative_money_rejected(self):
        record = base_record()
        record["payment"]["amount_minor"] = -1
        with self.assertRaises(ProofError):
            compile_proof(record)

    def test_non_settled_cannot_smuggle_amount(self):
        record = base_record()
        record["payment"]["status"] = "PENDING"
        with self.assertRaises(ProofError):
            compile_proof(record)

    def test_permission_true_requires_evidence(self):
        record = base_record()
        record["permissions"]["public_proof"] = permission(True)
        with self.assertRaises(ProofError):
            compile_proof(record)

    def test_irrelevant_input_order_is_deterministic(self):
        a = base_record()
        a["payment"]["evidence_refs"] = ["stripe:z", "stripe:a"]
        a["outcomes"].append({
            "claim": "A second synthetic verified fact.",
            "evidence_refs": ["evidence:z", "evidence:a"],
            "publication_permission": permission(False),
        })
        b = copy.deepcopy(a)
        b["payment"]["evidence_refs"].reverse()
        b["outcomes"].reverse()
        for outcome in b["outcomes"]:
            outcome["evidence_refs"].reverse()
        self.assertEqual(compile_proof(a).receipt_sha256, compile_proof(b).receipt_sha256)
        self.assertEqual(compile_proof(a).proof_json(), compile_proof(b).proof_json())

    def test_receipt_changes_on_material_permission_change(self):
        a = base_record()
        b = copy.deepcopy(a)
        b["permissions"]["public_proof"] = permission(True, "email:permission:public")
        b["permissions"]["payment_fact"] = permission(True, "email:permission:payment")
        self.assertNotEqual(compile_proof(a).receipt_sha256, compile_proof(b).receipt_sha256)

    def test_optimized_python_semantics_match(self):
        record = base_record()
        record["permissions"]["public_proof"] = permission(True, "email:permission:public")
        record["permissions"]["payment_fact"] = permission(True, "email:permission:payment")
        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.json"
            input_path.write_text(json.dumps(record), encoding="utf-8")
            normal = subprocess.run([sys.executable, "-m", "revenue.verified_paid_proof.verified_paid_proof", str(input_path), "--json"], check=True, capture_output=True, text=True, cwd=ROOT)
            optimized = subprocess.run([sys.executable, "-O", "-m", "revenue.verified_paid_proof.verified_paid_proof", str(input_path), "--json"], check=True, capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(normal.stdout, optimized.stdout)


if __name__ == "__main__":
    unittest.main()
