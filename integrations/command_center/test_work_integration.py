"""Workstream integration across durable state, shared tools, and HTTP."""
import json
import tempfile
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from .core import CommandCenter
from .equipment import CommandCenterEquipment
from .test_core import FakeProvider
from . import test_server as _server_tests


class WorkstreamIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        self.provider = FakeProvider()
        self.center = CommandCenter(self.path, fetcher=self.provider)

    def sample(self):
        return {"operation_id": "native-import", "source": {
            "id": "native", "provider": "codex_app", "observed_at": "2026-09-07T21:00:00Z",
            "activity_as_of": None, "coverage": {"complete": False, "pagination_remaining": None}},
            "items": [{"id": "task/1", "kind": "native_task", "title": "Actual work",
                       "updated_at": None, "activity_observed_at": None}]}

    def config(self, content="{}"):
        (self.path / "workstreams.config.json").write_text(content, encoding="utf-8")

    def join_refresh(self):
        worker = self.center._work_refresh_thread
        self.assertIsNotNone(worker)
        worker.join(5)
        self.assertFalse(worker.is_alive(), "bounded fake refresh did not finish")

    def test_lazy_work_state_and_owner_direction_do_not_refresh_resources(self):
        self.assertFalse((self.path / "workstreams.sqlite3").exists())
        self.center.ingest_work(self.sample())
        self.center.update_work({"operation_id": "owner-next", "source_id": "native",
                                 "item_id": "task/1", "priority": 0,
                                 "next_action": "Inspect real task"})
        state = CommandCenter(self.path, fetcher=self.provider).work_state()
        self.assertEqual(0, state["items"][0]["owner_work"]["priority"])
        self.assertEqual("Inspect real task", state["items"][0]["owner_work"]["next_action"])
        self.assertIsNone(state["items"][0]["activity_observed_at"])
        self.assertEqual("idle", state["refresh"]["status"])
        self.assertEqual([], self.provider.calls)

    def test_async_refresh_returns_and_cross_instance_lock_prevents_duplicate(self):
        from unittest.mock import patch
        import threading
        entered, release = threading.Event(), threading.Event()
        self.config()
        sample = self.sample()

        class FakeCollectors:
            calls = 0

            def __init__(self, store, config):
                self.store = store
                self.config = config

            def collect(self):
                FakeCollectors.calls += 1
                entered.set()
                if not release.wait(4):
                    raise RuntimeError("test did not release worker")
                self.store.ingest(sample)
                return {"sources": [sample["source"]], "items_observed": 1,
                        "observed_at": "2026-09-07T21:00:01Z"}

        with patch("integrations.command_center.collectors.LiveCollectors", FakeCollectors):
            first = self.center.refresh_work()
            try:
                self.assertTrue(first["started"])
                self.assertTrue(entered.wait(2))
                other = CommandCenter(self.path, fetcher=self.provider)
                second = other.refresh_work()
                self.assertFalse(second["started"])
                self.assertTrue(second["already_running"])
                self.assertEqual("running", other.work_state()["refresh"]["status"])
                self.assertEqual(1, FakeCollectors.calls)
                self.assertEqual([], self.provider.calls)
            finally:
                release.set()
                self.join_refresh()
        finished = CommandCenter(self.path, fetcher=self.provider).work_state()
        self.assertEqual("completed", finished["refresh"]["status"])
        self.assertEqual(1, finished["refresh"]["items_observed"])
        self.assertEqual("task/1", finished["items"][0]["id"])

    def test_worker_failure_releases_lock_and_never_persists_exception_text(self):
        from unittest.mock import patch
        self.config()

        class BrokenCollectors:
            def __init__(self, store, config):
                pass

            def collect(self):
                raise RuntimeError("private request contents should not persist")

        with patch("integrations.command_center.collectors.LiveCollectors", BrokenCollectors):
            self.assertTrue(self.center.refresh_work()["started"])
            self.join_refresh()
            self.assertEqual("failed", self.center.work_state()["refresh"]["status"])
            self.assertNotIn("private request", json.dumps(self.center.work_state()))
            self.assertTrue(self.center.refresh_work()["started"])
            self.join_refresh()

    def test_missing_private_config_is_visible_and_does_not_call_provider(self):
        from unittest.mock import patch
        with patch("integrations.command_center.collectors.LiveCollectors") as collector:
            self.assertTrue(self.center.refresh_work()["started"])
            self.join_refresh()
            collector.assert_not_called()
        self.assertEqual("not_configured", self.center.work_state()["refresh"]["status"])
        self.assertEqual([], self.provider.calls)

    def test_error_sources_report_degraded_completion_and_default_deadline(self):
        from unittest.mock import patch
        self.config()
        captured = {}

        class PartialCollectors:
            def __init__(self, store, config):
                captured.update(config)

            def collect(self):
                return {"sources": [{"error": "read_failed"}, {"error": None}],
                        "items_observed": 0, "observed_at": None}

        with patch("integrations.command_center.collectors.LiveCollectors", PartialCollectors):
            self.center.work_state(refresh=True)
            self.join_refresh()
        status = self.center.work_state()["refresh"]
        self.assertEqual("completed_with_errors", status["status"])
        self.assertEqual(1, status["sources_with_errors"])
        self.assertEqual(0, status["items_observed"])
        self.assertEqual(180, captured["refresh_deadline_seconds"])


class WorkHTTPIntegrationTest(unittest.TestCase):
    setUp = _server_tests.FeedHTTPIntegrationTest.setUp
    stop_server = _server_tests.FeedHTTPIntegrationTest.stop_server
    request_json = _server_tests.FeedHTTPIntegrationTest.request_json
    # Reuse the actual private temporary store and HTTP transport.
    def snapshot(self):
        return {"operation_id": "mail-observation", "source": {
            "id": "gmail:inbox", "provider": "Gmail", "sync_mode": "connector",
            "scope": {"query": "in:inbox"}, "observed_at": "2026-09-07T12:00:00Z",
            "coverage": {"complete": False, "pagination_remaining": True}},
            "items": [{"id": "message-1", "kind": "email", "title": "Existing buyer conversation",
                       "updated_at": "2026-09-06T10:00:00Z", "status": "unread"}]}

    def test_ingest_owner_work_and_peer_read_share_state(self):
        incoming = self.snapshot()
        self.request_json("/api/work/ingest", incoming)
        self.assertTrue(self.request_json("/api/work/ingest", incoming)["replayed"])
        update = {"operation_id": "owner-next", "source_id": "gmail:inbox", "item_id": "message-1",
                  "priority": 0, "next_action": "Inspect the original conversation", "job": {"objective": "Prepare a reply draft"}}
        result = self.request_json("/api/work/item", update)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["work"]["job"]["dispatch_status"], "not_dispatched")
        state = CommandCenterEquipment(CommandCenter(Path(self.directory.name))).call("command_center_work_state", {})
        self.assertEqual(state["items"][0]["owner_work"]["priority"], 0)
        self.assertEqual(state["items"][0]["updated_at"], "2026-09-06T10:00:00Z")
        self.assertFalse(state["sources"][0]["coverage"]["complete"])

    def test_shared_ingest_http_read_and_invalid_update(self):
        equipment = CommandCenterEquipment(self.center)
        equipment.call("command_center_ingest", self.snapshot())
        self.assertEqual(self.request_json("/api/work")["items"][0]["id"], "message-1")
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.request_json("/api/work/item", {"operation_id": "fake-dispatch", "source_id": "gmail:inbox",
                "item_id": "message-1", "job": {"status": "running"}})
        self.assertEqual(error.exception.code, 400)

    def test_new_static_assets_and_work_schema(self):
        for path, mime in (("/work.js", "text/javascript"), ("/work.css", "text/css")):
            with urllib.request.urlopen(self.base + path, timeout=5) as response:
                self.assertIn(mime, response.headers["Content-Type"])
                self.assertGreater(len(response.read()), 0)
        tools = {row["name"]: row for row in CommandCenterEquipment(self.center).tools()}
        self.assertEqual(len(tools), 12)
        self.assertIn("operation_id", tools["command_center_ingest"]["inputSchema"]["required"])
        self.assertNotIn("operation_id", tools["command_center_refresh_work"]["inputSchema"]["required"])


if __name__ == "__main__":
    unittest.main()
