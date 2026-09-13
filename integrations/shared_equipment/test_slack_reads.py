import io
import json
import tempfile
import threading
import unittest
import urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from integrations.shared_equipment.provider_io import GitHubSlackEquipment
from integrations.shared_equipment.slack_carrier import SlackCarrierDeferred, SlackEquipmentCarrier
from integrations.shared_equipment.slack_reads import SlackReadCoordinator


class SlackReadTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.now = 1000.0
        self.coordinator = SlackReadCoordinator(self.directory.name, clock=lambda: self.now)

    def call(self, runner, method="conversations.history", payload=None, **kwargs):
        return self.coordinator.call(method, payload or {"channel": "C1"}, "synthetic-token", runner, **kwargs)

    def test_identical_concurrent_reads_one_provider_call(self):
        effects = []
        entered, release = threading.Event(), threading.Event()
        def runner():
            effects.append(1)
            entered.set()
            self.assertTrue(release.wait(3))
            return {"ok": True, "messages": []}
        with ThreadPoolExecutor(max_workers=8) as pool:
            jobs = [pool.submit(self.call, runner) for _ in range(8)]
            self.assertTrue(entered.wait(3))
            release.set()
            results = [job.result(4) for job in jobs]
        self.assertEqual(len(effects), 1)
        self.assertEqual(sum(r["commons_read"]["cached"] for r in results), 7)

    def test_fresh_and_expiry_read_provider_again(self):
        effects = []
        runner = lambda: effects.append(1) or {"ok": True, "messages": []}
        self.call(runner)
        self.call(runner)
        self.call(runner, fresh=True)
        self.now += 11
        self.call(runner)
        self.assertEqual(len(effects), 3)

    def test_cache_response_mutation_does_not_change_later_reads(self):
        runner = lambda: {"ok": True, "messages": [{"text": "original"}]}
        self.call(runner)["messages"][0]["text"] = "changed"
        self.assertEqual(self.call(runner)["messages"][0]["text"], "original")

    def test_cooldown_persists_across_instances_and_does_not_stop_other_method(self):
        first = self.call(lambda: {"ok": False, "status": 429, "retry_after": "25", "uncertain": False})
        self.assertEqual(first["retry_after"], 25)
        second = SlackReadCoordinator(self.directory.name, clock=lambda: self.now)
        def forbidden():
            self.fail("cooldown should not contact provider")
        result = second.call("conversations.history", {"channel": "C2"}, "synthetic-token", forbidden, fresh=True)
        self.assertFalse(result["provider_contacted"])
        self.assertEqual(result["retry_after"], 25)
        self.assertTrue(second.call("conversations.replies", {}, "synthetic-token", lambda: {"ok": True})["ok"])
        self.now += 25
        self.assertTrue(second.call("conversations.history", {}, "synthetic-token", lambda: {"ok": True})["ok"])

    def test_account_scope_does_not_share_messages_or_cooldowns(self):
        self.call(lambda: {"ok": False, "status": 429, "retry_after": 30})
        result = self.coordinator.call("conversations.history", {}, "another-synthetic-token", lambda: {"ok": True})
        self.assertTrue(result["ok"])

    def test_successful_writes_not_cached_and_invalidate_reads(self):
        effects = []
        runner = lambda: effects.append(1) or {"ok": True}
        self.call(runner)
        self.call(runner)
        self.call(runner, method="chat.postMessage")
        self.call(runner, method="chat.postMessage")
        self.call(runner)
        self.assertEqual(len(effects), 4)

    def test_non_rate_errors_never_cached(self):
        effects = []
        runner = lambda: effects.append(1) or {"ok": False, "error": "missing_scope"}
        self.call(runner)
        self.call(runner)
        self.assertEqual(len(effects), 2)

    def test_inflight_read_cannot_refill_cache_after_write(self):
        entered, release = threading.Event(), threading.Event()
        def old_read():
            entered.set()
            self.assertTrue(release.wait(3))
            return {"ok": True, "messages": [{"text": "before-write"}]}
        with ThreadPoolExecutor(max_workers=1) as pool:
            old = pool.submit(self.call, old_read)
            self.assertTrue(entered.wait(3))
            self.call(lambda: {"ok": True}, method="chat.postMessage")
            release.set()
            old.result(4)
        latest = self.call(lambda: {"ok": True, "messages": [{"text": "after-write"}]})
        self.assertFalse(latest["commons_read"]["cached"])
        self.assertEqual(latest["messages"][0]["text"], "after-write")

    def test_memory_cache_bounds(self):
        self.coordinator.max_bytes = 140
        self.coordinator.max_entries = 2
        for n in range(10):
            self.call(lambda: {"ok": True, "messages": ["x" * 30]}, payload={"channel": str(n)})
        self.assertLessEqual(len(self.coordinator._cache), 2)
        self.assertLessEqual(self.coordinator._bytes, 140)

    def test_provider_wrapper_preserves_redaction_and_known_no_effect_429(self):
        def opener(request, **kwargs):
            raise urllib.error.HTTPError(request.full_url, 429, "limited", {"Retry-After": "31"}, io.BytesIO(b""))
        adapter = GitHubSlackEquipment(slack_token_loader=lambda: "xoxb-synthetic-only",
            opener=opener, slack_coordinator=self.coordinator)
        result = adapter.slack("chat.postMessage", {"channel": "C1", "text": "hello"})
        self.assertFalse(result["uncertain"])
        self.assertEqual(result["retry_after"], 31)
        self.assertNotIn("synthetic", json.dumps(result))

    def test_cooldown_database_has_no_credentials_or_message_text(self):
        self.call(lambda: {"ok": True, "messages": [{"text": "private-message-marker"}]})
        data = (Path(self.directory.name) / "request-budget.sqlite3").read_bytes()
        self.assertNotIn(b"synthetic-token", data)
        self.assertNotIn(b"private-message-marker", data)


class SlackCarrierCooldownTests(unittest.TestCase):
    def test_read_429_keeps_cursor_and_waits_provider_delay(self):
        class Services:
            def slack(self, method, payload):
                return {"ok": False, "error": "ratelimited", "status": 429, "retry_after": 80}
        class Catalog:
            services = Services()
        with tempfile.TemporaryDirectory() as directory:
            carrier = SlackEquipmentCarrier(Catalog(), None, {"channel_id": "C1"}, Path(directory) / "cursor.json")
            prior = carrier.cursor
            with self.assertRaises(SlackCarrierDeferred):
                carrier.once()
            waits = []
            class Stop:
                def is_set(self): return bool(waits)
                def wait(self, seconds): waits.append(seconds)
            carrier._stop = Stop()
            carrier.run()
            self.assertEqual(carrier.cursor, prior)
            self.assertGreater(waits[0], 79)
            self.assertEqual(carrier.status["phase"], "rate_limited")

    def test_transient_errors_back_off_and_success_resets(self):
        with tempfile.TemporaryDirectory() as directory:
            carrier = SlackEquipmentCarrier(None, None, {"channel_id": "C1", "poll_seconds": 5}, Path(directory) / "cursor.json")
            waits, runs = [], []
            def once():
                runs.append(1)
                if len(runs) < 4:
                    raise RuntimeError("temporary read failure")
                return {}
            class Stop:
                def is_set(self): return len(waits) == 4
                def wait(self, seconds): waits.append(seconds)
            carrier.once, carrier._stop = once, Stop()
            carrier.run()
            self.assertEqual(waits, [5, 10, 20, 5])


if __name__ == "__main__":
    unittest.main()
