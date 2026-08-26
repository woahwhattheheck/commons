from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from host.titan_hands.broker import TitanHandsBroker
from host.titan_hands.mcp_server import dispatch
from host.titan_hands.routes import HandsRoutes
from host.titan_hands.runtime import TitanHandsRuntime


class FakeServer:
    def __init__(self, platform):
        self.platform = platform
        self.closed = False
        self.calls = []

    def handle(self, request):
        self.calls.append(dict(request))
        if request.get("op") == "capabilities":
            return {"ok": True, "kind": "capabilities", "platform": self.platform}
        if request.get("op") == "observe":
            return {"ok": True, "kind": "observation_delta", "platform": self.platform, "full": True}
        if request.get("op") == "act":
            return {
                "ok": True,
                "kind": "action_outcome",
                "platform": self.platform,
                "action": request["action"]["type"],
            }
        if request.get("op") == "capture":
            return {"ok": True, "kind": "pixel_capture", "platform": self.platform, "pixel_ref": "shot.png"}
        return {"ok": True, "kind": request["op"], "platform": self.platform}

    def close(self):
        self.closed = True


class FakeHttp:
    def __init__(self):
        self.calls = []
        self.response = {
            "status": 200,
            "headers": {"content-type": "application/json"},
            "body": json.dumps({"ok": True, "ts": "111.222", "messages": []}).encode("utf-8"),
            "error": "",
        }

    def __call__(self, method, url, headers=None, body=None, timeout=30):
        self.calls.append(
            {"method": method, "url": url, "headers": dict(headers or {}), "body": body, "timeout": timeout}
        )
        return dict(self.response)


def init_repo(path: Path) -> None:
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "hands@example.test"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Titan Hands"], cwd=path, check=True, capture_output=True)
    (path / "README.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "seed"], cwd=path, check=True, capture_output=True)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        init_repo(self.root)
        self.windows = FakeServer("windows")
        self.android = FakeServer("android")
        self.http = FakeHttp()
        self.runtime = TitanHandsRuntime(
            broker=TitanHandsBroker(
                factories={"windows": lambda: self.windows, "android": lambda: self.android}
            ),
            routes=HandsRoutes(repo_root=self.root, http=self.http, environ={}),
        )

    def tearDown(self):
        self.runtime.close()
        self.tmp.cleanup()

    def test_primary_tool_is_hands_and_compat_aliases_remain(self):
        listed = dispatch(self.runtime, {"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        names = [tool["name"] for tool in listed["result"]["tools"]]
        self.assertEqual(names[0], "hands")
        for alias in (
            "hands_targets",
            "hands_observe",
            "hands_act",
            "hands_capture",
            "hands_capabilities",
        ):
            self.assertIn(alias, names)

    def test_hands_catalog_marks_linux_not_written(self):
        result = self.runtime.handle({"op": "catalog"})
        self.assertTrue(result["ok"])
        routes = {row["route"]: row for row in result["routes"]}
        self.assertEqual(routes["computer"]["status"], "LIVE")
        self.assertEqual(routes["linux"]["status"], "ADAPTER_NOT_WRITTEN")
        self.assertEqual(routes["slack"]["channel"], "C0BRGMDQB6G")

    def test_computer_observe_and_act_still_route_through_deltaui(self):
        observe = self.runtime.handle({"op": "observe", "target": "android"})
        self.assertEqual(observe["platform"], "android")
        self.assertEqual(observe["kind"], "observation_delta")
        acted = self.runtime.handle(
            {"route": "computer", "op": "act", "target": "windows", "action": {"type": "invoke", "id": "b"}}
        )
        self.assertTrue(acted["ok"])
        self.assertEqual(acted["action"], "invoke")
        self.assertEqual(self.windows.calls[-1]["op"], "act")

    def test_compat_observe_alias_still_works(self):
        called = dispatch(
            self.runtime,
            {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "tools/call",
                "params": {"name": "hands_observe", "arguments": {"target": "windows"}},
            },
        )
        payload = json.loads(called["result"]["content"][0]["text"])
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["platform"], "windows")
        self.assertFalse(called["result"]["isError"])

    def test_linux_is_named_and_not_pretend_live(self):
        result = self.runtime.handle({"route": "linux", "op": "observe"})
        self.assertFalse(result["ok"])
        self.assertEqual(result["failure_reason"], "ADAPTER_NOT_WRITTEN")
        self.assertEqual(result["evidence"]["sketch"]["observation"], "at-spi2 accessibility tree")

    def test_file_write_is_additive_only(self):
        created = self.runtime.handle(
            {"route": "file", "op": "write", "path": "notes/new.txt", "contents": "hello"}
        )
        self.assertTrue(created["ok"])
        self.assertEqual((self.root / "notes" / "new.txt").read_text(encoding="utf-8"), "hello")
        again = self.runtime.handle(
            {"route": "file", "op": "write", "path": "notes/new.txt", "contents": "nope"}
        )
        self.assertEqual(again["failure_reason"], "PATH_EXISTS")
        listed = self.runtime.handle({"route": "file", "op": "list", "path": "notes"})
        self.assertEqual(listed["names"], ["new.txt"])

    def test_board_post_refuses_remint_and_mno(self):
        first = self.runtime.handle(
            {
                "route": "board",
                "op": "post",
                "id": "cursor-hands-fixture-0001",
                "body": "PLAIN: fixture",
            }
        )
        self.assertTrue(first["ok"])
        remint = self.runtime.handle(
            {
                "route": "board",
                "op": "post",
                "id": "cursor-hands-fixture-0001",
                "body": "PLAIN: remint",
            }
        )
        self.assertEqual(remint["failure_reason"], "REMINT_REFUSED")
        mno = self.runtime.handle(
            {"route": "file", "op": "write", "path": "commons.mno", "contents": "no"}
        )
        self.assertEqual(mno["failure_reason"], "MNO_REFUSED")

    def test_git_add_refuses_tracked_head_paths(self):
        tracked = self.runtime.handle({"route": "git", "op": "add", "path": "README.md"})
        self.assertEqual(tracked["failure_reason"], "NOT_ADDITIVE")
        (self.root / "extra.md").write_text("new\n", encoding="utf-8")
        added = self.runtime.handle({"route": "git", "op": "add", "path": "extra.md"})
        self.assertTrue(added["ok"])
        committed = self.runtime.handle(
            {"route": "git", "op": "commit", "message": "add extra.md"}
        )
        self.assertTrue(committed["ok"])
        status = self.runtime.handle({"route": "git", "op": "status"})
        self.assertTrue(status["ok"])

    def test_slack_fails_closed_without_token_and_refuses_invented_dest(self):
        missing = self.runtime.handle({"route": "slack", "op": "read"})
        self.assertEqual(missing["failure_reason"], "TOKEN_MISS")
        self.assertEqual(self.http.calls, [])
        refused = self.runtime.handle(
            {"route": "slack", "op": "post", "channel": "C0SOMEOTHER1", "text": "hi"}
        )
        self.assertEqual(refused["failure_reason"], "CHANNEL_REFUSED")
        self.assertEqual(self.http.calls, [])

    def test_slack_posts_only_commons_when_token_present(self):
        self.runtime.routes.environ["COMMONS_SLACK_BOT_TOKEN"] = "xoxb-fixture"
        posted = self.runtime.handle({"route": "slack", "op": "post", "text": "same table"})
        self.assertTrue(posted["ok"])
        self.assertEqual(self.http.calls[-1]["url"], "https://slack.com/api/chat.postMessage")
        payload = json.loads(self.http.calls[-1]["body"].decode("utf-8"))
        self.assertEqual(payload["channel"], "C0BRGMDQB6G")
        self.assertNotIn("xoxb-fixture", json.dumps(posted))

    def test_shell_and_web_keep_pixels_off_default_path(self):
        shell = self.runtime.handle(
            {"route": "shell", "op": "run", "command": ["python3", "-c", "print('hands-ok')"]}
        )
        self.assertTrue(shell["ok"])
        self.assertIn("hands-ok", shell["stdout"])
        self.http.response = {
            "status": 200,
            "headers": {"content-type": "image/png"},
            "body": b"\x89PNG",
            "error": "",
        }
        image = self.runtime.handle({"route": "web", "op": "fetch", "url": "https://example.com/x.png"})
        self.assertTrue(image["ok"])
        self.assertFalse(image["pixels"])
        self.assertNotIn("text", image)
        self.http.response = {
            "status": 200,
            "headers": {"content-type": "text/plain"},
            "body": b"hello web",
            "error": "",
        }
        text = self.runtime.handle({"route": "web", "op": "fetch", "url": "https://example.com/"})
        self.assertEqual(text["text"], "hello web")

    def test_path_escape_is_typed(self):
        result = self.runtime.handle({"route": "file", "op": "read", "path": "../secret"})
        self.assertEqual(result["failure_reason"], "PATH_OUTSIDE_REPO")


if __name__ == "__main__":
    unittest.main()
