from __future__ import annotations

import copy
from datetime import datetime, timezone
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
NOW = datetime(2026, 9, 17, 4, 50, 0, tzinfo=timezone.utc)

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
        self.assertEqual(receipt["partner_conversion_posture"], "HOLD_ACTIVE_ORG_COLLISION_PENDING_MUSE")
        self.assertIn("ACTIVE_ORG_ROUTE_COLLISION_PENDING_MUSE", receipt["runtime_gate"]["holds"])
        self.assertEqual(receipt["candidate"]["muse_resolution"], "PENDING")
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

    def test_historical_preflight_cannot_be_rewritten_as_current_clearance(self) -> None:
        forged = copy.deepcopy(self.candidate)
        forged["collision_preflight"]["gmail_exact_history"] = 1
        with self.assertRaises(carrier.CarrierError):
            carrier.validate_candidate(forged)
        forged = copy.deepcopy(self.candidate)
        forged["collision_preflight"]["requires_muse_single_writer_clearance"] = False
        with self.assertRaises(carrier.CarrierError):
            carrier.validate_candidate(forged)

    def test_active_org_route_collision_is_machine_hold(self) -> None:
        holds = carrier.evaluate_runtime_state(self.source, self.candidate, now=NOW)
        self.assertIn("ACTIVE_ORG_ROUTE_COLLISION_PENDING_MUSE", holds)
        self.assertEqual(carrier._posture_for(holds), "HOLD_ACTIVE_ORG_COLLISION_PENDING_MUSE")
        forged = copy.deepcopy(self.candidate)
        forged["current_collision"]["status"] = "NO_COLLISION"
        with self.assertRaises(carrier.CarrierError):
            carrier.validate_candidate(forged)
        forged = copy.deepcopy(self.candidate)
        forged["current_collision"]["muse_resolution"] = "CLEAR_NHDES"
        with self.assertRaises(carrier.CarrierError):
            carrier.validate_candidate(forged)

    def test_future_source_state_fails_closed(self) -> None:
        forged = copy.deepcopy(self.source)
        forged["checked_at"] = "2026-09-18T00:00:00-04:00"
        holds = carrier.evaluate_runtime_state(forged, self.candidate, now=NOW)
        self.assertIn("SOURCE_STATE_FUTURE", holds)
        self.assertEqual(carrier._posture_for(holds), "HOLD_FUTURE_STATE_INVALID")

    def test_stale_source_state_fails_closed(self) -> None:
        forged = copy.deepcopy(self.source)
        forged["checked_at"] = "2026-09-15T00:00:00-04:00"
        holds = carrier.evaluate_runtime_state(forged, self.candidate, now=NOW)
        self.assertIn("SOURCE_STATE_STALE", holds)
        self.assertEqual(carrier._posture_for(holds), "HOLD_STALE_SOURCE_OR_COLLISION_STATE")

    def test_future_and_stale_candidate_state_fail_closed(self) -> None:
        future = copy.deepcopy(self.candidate)
        future["current_collision"]["observed_at"] = "2026-09-18T00:00:00-04:00"
        future["evidence_checked_before"] = "2026-09-17T00:37:14-04:00"
        holds = carrier.evaluate_runtime_state(self.source, future, now=NOW)
        self.assertIn("COLLISION_STATE_FUTURE", holds)
        self.assertEqual(carrier._posture_for(holds), "HOLD_FUTURE_STATE_INVALID")

        stale = copy.deepcopy(self.candidate)
        stale["evidence_checked_before"] = "2026-09-15T00:00:00-04:00"
        holds = carrier.evaluate_runtime_state(self.source, stale, now=NOW)
        self.assertIn("CANDIDATE_EVIDENCE_STALE", holds)
        self.assertEqual(carrier._posture_for(holds), "HOLD_STALE_SOURCE_OR_COLLISION_STATE")

    def test_post_deadline_execution_fails_closed(self) -> None:
        after_deadline = datetime(2026, 10, 24, 12, 0, 0, tzinfo=timezone.utc)
        holds = carrier.evaluate_runtime_state(self.source, self.candidate, now=after_deadline)
        self.assertIn("RESPONSE_DEADLINE_PASSED", holds)
        self.assertEqual(carrier._posture_for(holds), "HOLD_RESPONSE_DEADLINE_PASSED")

    def test_timestamps_must_be_offset_aware(self) -> None:
        forged = copy.deepcopy(self.source)
        forged["checked_at"] = "2026-09-17T00:40:00"
        with self.assertRaises(carrier.CarrierError):
            carrier.validate_source(forged)
        forged_candidate = copy.deepcopy(self.candidate)
        forged_candidate["current_collision"]["observed_at"] = "2026-09-17T00:38:55"
        with self.assertRaises(carrier.CarrierError):
            carrier.validate_candidate(forged_candidate)

    def test_public_authority_mapping_is_immutable(self) -> None:
        with self.assertRaises(TypeError):
            carrier.AUTHORITY["partner_contact_authorized_by_carrier"] = True

    def test_production_semantics_ignore_post_import_global_rebinding(self) -> None:
        baseline = carrier.build_receipt(self.source, self.candidate)
        originals = {
            "AUTHORITY": carrier.AUTHORITY,
            "_now_utc": carrier._now_utc,
            "evaluate_runtime_state": carrier.evaluate_runtime_state,
            "_posture_for": carrier._posture_for,
            "validate_source": carrier.validate_source,
            "validate_candidate": carrier.validate_candidate,
            "canonical_json": carrier.canonical_json,
            "digest": carrier.digest,
            "MAX_STATE_AGE_SECONDS": carrier.MAX_STATE_AGE_SECONDS,
            "MAX_CLOCK_SKEW_SECONDS": carrier.MAX_CLOCK_SKEW_SECONDS,
            "BUYER_TIMEZONE": carrier.BUYER_TIMEZONE,
        }
        try:
            carrier.AUTHORITY = {key: True for key in baseline["authority"]}
            carrier._now_utc = lambda: datetime(2099, 1, 1, tzinfo=timezone.utc)
            carrier.evaluate_runtime_state = lambda *args, **kwargs: []
            carrier._posture_for = lambda holds: "READY_FOR_MUSE_GATED_PARTNER_INQUIRY_ONLY"
            carrier.validate_source = lambda value: value
            carrier.validate_candidate = lambda value: value
            carrier.canonical_json = lambda value: b"forged"
            carrier.digest = lambda value: "f" * 64
            carrier.MAX_STATE_AGE_SECONDS = 10**12
            carrier.MAX_CLOCK_SKEW_SECONDS = 10**12
            carrier.BUYER_TIMEZONE = "UTC"

            rebuilt = carrier.build_receipt(self.source, self.candidate)
            self.assertEqual(rebuilt, baseline)
            self.assertEqual(rebuilt["partner_conversion_posture"], "HOLD_ACTIVE_ORG_COLLISION_PENDING_MUSE")
            self.assertTrue(all(value is False for value in rebuilt["authority"].values()))
            self.assertEqual(rebuilt["runtime_gate"]["max_state_age_seconds"], 24 * 60 * 60)
            self.assertEqual(rebuilt["runtime_gate"]["max_clock_skew_seconds"], 5 * 60)
            self.assertEqual(rebuilt["runtime_gate"]["buyer_timezone"], "America/New_York")
            carrier.verify_receipt(baseline, self.source, self.candidate)
        finally:
            for name, value in originals.items():
                setattr(carrier, name, value)

    def test_runtime_generation_ignores_builtin_and_exception_shadowing(self) -> None:
        baseline = carrier.build_receipt(self.source, self.candidate)
        original_error = carrier.CarrierError
        real_set = set

        def forged_set(value=()):
            result = real_set(value)
            if "ACTIVE_ORG_ROUTE_COLLISION_PENDING_MUSE" in result:
                return real_set()
            return result

        class ForgedCarrierError(Exception):
            pass

        poison = {
            "set": forged_set,
            "sorted": lambda values: [],
            "type": lambda value: object,
            "any": lambda values: False,
            "len": lambda value: 0,
            "dict": lambda *args, **kwargs: {"forged": True},
            "list": tuple,
            "str": bytes,
            "int": bool,
            "TypeError": RuntimeError,
            "ValueError": RuntimeError,
            "UnicodeError": RuntimeError,
            "RecursionError": RuntimeError,
            "OverflowError": RuntimeError,
            "CarrierError": ForgedCarrierError,
        }
        originals: dict[str, tuple[bool, object]] = {}
        try:
            for name, value in poison.items():
                originals[name] = (name in carrier.__dict__, carrier.__dict__.get(name))
                setattr(carrier, name, value)

            rebuilt = carrier.build_receipt(self.source, self.candidate)
            self.assertEqual(rebuilt, baseline)
            self.assertIn("ACTIVE_ORG_ROUTE_COLLISION_PENDING_MUSE", rebuilt["runtime_gate"]["holds"])
            self.assertEqual(rebuilt["partner_conversion_posture"], "HOLD_ACTIVE_ORG_COLLISION_PENDING_MUSE")
            self.assertTrue(all(value is False for value in rebuilt["authority"].values()))
            carrier.verify_receipt(baseline, self.source, self.candidate)

            forged = copy.deepcopy(self.candidate)
            forged["current_collision"]["muse_resolution"] = "CLEAR_NHDES"
            with self.assertRaises(original_error):
                carrier.validate_candidate(forged)
        finally:
            for name, (existed, value) in originals.items():
                if existed:
                    setattr(carrier, name, value)
                else:
                    delattr(carrier, name)

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
            self.assertEqual(parsed["partner_conversion_posture"], "HOLD_ACTIVE_ORG_COLLISION_PENDING_MUSE")

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
