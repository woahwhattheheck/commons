from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from host.titan_hands.mcp_one import TOOL, dispatch
from host.titan_hands.mcp_server import TOOLS as UNIFIED_TOOLS
from host.titan_hands.one_tool import TitanHandsOne, contains_pixel_payload
from host.titan_hands.lanes import (
    BoardServer,
    BrowserServer,
    FilesServer,
    GitServer,
    LinuxPendingServer,
    ShellServer,
    SlackServer,
)
from host.titan_hands_windows.mcp_server import TOOLS as WINDOWS_TOOLS


class FakeComputer:
    def __init__(self, platform: str) -> None:
        self.platform = platform
        self.closed = False
        self.name = "Idle"

    def handle(self, request):
        op = str(request.get("op") or "")
        if op == "capabilities":
            return {
                "ok": True,
                "kind": "capabilities",
                "platform": self.platform,
                "pixels": "on-demand-only",
            }
        if op == "observe":
            return {
                "ok": True,
                "kind": "observation_delta",
                "full": True,
                "added": [{"id": "b", "role": "Button", "name": self.name}],
                "updated": [],
                "removed": [],
                "pixels": "not-captured",
            }
        if op == "act":
            self.name = "Done"
            return {
                "ok": True,
                "kind": "action_outcome",
                "action": request["action"]["type"],
                "observation": {
                    "kind": "observation_delta",
                    "added": [],
                    "updated": [{"id": "b", "name": self.name}],
                    "removed": [],
                    "pixels": "not-captured",
                },
            }
        if op == "capture":
            return {
                "ok": True,
                "kind": "pixel_capture",
                "pixel_ref": f"{self.platform}.png",
                "platform": self.platform,
            }
        return {
            "ok": False,
            "kind": "failure",
            "failure_reason": "UNKNOWN_OPERATION",
            "message": f"unknown operation: {op or '<empty>'}",
        }

    def close(self):
        self.closed = True


class LeakyComputer(FakeComputer):
    def handle(self, request):
        result = super().handle(request)
        if request.get("op") == "observe":
            result = dict(result)
            result["pixel_ref"] = "leaked.png"
        return result


class OneToolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "notes.txt").write_text("hello", encoding="utf-8")
        self.windows = FakeComputer("windows")
        self.android = FakeComputer("android")
        self.posted = []
        self.board_ids = set()
        self.slack_messages = [{"ts": "1.0", "text": "table is open"}]
        self.browser_nodes = [
            {"id": "browser:document", "parent": "", "role": "Document", "name": "https://example", "actions": ["navigate"]},
            {"id": "a1", "parent": "browser:document", "role": "Link", "name": "Commons", "actions": ["click"]},
        ]
        self.one = TitanHandsOne(
            factories={
                "windows": lambda: self.windows,
                "android": lambda: self.android,
                "linux": LinuxPendingServer,
                "files": lambda: FilesServer(root=self.tmp),
                "git": lambda: GitServer(cwd=self.tmp, run=self._git),
                "slack": lambda: SlackServer(
                    history=lambda: list(self.slack_messages),
                    post=self._slack_post,
                ),
                "board": lambda: BoardServer(
                    exists=lambda ident: ident in self.board_ids,
                    submit=self._board_submit,
                    read=lambda ident: "landed" if ident in self.board_ids else None,
                    root=self.tmp,
                ),
                "shell": lambda: ShellServer(cwd=self.tmp, run=self._shell),
                "browser": lambda: BrowserServer(
                    snapshot=lambda: {"url": "https://example", "nodes": self.browser_nodes},
                    act=self._browser_act,
                    capture=lambda path: path,
                ),
            }
        )

    def tearDown(self):
        self.one.close()

    def _git(self, args):
        if args == ["rev-parse", "HEAD"]:
            return "abc123\n"
        if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
            return "main\n"
        if args[:2] == ["status", "--porcelain"]:
            return " M notes.txt\n"
        if args[0] == "log":
            return "abc123 land\n"
        if args[0] == "diff":
            return "diff --git a/notes.txt\n"
        return ""

    def _slack_post(self, text):
        row = {"ts": "2.0", "text": text}
        self.slack_messages.append(row)
        return row

    def _board_submit(self, payload):
        self.posted.append(dict(payload))
        self.board_ids.add(payload["id"])
        return {"ok": True, "http_status": 200, "note": "ntfy 200 is mail"}

    def _shell(self, command):
        if command == "false":
            return {"stdout": "", "stderr": "nope", "returncode": 1}
        return {"stdout": f"ran:{command}", "stderr": "", "returncode": 0}

    def _browser_act(self, action):
        if action.get("type") == "click":
            self.browser_nodes = [
                {"id": "browser:document", "parent": "", "role": "Document", "name": "clicked", "actions": []},
            ]
        return {"ok": True, "url": "https://example", "nodes": self.browser_nodes}

    def test_mcp_lists_exactly_one_tool_and_calls_it(self):
        listed = dispatch(self.one, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = [tool["name"] for tool in listed["result"]["tools"]]
        self.assertEqual(names, ["titan_hands"])
        self.assertEqual(TOOL["name"], "titan_hands")
        started = dispatch(self.one, {"jsonrpc": "2.0", "id": 2, "method": "initialize", "params": {}})
        self.assertIn("One TITAN Hands call", started["result"]["instructions"])
        called = dispatch(
            self.one,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "titan_hands", "arguments": {"op": "observe", "target": "windows"}},
            },
        )
        payload = json.loads(called["result"]["content"][0]["text"])
        self.assertTrue(payload["ok"])
        self.assertFalse(contains_pixel_payload(payload))
        self.assertFalse(called["result"]["isError"])

    def test_existing_four_and_five_tool_keeps_are_untouched(self):
        self.assertEqual([tool["name"] for tool in WINDOWS_TOOLS], [
            "hands_observe",
            "hands_act",
            "hands_capture",
            "hands_capabilities",
        ])
        self.assertEqual(len(UNIFIED_TOOLS), 5)

    def test_four_ops_cover_computer_use(self):
        observed = self.one.handle({"op": "observe", "target": "windows"})
        self.assertEqual(observed["added"][0]["name"], "Idle")
        self.assertFalse(contains_pixel_payload(observed))
        acted = self.one.handle({"op": "act", "target": "android", "action": {"type": "invoke", "id": "b"}})
        self.assertTrue(acted["ok"])
        self.assertFalse(contains_pixel_payload(acted))
        captured = self.one.handle({"op": "capture", "target": "windows"})
        self.assertEqual(captured["kind"], "pixel_capture")
        self.assertTrue(contains_pixel_payload(captured))
        caps = self.one.handle({"op": "capabilities", "target": "android"})
        self.assertEqual(caps["pixels"], "on-demand-only")
        self.assertFalse(contains_pixel_payload(caps))

    def test_observe_and_act_do_not_return_pixels(self):
        for target in ("windows", "android", "files", "git", "slack", "board", "shell", "browser"):
            observed = self.one.handle({"op": "observe", "target": target})
            self.assertTrue(observed["ok"], msg=target)
            self.assertFalse(contains_pixel_payload(observed), msg=target)
            self.assertNotEqual(observed.get("kind"), "pixel_capture")

    def test_capture_without_request_is_typed_on_non_pixel_lanes(self):
        for target in ("files", "git", "slack", "board", "shell"):
            result = self.one.handle({"op": "capture", "target": target})
            self.assertFalse(result["ok"], msg=target)
            self.assertEqual(result["failure_reason"], "PIXEL_UNSUPPORTED", msg=target)
            self.assertEqual(result["kind"], "failure")

    def test_leaked_observe_pixels_become_typed_failure(self):
        leaky = LeakyComputer("windows")
        router = TitanHandsOne(factories={"windows": lambda: leaky}, default_target="windows")
        result = router.handle({"op": "observe", "target": "windows"})
        self.assertEqual(result["failure_reason"], "PIXEL_POLICY")
        self.assertFalse(result["ok"])
        router.close()

    def test_linux_is_named_next_not_a_remint(self):
        caps = self.one.handle({"op": "capabilities", "target": "linux"})
        self.assertTrue(caps["ok"])
        self.assertEqual(caps["status"], "named-next")
        self.assertEqual(caps["adapter"], "at-spi")
        observed = self.one.handle({"op": "observe", "target": "linux"})
        self.assertEqual(observed["failure_reason"], "ADAPTER_PENDING")
        captured = self.one.handle({"op": "capture", "target": "linux"})
        self.assertEqual(captured["failure_reason"], "ADAPTER_PENDING")

    def test_unknown_target_and_empty_op_are_typed(self):
        missing = self.one.handle({"op": "observe", "target": "macos"})
        self.assertEqual(missing["failure_reason"], "INVALID_REQUEST")
        empty = self.one.handle({"op": "", "target": "windows"})
        self.assertEqual(empty["failure_reason"], "UNKNOWN_OPERATION")

    def test_files_read_write_and_git_status(self):
        written = self.one.handle(
            {
                "op": "act",
                "target": "files",
                "action": {"type": "write", "path": "out.txt", "text": "coil"},
            }
        )
        self.assertTrue(written["ok"])
        self.assertFalse(contains_pixel_payload(written))
        read = self.one.handle(
            {
                "op": "act",
                "target": "files",
                "action": {"type": "read", "path": "out.txt"},
                "observe_after": False,
            }
        )
        self.assertEqual(read["value"], "coil")
        git = self.one.handle({"op": "observe", "target": "git"})
        names = [node["name"] for node in git["added"]]
        self.assertIn("notes.txt", names)
        self.assertIn("abc123", names)

    def test_slack_board_shell_browser_routes(self):
        slack = self.one.handle(
            {"op": "act", "target": "slack", "action": {"type": "post", "text": "hello table"}}
        )
        self.assertTrue(slack["ok"])
        self.assertEqual(slack["channel"], "C0BRGMDQB6G")
        posted = self.one.handle(
            {
                "op": "act",
                "target": "board",
                "action": {
                    "type": "post",
                    "id": "coil-titan-hands-one-tool-test-20260826-01",
                    "body": "PLAIN: test",
                },
            }
        )
        self.assertTrue(posted["ok"])
        remint = self.one.handle(
            {
                "op": "act",
                "target": "board",
                "action": {
                    "type": "post",
                    "id": "coil-titan-hands-one-tool-test-20260826-01",
                    "body": "PLAIN: remint",
                },
                "observe_after": False,
            }
        )
        self.assertEqual(remint["failure_reason"], "ID_EXISTS")
        ran = self.one.handle({"op": "act", "target": "shell", "action": {"type": "run", "command": "echo hi"}})
        self.assertEqual(ran["stdout"], "ran:echo hi")
        failed = self.one.handle({"op": "act", "target": "shell", "action": {"type": "run", "command": "false"}})
        self.assertEqual(failed["failure_reason"], "COMMAND_FAILED")
        clicked = self.one.handle({"op": "act", "target": "browser", "action": {"type": "click", "id": "a1"}})
        self.assertTrue(clicked["ok"])
        self.assertFalse(contains_pixel_payload(clicked))
        captured = self.one.handle({"op": "capture", "target": "browser", "path": "shot.png"})
        self.assertEqual(captured["pixel_ref"], "shot.png")

    def test_slack_without_transport_is_typed(self):
        router = TitanHandsOne(factories={"slack": SlackServer})
        result = router.handle({"op": "observe", "target": "slack"})
        self.assertEqual(result["failure_reason"], "TRANSPORT_UNCONFIGURED")
        router.close()

    def test_target_catalog_names_linux_next(self):
        catalog = self.one.handle({"op": "targets"})
        names = [row["target"] for row in catalog["targets"]]
        self.assertEqual(
            names,
            ["android", "board", "browser", "files", "git", "linux", "shell", "slack", "windows"],
        )
        self.assertEqual(catalog["next_adapter"], "linux-at-spi")
        self.assertEqual(catalog["model_facing_tools"], 1)


if __name__ == "__main__":
    unittest.main()
