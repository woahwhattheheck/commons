from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "opportunities" / "nysdec_hale_creek_lims" / "partner_guard.py"
SOURCE_PATH = ROOT / "opportunities" / "nysdec_hale_creek_lims" / "partner_khemia_snapshot.json"

spec = importlib.util.spec_from_file_location("nysdec_hale_creek_khemia_partner_guard", MODULE_PATH)
assert spec and spec.loader
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


class HaleCreekKhemiaPartnerGuardTests(unittest.TestCase):
    def test_compile_preserves_prime_hold_and_candidate_boundary(self):
        receipt = guard.compile_from_path(SOURCE_PATH)
        self.assertEqual(receipt["direct_cots_lims_prime_status"], "HOLD")
        self.assertEqual(receipt["partner_candidate"]["company"], "Khemia Software, Inc.")
        self.assertIn("NOT_PARTNER", receipt["candidate_status"])
        self.assertTrue(all(value is False for value in receipt["authority"].values()))

    def test_reuses_merged_25k_offer_without_acceptance_claim(self):
        receipt = guard.compile_from_path(SOURCE_PATH)
        offer = receipt["commercial_offer"]
        self.assertEqual(offer["amount_usd"], 25000)
        self.assertEqual(offer["duration"], "2-4 weeks")
        self.assertEqual(offer["state"], "PROPOSED_NOT_ACCEPTED")
        self.assertEqual(offer["source"]["pull_request"], 14882)
        self.assertEqual(tuple(offer["modules"]), guard.WORKSHARE_MODULES)

    def test_unresolved_partner_gates_cannot_disappear(self):
        receipt = guard.compile_from_path(SOURCE_PATH)
        self.assertEqual(tuple(receipt["partner_candidate"]["unresolved_gates"]), guard.UNRESOLVED_PARTNER_GATES)
        self.assertIn("24x7x365 maintenance and support commitment", receipt["partner_candidate"]["unresolved_gates"])
        self.assertIn("willingness to pursue or respond to Hale Creek", receipt["partner_candidate"]["unresolved_gates"])

    def test_single_partner_and_provider_terminal_rules_are_code_owned(self):
        receipt = guard.compile_from_path(SOURCE_PATH)
        sw = receipt["single_writer"]
        self.assertTrue(sw["parallel_partner_outreach_forbidden"])
        self.assertTrue(sw["muse_exact_selection_required"])
        self.assertTrue(sw["last_inch_slack_gmail_recensus_required"])
        self.assertEqual(sw["provider_sent_terminal_state"], "HARD_DNR_PENDING_GENUINE_EVENT")
        self.assertEqual(sw["ambiguous_provider_state"], "DNR_RECONCILE_NEVER_RESEND")

    def test_collision_key_binds_opportunity_company_route_and_purpose(self):
        base = guard.collision_key()
        self.assertEqual(base, guard.collision_key(company="  Khemia   Software, Inc.  ", route="INFO@KHEMIA.COM"))
        self.assertNotEqual(base, guard.collision_key(route="other@khemia.com"))
        self.assertNotEqual(base, guard.collision_key(company="Another LIMS Vendor"))

    def test_source_byte_change_fails_even_when_valid_json(self):
        value = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        value["candidate"]["public_route"] = "other@khemia.com"
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "source.json"
            path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(guard.PartnerGuardError, "retained generation"):
                guard.compile_from_path(path)

    def test_duplicate_keys_and_lone_surrogates_rejected(self):
        with self.assertRaisesRegex(guard.PartnerGuardError, "duplicate JSON key"):
            guard.parse_json_bytes(b'{"a":1,"a":2}', where="test")
        with self.assertRaises(guard.PartnerGuardError):
            guard.parse_json_bytes(b'{"bad":"\\ud800"}', where="test")
        self.assertEqual(guard.parse_json_bytes('{"ok":"😀"}'.encode(), where="test")["ok"], "😀")

    def test_bool_cannot_alias_integer_price(self):
        value = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
        value["commercial_source"]["price_usd"] = True
        with self.assertRaisesRegex(guard.PartnerGuardError, "commercial source binding mismatch"):
            guard.validate_source(value)

    def test_receipt_tamper_authority_or_acceptance_rejected(self):
        receipt = guard.compile_from_path(SOURCE_PATH)
        receipt["authority"]["partner_contact_authorized"] = True
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "receipt.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaisesRegex(guard.PartnerGuardError, "exact recomputed"):
                guard.verify_receipt(SOURCE_PATH, path)

        receipt = guard.compile_from_path(SOURCE_PATH)
        receipt["commercial_offer"]["state"] = "ACCEPTED"
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "receipt.json"
            path.write_text(json.dumps(receipt), encoding="utf-8")
            with self.assertRaisesRegex(guard.PartnerGuardError, "exact recomputed"):
                guard.verify_receipt(SOURCE_PATH, path)

    def test_round_trip_compile_verify_cli_normal_and_optimized(self):
        for optimized in (False, True):
            with self.subTest(optimized=optimized), tempfile.TemporaryDirectory() as td:
                receipt = Path(td) / "receipt.json"
                command = [sys.executable]
                if optimized:
                    command.append("-O")
                command.extend([str(MODULE_PATH), "compile", "--source", str(SOURCE_PATH), "--output", str(receipt)])
                compiled = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(compiled.returncode, 0, compiled.stderr)
                verify = [sys.executable]
                if optimized:
                    verify.append("-O")
                verify.extend([str(MODULE_PATH), "verify", "--source", str(SOURCE_PATH), "--receipt", str(receipt)])
                checked = subprocess.run(verify, cwd=ROOT, capture_output=True, text=True)
                self.assertEqual(checked.returncode, 0, checked.stderr)
                result = json.loads(checked.stdout)
                self.assertTrue(result["valid"])
                self.assertFalse(result["partner_contact_authorized"])
                self.assertEqual(result["commercial_state"], "PROPOSED_NOT_ACCEPTED")

    def test_output_is_create_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "receipt.json"
            output.write_text("keep-me", encoding="utf-8")
            run = subprocess.run(
                [sys.executable, str(MODULE_PATH), "compile", "--source", str(SOURCE_PATH), "--output", str(output)],
                cwd=ROOT,
                capture_output=True,
                text=True,
            )
            self.assertEqual(run.returncode, 2)
            self.assertEqual(output.read_text(encoding="utf-8"), "keep-me")


if __name__ == "__main__":
    unittest.main()
