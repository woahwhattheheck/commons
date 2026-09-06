import ast
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = (
    Path(__file__).parent / "integrations" / "gemini_slack" / "install_capture_async.py"
)
SPEC = importlib.util.spec_from_file_location("gemini_capture_async_install", MODULE_PATH)
install_mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = install_mod
SPEC.loader.exec_module(install_mod)

HELPER_PATH = Path(__file__).parent / "integrations" / "gemini_slack" / "upstream_turn.py"

CAPTURE_SOURCE = """import time
import json
import urllib.request

TERMINAL_STATUSES = {"completed", "error"}

class EventStore:
    def __init__(self, event_log):
        self.latest_by_request = {}
    def append(self, **fields):
        return fields

class Gateway:
    def __init__(self, event_log, upstream=None):
        self.upstream = upstream
        self.events = EventStore(event_log)

    def upstream_turn(self, peer_name: str, message: str) -> str:
        return "sync-reply"

    def execute(self, request_id, peer_name, message):
        started = time.monotonic()
        try:
            if self.upstream is not None:
                if True:
                    reply = self.upstream_turn(peer_name, message)
            reply_bytes = reply.encode("utf-8")
            return self.events.append(
                request_id=request_id,
                peer=peer_name,
                status="completed",
                reply_bytes=len(reply_bytes),
            )
        except Exception as exc:
            return self.events.append(
                request_id=request_id,
                peer=peer_name,
                status="error",
                message=str(exc),
            )
"""


class CaptureAsyncInstallTests(unittest.TestCase):
    def test_patch_adds_async_forwarding_and_interrupted_terminal(self):
        patched = install_mod.patch_gateway(CAPTURE_SOURCE)
        ast.parse(patched)
        self.assertIn("commons-async-upstream-v1", patched)
        self.assertIn("commons-async-recovery-v1", patched)
        self.assertIn("commons-async-terminal-v1", patched)
        self.assertIn("on_submitted=remember_upstream", patched)
        namespace = {}
        exec(compile(patched, "<capture>", "exec"), namespace)
        self.assertIn("interrupted", namespace["TERMINAL_STATUSES"])
        self.assertIn("completed", namespace["TERMINAL_STATUSES"])
        self.assertIn("error", namespace["TERMINAL_STATUSES"])

    def test_patch_is_idempotent_and_repairs_missing_interrupted(self):
        first = install_mod.patch_gateway(CAPTURE_SOURCE)
        second = install_mod.patch_gateway(first)
        self.assertEqual(first, second)
        missing_terminal = first.replace(
            "TERMINAL_STATUSES = TERMINAL_STATUSES | {'interrupted'}  # commons-async-terminal-v1\n",
            "",
        )
        self.assertNotIn("commons-async-terminal-v1", missing_terminal)
        repaired = install_mod.patch_gateway(missing_terminal)
        self.assertIn("commons-async-terminal-v1", repaired)
        self.assertIn("commons-async-upstream-v1", repaired)

    def test_install_writes_helper_without_starting_a_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gateway = root / "commons_peer_gateway.py"
            gateway.write_text(CAPTURE_SOURCE, encoding="utf-8")
            backup = root / "backups"
            result = install_mod.install(gateway, HELPER_PATH, backup)
            self.assertFalse(result["process_started"])
            self.assertTrue(result["source_updated"])
            helper = root / "commons_async_upstream.py"
            self.assertTrue(helper.is_file())
            helper_source = helper.read_text(encoding="utf-8")
            self.assertIn("def wait_peer_turn", helper_source)
            patched = gateway.read_text(encoding="utf-8")
            self.assertIn("commons-async-upstream-v1", patched)
            self.assertTrue(any(path.name.startswith(gateway.name) for path in backup.iterdir()))
            again = install_mod.install(gateway, HELPER_PATH, backup)
            self.assertFalse(again["process_started"])
            self.assertFalse(again["source_updated"])


if __name__ == "__main__":
    unittest.main()
