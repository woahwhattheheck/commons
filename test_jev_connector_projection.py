import copy
import unittest

from integrations.command_center import jev_connector_projection as cp

OBS = "2026-09-20T20:00:00Z"
START = "2026-09-20T19:00:00Z"


def record(event_id="1789933003.369309", event_type="MESSAGE", resource="C0BU51F1PL3"):
    return {
        "provider_event_id": event_id,
        "provider_event_time": "2026-09-20T19:36:43Z",
        "observed_at": OBS,
        "resource_scope": resource,
        "event_type": event_type,
        "actor_id": "U0BR9670G2H",
        "work_id": None,
        "operation_id": None,
        "source_url": "https://example.invalid/exact-event",
    }


def source(source_id="slack-coordination", records=None):
    records = [record()] if records is None else records
    return {
        "source_id": source_id,
        "connector": "slack-history",
        "provider": "slack",
        "scope": ["C0BU51F1PL3"],
        "cursor": "opaque-cursor",
        "high_water_mark": "1789933003.369309",
        "observed_at": OBS,
        "last_successful_read": OBS,
        "status": "OK",
        "cooldown_until": None,
        "coverage": {
            "window_start": START,
            "window_end": OBS,
            "complete": True,
            "has_more": False,
            "pages_read": 1,
            "items_read": len(records),
        },
        "source_url": "https://example.invalid/slack/source",
        "records": records,
    }


def packet():
    return {
        "schema": cp.SCHEMA,
        "snapshot_id": "radar-20260920T2000Z",
        "max_source_age_seconds": 300,
        "sources": [source()],
    }


class ConnectorProjectionTests(unittest.TestCase):
    def test_basic_slack_projection(self):
        out = cp.project(packet())
        self.assertEqual(out["schema"], cp.LEDGER_SCHEMA)
        self.assertEqual(len(out["sources"]), 1)
        self.assertEqual(len(out["events"]), 1)
        event = out["events"][0]
        self.assertEqual(event["kind"], "MESSAGE")
        self.assertEqual(event["stage"], "EVENT")
        self.assertEqual(event["source_id"], "slack-coordination")
        self.assertTrue(event["event_id"].startswith("evt-"))

    def test_private_text_field_is_rejected(self):
        p = packet()
        p["sources"][0]["records"][0]["text"] = "private body"
        with self.assertRaises(cp.ProjectionError):
            cp.project(p)

    def test_stable_event_id_across_overlapping_exports(self):
        p = packet()
        other = copy.deepcopy(p["sources"][0])
        other["source_id"] = "slack-overlap"
        p["sources"].append(other)
        out = cp.project(p)
        self.assertEqual(out["events"][0]["event_id"], out["events"][1]["event_id"])

    def test_event_id_binds_resource_scope(self):
        p = packet()
        p["sources"][0]["scope"].append("COTHER")
        second = record(resource="COTHER")
        second["provider_event_id"] = p["sources"][0]["records"][0]["provider_event_id"]
        p["sources"][0]["records"].append(second)
        p["sources"][0]["coverage"]["items_read"] = 2
        out = cp.project(p)
        self.assertNotEqual(out["events"][0]["event_id"], out["events"][1]["event_id"])

    def test_event_id_binds_event_type_namespace(self):
        p = packet()
        p["sources"][0]["provider"] = "other"
        p["sources"][0]["connector"] = "generic-provider"
        second = copy.deepcopy(p["sources"][0]["records"][0])
        second["event_type"] = "COMMENT"
        p["sources"][0]["records"].append(second)
        p["sources"][0]["coverage"]["items_read"] = 2
        out = cp.project(p)
        self.assertNotEqual(out["events"][0]["event_id"], out["events"][1]["event_id"])

    def test_github_projection(self):
        p = packet()
        rec = record("repo:woahwhattheheck/commons:pr:16541", "PULL_REQUEST", "repo:woahwhattheheck/commons")
        rec["source_url"] = "https://github.com/woahwhattheheck/commons/pull/16541"
        src = source("github-recent", [rec])
        src.update(connector="github-prs", provider="github", scope=["repo:woahwhattheheck/commons"],
                   source_url="https://github.com/woahwhattheheck/commons/pulls")
        p["sources"] = [src]
        out = cp.project(p)
        self.assertEqual(out["events"][0]["kind"], "PULL_REQUEST")

    def test_provider_event_type_mismatch_rejected(self):
        p = packet()
        p["sources"][0]["records"][0]["event_type"] = "PULL_REQUEST"
        with self.assertRaises(cp.ProjectionError):
            cp.project(p)

    def test_record_scope_must_belong_to_source(self):
        p = packet()
        p["sources"][0]["records"][0]["resource_scope"] = "COTHER"
        with self.assertRaises(cp.ProjectionError):
            cp.project(p)

    def test_items_read_must_equal_projected_records(self):
        p = packet()
        p["sources"][0]["coverage"]["items_read"] = 2
        with self.assertRaises(cp.ProjectionError):
            cp.project(p)

    def test_complete_and_has_more_conflict_rejected(self):
        p = packet()
        p["sources"][0]["coverage"]["has_more"] = True
        with self.assertRaises(cp.ProjectionError):
            cp.project(p)

    def test_cooldown_requires_expiry(self):
        p = packet()
        p["sources"][0]["status"] = "COOLDOWN"
        with self.assertRaises(cp.ProjectionError):
            cp.project(p)

    def test_error_retains_last_good_projection(self):
        p = packet()
        p["sources"][0]["status"] = "ERROR"
        p["sources"][0]["observed_at"] = "2026-09-20T20:05:00Z"
        out = cp.project(p)
        self.assertEqual(out["sources"][0]["status"], "ERROR")
        self.assertEqual(out["events"][0]["observed_at"], "2026-09-20T20:00:00.000000Z")

    def test_chronology_rejected(self):
        p = packet()
        p["sources"][0]["records"][0]["provider_event_time"] = "2026-09-20T20:00:01Z"
        with self.assertRaises(cp.ProjectionError):
            cp.project(p)

    def test_duplicate_source_rejected(self):
        p = packet()
        p["sources"].append(copy.deepcopy(p["sources"][0]))
        with self.assertRaises(cp.ProjectionError):
            cp.project(p)

    def test_order_invariant(self):
        p = packet()
        p["sources"][0]["scope"].append("COTHER")
        other = record("1789933004.000000", resource="COTHER")
        p["sources"][0]["records"].append(other)
        p["sources"][0]["coverage"]["items_read"] = 2
        first = cp.project(p)
        p["sources"][0]["records"].reverse()
        p["sources"][0]["scope"].reverse()
        self.assertEqual(first, cp.project(p))

    def test_digest_is_deterministic(self):
        p = packet()
        self.assertEqual(cp.projection_digest(p), cp.projection_digest(copy.deepcopy(p)))
        self.assertRegex(cp.projection_digest(p), r"^[0-9a-f]{64}$")

    def test_strict_json_rejects_duplicate_and_nonfinite(self):
        with self.assertRaises(cp.ProjectionError):
            cp.strict_loads('{"schema":"x","schema":"y"}')
        with self.assertRaises(cp.ProjectionError):
            cp.strict_loads('{"x":NaN}')

    def test_source_url_credentials_rejected(self):
        p = packet()
        p["sources"][0]["source_url"] = "https://user:pass@example.invalid/source"
        with self.assertRaises(cp.ProjectionError):
            cp.project(p)

    def test_native_provider_id_can_be_opaque_before_hashing(self):
        p = packet()
        p["sources"][0]["records"][0]["provider_event_id"] = "opaque==cursor/event%2F1"
        out = cp.project(p)
        self.assertRegex(out["events"][0]["event_id"], r"^evt-[0-9a-f]{64}$")

    def test_fractional_timestamp_comparison_is_temporal_not_lexical(self):
        p = packet()
        p["sources"][0]["records"][0]["provider_event_time"] = "2026-09-20T19:36:43.9Z"
        p["sources"][0]["records"][0]["observed_at"] = "2026-09-20T19:36:44Z"
        cp.project(p)
        p["sources"][0]["records"][0]["provider_event_time"] = "2026-09-20T19:36:44.1Z"
        with self.assertRaises(cp.ProjectionError):
            cp.project(p)

    def test_round_trip_into_landed_ledger(self):
        # The production composition seam: adapter output must satisfy the exact ledger compiler.
        try:
            from integrations.command_center import jev_event_ledger as ledger
        except ImportError:
            self.skipTest("landed ledger module is not present in standalone source-only replay")
        report = ledger.compile_ledger(cp.project(packet()), evaluated_at=OBS)
        self.assertEqual(report["schema"], ledger.REPORT_SCHEMA)


if __name__ == "__main__":
    unittest.main()
