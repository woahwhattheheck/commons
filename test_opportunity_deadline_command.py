#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import os
import tempfile
import unittest
from pathlib import Path

from revenue.opportunity_deadline_command.engine import (
    EvidenceError,
    INPUT_VERSION,
    POLICY_VERSION,
    canonical_bytes,
    compile_portfolio,
    ics_projection,
    loads_strict,
    markdown_projection,
    read_bounded_json,
    verify_result,
    write_new_file,
)

AS_OF = "2026-09-13T12:00:00Z"
H = "a" * 64
H2 = "b" * 64
H3 = "c" * 64


def policy(**overrides):
    value = {
        "schema_version": POLICY_VERSION,
        "max_source_age_minutes": 10080,
        "critical_window_minutes": 1440,
        "high_window_minutes": 10080,
        "addenda_review_window_minutes": 20160,
    }
    value.update(overrides)
    return value


def source(source_id="official-1", authority="OFFICIAL", captured_at="2026-09-13T10:00:00Z", sha=H,
           url="https://buyer.example.gov/rfp", generation=1):
    return {
        "source_id": source_id,
        "authority": authority,
        "captured_at": captured_at,
        "sha256": sha,
        "url": url,
        "label": f"Source {source_id}",
        "generation": generation,
    }


def deadline(deadline_id="response-1", kind="RESPONSE", at="2026-09-20T12:00:00Z", source_id="official-1",
             generation=1, **optional):
    value = {
        "deadline_id": deadline_id,
        "kind": kind,
        "at": at,
        "source_id": source_id,
        "generation": generation,
    }
    value.update(optional)
    return value


def opportunity(opportunity_id="opp-1", **overrides):
    value = {
        "opportunity_id": opportunity_id,
        "buyer": "Example Public Buyer",
        "solicitation_id": "RFP-2026-001",
        "title": "Evidence-bound systems services",
        "owner_ref": "ZCF-C8V4",
        "route_state": "TEAMING",
        "source_set_complete": True,
        "controlling_source_id": "official-1",
        "packet_state": "COMPLETE",
        "sources": [source()],
        "deadlines": [deadline()],
        "blocker_codes": [],
        "owner_action_refs": ["OWNER-REVIEW"],
    }
    value.update(overrides)
    return value


def packet(*opps):
    if not opps:
        opps = (opportunity(),)
    return {"schema_version": INPUT_VERSION, "opportunities": list(opps)}


def row_of(result, opportunity_id="opp-1"):
    return next(row for row in result["rows"] if row["opportunity_id"] == opportunity_id)


class OpportunityDeadlineCommandTests(unittest.TestCase):
    def test_response_window_open(self):
        result = compile_portfolio(packet(), policy(), as_of=AS_OF)
        row = row_of(result)
        self.assertEqual(row["operating_state"], "RESPONSE_WINDOW_OPEN")
        self.assertEqual(row["priority"], "HIGH")
        self.assertEqual(row["next_deadline"]["kind"], "RESPONSE")
        self.assertFalse(result["manifest"]["authority"]["submission_authorized"])

    def test_response_due_soon_at_critical_boundary(self):
        op = opportunity(deadlines=[deadline(at="2026-09-14T12:00:00Z")])
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "RESPONSE_DUE_SOON")
        self.assertEqual(row["priority"], "CRITICAL")
        self.assertEqual(row["next_deadline"]["minutes_remaining"], 1440)

    def test_question_window_precedes_response(self):
        op = opportunity(deadlines=[
            deadline("q-1", "QUESTION", "2026-09-15T12:00:00Z"),
            deadline("response-1", "RESPONSE", "2026-09-20T12:00:00Z"),
        ])
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "QUESTION_WINDOW_OPEN")
        self.assertEqual(row["next_deadline"]["deadline_id"], "q-1")

    def test_conference_action_review(self):
        op = opportunity(deadlines=[
            deadline("conference-1", "CONFERENCE", "2026-09-16T12:00:00Z"),
            deadline("response-1", "RESPONSE", "2026-09-20T12:00:00Z"),
        ])
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "CONFERENCE_ACTION_REVIEW")

    def test_registration_action_review(self):
        op = opportunity(deadlines=[
            deadline("reg-1", "REGISTRATION", "2026-09-16T12:00:00Z"),
            deadline("response-1", "RESPONSE", "2026-09-20T12:00:00Z"),
        ])
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "REGISTRATION_ACTION_REVIEW")

    def test_market_engagement_uses_response_states(self):
        op = opportunity(deadlines=[deadline("pme-1", "MARKET_ENGAGEMENT", "2026-09-20T12:00:00Z")])
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "RESPONSE_WINDOW_OPEN")

    def test_not_yet_open(self):
        op = opportunity(deadlines=[deadline(opens_at="2026-09-15T12:00:00Z")])
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "NOT_YET_OPEN")

    def test_expired_at_exact_deadline_boundary(self):
        op = opportunity(deadlines=[deadline(at=AS_OF)])
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "EXPIRED")
        self.assertEqual(row["priority"], "TERMINAL")

    def test_no_bid_terminal_even_with_future_deadline(self):
        op = opportunity(route_state="NO_BID")
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "TERMINAL_NO_BID")

    def test_hold_route_is_hold(self):
        op = opportunity(route_state="HOLD")
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "HOLD")
        self.assertEqual(row["priority"], "HOLD")

    def test_unknown_route_is_hold(self):
        op = opportunity(route_state="UNKNOWN")
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "HOLD")

    def test_incomplete_source_set_requires_recovery(self):
        op = opportunity(source_set_complete=False)
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "SOURCE_RECOVERY_REQUIRED")
        self.assertIn("SOURCE_SET_INCOMPLETE", row["reason_codes"])

    def test_missing_packet_requires_recovery(self):
        op = opportunity(packet_state="MISSING_CONTROLLING_PACKET")
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "SOURCE_RECOVERY_REQUIRED")

    def test_partial_packet_requires_recovery(self):
        op = opportunity(packet_state="PARTIAL")
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "SOURCE_RECOVERY_REQUIRED")

    def test_unchecked_addenda_near_response(self):
        op = opportunity(packet_state="ADDENDA_UNCHECKED")
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "ADDENDA_REVIEW_REQUIRED")

    def test_unchecked_addenda_outside_review_window_does_not_preempt(self):
        op = opportunity(
            packet_state="ADDENDA_UNCHECKED",
            deadlines=[deadline(at="2026-12-20T12:00:00Z")],
        )
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "RESPONSE_WINDOW_OPEN")

    def test_secondary_deadline_cannot_drive_action(self):
        op = opportunity(
            sources=[source(), source("mirror-1", "SECONDARY", sha=H2, url="https://mirror.example/rfp")],
            deadlines=[deadline(source_id="mirror-1")],
        )
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "SOURCE_RECOVERY_REQUIRED")
        self.assertIn("DEADLINE_NOT_OFFICIAL", row["reason_codes"])

    def test_secondary_controlling_source_requires_recovery(self):
        op = opportunity(
            controlling_source_id="mirror-1",
            sources=[source("mirror-1", "SECONDARY", url="https://mirror.example/rfp")],
            deadlines=[deadline(source_id="mirror-1")],
        )
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "SOURCE_RECOVERY_REQUIRED")

    def test_stale_official_source_requires_recovery(self):
        op = opportunity(sources=[source(captured_at="2026-08-01T12:00:00Z")])
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["operating_state"], "SOURCE_RECOVERY_REQUIRED")
        self.assertIn("STALE_OFFICIAL_SOURCE", row["reason_codes"])

    def test_future_source_rejected(self):
        op = opportunity(sources=[source(captured_at="2026-09-14T12:00:00Z")])
        with self.assertRaisesRegex(EvidenceError, "future source"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_question_after_response_rejected(self):
        op = opportunity(deadlines=[
            deadline("q-1", "QUESTION", "2026-09-21T12:00:00Z"),
            deadline("response-1", "RESPONSE", "2026-09-20T12:00:00Z"),
        ])
        with self.assertRaisesRegex(EvidenceError, "QUESTION deadline may not follow"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_registration_after_response_rejected(self):
        op = opportunity(deadlines=[
            deadline("reg-1", "REGISTRATION", "2026-09-21T12:00:00Z"),
            deadline("response-1", "RESPONSE", "2026-09-20T12:00:00Z"),
        ])
        with self.assertRaisesRegex(EvidenceError, "REGISTRATION deadline may not follow"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_deadline_extension_supersedes_old_generation(self):
        op = opportunity(deadlines=[
            deadline("response-1", "RESPONSE", "2026-09-16T12:00:00Z", generation=1),
            deadline(
                "response-2", "RESPONSE", "2026-09-20T12:00:00Z", generation=2,
                supersedes_deadline_id="response-1",
            ),
        ])
        row = row_of(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertEqual(row["next_deadline"]["deadline_id"], "response-2")
        self.assertEqual([d["deadline_id"] for d in row["deadlines"]], ["response-2"])

    def test_deadline_supersession_requires_same_kind(self):
        op = opportunity(deadlines=[
            deadline("q-1", "QUESTION", "2026-09-15T12:00:00Z", generation=1),
            deadline("r-2", "RESPONSE", "2026-09-20T12:00:00Z", generation=2, supersedes_deadline_id="q-1"),
        ])
        with self.assertRaisesRegex(EvidenceError, "preserve kind"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_deadline_supersession_requires_generation_increase(self):
        op = opportunity(deadlines=[
            deadline("response-1", generation=2),
            deadline("response-2", generation=2, supersedes_deadline_id="response-1"),
        ])
        with self.assertRaisesRegex(EvidenceError, "generation must increase"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_ambiguous_same_kind_deadlines_rejected(self):
        op = opportunity(deadlines=[deadline("response-1"), deadline("response-2", at="2026-09-21T12:00:00Z")])
        with self.assertRaisesRegex(EvidenceError, "ambiguous effective"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_duplicate_source_id_rejected(self):
        op = opportunity(sources=[source(), source(sha=H2)])
        with self.assertRaisesRegex(EvidenceError, "duplicate source_id"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_duplicate_opportunity_id_rejected(self):
        with self.assertRaisesRegex(EvidenceError, "duplicate opportunity_id"):
            compile_portfolio(packet(opportunity(), opportunity()), policy(), as_of=AS_OF)

    def test_duplicate_blocker_code_rejected(self):
        op = opportunity(blocker_codes=["PACKET-MISSING", "PACKET-MISSING"])
        with self.assertRaisesRegex(EvidenceError, "duplicate code"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_bool_cannot_alias_policy_integer(self):
        with self.assertRaisesRegex(EvidenceError, "expected integer"):
            compile_portfolio(packet(), policy(critical_window_minutes=True), as_of=AS_OF)

    def test_policy_critical_must_not_exceed_high(self):
        with self.assertRaisesRegex(EvidenceError, "critical_window_minutes"):
            compile_portfolio(packet(), policy(critical_window_minutes=100, high_window_minutes=99), as_of=AS_OF)

    def test_http_source_url_rejected(self):
        op = opportunity(sources=[source(url="http://buyer.example.gov/rfp")])
        with self.assertRaisesRegex(EvidenceError, "HTTPS"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_secret_query_url_rejected(self):
        op = opportunity(sources=[source(url="https://buyer.example.gov/rfp?access_token=abc")])
        with self.assertRaisesRegex(EvidenceError, "secret-shaped"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_bad_digest_rejected(self):
        op = opportunity(sources=[source(sha="not-a-digest")])
        with self.assertRaisesRegex(EvidenceError, "sha256"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_secret_shaped_owner_action_rejected(self):
        op = opportunity(owner_action_refs=["api_key=abcdefghijk"])
        with self.assertRaises(EvidenceError):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_unknown_field_rejected(self):
        op = opportunity()
        op["surprise"] = "nope"
        with self.assertRaisesRegex(EvidenceError, "unknown fields"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(EvidenceError, "duplicate JSON key"):
            loads_strict('{"schema_version":"x","schema_version":"y"}')

    def test_nonfinite_json_rejected(self):
        with self.assertRaisesRegex(EvidenceError, "non-finite"):
            loads_strict('{"x":NaN}')

    def test_order_invariance(self):
        op1 = opportunity("opp-a", buyer="Buyer A")
        op2 = opportunity("opp-b", buyer="Buyer B", solicitation_id="RFP-B")
        a = compile_portfolio(packet(op1, op2), policy(), as_of=AS_OF)
        b = compile_portfolio(packet(op2, op1), policy(), as_of=AS_OF)
        self.assertEqual(canonical_bytes(a), canonical_bytes(b))

    def test_hold_and_source_recovery_sort_before_live(self):
        hold = opportunity("opp-hold", route_state="HOLD")
        recover = opportunity("opp-recover", source_set_complete=False)
        live = opportunity("opp-live")
        rows = compile_portfolio(packet(live, recover, hold), policy(), as_of=AS_OF)["rows"]
        self.assertEqual({rows[0]["operating_state"], rows[1]["operating_state"]}, {"HOLD", "SOURCE_RECOVERY_REQUIRED"})
        self.assertEqual(rows[2]["opportunity_id"], "opp-live")

    def test_queue_tie_breaks_by_opportunity_id(self):
        a = opportunity("opp-a")
        b = opportunity("opp-b")
        rows = compile_portfolio(packet(b, a), policy(), as_of=AS_OF)["rows"]
        self.assertEqual([r["opportunity_id"] for r in rows], ["opp-a", "opp-b"])

    def test_verify_exact_result_at_same_semantic_time(self):
        raw = packet()
        pol = policy()
        result = compile_portfolio(raw, pol, as_of=AS_OF)
        self.assertTrue(verify_result(raw, pol, result, current_as_of="2026-09-13T12:05:00Z"))

    def test_verify_rejects_tamper(self):
        raw = packet()
        pol = policy()
        result = compile_portfolio(raw, pol, as_of=AS_OF)
        result["rows"][0]["buyer"] = "Tampered"
        with self.assertRaisesRegex(EvidenceError, "result mismatch"):
            verify_result(raw, pol, result, current_as_of=AS_OF)

    def test_verify_rejects_policy_drift(self):
        raw = packet()
        result = compile_portfolio(raw, policy(), as_of=AS_OF)
        with self.assertRaisesRegex(EvidenceError, "result mismatch"):
            verify_result(raw, policy(high_window_minutes=10000), result, current_as_of=AS_OF)

    def test_verify_rejects_changed_current_semantics(self):
        raw = packet(opportunity(deadlines=[deadline(at="2026-09-13T13:00:00Z")]))
        pol = policy()
        result = compile_portfolio(raw, pol, as_of=AS_OF)
        with self.assertRaisesRegex(EvidenceError, "no longer current"):
            verify_result(raw, pol, result, current_as_of="2026-09-13T13:00:00Z")

    def test_markdown_is_deterministic_and_has_authority_ceiling(self):
        result = compile_portfolio(packet(), policy(), as_of=AS_OF)
        a = markdown_projection(result)
        b = markdown_projection(result)
        self.assertEqual(a, b)
        self.assertIn("OWNER REVIEW ONLY", a)
        self.assertIn("RESPONSE_WINDOW_OPEN", a)

    def test_markdown_escapes_pipe(self):
        op = opportunity(buyer="Buyer | Division")
        text = markdown_projection(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertIn("Buyer \\| Division", text)

    def test_ics_is_deterministic_and_has_no_attendees(self):
        result = compile_portfolio(packet(), policy(), as_of=AS_OF)
        a = ics_projection(result)
        b = ics_projection(result)
        self.assertEqual(a, b)
        self.assertTrue(a.startswith("BEGIN:VCALENDAR\r\n"))
        self.assertIn("OWNER REVIEW ONLY", a)
        self.assertNotIn("ATTENDEE", a)
        self.assertNotIn("ORGANIZER", a)

    def test_ics_escapes_commas_and_semicolons(self):
        op = opportunity(buyer="Buyer, Division; Lab")
        text = ics_projection(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertIn("Buyer\\, Division\\; Lab", text)

    def test_ics_excludes_secondary_deadlines(self):
        op = opportunity(
            sources=[source(), source("mirror-1", "SECONDARY", sha=H2, url="https://mirror.example/rfp")],
            deadlines=[deadline(source_id="mirror-1")],
        )
        text = ics_projection(compile_portfolio(packet(op), policy(), as_of=AS_OF))
        self.assertNotIn("BEGIN:VEVENT", text)

    def test_write_new_file_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "out.json"
            p.write_text("existing")
            with self.assertRaises(EvidenceError):
                write_new_file(p, b"new")
            self.assertEqual(p.read_text(), "existing")

    def test_write_new_file_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            target.write_text("original")
            link = Path(tmp) / "out"
            link.symlink_to(target)
            with self.assertRaises(EvidenceError):
                write_new_file(link, b"new")
            self.assertEqual(target.read_text(), "original")

    def test_read_bounded_json_refuses_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "input.json"
            target.write_text('{"x":1}')
            link = Path(tmp) / "link.json"
            link.symlink_to(target)
            with self.assertRaises(EvidenceError):
                read_bounded_json(link)

    def test_twenty_opportunity_synthetic_fleet(self):
        opps = []
        for i in range(20):
            op_id = f"fleet-{i:02d}"
            day = 14 + i
            opps.append(
                opportunity(
                    op_id,
                    buyer=f"Buyer {i:02d}",
                    solicitation_id=f"RFP-{i:02d}",
                    deadlines=[deadline(at=f"2026-09-{day:02d}T12:00:00Z")] if day <= 30 else [deadline(at=f"2026-10-{day-30:02d}T12:00:00Z")],
                )
            )
        result = compile_portfolio(packet(*opps), policy(), as_of=AS_OF)
        self.assertEqual(result["manifest"]["counts"]["total"], 20)
        self.assertEqual(len(result["rows"]), 20)
        self.assertEqual(len({r["opportunity_id"] for r in result["rows"]}), 20)
        self.assertNotIn("expected_revenue", json.dumps(result).lower())
        self.assertFalse(result["manifest"]["authority"]["revenue_recognition_authorized"])

    def test_canonical_result_is_byte_stable(self):
        raw = packet()
        pol = policy()
        self.assertEqual(
            canonical_bytes(compile_portfolio(raw, pol, as_of=AS_OF)),
            canonical_bytes(compile_portfolio(copy.deepcopy(raw), copy.deepcopy(pol), as_of=AS_OF)),
        )

    def test_opens_after_deadline_rejected(self):
        op = opportunity(deadlines=[deadline(opens_at="2026-09-21T12:00:00Z")])
        with self.assertRaisesRegex(EvidenceError, "opens_at"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_response_and_market_engagement_cannot_both_be_effective(self):
        op = opportunity(deadlines=[
            deadline("response-1", "RESPONSE", "2026-09-20T12:00:00Z"),
            deadline("pme-1", "MARKET_ENGAGEMENT", "2026-09-21T12:00:00Z"),
        ])
        with self.assertRaisesRegex(EvidenceError, "cannot both be effective"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_source_generation_bool_rejected(self):
        s = source()
        s["generation"] = True
        op = opportunity(sources=[s])
        with self.assertRaisesRegex(EvidenceError, "expected integer"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)

    def test_deadline_generation_bool_rejected(self):
        d = deadline()
        d["generation"] = True
        op = opportunity(deadlines=[d])
        with self.assertRaisesRegex(EvidenceError, "expected integer"):
            compile_portfolio(packet(op), policy(), as_of=AS_OF)


if __name__ == "__main__":
    unittest.main(verbosity=2)
