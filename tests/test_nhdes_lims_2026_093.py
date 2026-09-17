from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
LANE = ROOT / "opportunities" / "nhdes_lims_2026_093"
CARRIER_PATH = LANE / "carrier.py"
SOURCE_PATH = LANE / "source_snapshot.json"
CANDIDATE_PATH = LANE / "partner_candidate.json"

_spec = importlib.util.spec_from_file_location("nhdes_lims_2026_093_carrier", CARRIER_PATH)
assert _spec is not None and _spec.loader is not None
carrier = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(carrier)


class NhdesLims2026093CarrierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.source = carrier._load_source(SOURCE_PATH)
        self.candidate = carrier._load_candidate(CANDIDATE_PATH)

    def test_compile_verify_and_truth_ceiling(self) -> None:
        receipt = carrier.build_receipt(self.source, self.candidate)
        carrier.verify_receipt(receipt, self.source, self.candidate)
        self.assertEqual(receipt["prime_posture"], "HOLD_RAW_PACKET_AND_EXTERNAL_PRIME_EVIDENCE")
        self.assertEqual(
            receipt["partner_conversion_posture"],
            "READY_FOR_MUSE_GATED_PARTNER_INQUIRY_ONLY",
        )
        self.assertEqual(receipt["money_state"], "NO_ACCEPTANCE_NO_RECEIVABLE_NO_REVENUE")
        self.assertTrue(all(value is False for value in receipt["authority"].values()))

    def test_offer_is_existing_proposed_workshare_not_buyer_budget(self) -> None:
        receipt = carrier.build_receipt(self.source, self.candidate)
        offer = receipt["specialist_offer"]
        self.assertEqual(offer["price_usd"], 40000)
        self.assertEqual(offer["duration_business_days"], 15)
        self.assertEqual(offer["commercial_status"], "PROPOSED_NOT_ACCEPTED")
        self.assertEqual(offer["source_repo"], "woahwhattheheck/aquatrace-lims")
        self.assertEqual(offer["source_pr"], 170)
        self.assertIn("proposal submission or contract acceptance", offer["excludes"])

    def test_raw_packet_gap_cannot_be_promoted(self) -> None:
        forged = copy.deepcopy(self.source)
        forged["source_state"] = "RAW_PACKET_VERIFIED"
        with self.assertRaises(carrier.CarrierError):
            carrier.validate_source(forged)

    def test_reported_govramp_gate_cannot_be_self_certified(self) -> None:
        forged = copy.deepcopy(self.source)
        forged["reported_bidder_requirements"]["govramp_authorization"] = "VERIFIED"
        with self.assertRaises(carrier.CarrierError):
            carrier.validate_source(forged)

    def test_candidate_gaps_cannot_be_promoted(self) -> None:
        forged = copy.deepcopy(self.candidate)
        forged["qualification_gaps"]["govramp_authorization"] = "VERIFIED"
        with self.assertRaises(carrier.CarrierError):
            carrier.validate_candidate(forged)

    def test_candidate_file_cannot_grant_contact_authority(self) -> None:
        forged = copy.deepcopy(self.candidate)
        forged["external_authority"]["contact_authorized_by_file"] = True
        with self.assertRaises(carrier.CarrierError):
            carrier.validate_candidate(forged)

    def test_collision_preflight_must_be_zero_and_fresh_muse_gate_stays_required(self) -> None:
        forged = copy.deepcopy(self.candidate)
        forged["collision_preflight"]["gmail_exact_history"] = 1
        with self.assertRaises(carrier.CarrierError):
            carrier.validate_candidate(forged)
        forged = copy.deepcopy(self.candidate)
        forged["collision_preflight"]["requires_muse_single_writer_clearance"] = False
        with self.assertRaises(carrier.CarrierError):
            carrier.validate_candidate(forged)

    def test_receipt_tamper_fails_recompile_verification(self) -> None:
        receipt = carrier.build_receipt(self.source, self.candidate)
        receipt["candidate"]["govramp_authorization"] = "VERIFIED"
        with self.assertRaises(carrier.CarrierError):
            carrier.verify_receipt(receipt, self.source, self.candidate)

    def test_duplicate_and_nonfinite_json_are_rejected(self) -> None:
        with self.assertRaises(carrier.CarrierError):
            carrier.parse_json_bytes(b'{"a":1,"a":2}', where="hostile")
        with self.assertRaises(carrier.CarrierError):
            carrier.parse_json_bytes(b'{"a":NaN}', where="hostile")

    def test_create_exclusive_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "receipt.json"
            carrier.write_exclusive(out, {"ok": True})
            with self.assertRaises(carrier.CarrierError):
                carrier.write_exclusive(out, {"ok": False})

    def test_real_cli_compile_then_verify(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "receipt.json"
            compile_cmd = [
                sys.executable,
                str(CARRIER_PATH),
                "compile",
                "--source",
                str(SOURCE_PATH),
                "--candidate",
                str(CANDIDATE_PATH),
                "--output",
                str(out),
            ]
            compiled = subprocess.run(compile_cmd, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(compiled.returncode, 0, msg=compiled.stderr)
            self.assertTrue(out.is_file())
            parsed = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(parsed["specialist_offer"]["commercial_status"], "PROPOSED_NOT_ACCEPTED")

            verify_cmd = [
                sys.executable,
                str(CARRIER_PATH),
                "verify",
                "--source",
                str(SOURCE_PATH),
                "--candidate",
                str(CANDIDATE_PATH),
                "--receipt",
                str(out),
            ]
            verified = subprocess.run(verify_cmd, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(verified.returncode, 0, msg=verified.stderr)
            self.assertIn("VERIFIED", verified.stdout)


if __name__ == "__main__":
    unittest.main()
