"""Hermetic tests for integrations/claude_headless/claude_headless.py: records, cancel, recover.

Every test drives ``stub_claude.py`` (same stream-json shape as the real CLI) so nothing here
needs network, credentials, or the installed Claude Code CLI. The live acceptance against the
real CLI is a separate, measured record in the receipt, not a unit test.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PKG = ROOT / "integrations" / "claude_headless"
sys.path.insert(0, str(PKG))

import claude_headless as ch  # noqa: E402

STUB = PKG / "stub_claude.py"
STUB_ARGV = [sys.executable, str(STUB)]


class _Base(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        base = Path(self.tmp.name)
        self.root = base / "root"
        self.state = base / "state"
        self.state.mkdir()
        self._old_state = os.environ.get("STUB_CLAUDE_STATE")
        os.environ["STUB_CLAUDE_STATE"] = str(self.state)
        self.runner = ch.Runner(self.root, claude=STUB_ARGV)

    def tearDown(self) -> None:
        for record in self.runner.list_runs(limit=1000):
            if record["status"] in ch.ACTIVE:
                try:
                    self.runner.cancel(record["run_id"])
                except ch.HeadlessError:
                    pass
        if self._old_state is None:
            os.environ.pop("STUB_CLAUDE_STATE", None)
        else:
            os.environ["STUB_CLAUDE_STATE"] = self._old_state
        self.tmp.cleanup()

    def _wait_events(self, run_id: str, minimum: int, timeout: float = 15.0) -> int:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            count = self.runner.status(run_id)["event_count"]
            if count >= minimum:
                return count
            time.sleep(0.1)
        self.fail(f"run {run_id} never reached {minimum} events")


class RunnerRecords(_Base):
    def test_start_completes_with_result_and_preserves_session_id(self) -> None:
        record = self.runner.start("say hello", label="t1", peer="TEST")
        self.assertEqual(record["status"], "running")
        self.assertIsNotNone(record["pid"])
        done = self.runner.wait(record["run_id"], timeout=20)
        self.assertEqual(done["status"], "completed")
        self.assertEqual(done["session_id"], record["session_id"])
        self.assertIn("say hello", done["result_text"])
        self.assertEqual(done["exit_code"], 0)
        self.assertEqual(done["num_turns"], 1)
        self.assertEqual(done["child_model"], "stub-model")
        self.assertEqual(done["child_version"], "0.0.0-stub")
        self.assertEqual(done["label"], "t1")
        self.assertEqual(done["peer"], "TEST")
        run_dir = self.root / "runs" / record["run_id"]
        for name in ("run.json", "prompt.txt", "events.jsonl", "stderr.txt"):
            self.assertTrue((run_dir / name).exists(), name)
        self.assertEqual((run_dir / "prompt.txt").read_bytes(), b"say hello")
        self.assertEqual(done["prompt_bytes"], 9)
        self.assertIn("<prompt>", done["argv"])
        self.assertNotIn("say hello", done["argv"])
        self.assertIn("--session-id", done["argv"])
        self.assertIn("stream-json", done["argv"])

    def test_events_cursor_pagination_is_line_exact(self) -> None:
        record = self.runner.start("paginate me")
        self.runner.wait(record["run_id"], timeout=20)
        first, cursor = self.runner.events(record["run_id"], after=0, limit=2)
        self.assertEqual([e["seq"] for e in first], [1, 2])
        self.assertEqual(cursor, 2)
        self.assertEqual(first[0]["event"]["type"], "system")
        rest, cursor2 = self.runner.events(record["run_id"], after=cursor, limit=100)
        self.assertEqual(rest[0]["seq"], 3)
        self.assertEqual(rest[-1]["event"]["type"], "result")
        empty, cursor3 = self.runner.events(record["run_id"], after=cursor2, limit=100)
        self.assertEqual(empty, [])
        self.assertEqual(cursor3, cursor2)
        self.assertEqual(self.runner.status(record["run_id"])["event_count"], cursor2)

    def test_followup_resumes_the_same_conversation(self) -> None:
        first = self.runner.wait(self.runner.start("first question", model="stub-a", peer="P1")["run_id"], timeout=20)
        second = self.runner.followup(first["run_id"], "second question")
        self.assertNotEqual(second["run_id"], first["run_id"])
        self.assertEqual(second["session_id"], first["session_id"])
        self.assertTrue(second["resume"])
        self.assertIn("--resume", second["argv"])
        self.assertEqual(second["model"], "stub-a")
        self.assertEqual(second["peer"], "P1")
        done = self.runner.wait(second["run_id"], timeout=20)
        self.assertEqual(done["status"], "completed")
        self.assertIn('"first question"', done["result_text"])
        self.assertIn("stub reply #2", done["result_text"])
        by_session = self.runner.followup(first["session_id"], "third question")
        self.assertEqual(by_session["session_id"], first["session_id"])
        self.assertIn("stub reply #3", self.runner.wait(by_session["run_id"], timeout=20)["result_text"])
        session = self.runner.session(first["session_id"])
        self.assertEqual(session["run_count"], 3)
        self.assertTrue(session["resumable"])

    def test_followup_of_unknown_session_reports_error(self) -> None:
        record = self.runner.start("x", session_id="11111111-2222-4333-8444-555555555555", resume=True)
        done = self.runner.wait(record["run_id"], timeout=20)
        self.assertEqual(done["status"], "error")
        self.assertTrue(done["is_error"])
        self.assertIn("No conversation found", done["result_text"])

    def test_error_result_marks_error_with_exit_code(self) -> None:
        done = self.runner.wait(self.runner.start("please FAIL")["run_id"], timeout=20)
        self.assertEqual(done["status"], "error")
        self.assertTrue(done["is_error"])
        self.assertEqual(done["exit_code"], 1)
        self.assertEqual(done["result_subtype"], "error_during_execution")

    def test_child_that_vanishes_without_result_is_interrupted(self) -> None:
        done = self.runner.wait(self.runner.start("CRASH now")["run_id"], timeout=20)
        self.assertEqual(done["status"], "interrupted")
        self.assertEqual(done["exit_code"], 3)
        self.assertIsNone(done["result_text"])
        self.assertIn("without a result", done["error"])

    def test_env_scrub_removes_nested_session_variables(self) -> None:
        planted = {"CLAUDECODE": "1", "ANTHROPIC_BASE_URL": "http://127.0.0.1:1", "CLAUDE_CODE_SESSION_ID": "parent"}
        saved = {k: os.environ.get(k) for k in planted}
        os.environ.update(planted)
        try:
            record = self.runner.start("ECHOENV")
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        done = self.runner.wait(record["run_id"], timeout=20)
        self.assertEqual(done["status"], "completed")
        self.assertIn("CLAUDECODE=<absent>", done["result_text"])
        self.assertIn("ANTHROPIC_BASE_URL=<absent>", done["result_text"])
        self.assertIn("CLAUDE_CODE_SESSION_ID=<absent>", done["result_text"])
        for name in planted:
            self.assertIn(name, done["env_removed"])
        keep_env, removed = ch.scrub_env({"CLAUDE_CODE_X": "1", "KEEP_ME": "2", "CLAUDE_PREVIEW_Y": "3"})
        self.assertEqual(keep_env, {"KEEP_ME": "2"})
        self.assertEqual(removed, ["CLAUDE_CODE_X", "CLAUDE_PREVIEW_Y"])

    def test_long_prompt_goes_through_stdin(self) -> None:
        explicit = self.runner.wait(self.runner.start("via stdin please", via_stdin=True)["run_id"], timeout=20)
        self.assertEqual(explicit["prompt_via"], "stdin")
        self.assertEqual(explicit["headless"]["stdin"], "prompt.txt")
        self.assertNotIn("<prompt>", explicit["argv"])
        self.assertIn("via stdin please", explicit["result_text"])
        big = "y" * (ch.STDIN_PROMPT_THRESHOLD + 1)
        auto = self.runner.wait(self.runner.start(big)["run_id"], timeout=20)
        self.assertEqual(auto["prompt_via"], "stdin")
        self.assertEqual(auto["prompt_bytes"], len(big))
        self.assertEqual(auto["status"], "completed")

    def test_journal_records_lifecycle_with_increasing_cursor(self) -> None:
        before = self.runner.journal.cursor
        record = self.runner.start("journal me")
        self.runner.wait(record["run_id"], timeout=20)
        events = self.runner.journal.after(before, limit=100)
        statuses = [e["status"] for e in events if e.get("run_id") == record["run_id"]]
        self.assertEqual(statuses, ["queued", "running", "completed"])
        ids = [e["event_id"] for e in events]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(set(ids)), len(ids))
        self.assertEqual(self.runner.journal.after(self.runner.journal.cursor, limit=10), [])
        other = ch.Runner(self.root, claude=STUB_ARGV)
        self.assertEqual(other.journal.cursor, self.runner.journal.cursor)

    def test_invalid_inputs_are_refused(self) -> None:
        with self.assertRaises(ch.HeadlessError):
            self.runner.start("   ")
        with self.assertRaises(ch.HeadlessError):
            self.runner.start("x", session_id="not-a-uuid")
        with self.assertRaises(ch.HeadlessError):
            self.runner.start("x", resume=True)
        with self.assertRaises(ch.HeadlessError):
            self.runner.status("../escape")
        with self.assertRaises(ch.HeadlessError):
            self.runner.status("missing")


class CancelAndRecover(_Base):
    def test_cancel_kills_the_tree_and_the_session_stays_resumable(self) -> None:
        record = self.runner.start("SLOW essay", partial=True)
        self._wait_events(record["run_id"], 3)
        outcome = self.runner.cancel(record["run_id"])
        self.assertTrue(outcome["ok"], outcome)
        self.assertEqual(outcome["status"], "cancelled")
        self.assertIn(record["pid"], outcome["tree"])
        self.assertFalse(ch._pid_alive(record["pid"], record.get("pid_create_time")))
        done = self.runner.status(record["run_id"])
        self.assertEqual(done["status"], "cancelled")
        self.assertIsNotNone(done["cancel_requested_at"])
        self.assertGreaterEqual(done["event_count"], 3)
        self.assertIsNone(done["result_text"])
        again = self.runner.cancel(record["run_id"])
        self.assertFalse(again["ok"])
        self.assertEqual(again["reason"], "already terminal")
        followup = self.runner.wait(self.runner.followup(record["run_id"], "continue after cancel")["run_id"], timeout=20)
        self.assertEqual(followup["status"], "completed")
        self.assertEqual(followup["session_id"], record["session_id"])
        self.assertIn('"SLOW essay"', followup["result_text"])

    def test_replacement_controller_sees_and_cancels_a_run_it_did_not_start(self) -> None:
        record = self.runner.start("SLOW background work")
        self._wait_events(record["run_id"], 2)
        self.runner._procs.clear()  # the starting controller is gone; only the disk remains
        replacement = ch.Runner(self.root, claude=STUB_ARGV)
        seen = replacement.status(record["run_id"])
        self.assertEqual(seen["status"], "running")
        self.assertEqual(replacement.recover(), [])  # alive child: nothing to finalize
        self.assertEqual([r["run_id"] for r in replacement.active()], [record["run_id"]])
        outcome = replacement.cancel(record["run_id"])
        self.assertTrue(outcome["ok"], outcome)
        self.assertEqual(replacement.status(record["run_id"])["status"], "cancelled")

    def test_recover_finalizes_orphans_from_bytes_on_disk(self) -> None:
        finished = self.runner.wait(self.runner.start("finished before the controller died")["run_id"], timeout=20)
        probe = subprocess.run([sys.executable, "-c", "pass"], capture_output=True)
        self.assertEqual(probe.returncode, 0)
        dead_pid = subprocess.Popen([sys.executable, "-c", "pass"])
        dead_pid.wait()
        run_dir = self.root / "runs" / finished["run_id"]
        forged = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        forged.update({"status": "running", "pid": dead_pid.pid, "pid_create_time": None, "exit_code": None, "ended_at": None, "result_text": None})
        (run_dir / "run.json").write_text(json.dumps(forged), encoding="utf-8")
        orphan_dir = self.root / "runs" / "orphan0000000001"
        orphan_dir.mkdir()
        (orphan_dir / "prompt.txt").write_bytes(b"never answered")
        (orphan_dir / "events.jsonl").write_bytes(b'{"type":"system","subtype":"init","session_id":"aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee","model":"stub-model"}\n')
        orphan = dict(forged)
        orphan.update({"run_id": "orphan0000000001", "session_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee", "created_at": "2026-01-01T00:00:00.000Z", "child_model": None, "event_count": 0})
        (orphan_dir / "run.json").write_text(json.dumps(orphan), encoding="utf-8")
        replacement = ch.Runner(self.root, claude=STUB_ARGV)
        recovered = {r["run_id"]: r["status"] for r in replacement.recover()}
        self.assertEqual(recovered[finished["run_id"]], "completed")
        self.assertEqual(recovered["orphan0000000001"], "interrupted")
        self.assertIn("finished before", replacement.status(finished["run_id"])["result_text"])
        self.assertEqual(replacement.recover(), [])

    @unittest.skipUnless(os.name == "nt", "window enumeration is Windows-only")
    def test_child_owns_no_visible_window_on_windows(self) -> None:
        record = self.runner.start("SLOW quiet")
        self.assertEqual(record["headless"]["creationflags"], ch.CREATE_NO_WINDOW | ch.CREATE_NEW_PROCESS_GROUP)
        time.sleep(1.6)
        seen = self.runner.status(record["run_id"])["headless"]
        self.assertEqual(seen["child_visible_windows"], 0)
        self.assertIn(record["pid"], seen["child_pids_t_plus_1s"])
        self.assertIsInstance(seen["foreground_before"], list)
        self.runner.cancel(record["run_id"])
        final = self.runner.status(record["run_id"])["headless"]
        self.assertIsInstance(final["foreground_at_finalize"], list)
        self.assertIn(final["foreground_unchanged"], (True, False))


if __name__ == "__main__":
    unittest.main()
