#!/usr/bin/env python3
"""Headless Claude gateway: start, watch, follow up, cancel, recover — against a stub CLI.

These tests never invoke the real Claude CLI and spend no model usage. A stub
``claude`` (a Python script) speaks the CLI's stream-json shape and keeps a
per-session memory file so ``--resume`` continuity is observable. The live
round trip against the real CLI is recorded in the receipt, not here.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import uuid
from pathlib import Path

MODULE_PATH = Path(__file__).parent / "integrations" / "claude_headless" / "gateway.py"
SPEC = importlib.util.spec_from_file_location("claude_headless_gateway", MODULE_PATH)
gateway = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = gateway
SPEC.loader.exec_module(gateway)

CLIENT_PATH = Path(__file__).parent / "integrations" / "claude_headless" / "client.py"
CSPEC = importlib.util.spec_from_file_location("claude_headless_client", CLIENT_PATH)
client_mod = importlib.util.module_from_spec(CSPEC)
assert CSPEC.loader is not None
sys.modules[CSPEC.name] = client_mod
CSPEC.loader.exec_module(client_mod)


STUB = r'''
import json, os, sys, time, uuid
args = sys.argv[1:]
def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default
if "--version" in args:
    print("0.0.0-stub (claude stub)"); sys.exit(0)
sid = opt("--session-id") or opt("--resume") or str(uuid.uuid4())
prompt = sys.stdin.read()
def emit(o):
    sys.stdout.write(json.dumps(o) + "\n"); sys.stdout.flush()
emit({"type": "system", "subtype": "init", "session_id": sid, "model": opt("--model", "stub-model"),
      "cwd": os.getcwd(), "claudecode_env": "CLAUDECODE" in os.environ,
      "run_env": os.environ.get("CLAUDE_HEADLESS_RUN_ID"), "resumed": "--resume" in args, "argv": args})
mem_dir = os.environ.get("STUB_MEMORY_DIR", ".")
mem = os.path.join(mem_dir, sid + ".txt")
if prompt.startswith("REMEMBER "):
    open(mem, "w").write(prompt.split(" ", 1)[1].strip()); text = "stored"
elif prompt.startswith("RECALL"):
    text = open(mem).read() if os.path.exists(mem) else "nothing"
elif prompt.startswith("SLEEP "):
    time.sleep(float(prompt.split()[1])); text = "woke"
elif prompt.startswith("FAIL"):
    emit({"type": "assistant", "message": {"content": [{"type": "text", "text": "boom"}]}, "session_id": sid})
    emit({"type": "result", "subtype": "error_during_execution", "is_error": True, "result": "boom",
          "session_id": sid, "num_turns": 1})
    sys.exit(1)
elif prompt.startswith("CRASH"):
    sys.stderr.write("stub crashed on purpose\n"); sys.exit(3)
else:
    text = "echo:" + prompt.strip()
emit({"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": text}]},
      "session_id": sid})
emit({"type": "result", "subtype": "success", "is_error": False, "result": text, "session_id": sid,
      "num_turns": 1, "total_cost_usd": 0.0, "duration_ms": 5})
'''


def http(method, url, body=None, timeout=30):
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode())


class Fixture:
    def __init__(self, state_dir=None, max_concurrent=3, mem_dir=None):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.state_dir = Path(state_dir) if state_dir else self.root / "state"
        self.stub = self.root / "stub_claude.py"
        self.stub.write_text(STUB, encoding="utf-8")
        self.mem = Path(mem_dir) if mem_dir else self.root / "mem"
        self.mem.mkdir(exist_ok=True)
        env = dict(os.environ)
        env["CLAUDECODE"] = "1"  # the gateway must strip this before the child starts
        env["CLAUDE_CODE_ENTRYPOINT"] = "test"
        env["STUB_MEMORY_DIR"] = str(self.mem)
        self.server = gateway.Gateway(
            ("127.0.0.1", 0),
            state_dir=self.state_dir,
            claude_cmd=[sys.executable, str(self.stub)],
            max_concurrent=max_concurrent,
            env_base=env,
        )
        self.port = self.server.server_address[1]
        self.base = f"http://127.0.0.1:{self.port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.client = client_mod.HeadlessClient(self.base)

    def close(self, keep_state=False):
        self.server.shutdown_gateway()
        if not keep_state:
            self.tmp.cleanup()

    def submit(self, prompt, **fields):
        status, body = http("POST", self.base + "/v1/runs", {"prompt": prompt, "cwd": str(self.root), **fields})
        assert status == 202, (status, body)
        return body

    def wait(self, run_id, seconds=15):
        status, body = http("GET", self.base + f"/v1/runs/{run_id}?wait_ms={int(seconds * 1000)}")
        assert status == 200, (status, body)
        return body["run"]

    def until(self, run_id, wanted, seconds=10):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            status, body = http("GET", self.base + f"/v1/runs/{run_id}")
            if body["run"]["status"] in wanted:
                return body["run"]
            time.sleep(0.05)
        raise AssertionError(f"run {run_id} never reached {wanted}: {body['run']['status']}")


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.fx = Fixture()

    def tearDown(self):
        self.fx.close()

    def test_submit_runs_headless_and_completes_with_durable_session(self):
        ack = self.fx.submit("hello there", label="first", **{"from": "TESTPEER"})
        self.assertEqual(ack["status"], "queued")
        uuid.UUID(ack["session_id"])
        run = self.fx.wait(ack["run_id"])
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["result_text"], "echo:hello there")
        self.assertEqual(run["reply"], "echo:hello there")
        self.assertEqual(run["kind"], "new")
        self.assertEqual(run["submitted_by"], "TESTPEER")
        self.assertEqual(run["exit_code"], 0)
        self.assertIn("--session-id", run["command"])
        self.assertIn(ack["session_id"], run["command"])
        self.assertNotIn("hello there", " ".join(run["command"]), "prompt travels over stdin, not argv")
        status, page = http("GET", self.fx.base + f"/v1/runs/{ack['run_id']}/events")
        kinds = [e["kind"] for e in page["events"]]
        statuses = [e["status"] for e in page["events"] if e["kind"] == "gateway"]
        self.assertEqual(statuses, ["queued", "starting", "running", "completed"])
        self.assertEqual(kinds[:4], ["gateway", "gateway", "gateway", "system"])
        self.assertIn("assistant", kinds)
        self.assertIn("result", kinds)
        self.assertEqual(page["events"][-1]["status"], "completed")
        init = next(e for e in page["events"] if e["kind"] == "system")["payload"]
        self.assertFalse(init["claudecode_env"], "CLAUDECODE must not reach the child")
        self.assertEqual(init["run_env"], ack["run_id"])
        self.assertEqual(init["session_id"], ack["session_id"])
        self.assertTrue((self.fx.state_dir / "runs" / f"{ack['run_id']}.stdout.jsonl").is_file())

    def test_followup_resumes_the_exact_same_conversation(self):
        first = self.fx.submit("REMEMBER pearl")
        self.assertEqual(self.fx.wait(first["run_id"])["result_text"], "stored")
        status, ack = http("POST", self.fx.base + f"/v1/runs/{first['run_id']}/followup", {"prompt": "RECALL"})
        self.assertEqual(status, 202, ack)
        self.assertEqual(ack["session_id"], first["session_id"])
        run = self.fx.wait(ack["run_id"])
        self.assertEqual(run["status"], "completed")
        self.assertEqual(run["result_text"], "pearl")
        self.assertEqual(run["kind"], "followup")
        self.assertEqual(run["parent_run_id"], first["run_id"])
        self.assertIn("--resume", run["command"])
        self.assertNotIn("--session-id", run["command"])
        # a coordinator holding only the session id can also continue it
        status, ack2 = http("POST", self.fx.base + f"/v1/sessions/{first['session_id']}/runs", {"prompt": "RECALL"})
        self.assertEqual(status, 202, ack2)
        self.assertEqual(self.fx.wait(ack2["run_id"])["result_text"], "pearl")
        status, view = http("GET", self.fx.base + f"/v1/sessions/{first['session_id']}")
        self.assertEqual(status, 200)
        self.assertEqual(view["run_count"], 3)
        self.assertEqual([r["kind"] for r in view["runs"]], ["new", "followup", "followup"])
        self.assertIn("transcript_path", view)

    def test_cancel_stops_that_run_only_and_session_stays_resumable(self):
        first = self.fx.submit("REMEMBER anchor")
        self.fx.wait(first["run_id"])
        status, sleeper = http("POST", self.fx.base + f"/v1/runs/{first['run_id']}/followup", {"prompt": "SLEEP 30"})
        running = self.fx.until(sleeper["run_id"], {"running"})
        pid = running["pid"]
        self.assertTrue(gateway.pid_alive(pid))
        started = time.monotonic()
        status, outcome = http("POST", self.fx.base + f"/v1/runs/{sleeper['run_id']}/cancel", {})
        self.assertEqual(status, 200, outcome)
        self.assertEqual(outcome["status"], "cancelled")
        self.assertLess(time.monotonic() - started, 10)
        run = self.fx.wait(sleeper["run_id"], 5)
        self.assertEqual(run["status"], "cancelled")
        self.assertTrue(run["cancel_requested"])
        deadline = time.monotonic() + 5
        while gateway.pid_alive(pid) and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertFalse(gateway.pid_alive(pid), "the cancelled run's process must be gone")
        status, ack = http("POST", self.fx.base + f"/v1/runs/{first['run_id']}/followup", {"prompt": "RECALL"})
        self.assertEqual(self.fx.wait(ack["run_id"])["result_text"], "anchor")
        status, again = http("POST", self.fx.base + f"/v1/runs/{sleeper['run_id']}/cancel", {})
        self.assertEqual(again["note"], "already terminal")

    def test_cancel_before_start_never_spawns(self):
        blocker = self.fx.submit("SLEEP 3")
        self.fx.until(blocker["run_id"], {"running"})
        status, queued = http("POST", self.fx.base + f"/v1/runs/{blocker['run_id']}/followup", {"prompt": "never"})
        self.assertEqual(self.fx.until(queued["run_id"], {"queued"})["status"], "queued")
        status, outcome = http("POST", self.fx.base + f"/v1/runs/{queued['run_id']}/cancel", {})
        self.assertEqual(outcome["status"], "cancelled")
        run = self.fx.wait(queued["run_id"], 2)
        self.assertIsNone(run["pid"])
        self.assertEqual(run["error"], "cancelled before start")
        http("POST", self.fx.base + f"/v1/runs/{blocker['run_id']}/cancel", {})

    def test_failed_result_and_crash_are_reported_not_hidden(self):
        failed = self.fx.wait(self.fx.submit("FAIL")["run_id"])
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["result_text"], "boom")
        self.assertIn("is_error=True", failed["error"])
        crashed = self.fx.wait(self.fx.submit("CRASH")["run_id"])
        self.assertEqual(crashed["status"], "failed")
        self.assertEqual(crashed["exit_code"], 3)
        self.assertIn("without a result event", crashed["error"])
        self.assertIn("stub crashed on purpose", crashed["stderr_tail"])

    def test_same_session_is_fifo_and_other_sessions_run_concurrently(self):
        a1 = self.fx.submit("SLEEP 2")
        self.fx.until(a1["run_id"], {"running"})
        status, a2 = http("POST", self.fx.base + f"/v1/runs/{a1['run_id']}/followup", {"prompt": "second"})
        time.sleep(0.3)
        self.assertEqual(self.fx.until(a2["run_id"], {"queued"})["status"], "queued")
        b1 = self.fx.submit("other session")
        b_done = self.fx.wait(b1["run_id"], 5)
        self.assertEqual(b_done["status"], "completed")
        self.assertIn(self.fx.until(a1["run_id"], {"running", "completed"})["status"], {"running", "completed"})
        self.assertEqual(self.fx.wait(a2["run_id"], 10)["result_text"], "echo:second")
        self.assertEqual(self.fx.wait(a1["run_id"], 1)["result_text"], "woke")

    def test_events_cursor_long_polls_and_never_repeats(self):
        status, before = http("GET", self.fx.base + "/v1/events?after=0")
        cursor = before["next_cursor"]
        box = {}

        def poll():
            box["page"] = http("GET", self.fx.base + f"/v1/events?after={cursor}&wait_ms=8000")[1]

        thread = threading.Thread(target=poll)
        thread.start()
        time.sleep(0.2)
        ack = self.fx.submit("ping")
        thread.join(timeout=10)
        page = box["page"]
        self.assertTrue(page["events"], "long poll must wake on the new event")
        self.assertTrue(all(e["event_id"] > cursor for e in page["events"]))
        self.assertEqual(page["events"][0]["run_id"], ack["run_id"])
        self.fx.wait(ack["run_id"])
        status, rest = http("GET", self.fx.base + f"/v1/events?after={page['next_cursor']}")
        ids = [e["event_id"] for e in rest["events"]]
        self.assertEqual(ids, sorted(set(ids)))
        self.assertTrue(all(i > page["next_cursor"] for i in ids))

    def test_message_alias_matches_gemini_gateway_shape(self):
        status, body = http("POST", self.fx.base + "/v1/message", {"peer": "CLAUDE", "message": "shape", "wait_ms": 10000})
        self.assertEqual(status, 200, body)
        self.assertTrue(body["ok"])
        self.assertEqual(body["reply"], "echo:shape")
        self.assertEqual(body["reply_utf8_base64"], "ZWNobzpzaGFwZQ==")
        self.assertEqual(body["request_id"], body["run_id"])
        status, req = http("GET", self.fx.base + f"/v1/requests/{body['run_id']}")
        self.assertEqual(req["event"]["status"], "completed")
        status, asyn = http("POST", self.fx.base + "/v1/message", {"peer": "ANY", "message": "later", "async": True})
        self.assertEqual(status, 202)
        self.assertEqual(asyn["status"], "queued")
        self.fx.wait(asyn["run_id"])

    def test_health_reports_cli_and_counts(self):
        status, health = http("GET", self.fx.base + "/health")
        self.assertTrue(health["ok"])
        self.assertEqual(health["service"], gateway.SERVICE)
        self.assertTrue(health["cli"]["ok"])
        self.assertIn("stub", health["cli"]["version"])
        self.assertIn("POST /v1/runs", health["endpoints"])
        self.fx.wait(self.fx.submit("x")["run_id"])
        status, health = http("GET", self.fx.base + "/health")
        self.assertEqual(health["counts"].get("completed"), 1)
        self.assertGreater(health["event_cursor"], 0)

    def test_bad_requests_are_explained(self):
        status, body = http("POST", self.fx.base + "/v1/runs", {"prompt": "   "})
        self.assertEqual(status, 400)
        self.assertIn("nonempty", body["message"])
        status, body = http("POST", self.fx.base + "/v1/runs", {"prompt": "x", "session_id": "not-a-uuid"})
        self.assertEqual(status, 400)
        status, body = http("POST", self.fx.base + "/v1/runs/nope/followup", {"prompt": "x"})
        self.assertEqual(status, 400)
        status, body = http("GET", self.fx.base + "/v1/runs/nope")
        self.assertEqual(status, 404)
        status, body = http("POST", self.fx.base + "/v1/runs", {"prompt": "x", "cwd": str(self.fx.root / "missing")})
        self.assertEqual(status, 400)

    def test_any_loopback_caller_is_served_without_identity_fields(self):
        status, body = http("POST", self.fx.base + "/v1/runs", {"prompt": "no identity fields at all"})
        self.assertEqual(status, 202, body)
        run = self.fx.wait(body["run_id"])
        self.assertEqual(run["status"], "completed")
        self.assertIsNone(run["submitted_by"])

    def test_client_module_round_trip(self):
        ack = self.fx.client.submit("via client", cwd=str(self.fx.root))
        view = self.fx.client.wait(ack["run_id"], 15)
        self.assertEqual(view["run"]["result_text"], "echo:via client")
        follow = self.fx.client.followup(ack["run_id"], "again", cwd=str(self.fx.root))
        self.assertEqual(self.fx.client.wait(follow["run_id"], 15)["run"]["result_text"], "echo:again")
        events = self.fx.client.events(ack["run_id"])
        self.assertTrue(events["events"])
        self.assertEqual(self.fx.client.session(ack["session_id"])["run_count"], 2)
        self.assertTrue(self.fx.client.health()["ok"])


class RecoveryTests(unittest.TestCase):
    def test_restart_marks_dead_runs_interrupted_and_dispatches_queued_ones(self):
        first = Fixture()
        state_dir = first.state_dir
        root = first.root
        done = first.wait(first.submit("REMEMBER before-restart")["run_id"])
        session_id = done["session_id"]
        # a run left active by a gateway that died: dead pid, no reader
        store = first.server.store
        dead = {
            "run_id": uuid.uuid4().hex, "session_id": str(uuid.uuid4()), "parent_run_id": None, "kind": "new",
            "label": None, "submitted_by": None, "cwd": str(root), "prompt": "orphan", "prompt_sha256": "x",
            "prompt_bytes": 6, "options": {}, "status": "running", "created_at": gateway.utc_now(),
        }
        store.insert_run(dead)
        store.update_run(dead["run_id"], pid=2_000_000_000)
        # a run queued but never started by the previous process, prompt retained
        queued = {**dead, "run_id": uuid.uuid4().hex, "session_id": str(uuid.uuid4()), "prompt": "late start",
                  "status": "queued", "created_at": gateway.utc_now()}
        store.insert_run(queued)
        first.server.shutdown_gateway()
        # same journal, same stub memory (the "transcript"); a brand-new gateway process
        second = Fixture(state_dir=state_dir, mem_dir=first.mem)
        try:
            self.assertIn(dead["run_id"], second.server.recovery["interrupted"])
            self.assertIn(queued["run_id"], second.server.recovery["requeued"])
            interrupted = http("GET", second.base + f"/v1/runs/{dead['run_id']}")[1]["run"]
            self.assertEqual(interrupted["status"], "interrupted")
            self.assertIn("follow up to continue", interrupted["error"])
            self.assertFalse(interrupted["pid_alive"])
            late = second.wait(queued["run_id"], 15)
            self.assertEqual(late["status"], "completed")
            self.assertEqual(late["result_text"], "echo:late start")
            # the earlier conversation is still continuable after the restart
            status, ack = http("POST", second.base + f"/v1/sessions/{session_id}/runs", {"prompt": "RECALL"})
            self.assertEqual(status, 202, ack)
            self.assertEqual(second.wait(ack["run_id"])["result_text"], "before-restart")
            status, health = http("GET", second.base + "/health")
            self.assertEqual(health["counts"]["interrupted"], 1)
            self.assertGreaterEqual(health["event_cursor"], 10)
        finally:
            second.close()
            first.tmp.cleanup()


class PureFunctionTests(unittest.TestCase):
    def test_transcript_path_matches_claude_code_folder_naming(self):
        cwd = r"C:\Users\lucys\AppData\Local\Temp\claude\C--\c1d88905-bcd5-4af0-9ec8-00b8c9e56ac3\scratchpad\c1probe"
        path = gateway.transcript_path(cwd, "836f29ca-035f-4b5c-85ac-590a43db541d", home=Path("/h"))
        self.assertEqual(
            path.name, "836f29ca-035f-4b5c-85ac-590a43db541d.jsonl",
        )
        self.assertEqual(
            path.parent.name,
            "C--Users-lucys-AppData-Local-Temp-claude-C---c1d88905-bcd5-4af0-9ec8-00b8c9e56ac3-scratchpad-c1probe",
        )

    def test_popen_kwargs_are_headless_and_env_is_unnested(self):
        env = gateway.headless_env({"CLAUDECODE": "1", "CLAUDE_CODE_ENTRYPOINT": "x", "PATH": "p"}, "run1")
        self.assertNotIn("CLAUDECODE", env)
        self.assertNotIn("CLAUDE_CODE_ENTRYPOINT", env)
        self.assertEqual(env["CLAUDE_HEADLESS_RUN_ID"], "run1")
        self.assertEqual(env["PATH"], "p")
        kwargs = gateway.build_popen_kwargs(".", env)
        self.assertIs(kwargs["stdin"], gateway.subprocess.PIPE)
        if os.name == "nt":
            self.assertTrue(kwargs["creationflags"] & 0x08000000, "CREATE_NO_WINDOW")
            self.assertTrue(kwargs["creationflags"] & 0x00000200, "CREATE_NEW_PROCESS_GROUP")
        else:
            self.assertTrue(kwargs["start_new_session"])

    def test_build_command_passes_only_requested_options(self):
        run = {"kind": "new", "session_id": "s", "options": {"model": "sonnet", "max_turns": 3, "strict_mcp_config": True,
                                                            "allowed_tools": ["Read", "Bash(git *)"], "fork_session": False}}
        cmd = gateway.build_command(["claude"], run)
        self.assertEqual(cmd[:6], ["claude", "-p", "--output-format", "stream-json", "--verbose", "--session-id"])
        self.assertIn("--model", cmd)
        self.assertEqual(cmd[cmd.index("--max-turns") + 1], "3")
        self.assertIn("--strict-mcp-config", cmd)
        self.assertNotIn("--fork-session", cmd)
        self.assertEqual(cmd[cmd.index("--allowedTools") + 1:cmd.index("--allowedTools") + 3], ["Read", "Bash(git *)"])
        follow = gateway.build_command(["claude"], {"kind": "followup", "session_id": "s", "options": {}})
        self.assertIn("--resume", follow)
        self.assertNotIn("--session-id", follow)


if __name__ == "__main__":
    unittest.main()
