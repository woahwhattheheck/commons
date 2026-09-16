import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

from .compiler import compile_proof, public_json, public_payload, write_outputs
from .core import POLICY_VERSION, ProofError, _canonical_json
from .test_verified_paid_proof import ROOT, base_record, permission
from .verified_paid_proof import main


class PublicReleaseBoundaryTests(unittest.TestCase):
    def _public_record(self):
        record = base_record()
        record["permissions"]["public_proof"] = permission(
            True, "email:permission:public"
        )
        record["permissions"]["payment_fact"] = permission(
            True, "email:permission:payment"
        )
        return record

    def test_private_and_hold_markdown_collapse_to_same_no_claim_artifact(self):
        private = compile_proof(base_record())
        hold_record = self._public_record()
        hold_record["revocation"] = {
            "revoked": True,
            "evidence_refs": ["email:revocation:1"],
        }
        hold = compile_proof(hold_record)
        self.assertEqual(private.proof["status"], "PRIVATE_VERIFIED")
        self.assertEqual(hold.proof["status"], "HOLD")
        self.assertEqual(private.markdown, hold.markdown)
        self.assertIn("No public paid-work claim is authorized", private.markdown)
        for secret in (
            "PRIVATE_VERIFIED",
            "HOLD",
            "Synthetic Buyer",
            "Settled payment",
            "bounded artifact",
            "acceptance checks passed",
            "publication_permission_revoked",
            "stripe:",
        ):
            self.assertNotIn(secret, private.markdown)
            self.assertNotIn(secret, hold.markdown)

    def test_public_markdown_does_not_disclose_withheld_inventory(self):
        compiled = compile_proof(self._public_record())
        self.assertEqual(compiled.proof["status"], "PUBLIC_ANONYMOUS")
        for private_metadata in (
            "Withheld from public projection",
            "outcome_claim",
            "customer_identity",
            "delivery_acceptance",
            "quote",
            "logo",
            "Buyer confirmed the requested acceptance checks passed",
            "The bounded artifact met the requested acceptance checks",
            "email:synthetic-acceptance-1",
        ):
            self.assertNotIn(private_metadata, compiled.markdown)
        self.assertIn("Paid engagement verified", compiled.markdown)
        self.assertNotIn("Settled amount", compiled.markdown)

    def test_private_and_hold_public_json_are_identical_no_claim_envelopes(self):
        private = compile_proof(base_record())
        hold_record = self._public_record()
        hold_record["revocation"] = {
            "revoked": True,
            "evidence_refs": ["email:revocation:1"],
        }
        hold = compile_proof(hold_record)
        self.assertEqual(public_json(private), public_json(hold))
        payload = json.loads(public_json(private))
        self.assertEqual(
            payload,
            {
                "policy_version": POLICY_VERSION,
                "public_projection": None,
                "release_state": "NO_PUBLIC_CLAIM",
                "schema_version": 1,
            },
        )
        blob = public_json(private)
        for secret in (
            "PRIVATE_VERIFIED",
            "HOLD",
            "Synthetic Buyer",
            "eng.synthetic.001",
            "private_evidence",
            "receipt_sha256",
            "stripe:",
        ):
            self.assertNotIn(secret, blob)

    def test_public_json_is_allowlisted_against_future_internal_fields(self):
        record = self._public_record()
        record["outcomes"][0]["publication_permission"] = permission(
            True, "email:permission:outcome"
        )
        compiled = compile_proof(record)
        compiled.proof["public_projection"]["internal_secret"] = "DO NOT SHIP"
        compiled.proof["public_projection"]["outcomes"][0]["evidence_refs"] = [
            "email:private-source"
        ]
        blob = public_json(compiled)
        self.assertNotIn("DO NOT SHIP", blob)
        self.assertNotIn("private-source", blob)
        payload = json.loads(blob)
        self.assertEqual(
            set(payload["public_projection"]),
            {
                "status",
                "proof_id",
                "customer",
                "paid_engagement",
                "exact_amount",
                "delivery_accepted",
                "quote",
                "logo_ref",
                "outcomes",
            },
        )
        self.assertEqual(
            payload["public_projection"]["outcomes"],
            [{"claim": record["outcomes"][0]["claim"]}],
        )

    def test_public_projection_status_mismatch_fails_closed(self):
        compiled = compile_proof(self._public_record())
        compiled.proof["public_projection"]["status"] = "PRIVATE_VERIFIED"
        with self.assertRaises(ProofError):
            public_payload(compiled)

    def test_public_receipt_binds_only_public_envelope(self):
        compiled = compile_proof(self._public_record())
        payload = json.loads(public_json(compiled))
        receipt = payload.pop("public_receipt_sha256")
        expected = hashlib.sha256(
            _canonical_json(payload).encode("utf-8")
        ).hexdigest()
        self.assertEqual(receipt, expected)
        self.assertNotEqual(receipt, compiled.receipt_sha256)
        public_blob = json.dumps(payload)
        for secret in (
            "Synthetic Buyer",
            "eng.synthetic.001",
            "stripe:",
            "email:synthetic-acceptance-1",
            "bounded artifact",
            "acceptance checks passed",
        ):
            self.assertNotIn(secret, public_blob)

    def test_public_receipt_is_deterministic_and_changes_with_public_facts(self):
        first_record = self._public_record()
        second_record = self._public_record()
        second_record["permissions"]["exact_amount"] = permission(
            True, "email:permission:amount"
        )
        first = json.loads(public_json(compile_proof(first_record)))
        first_again = json.loads(public_json(compile_proof(first_record)))
        second = json.loads(public_json(compile_proof(second_record)))
        self.assertEqual(first, first_again)
        self.assertNotEqual(
            first["public_receipt_sha256"], second["public_receipt_sha256"]
        )

    def test_write_outputs_separates_internal_and_public_artifacts(self):
        compiled = compile_proof(base_record())
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            write_outputs(compiled, out)
            self.assertEqual(
                {path.name for path in out.iterdir()},
                {"proof.json", "public.json", "proof.md", "receipt.sha256"},
            )
            self.assertIn("private_evidence", (out / "proof.json").read_text())
            self.assertNotIn("private_evidence", (out / "public.json").read_text())
            self.assertNotIn("PRIVATE_VERIFIED", (out / "proof.md").read_text())

    def test_cli_public_json_matches_output_file(self):
        record = self._public_record()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.json"
            out = root / "out"
            input_path.write_text(json.dumps(record), encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    "-W",
                    "error::SyntaxWarning",
                    "-m",
                    "revenue.verified_paid_proof.verified_paid_proof",
                    str(input_path),
                    "--out-dir",
                    str(out),
                ],
                check=True,
                cwd=ROOT,
            )
            printed = subprocess.run(
                [
                    sys.executable,
                    "-W",
                    "error::SyntaxWarning",
                    "-m",
                    "revenue.verified_paid_proof.verified_paid_proof",
                    str(input_path),
                    "--public-json",
                ],
                check=True,
                capture_output=True,
                text=True,
                cwd=ROOT,
            ).stdout
            self.assertEqual(printed, (out / "public.json").read_text())

    def test_cli_output_write_error_returns_two_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.json"
            not_a_directory = root / "occupied"
            input_path.write_text(json.dumps(base_record()), encoding="utf-8")
            not_a_directory.write_text("occupied", encoding="utf-8")
            stderr = StringIO()
            with redirect_stderr(stderr):
                result = main(
                    [str(input_path), "--out-dir", str(not_a_directory)]
                )
            self.assertEqual(result, 2)
            self.assertIn("ERROR:", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_markdown_neutralizes_structure_controls_autolinks_and_extensions(self):
        record = base_record()
        record["customer"]["display_name"] = (
            "O' **X**\n# H https://x.test a@b.test @u ~~s~~ $m$ ^u^\u202e"
        )
        record["customer"]["logo_ref"] = "`logo` [click](https://bad.example)"
        record["quote"] = {
            "text": "Contact @buyer / see https://example.invalid/path.\n- bullet",
            "evidence_ref": "email:q",
        }
        record["outcomes"][0]["claim"] = "<script>alert(1)</script> ~~claim~~"
        for scope in record["permissions"]:
            record["permissions"][scope] = permission(
                True, f"email:permission:{scope}"
            )
        record["outcomes"][0]["publication_permission"] = permission(
            True, "email:permission:outcome"
        )
        markdown = compile_proof(record).markdown
        for unsafe in (
            "\n# H",
            "**X**",
            "](https://bad.example)",
            "<script>",
            "https://",
            "a@b",
            "@u",
            "~~s~~",
            "$m$",
            "^u^",
            "\u202e",
        ):
            self.assertNotIn(unsafe, markdown)
        for escaped in (
            r"\# H",
            r"\*\*X\*\*",
            r"\~\~s\~\~",
            r"\$m\$",
            r"\^u\^",
            "https&#58;&#47;&#47;x&#46;test",
            "a&#64;b&#46;test",
            "O&#x27;",
        ):
            self.assertIn(escaped, markdown)

    def test_policy_bumped_for_receipt_visible_boundary_change(self):
        self.assertEqual(POLICY_VERSION, "verified-paid-proof/v3")
        self.assertEqual(
            compile_proof(base_record()).proof["policy_version"],
            "verified-paid-proof/v3",
        )


if __name__ == "__main__":
    unittest.main()
