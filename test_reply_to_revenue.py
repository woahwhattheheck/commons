from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("reply_to_revenue", ROOT / "host" / "reply_to_revenue.py")
assert SPEC and SPEC.loader
r2r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r2r)


class ReplyToRevenueTests(unittest.TestCase):
    def test_auto_ack_is_never_buyer_interest(self) -> None:
        verdict = r2r.classify_signals(
            ["thank you for reaching out", "ticket has been created", "delivered by zendesk"],
            "POSITIVE_SCOPE",
        )
        self.assertEqual(verdict["classification"], "AUTO_RESPONSE")
        self.assertFalse(verdict["buyer_interest"])
        self.assertTrue(verdict["auto_ack"])
        self.assertEqual(verdict["next_action"], "WAIT_FOR_HUMAN_REPLY")

    def test_vendor_ai_assistant_is_auto_ack(self) -> None:
        verdict = r2r.classify_signals(
            ["ai assistant", "a human will respond", "this answer was composed by", "ai agent"]
        )
        self.assertEqual(verdict["classification"], "AUTO_RESPONSE")
        self.assertFalse(verdict["buyer_interest"])

    def test_csat_survey_is_auto_ack(self) -> None:
        verdict = r2r.classify_signals(["how would you rate", "rate the support you received"])
        self.assertEqual(verdict["classification"], "AUTO_RESPONSE")
        self.assertFalse(verdict["buyer_interest"])

    def test_explicit_scope_language_without_auto_ack_is_positive(self) -> None:
        verdict = r2r.classify_signals(["please invoice", "we accept the scope"])
        self.assertEqual(verdict["classification"], "POSITIVE_SCOPE")
        self.assertTrue(verdict["buyer_interest"])
        self.assertEqual(verdict["next_action"], "NEEDS_ACCEPTANCE")

    def test_checked_in_funnel_is_all_dnr_auto_acks_and_zero_cash(self) -> None:
        funnel = r2r.validate_funnel()
        self.assertEqual(funnel["truth"]["cash_usd"], 0)
        self.assertEqual(funnel["truth"]["resends"], 0)
        self.assertEqual(funnel["truth"]["transport_actions"], 0)
        self.assertEqual(funnel["truth"]["human_positive"], 0)
        self.assertEqual(funnel["truth"]["scope_acceptances"], 0)
        self.assertEqual(funnel["truth"]["inbound_recorded"], 4)
        self.assertEqual(funnel["truth"]["auto_acks"], 4)
        self.assertEqual(funnel["surfaces"], [])
        self.assertTrue(funnel["truth"]["distinct_contacts"] >= 7)
        self.assertEqual(funnel["truth"]["hard_dnr_contacts"], funnel["truth"]["distinct_contacts"])
        self.assertTrue(all(contact["hard_dnr"] and contact["resend"] is False for contact in funnel["contacts"]))
        self.assertTrue(all(event["auto_ack"] and not event["buyer_interest"] for event in funnel["inbound"]))
        blob = r2r.canonical_text(funnel)
        for word in ("replied", "accepted", "invoiced", "authorized", "settled", "delivered", "paid"):
            self.assertNotRegex(blob, rf"\b{word}\b")

    def test_duplicate_event_ref_with_new_hash_collides(self) -> None:
        observations = r2r.read_object(r2r.OBSERVATIONS_PATH)
        duplicate = copy.deepcopy(observations["events"][0])
        duplicate["payload_sha256"] = "0" * 64
        observations["events"].append(duplicate)
        observations["monitor"]["attributed_inbound"] = len(observations["events"])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observations.json"
            path.write_text(r2r.canonical_text(observations), encoding="utf-8")
            with self.assertRaises(r2r.CollisionError):
                r2r.load_observations(path)

    def test_same_event_is_ingested_once(self) -> None:
        observations = r2r.read_object(r2r.OBSERVATIONS_PATH)
        observations["events"].append(copy.deepcopy(observations["events"][0]))
        observations["monitor"]["attributed_inbound"] = 4
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "observations.json"
            path.write_text(r2r.canonical_text(observations), encoding="utf-8")
            loaded = r2r.load_observations(path)
        self.assertEqual(len(loaded["events"]), 4)

    def test_send_flag_is_always_refused(self) -> None:
        funnel = r2r.build_funnel()
        with self.assertRaises(r2r.ResendError):
            r2r.assert_no_resend(funnel, send=True)

    def test_cli_validate_and_classify_are_deterministic(self) -> None:
        command = [sys.executable, str(ROOT / "host" / "reply_to_revenue.py"), "validate"]
        first = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout
        second = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True).stdout
        self.assertEqual(first, second)
        self.assertIn("0 resends", first)
        self.assertIn("USD 0 cash", first)
        classify = subprocess.run(
            [
                sys.executable,
                str(ROOT / "host" / "reply_to_revenue.py"),
                "classify",
                "--markers",
                "ticket has been created,thank you for reaching out",
                "--requested",
                "POSITIVE_SCOPE",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        parsed = json.loads(classify)
        self.assertEqual(parsed["classification"], "AUTO_RESPONSE")
        self.assertFalse(parsed["buyer_interest"])

    def test_monitor_send_exits_three(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "host" / "reply_to_revenue.py"), "monitor", "--send"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 3)
        self.assertIn("never sends", result.stderr)

    def test_positive_surface_hands_to_acceptance(self) -> None:
        contacts = [
            {
                "prospect_key": "example-buyer",
                "organization": "Example",
                "lane": "HUMAN_POSITIVE",
                "hard_dnr": True,
                "resend": False,
            }
        ]
        inbound = [
            {
                "event_ref": "opaque:fixture-positive-01",
                "received_at": "2026-08-28T00:00:00Z",
                "prospect_key": "example-buyer",
                "classification": "POSITIVE_SCOPE",
            }
        ]
        surfaces = r2r.surface_positives(contacts, inbound)
        self.assertEqual(len(surfaces), 1)
        self.assertEqual(surfaces[0]["next_action"], "NEEDS_ACCEPTANCE")
        self.assertEqual(surfaces[0]["handoff"], "revenue/production_survival/acceptance.py")
        self.assertTrue(surfaces[0]["buyer_interest"])


if __name__ == "__main__":
    unittest.main()
