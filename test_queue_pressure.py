#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from integrations.command_center.collectors import LiveCollectors
from integrations.command_center.queue_pressure import (
    PRESSURED_AGE_SECONDS,
    PRESSURED_QUEUED,
    SATURATED_AGE_SECONDS,
    SATURATED_QUEUED,
    queue_pressure,
)


UTC = timezone.utc
NOW = datetime(2026, 9, 19, 23, 0, tzinfo=UTC)


def source(*, complete=True, stale=False, retained=False, active_complete=True,
           queried=("in_progress", "queued"), metadata=True):
    row = {
        "id": "github:actions:woahwhattheheck/commons",
        "provider": "GitHub",
        "scope": {"repository": "woahwhattheheck/commons"},
        "coverage": {"complete": complete, "pagination_remaining": not complete},
        "error": None,
        "retained_last_good": retained,
        "stale": stale,
        "data_stale": False,
    }
    if metadata:
        row["metadata"] = {
            "active_queue_coverage": {
                "complete": active_complete,
                "queried_statuses": list(queried),
            }
        }
    return row


def run(run_id, status, age_seconds, *, created=True):
    stamp = (NOW - timedelta(seconds=age_seconds)).isoformat().replace("+00:00", "Z")
    row = {
        "id": "github:run:woahwhattheheck/commons:" + str(run_id),
        "source_id": "github:actions:woahwhattheheck/commons",
        "status": status,
        "refs": {"provider_status": status},
        "updated_at": NOW.isoformat().replace("+00:00", "Z"),
    }
    if created:
        row["created_at"] = stamp
    return row


def state(items, *, src=None):
    return {"sources": [src or source()], "items": list(items)}


class QueuePressureTests(unittest.TestCase):
    def test_normal_pressure_and_saturation_thresholds(self):
        normal = queue_pressure(state([
            run(1, "queued", PRESSURED_AGE_SECONDS - 1),
            run(2, "in_progress", 20),
        ]), now=NOW)
        self.assertEqual(normal["state"], "NORMAL")
        self.assertFalse(normal["warning"])
        self.assertEqual((normal["queued"], normal["in_progress"]), (1, 1))
        self.assertFalse(normal["ci_green_claim_allowed"])

        pressured = queue_pressure(state([
            run(index, "queued", 1) for index in range(PRESSURED_QUEUED)
        ]), now=NOW)
        self.assertEqual(pressured["state"], "PRESSURED")
        self.assertTrue(pressured["warning"])

        saturated = queue_pressure(state([
            run(index, "queued", 1) for index in range(SATURATED_QUEUED)
        ]), now=NOW)
        self.assertEqual(saturated["state"], "SATURATED")

    def test_oldest_age_uses_creation_time_not_recent_update(self):
        pressured = queue_pressure(state([
            run(1, "queued", PRESSURED_AGE_SECONDS),
        ]), now=NOW)
        self.assertEqual(pressured["state"], "PRESSURED")
        self.assertEqual(pressured["oldest_active_age_seconds"], PRESSURED_AGE_SECONDS)

        saturated = queue_pressure(state([
            run(1, "in_progress", SATURATED_AGE_SECONDS),
        ]), now=NOW)
        self.assertEqual(saturated["state"], "SATURATED")
        self.assertEqual(saturated["oldest_active_age_seconds"], SATURATED_AGE_SECONDS)

    def test_completed_rows_do_not_count_as_active(self):
        report = queue_pressure(state([
            run(1, "completed", SATURATED_AGE_SECONDS * 10),
        ]), now=NOW)
        self.assertEqual(report["state"], "NORMAL")
        self.assertEqual(report["active"], 0)
        self.assertIsNone(report["oldest_active_age_seconds"])

    def test_incomplete_stale_retained_or_malformed_active_observation_is_unknown(self):
        variants = [
            source(stale=True),
            source(retained=True),
        ]
        for src in variants:
            with self.subTest(src=src):
                report = queue_pressure(state([run(1, "queued", 1)], src=src), now=NOW)
                self.assertEqual(report["state"], "UNKNOWN")
                self.assertTrue(report["warning"])
                self.assertFalse(report["ci_green_claim_allowed"])

        no_created = queue_pressure(state([run(1, "queued", 1, created=False)]), now=NOW)
        self.assertEqual(no_created["state"], "UNKNOWN")
        self.assertEqual(no_created["reason"], "active_run_timestamp_unusable")

    def test_history_incomplete_does_not_invalidate_complete_active_queue(self):
        report = queue_pressure(state(
            [run(1, "queued", 1)],
            src=source(complete=False, active_complete=True),
        ), now=NOW)
        self.assertEqual(report["state"], "NORMAL")
        self.assertEqual(report["queued"], 1)
        self.assertFalse(report["ci_green_claim_allowed"])

    def test_active_incomplete_or_missing_metadata_is_unknown(self):
        cases = [
            source(complete=True, active_complete=False),
            source(complete=True, metadata=False),
            source(complete=True, queried=("queued",)),
            source(complete=True, queried=("queued", "in_progress", "completed")),
        ]
        for src in cases:
            with self.subTest(src=src):
                report = queue_pressure(state([run(1, "queued", 1)], src=src), now=NOW)
                self.assertEqual(report["state"], "UNKNOWN")
                self.assertEqual(report["reason"], "active_queue_coverage_incomplete")
                self.assertFalse(report["ci_green_claim_allowed"])

    def test_no_actions_source_is_unknown_not_green(self):
        report = queue_pressure({"sources": [], "items": []}, now=NOW)
        self.assertEqual(report["state"], "UNKNOWN")
        self.assertFalse(report["ci_green_claim_allowed"])

    def test_thresholds_are_published_with_every_advisory(self):
        report = queue_pressure(state([]), now=NOW)
        self.assertEqual(report["thresholds"], {
            "pressured_queued": 50,
            "saturated_queued": 200,
            "pressured_age_seconds": 900,
            "saturated_age_seconds": 3600,
        })

    def test_actions_normalizer_retains_provider_created_at(self):
        class Store:
            def __init__(self, path):
                self.state_dir = Path(path)

        class Equipment:
            pass

        with tempfile.TemporaryDirectory() as temp:
            collector = LiveCollectors(Store(temp), equipment=Equipment())
            collector._pages = lambda endpoint, key=None: ([{
                "id": 9,
                "status": "queued",
                "conclusion": None,
                "name": "tests",
                "display_title": "tests",
                "html_url": "https://example.invalid/run/9",
                "created_at": "2026-09-19T20:00:00Z",
                "updated_at": "2026-09-19T22:59:00Z",
                "run_attempt": 1,
                "head_sha": "a" * 40,
                "head_branch": "feature",
                "actor": {"login": "builder"},
            }], True)
            batch = collector._actions("woahwhattheheck/commons")
        self.assertEqual(len(batch["items"]), 1)
        row = batch["items"][0]
        self.assertEqual(row["created_at"], "2026-09-19T20:00:00Z")
        self.assertEqual(row["updated_at"], "2026-09-19T22:59:00Z")
        self.assertEqual(row["refs"]["provider_status"], "queued")
        coverage = batch["source"]["metadata"]["active_queue_coverage"]
        self.assertTrue(coverage["complete"])
        self.assertEqual(set(coverage["queried_statuses"]), {"in_progress", "queued"})


if __name__ == "__main__":
    unittest.main()
