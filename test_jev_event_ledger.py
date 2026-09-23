import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from integrations.command_center.jev_event_ledger import (
    LedgerError,
    SCHEMA,
    compile_ledger,
    load_json,
    verify_report,
)


NOW = "2026-09-20T20:00:00Z"


def source(
    source_id="slack-coord",
    provider="slack",
    status="OK",
    complete=True,
    has_more=False,
    last_good="2026-09-20T19:59:00Z",
    observed="2026-09-20T19:59:30Z",
    start="2026-09-19T00:00:00Z",
    end="2026-09-20T20:00:00Z",
    cooldown=None,
):
    return {
        "source_id": source_id,
        "connector": f"{provider}-connector",
        "provider": provider,
        "scope": ["coordination"],
        "cursor": "cursor-1",
        "high_water_mark": "hwm-1",
        "observed_at": observed,
        "last_successful_read": last_good,
        "status": status,
        "cooldown_until": cooldown,
        "coverage": {
            "window_start": start,
            "window_end": end,
            "complete": complete,
            "has_more": has_more,
            "pages_read": 2,
            "items_read": 10,
        },
        "source_url": "https://example.test/source",
    }


def event(
    event_id="slack:C1:1.0",
    source_id="slack-coord",
    provider_time="2026-09-20T19:55:00Z",
    observed="2026-09-20T19:56:00Z",
    stage="EVENT",
    kind="MESSAGE",
    actor="user-1",
    work=None,
    operation=None,
    url="https://example.test/event",
):
    return {
        "event_id": event_id,
        "source_id": source_id,
        "provider_event_time": provider_time,
        "observed_at": observed,
        "stage": stage,
        "kind": kind,
        "actor_id": actor,
        "work_id": work,
        "operation_id": operation,
        "source_url": url,
    }


def packet():
    return {
        "schema": SCHEMA,
        "snapshot_id": "snapshot-1",
        "max_source_age_seconds": 300,
        "sources": [source()],
        "events": [event()],
        "aliases": [],
    }


class LedgerTests(unittest.TestCase):
    def compile(self, value=None):
        return compile_ledger(packet() if value is None else value, evaluated_at=NOW)

    def window(self, report, label):
        return next(row for row in report["windows"] if row["label"] == label)

    def test_basic_report_verifies(self):
        report = self.compile()
        self.assertTrue(verify_report(report))
        self.assertEqual(report["source_summary"]["freshness_counts"], {"FRESH": 1})
        self.assertEqual(self.window(report, "15m")["event_count"], 1)

    def test_windows_are_exact(self):
        p = packet()
        p["events"] = [
            event("e15", provider_time="2026-09-20T19:50:00Z"),
            event("e1h", provider_time="2026-09-20T19:20:00Z"),
            event("e24h", provider_time="2026-09-20T10:00:00Z"),
            event("ehist", provider_time="2026-09-19T10:00:00Z"),
        ]
        report = self.compile(p)
        self.assertEqual(self.window(report, "15m")["event_count"], 1)
        self.assertEqual(self.window(report, "1h")["event_count"], 2)
        self.assertEqual(self.window(report, "24h")["event_count"], 3)
        self.assertEqual(self.window(report, "historical")["event_count"], 4)

    def test_stage_counts_do_not_conflate_activity_and_outcomes(self):
        p = packet()
        p["events"] = [
            event("e0"),
            event("e1", stage="CLAIM", kind="CLAIM", work="w1"),
            event("e2", stage="CONFIRMED_SESSION", kind="SESSION"),
            event("e3", stage="PROVIDER_ACCEPTED", kind="ACCEPTED", work="w1", operation="op1"),
            event("e4", stage="LANDED", kind="LANDED", work="w1", operation="op1"),
            event("e5", stage="BUSINESS_OUTCOME", kind="BUSINESS_OUTCOME", work="w1"),
        ]
        counts = self.window(self.compile(p), "15m")["by_stage"]
        self.assertEqual(counts["EVENT"], 1)
        self.assertEqual(counts["CLAIM"], 1)
        self.assertEqual(counts["CONFIRMED_SESSION"], 1)
        self.assertEqual(counts["PROVIDER_ACCEPTED"], 1)
        self.assertEqual(counts["LANDED"], 1)
        self.assertEqual(counts["BUSINESS_OUTCOME"], 1)

    def test_duplicate_event_across_exports_counts_once(self):
        p = packet()
        p["sources"].append(source("slack-search"))
        p["events"] = [
            event("e1", source_id="slack-coord", observed="2026-09-20T19:56:00Z"),
            event("e1", source_id="slack-search", observed="2026-09-20T19:57:00Z"),
        ]
        report = self.compile(p)
        self.assertEqual(self.window(report, "15m")["event_count"], 1)
        self.assertEqual(report["events"][0]["observed_source_ids"], ["slack-coord", "slack-search"])
        self.assertEqual(self.window(report, "15m")["source_observation_counts"], {
            "slack-coord": 1,
            "slack-search": 1,
        })

    def test_conflicting_same_event_identity_rejected(self):
        p = packet()
        p["events"].append(event("slack:C1:1.0", stage="CONFIRMED_SESSION", kind="SESSION"))
        with self.assertRaises(LedgerError):
            self.compile(p)

    def test_explicit_alias_reduces_before_count(self):
        p = packet()
        p["events"] = [event("canonical"), event("alias")]
        p["aliases"] = [{"alias_event_id": "alias", "canonical_event_id": "canonical"}]
        report = self.compile(p)
        self.assertEqual(self.window(report, "15m")["event_count"], 1)
        self.assertEqual(report["events"][0]["event_id"], "canonical")
        self.assertEqual(report["events"][0]["alias_event_ids"], ["alias"])

    def test_alias_semantic_mismatch_rejected(self):
        p = packet()
        p["events"] = [
            event("canonical"),
            event("alias", provider_time="2026-09-20T19:54:00Z"),
        ]
        p["aliases"] = [{"alias_event_id": "alias", "canonical_event_id": "canonical"}]
        with self.assertRaises(LedgerError):
            self.compile(p)

    def test_alias_cycle_rejected(self):
        p = packet()
        p["events"] = [event("a"), event("b")]
        p["aliases"] = [
            {"alias_event_id": "a", "canonical_event_id": "b"},
            {"alias_event_id": "b", "canonical_event_id": "a"},
        ]
        with self.assertRaises(LedgerError):
            self.compile(p)

    def test_alias_missing_endpoint_rejected(self):
        p = packet()
        p["aliases"] = [{"alias_event_id": "slack:C1:1.0", "canonical_event_id": "missing"}]
        with self.assertRaises(LedgerError):
            self.compile(p)

    def test_partial_pagination_is_lower_bound_not_zero(self):
        p = packet()
        p["sources"] = [source(status="PARTIAL", complete=False, has_more=True)]
        report = self.compile(p)
        win = self.window(report, "15m")
        self.assertEqual(win["event_count"], 1)
        self.assertEqual(win["coverage"]["state"], "LOWER_BOUND")
        self.assertEqual(win["coverage"]["incomplete_or_stale_sources"], ["slack-coord"])
        self.assertEqual(report["source_summary"]["partial_or_paginated_sources"], ["slack-coord"])

    def test_stale_last_good_is_lower_bound(self):
        p = packet()
        p["sources"] = [source(last_good="2026-09-20T19:30:00Z")]
        report = self.compile(p)
        self.assertEqual(report["sources"][0]["freshness"], "STALE")
        self.assertTrue(self.window(report, "15m")["coverage"]["lower_bound"])

    def test_error_retains_last_good_events_as_stale(self):
        p = packet()
        p["sources"] = [source(status="ERROR")]
        report = self.compile(p)
        self.assertEqual(report["sources"][0]["freshness"], "STALE")
        self.assertEqual(self.window(report, "15m")["event_count"], 1)

    def test_no_last_good_is_unavailable(self):
        p = packet()
        p["sources"] = [source(status="ERROR", last_good=None)]
        report = self.compile(p)
        self.assertEqual(report["sources"][0]["freshness"], "UNAVAILABLE")

    def test_active_cooldown_is_visible(self):
        p = packet()
        p["sources"] = [source(
            status="COOLDOWN",
            cooldown="2026-09-20T20:10:00Z",
            complete=False,
            has_more=True,
        )]
        report = self.compile(p)
        self.assertEqual(report["sources"][0]["freshness"], "COOLDOWN")
        self.assertTrue(self.window(report, "15m")["coverage"]["lower_bound"])

    def test_expired_cooldown_status_rejected(self):
        p = packet()
        p["sources"] = [source(
            status="COOLDOWN",
            cooldown="2026-09-20T19:50:00Z",
            complete=False,
            has_more=True,
        )]
        with self.assertRaises(LedgerError):
            self.compile(p)

    def test_coverage_that_does_not_span_window_is_lower_bound(self):
        p = packet()
        p["sources"] = [source(start="2026-09-20T19:50:00Z")]
        report = self.compile(p)
        self.assertEqual(self.window(report, "15m")["coverage"]["state"], "LOWER_BOUND")
        self.assertEqual(self.window(report, "1h")["coverage"]["state"], "LOWER_BOUND")

    def test_complete_fresh_full_window_is_complete(self):
        report = self.compile()
        self.assertEqual(self.window(report, "15m")["coverage"]["state"], "COMPLETE")
        self.assertEqual(self.window(report, "24h")["coverage"]["state"], "COMPLETE")

    def test_distinct_contributors_and_work_are_exact(self):
        p = packet()
        p["events"] = [
            event("a", actor="u1"),
            event("b", actor="u1", stage="CLAIM", kind="CLAIM", work="w1"),
            event("c", actor="u2", stage="CLAIM", kind="CLAIM", work="w1"),
            event("d", actor=None, stage="BUSINESS_OUTCOME", kind="BUSINESS_OUTCOME", work="w2"),
        ]
        win = self.window(self.compile(p), "15m")
        self.assertEqual(win["distinct_observed_contributors"], 2)
        self.assertEqual(win["distinct_work_items"], 2)

    def test_private_text_field_rejected(self):
        p = packet()
        p["events"][0]["text"] = "secret raw body"
        with self.assertRaises(LedgerError):
            self.compile(p)

    def test_stage_requires_work_id(self):
        for stage, kind in [
            ("CLAIM", "CLAIM"),
            ("PROVIDER_ACCEPTED", "ACCEPTED"),
            ("LANDED", "LANDED"),
            ("BUSINESS_OUTCOME", "BUSINESS_OUTCOME"),
        ]:
            with self.subTest(stage=stage):
                p = packet()
                p["events"] = [event(stage=stage, kind=kind, work=None, operation="op")]
                with self.assertRaises(LedgerError):
                    self.compile(p)

    def test_accepted_and_landed_require_operation_id(self):
        for stage, kind in [("PROVIDER_ACCEPTED", "ACCEPTED"), ("LANDED", "LANDED")]:
            with self.subTest(stage=stage):
                p = packet()
                p["events"] = [event(stage=stage, kind=kind, work="w1", operation=None)]
                with self.assertRaises(LedgerError):
                    self.compile(p)

    def test_future_provider_event_rejected(self):
        p = packet()
        p["events"] = [event(provider_time="2026-09-20T20:10:00Z", observed="2026-09-20T20:10:00Z")]
        with self.assertRaises(LedgerError):
            self.compile(p)

    def test_duplicate_source_id_rejected(self):
        p = packet()
        p["sources"].append(copy.deepcopy(p["sources"][0]))
        with self.assertRaises(LedgerError):
            self.compile(p)

    def test_complete_and_has_more_is_contradiction(self):
        p = packet()
        p["sources"] = [source(complete=True, has_more=True)]
        with self.assertRaises(LedgerError):
            self.compile(p)

    def test_report_tamper_rejected(self):
        report = self.compile()
        report["windows"][0]["event_count"] += 1
        self.assertFalse(verify_report(report))

    def test_nested_receipt_tamper_rejected_even_if_outer_rehashed_not_available(self):
        report = self.compile()
        report["sources"][0]["status"] = "ERROR"
        self.assertFalse(verify_report(report))

    def test_input_order_does_not_change_receipt(self):
        p1 = packet()
        p1["sources"].append(source("github-main", provider="github"))
        p1["events"] = [
            event("s1"),
            event(
                "g1",
                source_id="github-main",
                stage="LANDED",
                kind="LANDED",
                work="w1",
                operation="op1",
                url="https://github.com/example/repo/pull/1",
            ),
        ]
        p2 = copy.deepcopy(p1)
        p2["sources"].reverse()
        p2["events"].reverse()
        r1 = self.compile(p1)
        r2 = self.compile(p2)
        self.assertEqual(r1["ledger_receipt_sha256"], r2["ledger_receipt_sha256"])

    def test_absolute_url_required_and_credentials_forbidden(self):
        for value in ["relative/path", "https://user:pass@example.test/x"]:
            with self.subTest(value=value):
                p = packet()
                p["events"][0]["source_url"] = value
                with self.assertRaises(LedgerError):
                    self.compile(p)

    def test_load_json_rejects_duplicate_keys(self):
        with self.assertRaises(LedgerError):
            load_json('{"schema":"x","schema":"y"}')

    def test_authority_ceiling_is_hard_false(self):
        report = self.compile()
        self.assertEqual(report["authority"], {
            "provider_read_authority": False,
            "provider_write_authority": False,
            "claim_authority": False,
            "merge_authority": False,
            "payment_authority": False,
            "raw_private_text_included": False,
        })


if __name__ == "__main__":
    unittest.main()
