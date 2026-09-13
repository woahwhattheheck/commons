from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import unittest

from revenue.sales_meeting_calendar_consumer.calendar_consumer import (
    CALENDAR_ID,
    CAPTURE_SCHEMA,
    CalendarConsumerError,
    HUMAN_AUTHORITY_SCHEMA,
    RECEIPT_SCHEMA,
    TRIGGER_SCHEMA,
    build_google_availability_plan,
    canonical_json_bytes,
    capture_google_availability,
    compile_calendar_consumer,
    google_tool_args,
    render_markdown,
    sha256_hex,
    strict_json_loads,
)


NOW = datetime(2026, 9, 13, 16, 26, tzinfo=timezone.utc)


def trigger(*, thread_ref: str = "thread/demo", windows=None, duration: int = 30):
    windows = windows or [
        {"start": "2026-09-14T17:00:00Z", "end": "2026-09-14T19:00:00Z"},
    ]
    inbound = {
        "observation_id": "gmail/msg-demo",
        "content_sha256": "a" * 64,
        "received_at": "2026-09-13T16:20:00Z",
    }
    authority = {
        "schema": HUMAN_AUTHORITY_SCHEMA,
        "authority_id": "human-auth/demo",
        "provider_ref": "gmail:message",
        "event_id": inbound["observation_id"],
        "event_sha256": inbound["content_sha256"],
        "observed_at": inbound["received_at"],
        "opportunity_id": "opp/demo",
        "thread_ref": thread_ref,
        "classification": "MEETING_REQUEST",
        "verified_human": True,
        "meeting_requested": True,
    }
    return {
        "schema": TRIGGER_SCHEMA,
        "opportunity_id": "opp/demo",
        "owner_ref": "owner/bryce",
        "counterparty_ref": "buyer/demo",
        "thread_ref": thread_ref,
        "inbound": inbound,
        "request": {
            "duration_minutes": duration,
            "timezone": "America/Kentucky/Louisville",
            "windows": windows,
        },
        "prep": {
            "context": [
                {"text": "Buyer asked to discuss the scoped evidence pilot.", "source_ref": "gmail/msg-demo"},
                {"text": "No pricing or timeline commitment is accepted yet.", "source_ref": "scope/current"},
            ],
            "objective": "Confirm fit, decision process, and the smallest truthful paid next step.",
            "key_questions": ["What outcome must the buyer approve?", "Who owns the final decision?"],
            "likely_asks": ["Scope detail", "Delivery timeline"],
            "risks_commitments_to_avoid": ["Do not promise unsupported integrations.", "Do not accept a start date."],
            "recommended_opening": "Thanks for making time; I want to pin down the outcome and acceptance boundary.",
            "recommended_closing": "I will send a bounded written scope only after we confirm the decision path.",
            "owner_actions": ["Review the brief before confirming any slot."],
        },
        "human_authority": authority,
    }


def human_sha(t):
    return sha256_hex(canonical_json_bytes(t["human_authority"]))


def provider_result(*, busy=None, errors=None):
    return {
        "calendars": [{
            "calendar_id": CALENDAR_ID,
            "busy": busy or [],
            "errors": errors,
        }]
    }


class ConsumerTests(unittest.TestCase):
    def plan_and_capture(self, t=None, *, busy=None, errors=None, captured_at=None):
        t = t or trigger()
        hsha = human_sha(t)
        plan = build_google_availability_plan(t, expected_human_authority_sha256=hsha)
        capture = capture_google_availability(
            plan,
            provider_result(busy=busy, errors=errors),
            captured_at=captured_at or NOW - timedelta(minutes=1),
        )
        return t, hsha, plan, capture

    def test_plan_matches_exact_trigger_window_and_timezone(self):
        t, hsha, plan, _ = self.plan_and_capture()
        self.assertEqual(plan["calendar_id"], "primary")
        self.assertEqual(plan["time_min"], "2026-09-14T17:00:00Z")
        self.assertEqual(plan["time_max"], "2026-09-14T19:00:00Z")
        self.assertEqual(plan["response_timezone_str"], "America/Kentucky/Louisville")
        self.assertEqual(plan["human_authority_sha256"], hsha)

    def test_tool_args_are_read_only_freebusy_shape_only(self):
        _, _, plan, _ = self.plan_and_capture()
        self.assertEqual(
            google_tool_args(plan),
            {
                "calendar_ids": ["primary"],
                "time_min": "2026-09-14T17:00:00Z",
                "time_max": "2026-09-14T19:00:00Z",
                "response_timezone_str": "America/Kentucky/Louisville",
            },
        )
        encoded = json.dumps(google_tool_args(plan))
        for forbidden in ("attendees", "title", "create", "update", "delete", "invite"):
            self.assertNotIn(forbidden, encoded)

    def test_empty_busy_live_shape_reaches_owner_review_only(self):
        t, hsha, _, capture = self.plan_and_capture()
        receipt = compile_calendar_consumer(
            t, capture,
            expected_human_authority_sha256=hsha,
            expected_calendar_capture_sha256=capture["capture_sha256"],
            as_of=NOW,
        )
        self.assertEqual(receipt["schema"], RECEIPT_SCHEMA)
        self.assertEqual(receipt["state"], "READY_FOR_OWNER_SCHEDULING_REVIEW")
        authority = receipt["authority"]
        self.assertTrue(authority["owner_review_only"])
        self.assertTrue(authority["calendar_freebusy_read_consumed"])
        for key in (
            "calendar_create", "calendar_update", "calendar_delete", "invite_or_rsvp",
            "provider_send_or_reply", "scheduling_confirmation", "commercial_commitment",
        ):
            self.assertFalse(authority[key])
        self.assertEqual(
            receipt["core_receipt"]["meeting"]["proposed_slot"],
            {"start": "2026-09-14T17:00:00Z", "end": "2026-09-14T17:30:00Z"},
        )

    def test_busy_at_window_start_selects_next_free_duration(self):
        busy = [{"start": "2026-09-14T17:00:00Z", "end": "2026-09-14T17:30:00Z"}]
        t, hsha, _, capture = self.plan_and_capture(busy=busy)
        receipt = compile_calendar_consumer(
            t, capture,
            expected_human_authority_sha256=hsha,
            expected_calendar_capture_sha256=capture["capture_sha256"],
            as_of=NOW,
        )
        self.assertEqual(receipt["state"], "READY_FOR_OWNER_SCHEDULING_REVIEW")
        self.assertEqual(
            receipt["core_receipt"]["meeting"]["proposed_slot"],
            {"start": "2026-09-14T17:30:00Z", "end": "2026-09-14T18:00:00Z"},
        )

    def test_fully_busy_window_is_conflict_not_ready(self):
        busy = [{"start": "2026-09-14T17:00:00Z", "end": "2026-09-14T19:00:00Z"}]
        t, hsha, _, capture = self.plan_and_capture(busy=busy)
        receipt = compile_calendar_consumer(
            t, capture,
            expected_human_authority_sha256=hsha,
            expected_calendar_capture_sha256=capture["capture_sha256"],
            as_of=NOW,
        )
        self.assertEqual(receipt["state"], "SLOT_CONFLICT")

    def test_provider_error_is_unknown_and_requires_fresh_calendar(self):
        t, hsha, _, capture = self.plan_and_capture(errors=[{"reason": "backendError"}])
        self.assertTrue(capture["response"]["calendars"][0]["errors_present"])
        self.assertNotIn("backendError", json.dumps(capture))
        receipt = compile_calendar_consumer(
            t, capture,
            expected_human_authority_sha256=hsha,
            expected_calendar_capture_sha256=capture["capture_sha256"],
            as_of=NOW,
        )
        self.assertEqual(receipt["state"], "CALENDAR_CHECK_REQUIRED")

    def test_offset_busy_is_normalized_to_utc(self):
        busy = [{"start": "2026-09-14T13:00:00-04:00", "end": "2026-09-14T13:30:00-04:00"}]
        _, _, _, capture = self.plan_and_capture(busy=busy)
        self.assertEqual(
            capture["response"]["calendars"][0]["busy"],
            [{"start": "2026-09-14T17:00:00Z", "end": "2026-09-14T17:30:00Z"}],
        )

    def test_capture_outside_exact_query_bounds_rejected(self):
        t = trigger()
        hsha = human_sha(t)
        plan = build_google_availability_plan(t, expected_human_authority_sha256=hsha)
        with self.assertRaisesRegex(CalendarConsumerError, "exceeds exact query bounds"):
            capture_google_availability(
                plan,
                provider_result(busy=[{
                    "start": "2026-09-14T16:59:59Z",
                    "end": "2026-09-14T17:15:00Z",
                }]),
                captured_at=NOW,
            )

    def test_wrong_calendar_rejected(self):
        t = trigger()
        hsha = human_sha(t)
        plan = build_google_availability_plan(t, expected_human_authority_sha256=hsha)
        raw = {"calendars": [{"calendar_id": "someone@example.com", "busy": [], "errors": None}]}
        with self.assertRaisesRegex(CalendarConsumerError, "calendar binding"):
            capture_google_availability(plan, raw, captured_at=NOW)

    def test_external_human_authority_digest_is_required(self):
        t = trigger()
        with self.assertRaisesRegex(CalendarConsumerError, "retained authority"):
            build_google_availability_plan(t, expected_human_authority_sha256="0" * 64)

    def test_unverified_or_nonmeeting_human_authority_rejected(self):
        t = trigger()
        t["human_authority"]["verified_human"] = False
        with self.assertRaisesRegex(CalendarConsumerError, "not verified human meeting intent"):
            build_google_availability_plan(t, expected_human_authority_sha256="0" * 64)

    def test_human_authority_transplant_rejected(self):
        t = trigger()
        t["human_authority"]["thread_ref"] = "thread/other"
        hsha = human_sha(t)
        with self.assertRaisesRegex(CalendarConsumerError, "thread binding mismatch"):
            build_google_availability_plan(t, expected_human_authority_sha256=hsha)

    def test_capture_digest_tamper_rejected_even_if_expected_is_old(self):
        t, hsha, _, capture = self.plan_and_capture()
        original_sha = capture["capture_sha256"]
        capture["captured_at"] = "2026-09-13T16:25:30Z"
        with self.assertRaisesRegex(CalendarConsumerError, "capture digest mismatch"):
            compile_calendar_consumer(
                t, capture,
                expected_human_authority_sha256=hsha,
                expected_calendar_capture_sha256=original_sha,
                as_of=NOW,
            )

    def test_plan_from_different_reply_generation_cannot_be_reused(self):
        first = trigger()
        second = trigger(thread_ref="thread/new-generation")
        second["inbound"]["observation_id"] = "gmail/msg-new"
        second["inbound"]["content_sha256"] = "b" * 64
        second["human_authority"].update({
            "event_id": "gmail/msg-new",
            "event_sha256": "b" * 64,
            "thread_ref": "thread/new-generation",
        })
        second_sha = human_sha(second)
        second_plan = build_google_availability_plan(second, expected_human_authority_sha256=second_sha)
        second_capture = capture_google_availability(second_plan, provider_result(), captured_at=NOW - timedelta(minutes=1))
        first_sha = human_sha(first)
        with self.assertRaisesRegex(CalendarConsumerError, "capture plan human authority mismatch|capture plan does not match"):
            compile_calendar_consumer(
                first, second_capture,
                expected_human_authority_sha256=first_sha,
                expected_calendar_capture_sha256=second_capture["capture_sha256"],
                as_of=NOW,
            )

    def test_stale_capture_cannot_retain_ready(self):
        t, hsha, _, capture = self.plan_and_capture(captured_at=NOW - timedelta(minutes=31))
        receipt = compile_calendar_consumer(
            t, capture,
            expected_human_authority_sha256=hsha,
            expected_calendar_capture_sha256=capture["capture_sha256"],
            as_of=NOW,
        )
        self.assertEqual(receipt["state"], "CALENDAR_CHECK_REQUIRED")

    def test_busy_capture_from_old_request_cannot_be_freshened_by_as_of_only(self):
        t, hsha, _, capture = self.plan_and_capture(captured_at=NOW - timedelta(hours=3))
        receipt = compile_calendar_consumer(
            t, capture,
            expected_human_authority_sha256=hsha,
            expected_calendar_capture_sha256=capture["capture_sha256"],
            as_of=NOW,
        )
        self.assertNotEqual(receipt["state"], "READY_FOR_OWNER_SCHEDULING_REVIEW")

    def test_request_window_shorter_than_duration_rejected_before_query(self):
        t = trigger(
            windows=[{"start": "2026-09-14T17:00:00Z", "end": "2026-09-14T17:20:00Z"}],
            duration=30,
        )
        hsha = human_sha(t)
        with self.assertRaisesRegex(CalendarConsumerError, "shorter than requested duration"):
            build_google_availability_plan(t, expected_human_authority_sha256=hsha)

    def test_multiple_windows_use_covering_query_but_slot_stays_inside_requested_window(self):
        t = trigger(windows=[
            {"start": "2026-09-14T17:00:00Z", "end": "2026-09-14T18:00:00Z"},
            {"start": "2026-09-14T20:00:00Z", "end": "2026-09-14T21:00:00Z"},
        ])
        busy = [{"start": "2026-09-14T17:00:00Z", "end": "2026-09-14T18:00:00Z"}]
        t, hsha, plan, capture = self.plan_and_capture(t=t, busy=busy)
        self.assertEqual(plan["time_min"], "2026-09-14T17:00:00Z")
        self.assertEqual(plan["time_max"], "2026-09-14T21:00:00Z")
        receipt = compile_calendar_consumer(
            t, capture,
            expected_human_authority_sha256=hsha,
            expected_calendar_capture_sha256=capture["capture_sha256"],
            as_of=NOW,
        )
        self.assertEqual(receipt["state"], "READY_FOR_OWNER_SCHEDULING_REVIEW")
        self.assertEqual(receipt["core_receipt"]["meeting"]["proposed_slot"]["start"], "2026-09-14T20:00:00Z")

    def test_strict_json_rejects_duplicate_keys(self):
        with self.assertRaisesRegex(CalendarConsumerError, "duplicate JSON key"):
            strict_json_loads('{"schema":"a","schema":"b"}')

    def test_capture_does_not_persist_error_text_or_event_details(self):
        t, _, _, capture = self.plan_and_capture(errors=[{
            "domain": "global",
            "reason": "forbidden",
            "message": "sensitive provider detail",
        }])
        encoded = json.dumps(capture)
        self.assertNotIn("sensitive provider detail", encoded)
        self.assertNotIn("reason", encoded)
        self.assertIn("provider_result_sha256", capture)

    def test_render_contains_full_prep_and_no_scheduling_authority(self):
        t, hsha, _, capture = self.plan_and_capture()
        receipt = compile_calendar_consumer(
            t, capture,
            expected_human_authority_sha256=hsha,
            expected_calendar_capture_sha256=capture["capture_sha256"],
            as_of=NOW,
        )
        md = render_markdown(receipt)
        self.assertIn("Mutation boundary", md)
        self.assertIn("not authorized", md)
        self.assertIn("Confirm fit", md)
        self.assertIn("What outcome must the buyer approve?", md)
        self.assertIn("Do not promise unsupported integrations.", md)

    def test_capture_schema_and_hash_are_deterministic_for_same_inputs(self):
        t = trigger()
        hsha = human_sha(t)
        plan = build_google_availability_plan(t, expected_human_authority_sha256=hsha)
        raw = provider_result()
        a = capture_google_availability(plan, raw, captured_at=NOW)
        b = capture_google_availability(deepcopy(plan), deepcopy(raw), captured_at=NOW)
        self.assertEqual(a, b)
        self.assertEqual(a["schema"], CAPTURE_SCHEMA)


if __name__ == "__main__":
    unittest.main()
