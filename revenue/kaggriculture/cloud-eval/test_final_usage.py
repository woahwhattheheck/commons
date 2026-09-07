"""Real worker teardown coverage; no engine, network, or tournament required."""
import errno
import os
from pathlib import Path
import signal
import tempfile
import unittest
from unittest import mock

import evaluate as ev


AGENTS = '''import os, time

def good(obs, cfg):
    return {"farmer": ["PASS"], "market": []}

def hungry(obs, cfg):
    allocation = bytearray(32 * 1024 * 1024)
    until = time.process_time() + 0.08
    while time.process_time() < until:
        allocation[0] = (allocation[0] + 1) % 256
    time.sleep(5)
    return {}

def zero(obs, cfg):
    os._exit(0)

def abrupt(obs, cfg):
    allocation = bytearray(32 * 1024 * 1024)
    os._exit(23)
'''


class FinalUsageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "agents.py"
        self.path.write_text(AGENTS)
        self.actors = []

    def tearDown(self):
        for actor in self.actors:
            actor.close()
        self.temp.cleanup()

    def actor(self, name):
        actor = ev.Actor(str(self.path) + "::" + name, self.temp.name, self.path, 123)
        self.actors.append(actor)
        self.assertEqual(actor.ready["kind"], "ready")
        return actor

    def assert_clean(self, actor, expected_code):
        self.assertEqual(actor.report()["exit_code"], expected_code)
        self.assertEqual(actor.proc.returncode, expected_code)
        self.assertTrue(actor.proc.stdin.closed)
        self.assertTrue(actor.proc.stdout.closed)
        self.assertFalse(Path(actor.directory.name).exists())
        report = actor.report()
        actor.close()
        self.assertEqual(report, actor.report())

    @unittest.skipUnless(hasattr(os, "wait4"), "wait4 unavailable")
    def test_timeout_keeps_final_usage_without_procfs(self):
        actor = self.actor("hungry")
        initial = actor.report()
        self.assertEqual(actor.act({}, {}, 0.3)["kind"], "timeout")
        # Simulate the recorded cloud /proc restriction, not the child resource use.
        with mock.patch.object(ev.Path, "read_text", side_effect=PermissionError(errno.EACCES, "procfs unavailable")):
            actor.close()
        report = actor.report()
        self.assertEqual(report["final_resource_sample"], "wait4")
        self.assertEqual(report["resource_sample"], "child_rusage")
        self.assertGreater(report["peak_rss_kib"], initial["peak_rss_kib"] + 16 * 1024)
        self.assertGreater(report["cpu_seconds"], initial["cpu_seconds"] + 0.05)
        self.assert_clean(actor, -signal.SIGKILL)

    @unittest.skipUnless(hasattr(os, "wait4"), "wait4 unavailable")
    def test_abrupt_exit_keeps_usage_and_exit_status(self):
        actor = self.actor("abrupt")
        initial = actor.report()
        self.assertEqual(actor.act({}, {}, 2)["kind"], "process_exit")
        with mock.patch.object(ev.Path, "read_text", side_effect=FileNotFoundError("exited proc")):
            actor.close()
        report = actor.report()
        self.assertEqual(report["final_resource_sample"], "wait4")
        self.assertGreater(report["peak_rss_kib"], initial["peak_rss_kib"] + 16 * 1024)
        self.assert_clean(actor, 23)

    @unittest.skipUnless(hasattr(os, "wait4"), "wait4 unavailable")
    def test_successful_action_and_bounded_cleanup_keep_usage(self):
        actor = self.actor("good")
        self.assertEqual(actor.act({}, {}, 1)["action"], {"farmer": ["PASS"], "market": []})
        actor.close()
        self.assertEqual(actor.report()["final_resource_sample"], "wait4")
        self.assertEqual(actor.report()["calls"], 1)
        # Interpreter shutdown may outlast the existing 100-ms grace.
        self.assertIn(actor.report()["exit_code"], (0, -signal.SIGKILL))
        self.assert_clean(actor, actor.report()["exit_code"])

    @unittest.skipUnless(hasattr(os, "wait4"), "wait4 unavailable")
    def test_zero_exit_status_is_not_confused_with_a_running_child(self):
        actor = self.actor("zero")
        self.assertEqual(actor.act({}, {}, 2)["kind"], "process_exit")
        actor.close()
        self.assertEqual(actor.report()["final_resource_sample"], "wait4")
        self.assert_clean(actor, 0)

    def test_missing_wait4_retains_fallback_and_cleans_up(self):
        actor = self.actor("hungry")
        self.assertEqual(actor.act({}, {}, 0.3)["kind"], "timeout")
        initial = actor.report()
        with mock.patch.object(ev.os, "wait4", None, create=True), mock.patch.object(
            ev.Path, "read_text", side_effect=PermissionError("procfs unavailable")
        ):
            actor.close()
        report = actor.report()
        self.assertEqual(report["final_resource_sample"], "unavailable:wait4_unsupported")
        self.assertEqual(report["cpu_seconds"], initial["cpu_seconds"])
        self.assertEqual(report["peak_rss_kib"], initial["peak_rss_kib"])
        self.assert_clean(actor, -signal.SIGKILL)

    def test_unavailable_wait4_does_not_break_cleanup(self):
        actor = self.actor("abrupt")
        self.assertEqual(actor.act({}, {}, 2)["kind"], "process_exit")
        with mock.patch.object(ev.os, "wait4", side_effect=OSError(errno.ENOSYS, "unsupported"), create=True):
            actor.close()
        self.assertEqual(actor.report()["final_resource_sample"], f"unavailable:wait4_errno_{errno.ENOSYS}")
        self.assert_clean(actor, 23)

    @unittest.skipUnless(hasattr(os, "wait4"), "wait4 unavailable")
    def test_interrupted_wait_retries_without_losing_usage(self):
        actor = self.actor("zero")
        self.assertEqual(actor.act({}, {}, 2)["kind"], "process_exit")
        real_wait4 = os.wait4
        calls = []

        def interrupted_once(pid, options):
            calls.append(pid)
            if len(calls) == 1:
                raise InterruptedError(errno.EINTR, "interrupted")
            return real_wait4(pid, options)

        with mock.patch.object(ev.os, "wait4", side_effect=interrupted_once):
            actor.close()
        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(actor.report()["final_resource_sample"], "wait4")
        self.assert_clean(actor, 0)

    def test_previously_reaped_process_preserves_known_status(self):
        actor = self.actor("abrupt")
        self.assertEqual(actor.act({}, {}, 2)["kind"], "process_exit")
        self.assertEqual(actor.proc.wait(timeout=2), 23)
        actor.close()
        self.assertEqual(actor.report()["final_resource_sample"], "unavailable:already_reaped")
        self.assert_clean(actor, 23)


if __name__ == "__main__":
    unittest.main(verbosity=2)
