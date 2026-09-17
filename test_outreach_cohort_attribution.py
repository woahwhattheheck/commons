from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

from revenue.outreach_cohort_attribution.core import (
    AttributionError,
    INPUT_SCHEMA,
    compile_attribution,
    strict_json_loads,
    verify_attribution,
)


def money(amount: int, currency: str = "USD", decimals: int = 2):
    return {"amount_minor": amount, "currency": currency, "decimals": decimals}


def event(kind: str, at: str, ref: str, amount=None):
    return {"type": kind, "at": at, "evidence_refs": [ref], "amount": amount}


def sent_campaign(cid: str, org: str, route: str, sent_at: str, *, offer="OFFER-A", segment="HOTEL"):
    return {
        "campaign_id": cid,
        "offer_id": offer,
        "segment": segment,
        "target_org": org,
        "route": route,
        "purpose": "PAID-WORKSHARE",
        "events": [
            event("MUSE_SELECTED", sent_at, f"slack:{cid}:muse"),
            event("SENT", sent_at, f"gmail:{cid}:sent"),
        ],
    }


def base_input():
    a = sent_campaign("c-paid", "Alpha Hotel", "alpha@example.com", "2026-09-10T10:00:00-04:00")
    a["events"] += [
        event("PROPOSED", "2026-09-10T10:00:00-04:00", "offer:a", money(500000)),
        event("HUMAN_REPLY", "2026-09-11T09:00:00-04:00", "gmail:a:reply"),
        event("QUALIFIED", "2026-09-11T09:05:00-04:00", "crm:a:qualified"),
        event("ACCEPTED", "2026-09-12T11:00:00-04:00", "contract:a", money(500000)),
        event("INVOICED", "2026-09-12T12:00:00-04:00", "invoice:a", money(500000)),
        event("PAID", "2026-09-13T14:00:00-04:00", "bank:a", money(500000)),
        event("DNR", "2026-09-13T14:01:00-04:00", "policy:a:dnr"),
    ]
    b = sent_campaign("c-mature", "Beta Hotel", "beta@example.com", "2026-09-10T10:00:00-04:00")
    b["events"] += [event("PROPOSED", "2026-09-10T10:00:00-04:00", "offer:b", money(500000))]
    c = sent_campaign("c-pending", "Gamma Hotel", "gamma@example.com", "2026-09-17T01:30:00-04:00")
    c["events"] += [event("PROPOSED", "2026-09-17T01:30:00-04:00", "offer:c", money(500000))]
    d = sent_campaign("c-bounce", "Delta Hotel", "delta@example.com", "2026-09-15T12:00:00-04:00")
    d["events"] += [
        event("PROPOSED", "2026-09-15T12:00:00-04:00", "offer:d", money(500000)),
        event("BOUNCE", "2026-09-15T12:00:03-04:00", "dsn:d"),
        event("DNR", "2026-09-15T12:00:04-04:00", "policy:d"),
    ]
    return {
        "schema": INPUT_SCHEMA,
        "as_of": "2026-09-17T03:00:00-04:00",
        "policy": {
            "observation_hours": 48,
            "min_mature_sends": 2,
            "expand_reply_rate_bp": 3000,
            "max_bounce_rate_bp": 3000,
        },
        "campaigns": [a, b, c, d],
    }


class AttributionTests(unittest.TestCase):
    def test_valid_compile_separates_pending_bounce_reply_and_paid(self):
        packet = compile_attribution(base_input())
        cohort = packet["cohorts"][0]
        self.assertEqual(cohort["sent_targets"], 4)
        self.assertEqual(cohort["mature_targets"], 3)
        self.assertEqual(cohort["delivered_mature_targets"], 2)
        self.assertEqual(cohort["pending_targets"], 1)
        self.assertEqual(cohort["bounced_targets"], 1)
        self.assertEqual(cohort["human_reply_targets"], 1)
        self.assertEqual(cohort["paid_targets"], 1)
        self.assertEqual(cohort["reply_rate_bp"], 5000)
        self.assertEqual(cohort["bounce_rate_bp"], 2500)
        self.assertEqual(cohort["disposition"], "EXPAND_CAUTIOUSLY")
        self.assertEqual(cohort["money_by_currency"]["USD"]["proposed_minor"], 2_000_000)
        self.assertEqual(cohort["money_by_currency"]["USD"]["paid_minor"], 500_000)
        self.assertFalse(packet["authority"]["automatic_scaling_authorized"])
        self.assertFalse(packet["authority"]["revenue_recognition_authorized"])
        self.assertTrue(verify_attribution(base_input(), packet))

    def test_pending_is_not_counted_as_mature_failure(self):
        data = base_input(); data["campaigns"] = [data["campaigns"][2]]
        cohort = compile_attribution(data)["cohorts"][0]
        self.assertEqual(cohort["pending_targets"], 1)
        self.assertEqual(cohort["mature_targets"], 0)
        self.assertIsNone(cohort["reply_rate_bp"])
        self.assertEqual(cohort["disposition"], "UNDER_OBSERVED")

    def test_bounce_is_not_buyer_rejection(self):
        data = base_input(); data["campaigns"] = [data["campaigns"][3]]
        summary = compile_attribution(data)["campaigns"][0]["summary"]
        self.assertTrue(summary["ever_bounced"])
        self.assertFalse(summary["rejected"])
        self.assertFalse(summary["human_reply"])
        self.assertEqual(summary["next_contact_disposition"], "HOLD_COLLISION_OR_DNR")

    def test_route_quality_pause_precedes_reply_expansion(self):
        data = base_input(); data["policy"]["max_bounce_rate_bp"] = 1000
        self.assertEqual(compile_attribution(data)["cohorts"][0]["disposition"], "PAUSE_ROUTE_QUALITY")

    def test_conversion_pause_after_enough_mature_no_reply(self):
        data = base_input()
        data["campaigns"] = [
            sent_campaign("x1", "X One", "x1@example.com", "2026-09-10T00:00:00Z"),
            sent_campaign("x2", "X Two", "x2@example.com", "2026-09-10T00:00:00Z"),
        ]
        self.assertEqual(compile_attribution(data)["cohorts"][0]["disposition"], "PAUSE_CONVERSION")

    def test_under_observed(self):
        data = base_input(); data["policy"]["min_mature_sends"] = 10
        self.assertEqual(compile_attribution(data)["cohorts"][0]["disposition"], "UNDER_OBSERVED")

    def test_all_held_yields_hold_disposition(self):
        data = base_input(); data["campaigns"] = [data["campaigns"][3]]
        self.assertEqual(compile_attribution(data)["cohorts"][0]["disposition"], "HOLD_COLLISION_OR_DNR")

    def test_duplicate_target_route_purpose_rejected_case_insensitive(self):
        data = base_input(); clone = copy.deepcopy(data["campaigns"][1])
        clone["campaign_id"] = "dup"
        clone["target_org"] = data["campaigns"][0]["target_org"].upper()
        clone["route"] = data["campaigns"][0]["route"].upper()
        data["campaigns"].append(clone)
        with self.assertRaisesRegex(AttributionError, "duplicate target×route×purpose"):
            compile_attribution(data)

    def test_duplicate_campaign_id_rejected(self):
        data = base_input(); data["campaigns"][1]["campaign_id"] = "c-paid"
        with self.assertRaisesRegex(AttributionError, "duplicate campaign_id"):
            compile_attribution(data)

    def test_sent_requires_muse(self):
        data = base_input(); data["campaigns"][0]["events"] = data["campaigns"][0]["events"][1:]
        with self.assertRaisesRegex(AttributionError, "fresh preceding MUSE_SELECTED"):
            compile_attribution(data)

    def test_repeat_send_requires_reply_and_fresh_muse(self):
        data = base_input(); c = data["campaigns"][1]
        c["events"] += [
            event("MUSE_SELECTED", "2026-09-11T10:00:00-04:00", "muse:b:2"),
            event("SENT", "2026-09-11T10:01:00-04:00", "gmail:b:2"),
        ]
        with self.assertRaisesRegex(AttributionError, "repeat SENT requires HUMAN_REPLY"):
            compile_attribution(data)

    def test_repeat_send_after_reply_and_fresh_muse_valid(self):
        data = base_input(); c = data["campaigns"][1]
        c["events"] += [
            event("HUMAN_REPLY", "2026-09-11T09:00:00-04:00", "reply:b"),
            event("MUSE_SELECTED", "2026-09-11T10:00:00-04:00", "muse:b:2"),
            event("SENT", "2026-09-11T10:01:00-04:00", "gmail:b:2"),
        ]
        summary = next(c for c in compile_attribution(data)["campaigns"] if c["campaign_id"] == "c-mature")["summary"]
        self.assertEqual(summary["sent_count"], 2)

    def test_chronology_reversal_rejected(self):
        data = base_input(); data["campaigns"][0]["events"][1]["at"] = "2026-09-09T10:00:00-04:00"
        with self.assertRaisesRegex(AttributionError, "reverses chronology"):
            compile_attribution(data)

    def test_event_after_as_of_rejected(self):
        data = base_input(); data["campaigns"][2]["events"][-1]["at"] = "2026-09-18T01:30:00-04:00"
        with self.assertRaisesRegex(AttributionError, "after as_of"):
            compile_attribution(data)

    def test_qualified_requires_reply(self):
        data = base_input(); data["campaigns"][1]["events"].append(event("QUALIFIED", "2026-09-11T10:00:00-04:00", "bad:q"))
        with self.assertRaisesRegex(AttributionError, "QUALIFIED requires"):
            compile_attribution(data)

    def test_accepted_requires_proposal_and_reply(self):
        data = base_input(); c = sent_campaign("z", "Zeta", "z@example.com", "2026-09-10T00:00:00Z")
        c["events"] += [event("HUMAN_REPLY", "2026-09-10T01:00:00Z", "z:r"), event("ACCEPTED", "2026-09-10T02:00:00Z", "z:a", money(100))]
        data["campaigns"] = [c]
        with self.assertRaisesRegex(AttributionError, "ACCEPTED requires"):
            compile_attribution(data)

    def test_paid_requires_invoice(self):
        data = base_input(); c = data["campaigns"][0]
        c["events"] = [e for e in c["events"] if e["type"] != "INVOICED"]
        with self.assertRaisesRegex(AttributionError, "PAID requires prior INVOICED"):
            compile_attribution(data)

    def test_paid_cannot_exceed_invoice(self):
        data = base_input(); c = data["campaigns"][0]
        next(e for e in c["events"] if e["type"] == "PAID")["amount"]["amount_minor"] = 600000
        with self.assertRaisesRegex(AttributionError, "paid amount cannot exceed invoiced"):
            compile_attribution(data)

    def test_money_currency_conversion_is_not_allowed(self):
        data = base_input(); c = data["campaigns"][0]
        next(e for e in c["events"] if e["type"] == "PAID")["amount"] = money(500000, "EUR", 2)
        with self.assertRaisesRegex(AttributionError, "one native currency"):
            compile_attribution(data)

    def test_bool_is_not_integer_money(self):
        data = base_input(); c = data["campaigns"][0]
        next(e for e in c["events"] if e["type"] == "PAID")["amount"]["amount_minor"] = True
        with self.assertRaisesRegex(AttributionError, "must be an integer"):
            compile_attribution(data)

    def test_empty_evidence_refs_rejected(self):
        data = base_input(); data["campaigns"][0]["events"][0]["evidence_refs"] = []
        with self.assertRaisesRegex(AttributionError, "at least one evidence"):
            compile_attribution(data)

    def test_dnr_is_cleared_only_by_explicit_human_or_route_recovery_event(self):
        data = base_input(); data["campaigns"][3]["events"] += [event("ROUTE_RECOVERED", "2026-09-16T00:00:00-04:00", "provider:d:recovered")]
        summary = next(x for x in compile_attribution(data)["campaigns"] if x["campaign_id"] == "c-bounce")["summary"]
        self.assertFalse(summary["active_bounce"])
        self.assertFalse(summary["dnr_active"])
        self.assertEqual(summary["next_contact_disposition"], "OWNER_REVIEW_ONLY")

    def test_route_recovery_without_prior_hold_rejected(self):
        data = base_input(); data["campaigns"][1]["events"].append(event("ROUTE_RECOVERED", "2026-09-11T00:00:00-04:00", "bad:recover"))
        with self.assertRaisesRegex(AttributionError, "requires prior BOUNCE or DNR"):
            compile_attribution(data)

    def test_rejected_requires_human_reply(self):
        data = base_input(); data["campaigns"][1]["events"].append(event("REJECTED", "2026-09-11T00:00:00-04:00", "bad:reject"))
        with self.assertRaisesRegex(AttributionError, "REJECTED requires"):
            compile_attribution(data)

    def test_strict_json_rejects_duplicate_keys(self):
        with self.assertRaisesRegex(AttributionError, "duplicate JSON key"):
            strict_json_loads('{"a":1,"a":2}')

    def test_strict_json_rejects_float_and_nan(self):
        with self.assertRaises(AttributionError):
            strict_json_loads('{"a":1.25}')
        with self.assertRaises(AttributionError):
            strict_json_loads('{"a":NaN}')

    def test_forged_packet_fails_verification(self):
        data = base_input(); packet = compile_attribution(data)
        packet["cohorts"][0]["paid_targets"] = 99
        self.assertFalse(verify_attribution(data, packet))

    def test_reminted_receipt_fails_verification(self):
        data = base_input(); packet = compile_attribution(data)
        packet["receipt"]["sha256"] = "0" * 64
        self.assertFalse(verify_attribution(data, packet))

    def test_cli_compile_and_verify(self):
        with tempfile.TemporaryDirectory() as td:
            input_path = os.path.join(td, "input.json")
            packet_path = os.path.join(td, "packet.json")
            with open(input_path, "w", encoding="utf-8") as fh:
                json.dump(base_input(), fh)
            env = dict(os.environ); env["PYTHONPATH"] = os.path.dirname(__file__)
            cp = subprocess.run([sys.executable, "-m", "revenue.outreach_cohort_attribution.core", "compile", input_path, packet_path], env=env, capture_output=True, text=True)
            self.assertEqual(cp.returncode, 0, cp.stderr)
            vp = subprocess.run([sys.executable, "-m", "revenue.outreach_cohort_attribution.core", "verify", input_path, packet_path], env=env, capture_output=True, text=True)
            self.assertEqual(vp.returncode, 0, vp.stderr)


if __name__ == "__main__":
    unittest.main()
