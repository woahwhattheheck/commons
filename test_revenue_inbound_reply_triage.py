from __future__ import annotations

import copy
import subprocess
import sys
import unittest

from revenue.inbound_reply_triage.core import (
    AUTHORITY,
    INPUT_SCHEMA,
    TriageError,
    compile_triage,
    make_receipt,
    strict_json_loads,
    verify_triage,
)


def event(kind: str, at: str, key: str):
    return {"id": key, "type": kind, "at": at, "evidence_refs": [f"evidence:{key}"]}


def lease(*, expires="2026-09-17T06:00:00Z"):
    return {
        "holder": "sol-z",
        "acquired_at": "2026-09-17T03:00:00Z",
        "expires_at": expires,
        "evidence_refs": ["slack:lease:1"],
    }


def lane(lid: str, events, *, lease_value=None, org=None, route=None, thread=None):
    return {
        "id": lid,
        "org_key": org or f"Org {lid}",
        "route_key": route or f"{lid}@example.com",
        "domain": "example.com",
        "purpose_key": "PAID-WORK",
        "thread_key": thread or f"thread:{lid}",
        "lease": lease_value,
        "events": events,
    }


def base_input():
    return {
        "schema": INPUT_SCHEMA,
        "evaluation_at": "2026-09-17T04:00:00Z",
        "stale_after_minutes": 120,
        "lanes": [],
    }


class InboundReplyTriageTests(unittest.TestCase):
    def test_unsolicited_human_inbound_is_surfaced_without_prior_send(self):
        data = base_input()
        data["lanes"] = [lane("hot", [event("HUMAN_REPLY", "2026-09-17T03:30:00Z", "h1")])]
        packet = compile_triage(data)
        self.assertEqual(packet["owner_review_queue"][0]["state"], "NEW_HUMAN_INBOUND")
        self.assertEqual(packet["owner_review_queue"][0]["human_reply_age_minutes"], 30)
        self.assertEqual(packet["owner_review_queue"][0]["next_gate"], "MUSE_REQUIRED_BEFORE_ANY_SEND")
        self.assertTrue(all(value is False for value in packet["authority"].values()))

    def test_draft_plus_active_lease_is_owner_review_ready_not_send_authority(self):
        data = base_input()
        data["lanes"] = [lane("ready", [
            event("HUMAN_REPLY", "2026-09-17T03:00:00Z", "h"),
            event("RESPONSE_DRAFT_READY", "2026-09-17T03:10:00Z", "d"),
        ], lease_value=lease())]
        row = compile_triage(data)["owner_review_queue"][0]
        self.assertEqual(row["state"], "RESPONSE_READY_OWNER_REVIEW")
        self.assertEqual(row["active_lease_holder"], "sol-z")
        self.assertEqual(row["next_gate"], "MUSE_REQUIRED_BEFORE_ANY_SEND")

    def test_expired_lease_holds_draft(self):
        data = base_input()
        data["lanes"] = [lane("expired", [
            event("HUMAN_REPLY", "2026-09-17T02:00:00Z", "h"),
            event("RESPONSE_DRAFT_READY", "2026-09-17T02:10:00Z", "d"),
        ], lease_value=lease(expires="2026-09-17T03:30:00Z"))]
        self.assertEqual(compile_triage(data)["owner_review_queue"][0]["state"], "COLLISION_HOLD")

    def test_sent_requires_fresh_muse_and_repeat_send_requires_reply(self):
        data = base_input()
        data["lanes"] = [lane("bad", [event("SENT", "2026-09-17T01:00:00Z", "s")])]
        with self.assertRaisesRegex(TriageError, "fresh prior MUSE_SELECTED"):
            compile_triage(data)
        data["lanes"] = [lane("repeat", [
            event("MUSE_SELECTED", "2026-09-17T01:00:00Z", "m1"),
            event("SENT", "2026-09-17T01:01:00Z", "s1"),
            event("MUSE_SELECTED", "2026-09-17T02:00:00Z", "m2"),
            event("SENT", "2026-09-17T02:01:00Z", "s2"),
        ])]
        with self.assertRaisesRegex(TriageError, "repeat SENT requires"):
            compile_triage(data)

    def test_send_authority_predecessors_must_be_strictly_earlier(self):
        data = base_input()
        data["lanes"] = [lane("same-muse", [
            event("MUSE_SELECTED", "2026-09-17T01:00:00Z", "m"),
            event("SENT", "2026-09-17T01:00:00Z", "s"),
        ])]
        with self.assertRaisesRegex(TriageError, "fresh prior MUSE_SELECTED"):
            compile_triage(data)

        data["lanes"] = [lane("repeat-same-muse", [
            event("MUSE_SELECTED", "2026-09-17T01:00:00Z", "m1"),
            event("SENT", "2026-09-17T01:01:00Z", "s1"),
            event("HUMAN_REPLY", "2026-09-17T01:30:00Z", "h"),
            event("MUSE_SELECTED", "2026-09-17T02:00:00Z", "m2"),
            event("SENT", "2026-09-17T02:00:00Z", "s2"),
        ])]
        with self.assertRaisesRegex(TriageError, "fresh prior MUSE_SELECTED"):
            compile_triage(data)

        data["lanes"] = [lane("repeat-same-human", [
            event("MUSE_SELECTED", "2026-09-17T01:00:00Z", "m1"),
            event("SENT", "2026-09-17T01:01:00Z", "s1"),
            event("MUSE_SELECTED", "2026-09-17T01:30:00Z", "m2"),
            event("HUMAN_REPLY", "2026-09-17T02:00:00Z", "h"),
            event("SENT", "2026-09-17T02:00:00Z", "s2"),
        ])]
        with self.assertRaisesRegex(TriageError, "repeat SENT requires"):
            compile_triage(data)

        data["lanes"] = [lane("valid-repeat", [
            event("MUSE_SELECTED", "2026-09-17T01:00:00Z", "m1"),
            event("SENT", "2026-09-17T01:01:00Z", "s1"),
            event("HUMAN_REPLY", "2026-09-17T02:00:00Z", "h"),
            event("MUSE_SELECTED", "2026-09-17T02:01:00Z", "m2"),
            event("SENT", "2026-09-17T02:02:00Z", "s2"),
        ])]
        self.assertEqual(compile_triage(data)["owner_review_queue"][0]["state"], "WAITING_EXTERNAL")

    def test_waiting_external(self):
        data = base_input()
        data["lanes"] = [lane("waiting", [
            event("MUSE_SELECTED", "2026-09-17T01:00:00Z", "m"),
            event("SENT", "2026-09-17T01:01:00Z", "s"),
        ])]
        self.assertEqual(compile_triage(data)["owner_review_queue"][0]["state"], "WAITING_EXTERNAL")

    def test_auto_reply_and_bounce_are_not_human_reply(self):
        for kind, expected in [("AUTO_REPLY", "AUTO_REPLY"), ("HARD_BOUNCE", "BOUNCE"), ("SOFT_BOUNCE", "WAITING_EXTERNAL")]:
            data = base_input()
            data["lanes"] = [lane(kind.lower(), [
                event("MUSE_SELECTED", "2026-09-17T01:00:00Z", f"{kind}-m"),
                event("SENT", "2026-09-17T01:01:00Z", f"{kind}-s"),
                event(kind, "2026-09-17T01:02:00Z", f"{kind}-x"),
            ])]
            self.assertEqual(compile_triage(data)["owner_review_queue"][0]["state"], expected)
            self.assertIsNone(compile_triage(data)["owner_review_queue"][0]["latest_human_reply_at"])

    def test_dnr_and_collision_precedence(self):
        data = base_input()
        data["lanes"] = [
            lane("dnr", [
                event("MUSE_SELECTED", "2026-09-17T01:00:00Z", "dm"),
                event("SENT", "2026-09-17T01:01:00Z", "ds"),
                event("DNR", "2026-09-17T01:02:00Z", "dd"),
            ]),
            lane("collision", [event("COLLISION", "2026-09-17T02:00:00Z", "c")]),
        ]
        states = {x["lane_id"]: x["state"] for x in compile_triage(data)["owner_review_queue"]}
        self.assertEqual(states["dnr"], "DNR")
        self.assertEqual(states["collision"], "COLLISION_HOLD")

    def test_later_human_reply_reopens_dnr_for_inbound_review_only(self):
        data = base_input()
        data["lanes"] = [lane("reopen", [
            event("MUSE_SELECTED", "2026-09-17T01:00:00Z", "m"),
            event("SENT", "2026-09-17T01:01:00Z", "s"),
            event("DNR", "2026-09-17T01:02:00Z", "d"),
            event("HUMAN_REPLY", "2026-09-17T02:00:00Z", "h"),
        ])]
        row = compile_triage(data)["owner_review_queue"][0]
        self.assertEqual(row["state"], "NEW_HUMAN_INBOUND")
        self.assertEqual(row["next_gate"], "MUSE_REQUIRED_BEFORE_ANY_SEND")

    def test_rejection(self):
        data = base_input()
        data["lanes"] = [lane("rej", [event("HUMAN_REPLY", "2026-09-17T02:00:00Z", "h"), event("REJECTION", "2026-09-17T02:01:00Z", "r")])]
        self.assertEqual(compile_triage(data)["owner_review_queue"][0]["state"], "REJECTION")

    def test_no_events_requires_muse_before_any_outbound(self):
        data = base_input()
        data["lanes"] = [lane("cold", [])]
        self.assertEqual(compile_triage(data)["owner_review_queue"][0]["state"], "MUSE_REQUIRED")

    def test_stale_hot_reply_prioritizes_before_newer_hot_reply(self):
        data = base_input()
        data["lanes"] = [
            lane("new", [event("HUMAN_REPLY", "2026-09-17T03:50:00Z", "n")]),
            lane("old", [event("HUMAN_REPLY", "2026-09-17T01:00:00Z", "o")]),
        ]
        queue = compile_triage(data)["owner_review_queue"]
        self.assertEqual([row["lane_id"] for row in queue], ["old", "new"])
        self.assertTrue(queue[0]["human_reply_stale"])
        self.assertFalse(queue[1]["human_reply_stale"])

    def test_duplicate_lane_and_binding_rejected(self):
        data = base_input()
        one = lane("a", [])
        data["lanes"] = [one, copy.deepcopy(one)]
        with self.assertRaisesRegex(TriageError, "duplicate lane id"):
            compile_triage(data)
        two = lane("b", [], org=one["org_key"], route=one["route_key"], thread=one["thread_key"])
        data["lanes"] = [one, two]
        with self.assertRaisesRegex(TriageError, "duplicate org×route×purpose×thread"):
            compile_triage(data)

    def test_binding_keys_reject_invisible_controls_and_non_nfkc(self):
        cases = [
            ("org_key", "Ac\u200bme", "invisible/control"),
            ("org_key", "Ac\u202eme", "invisible/control"),
            ("route_key", "sales\u2060@example.com", "invisible/control"),
            ("org_key", "\uff21cme", "exact NFKC"),
            ("org_key", "Cafe\u0301", "exact NFKC"),
        ]
        for field, value, message in cases:
            with self.subTest(field=field, value=repr(value)):
                data = base_input()
                candidate = lane("u", [])
                candidate[field] = value
                data["lanes"] = [candidate]
                with self.assertRaisesRegex(TriageError, message):
                    compile_triage(data)

        data = base_input()
        data["lanes"] = [lane("accent", [], org="Caf\u00e9", route="caf\u00e9@example.com")]
        packet = compile_triage(data)
        self.assertEqual(packet["lanes"][0]["binding"]["org_key"], "Caf\u00e9")

    def test_chronology_future_and_same_second_ambiguity_fail_closed(self):
        data = base_input()
        data["lanes"] = [lane("reverse", [
            event("HUMAN_REPLY", "2026-09-17T03:00:00Z", "a"),
            event("RESPONSE_DRAFT_READY", "2026-09-17T02:59:00Z", "b"),
        ])]
        with self.assertRaisesRegex(TriageError, "chronology reverses"):
            compile_triage(data)
        data["lanes"] = [lane("future", [event("HUMAN_REPLY", "2026-09-17T05:00:00Z", "f")])]
        with self.assertRaisesRegex(TriageError, "after evaluation_at"):
            compile_triage(data)
        data["lanes"] = [lane("same", [
            event("HUMAN_REPLY", "2026-09-17T03:00:00Z", "h"),
            event("REJECTION", "2026-09-17T03:00:00Z", "r"),
        ])]
        with self.assertRaisesRegex(TriageError, "ambiguous same-time status"):
            compile_triage(data)

    def test_strict_json_rejects_duplicate_keys_float_and_huge_integer(self):
        with self.assertRaisesRegex(TriageError, "duplicate JSON key"):
            strict_json_loads('{"a":1,"a":2}')
        with self.assertRaisesRegex(TriageError, "floats"):
            strict_json_loads('{"x":1.5}')
        with self.assertRaisesRegex(TriageError, "integer token too long"):
            strict_json_loads('{"x":' + '9' * 129 + '}')

    def test_invalid_domain_surrogate_and_bool_integer_rejected(self):
        data = base_input()
        bad = lane("x", [])
        bad["domain"] = "not-a-domain"
        data["lanes"] = [bad]
        with self.assertRaisesRegex(TriageError, "domain invalid"):
            compile_triage(data)
        data = base_input()
        bad = lane("x", [])
        bad["org_key"] = "\ud800"
        data["lanes"] = [bad]
        with self.assertRaisesRegex(TriageError, "surrogate"):
            compile_triage(data)
        data = base_input()
        data["stale_after_minutes"] = True
        with self.assertRaisesRegex(TriageError, "must be integer"):
            compile_triage(data)

    def test_red_closure_executes_under_python_optimized(self):
        script = r'''
from revenue.inbound_reply_triage.core import INPUT_SCHEMA, TriageError, compile_triage

def ev(t, at, i):
    return {"id": i, "type": t, "at": at, "evidence_refs": ["e:" + i]}

def ln(org, events):
    return {"id":"x","org_key":org,"route_key":"x@example.com","domain":"example.com","purpose_key":"PAID-WORK","thread_key":"thread:x","lease":None,"events":events}

def source(lane):
    return {"schema":INPUT_SCHEMA,"evaluation_at":"2026-09-17T04:00:00Z","stale_after_minutes":120,"lanes":[lane]}

bad = [
    ln("Ac\u200bme", []),
    ln("Acme", [ev("MUSE_SELECTED","2026-09-17T01:00:00Z","m"), ev("SENT","2026-09-17T01:00:00Z","s")]),
]
for item in bad:
    try:
        compile_triage(source(item))
    except TriageError:
        pass
    else:
        raise SystemExit(23)
'''
        proc = subprocess.run([sys.executable, "-O", "-c", script], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_receipt_recompiles_and_tamper_fails(self):
        data = base_input()
        data["lanes"] = [lane("hot", [event("HUMAN_REPLY", "2026-09-17T03:30:00Z", "h")])]
        packet = compile_triage(data)
        receipt = make_receipt(data, packet)
        self.assertTrue(verify_triage(data, packet, receipt))
        tampered = copy.deepcopy(packet)
        tampered["owner_review_queue"][0]["state"] = "WAITING_EXTERNAL"
        self.assertFalse(verify_triage(data, tampered, receipt))
        bad_receipt = dict(receipt)
        bad_receipt["packet_sha256"] = "0" * 64
        self.assertFalse(verify_triage(data, packet, bad_receipt))

    def test_authority_is_exactly_hard_false(self):
        expected = {
            "external_send_authorized",
            "muse_selection_authorized",
            "buyer_acceptance_authorized",
            "contract_authorized",
            "invoice_authorized",
            "payment_mutation_authorized",
            "receivable_authorized",
            "revenue_recognition_authorized",
        }
        self.assertEqual(set(AUTHORITY), expected)
        self.assertTrue(all(AUTHORITY[key] is False for key in expected))


if __name__ == "__main__":
    unittest.main()
