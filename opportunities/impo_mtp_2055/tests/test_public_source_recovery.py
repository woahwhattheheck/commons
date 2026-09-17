import json
import pathlib
import subprocess
import sys
import unittest

from opportunities.impo_mtp_2055.public_source_recovery import SourceRecoveryError, compile_recovery, validate_snapshot

HERE = pathlib.Path(__file__).resolve().parents[1]
FIX = HERE / "public_source_snapshot.json"


def payload():
    return json.loads(FIX.read_text())


class Tests(unittest.TestCase):
    def test_current_public_source_recovered_but_bytes_pending(self):
        out = compile_recovery(payload())
        self.assertTrue(out["base_rfp_public_source_recovered"])
        self.assertTrue(out["source_fact_authority_bound"])
        self.assertFalse(out["raw_pdf_byte_custody"])
        self.assertIn("RAW_PDF_BYTES_AND_SHA256_NOT_RETAINED", out["pending_source_items"])

    def test_addendum_pending(self):
        out = compile_recovery(payload())
        self.assertEqual(out["questions_addendum_state"], "NOT_YET_POSTED")
        self.assertIn("QUESTIONS_ADDENDUM_NOT_YET_POSTED_OR_RETAINED", out["pending_source_items"])

    def test_external_authority_false(self):
        self.assertIs(compile_recovery(payload())["external_action_authorized"], False)

    def test_hash_cannot_exist_without_bytes(self):
        p = payload(); p["raw_pdf_sha256"] = "0" * 64
        with self.assertRaises(SourceRecoveryError):
            validate_snapshot(p)

    def test_bytes_require_real_hash(self):
        p = payload(); p["raw_pdf_bytes_retained"] = True; p["raw_pdf_sha256"] = None
        with self.assertRaises(SourceRecoveryError):
            validate_snapshot(p)

    def test_evaluation_drift_fails(self):
        p = payload(); p["controlling_facts"]["evaluation_points"]["project_team"] = 34
        with self.assertRaises(SourceRecoveryError):
            validate_snapshot(p)

    def test_authority_flip_fails(self):
        p = payload(); p["external_authority"]["contact_buyer"] = True
        with self.assertRaises(SourceRecoveryError):
            validate_snapshot(p)

    def test_digest_tamper_fails(self):
        p = payload(); p["controlling_facts"]["response_subject"] = "wrong"
        with self.assertRaises(SourceRecoveryError):
            validate_snapshot(p)

    def test_bool_page_count_fails(self):
        p = payload(); p["rfp_page_count"] = True
        with self.assertRaises(SourceRecoveryError):
            validate_snapshot(p)

    def test_cli(self):
        proc = subprocess.run([sys.executable, "-m", "opportunities.impo_mtp_2055.public_source_recovery", str(FIX)], cwd=HERE.parents[1], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertFalse(json.loads(proc.stdout)["external_action_authorized"])


if __name__ == "__main__":
    unittest.main()
