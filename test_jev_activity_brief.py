import copy
import unittest

from integrations.command_center.jev_action_loop import compile_action, make_readback_receipt
from integrations.command_center.jev_activity_brief import (
    ActivityBriefError,
    OPERATION_ID,
    SCHEMA,
    compile_brief,
    verify_brief,
)
from integrations.command_center.jev_event_ledger import SCHEMA as LEDGER_INPUT_SCHEMA
from integrations.command_center.jev_event_ledger import compile_ledger


NOW = "2026-09-20T20:00:00Z"


def source(
    source_id="slack-coord",
    provider="slack",
    *,
    status="OK",
    last_good="2026-09-20T19:59:00Z",
    complete=True,
    has_more=False,
):
    return {
        "source_id": source_id,
        "connector": f"{provider}-connector",
        "provider": provider,
        "scope": ["coordination"],
        "cursor": "cursor-1",
        "high_water_mark": "hwm-1",
        "observed_at": "2026-09-20T19:59:30Z",
        "last_successful_read": last_good,
        "status": status,
        "cooldown_until": None,
        "coverage": {
            "window_start": "2026-09-19T00:00:00Z",
            "window_end": "2026-09-20T19:59:30Z",
            "complete": complete,
            "has_more": has_more,
            "pages_read": 2,
            "items_read": 10,
        },
        "source_url": "https://example.test/source",
    }


def event(
    event_id,
    *,
    kind="MESSAGE",
    stage="EVENT",
    provider_time="2026-09-20T19:55:00Z",
    actor="user-1",
    work=None,
    operation=None,
    source_id="slack-coord",
    url=None,
):
    return {
        "event_id": event_id,
        "source_id": source_id,
        "provider_event_time": provider_time,
        "observed_at": "2026-09-20T19:56:00Z",
        "stage": stage,
        "kind": kind,
        "actor_id": actor,
        "work_id": work,
        "operation_id": operation,
        "source_url": url or f"https://example.test/event/{event_id}",
    }


def ledger(events=None, sources=None):
    packet = {
        "schema": LEDGER_INPUT_SCHEMA,
        "snapshot_id": "snapshot-brief-1",
        "max_source_age_seconds": 300,
        "sources": sources or [source()],
        "events": events or [event("message-1")],
        "aliases": [],
    }
    return compile_ledger(packet, evaluated_at=NOW)


def receipt(*, outcome="CONFIRMED", observed_at="2026-09-20T19:58:00Z", op_suffix="1"):
    observations = [{
        "provider": "slack",
        "scope": "coordination",
        "resource_id": f"thread-{op_suffix}",
        "event_id": f"event-{op_suffix}",
        "status": "OPEN",
        "provider_event_at": "2026-09-20T19:50:00Z",
        "observed_at": "2026-09-20T19:51:00Z",
        "source_url": f"https://example.test/thread/{op_suffix}",
    }]
    decision = {
        "model": "jev-1.13.0",
        "surface": "swarm-radar",
        "selected_action": "UPDATE_SHARED_VIEW",
        "confidence_ppm": 900000,
        "answers_sha256": "a" * 64,
        "decided_at": "2026-09-20T19:52:00Z",
    }
    target = {
        "provider": "slack",
        "destination_id": "C0BU51F1PL3",
        "thread_id": "1789928286.342349",
    }
    plan = compile_action(observations, decision, target)
    return make_readback_receipt(
        plan,
        provider_resource_id=f"message-{op_suffix}" if outcome == "CONFIRMED" else None,
        provider_observed_operation_id=plan["operation_id"] if outcome == "CONFIRMED" else None,
        source_url=f"https://example.test/receipt/{op_suffix}",
        outcome=outcome,
        attempted_at="2026-09-20T19:57:00Z",
        observed_at=observed_at,
    )


class ActivityBriefTests(unittest.TestCase):
    def test_basic_brief_verifies(self):
        result = compile_brief(ledger())
        self.assertEqual(result["schema"], SCHEMA)
        self.assertEqual(result["operation_id"], OPERATION_ID)
        self.assertTrue(verify_brief(result))
        self.assertIn("Jev swarm activity brief", result["markdown"])

    def test_stable_operation_across_generations(self):
        one = compile_brief(ledger([event("a")]))
        two = compile_brief(ledger([event("a"), event("b")]))
        self.assertEqual(one["operation_id"], two["operation_id"])
        self.assertNotEqual(one["generation_sha256"], two["generation_sha256"])

    def test_exact_windows_projected(self):
        result = compile_brief(ledger())
        self.assertEqual([row["label"] for row in result["windows"]], ["15m", "1h", "24h", "historical"])
        self.assertEqual(result["windows"][0]["event_count"], 1)

    def test_stage_counts_remain_separate(self):
        report = ledger([
            event("m"),
            event("c", kind="CLAIM", stage="CLAIM", work="w1"),
            event("s", kind="SESSION", stage="CONFIRMED_SESSION"),
            event("a", kind="ACCEPTED", stage="PROVIDER_ACCEPTED", work="w1", operation="op1"),
            event("l", kind="LANDED", stage="LANDED", work="w1", operation="op1"),
            event("o", kind="BUSINESS_OUTCOME", stage="BUSINESS_OUTCOME", work="w1"),
        ])
        stage = compile_brief(report)["windows"][0]["by_stage"]
        self.assertEqual(stage["EVENT"], 1)
        self.assertEqual(stage["CLAIM"], 1)
        self.assertEqual(stage["CONFIRMED_SESSION"], 1)
        self.assertEqual(stage["PROVIDER_ACCEPTED"], 1)
        self.assertEqual(stage["LANDED"], 1)
        self.assertEqual(stage["BUSINESS_OUTCOME"], 1)

    def test_attention_only_exact_event_kinds(self):
        report = ledger([
            event("ask", kind="ASK", work="w1"),
            event("owner", kind="OWNER_DIRECTION"),
            event("handoff", kind="HANDOFF", work="w2"),
            event("collision", kind="COLLISION", work="w2"),
            event("ordinary", kind="MESSAGE"),
        ])
        kinds = [row["kind"] for row in compile_brief(report)["attention_candidates"]]
        self.assertEqual(set(kinds), {"ASK", "OWNER_DIRECTION", "HANDOFF", "COLLISION"})
        self.assertNotIn("MESSAGE", kinds)

    def test_attention_is_recent_first_and_bounded(self):
        events = [
            event(f"ask-{i}", kind="ASK", provider_time=f"2026-09-20T19:{30+i:02d}:00Z")
            for i in range(13)
        ]
        rows = compile_brief(ledger(events))["attention_candidates"]
        self.assertEqual(len(rows), 12)
        self.assertEqual(rows[0]["event_id"], "ask-12")
        self.assertNotIn("ask-0", {row["event_id"] for row in rows})

    def test_attention_markdown_does_not_claim_unanswered(self):
        result = compile_brief(ledger([event("ask", kind="ASK")]))
        self.assertIn("not assertions that an obligation remains unanswered", result["markdown"])

    def test_partial_source_remains_lower_bound(self):
        report = ledger(sources=[source(status="PARTIAL", complete=False, has_more=True)])
        result = compile_brief(report)
        self.assertEqual(result["freshness"]["degraded"], 1)
        self.assertEqual(result["freshness"]["partial"], 1)
        self.assertEqual(result["windows"][0]["coverage_state"], "LOWER_BOUND")
        self.assertIn("lower-bound", result["markdown"])

    def test_stale_source_visible(self):
        report = ledger(sources=[source(last_good="2026-09-20T19:30:00Z")])
        result = compile_brief(report)
        self.assertEqual(result["freshness"]["degraded_source_ids"], ["slack-coord"])
        self.assertIn("`slack-coord`", result["markdown"])

    def test_confirmed_receipt_projects_provider_readback(self):
        result = compile_brief(ledger(), [receipt()])
        self.assertEqual(result["actions"]["receipt_count"], 1)
        self.assertEqual(result["actions"]["confirmed"], 1)
        self.assertEqual(result["action_receipts"][0]["outcome"], "CONFIRMED")
        self.assertIn("CONFIRMED", result["markdown"])

    def test_delivery_uncertain_receipt_not_promoted(self):
        result = compile_brief(ledger(), [receipt(outcome="DELIVERY_UNCERTAIN")])
        self.assertEqual(result["actions"]["confirmed"], 0)
        self.assertEqual(result["actions"]["delivery_uncertain"], 1)

    def test_rejected_receipt_counted(self):
        result = compile_brief(ledger(), [receipt(outcome="REJECTED")])
        self.assertEqual(result["actions"]["rejected"], 1)

    def test_duplicate_receipt_digest_collapses(self):
        r = receipt()
        result = compile_brief(ledger(), [r, copy.deepcopy(r)])
        self.assertEqual(result["actions"]["receipt_count"], 1)

    def test_receipt_newer_than_ledger_rejected(self):
        with self.assertRaises(ActivityBriefError):
            compile_brief(ledger(), [receipt(observed_at="2026-09-20T20:01:00Z")])

    def test_tampered_receipt_rejected(self):
        r = receipt()
        r["destination_id"] = "other-channel"
        with self.assertRaises(ActivityBriefError):
            compile_brief(ledger(), [r])

    def test_tampered_ledger_rejected(self):
        report = ledger()
        report["windows"][0]["event_count"] += 100
        with self.assertRaises(ActivityBriefError):
            compile_brief(report)

    def test_authority_is_hard_false(self):
        authority = compile_brief(ledger())["authority"]
        self.assertEqual(authority, {
            "provider_send_authority": False,
            "provider_edit_authority": False,
            "claim_authority": False,
            "merge_authority": False,
            "payment_authority": False,
            "raw_private_text_included": False,
        })

    def test_publication_contract_is_update_not_spray(self):
        result = compile_brief(ledger())
        self.assertEqual(result["publication"]["mode"], "EDIT_EXISTING_OR_CREATE_ONCE")
        self.assertTrue(result["publication"]["requires_provider_readback"])
        self.assertIn(OPERATION_ID, result["markdown"])

    def test_brief_tamper_rejected(self):
        result = compile_brief(ledger())
        result["windows"][0]["event_count"] += 1
        self.assertFalse(verify_brief(result))

    def test_markdown_tamper_rejected_even_if_structured_body_unchanged(self):
        result = compile_brief(ledger())
        result["markdown"] += "forged\n"
        self.assertFalse(verify_brief(result))

    def test_generation_is_deterministic_for_input_order(self):
        r1 = receipt(op_suffix="1")
        r2 = receipt(op_suffix="2")
        one = compile_brief(ledger([event("b"), event("a")]), [r2, r1])
        two = compile_brief(ledger([event("a"), event("b")]), [r1, r2])
        self.assertEqual(one["generation_sha256"], two["generation_sha256"])
        self.assertEqual(one["record_sha256"], two["record_sha256"])


if __name__ == "__main__":
    unittest.main()
