import json
import os
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PLUGIN = ROOT / "integrations" / "commons_network_plugin"
SERVER = PLUGIN / "scripts" / "server.mjs"
GIT_SHA = "a" * 40
CATALOG = {
    "call_first": {"tool": "discover_commons_capabilities", "resource": "commons://capabilities"},
    "parity_rule": "same capability, harness-native road",
    "shared": {"truth": "GitHub main"},
    "roads": [{"id": "raw-github"}],
    "harnesses": [
        {
            "id": "gemini-custom",
            "label": "Gemini custom MCP",
            "family": "gemini",
            "surface": "custom",
            "aliases": ["gemini"],
        }
    ],
    "capabilities": [{"id": "discover", "plain": "discover Commons capabilities"}],
}


class _GitTruthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/repos/test-owner/test-repo/commits/main":
            self._reply({"sha": GIT_SHA})
            return
        if path in {
            f"/test-owner/test-repo/{GIT_SHA}/harnesses/catalog.json",
            "/test-owner/test-repo/main/harnesses/catalog.json",
        }:
            self._reply(CATALOG)
            return
        self.send_response(404)
        self.end_headers()

    def _reply(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


class CommonsNetworkPluginTests(unittest.TestCase):
    def run_jsonl(self, *requests, env=None):
        completed = subprocess.run(
            ["node", str(SERVER), "--stdio"],
            cwd=PLUGIN,
            env=env,
            input="\n".join(json.dumps(request) for request in requests) + "\n",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        return [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]

    def test_manifest_and_self_test_report_repaired_surface(self):
        manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["version"], "0.3.1")
        completed = subprocess.run(
            ["node", str(SERVER), "--self-test"],
            cwd=PLUGIN,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        receipt = json.loads(completed.stdout)
        self.assertEqual(receipt["version"], "0.3.1")
        self.assertEqual(receipt["resources"], 18)

    def test_unsupported_protocol_is_not_echoed_and_capability_alias_is_listed(self):
        initialized, resources = self.run_jsonl(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2099-01-01"}},
            {"jsonrpc": "2.0", "id": 2, "method": "resources/list", "params": {}},
        )
        self.assertEqual(initialized["result"]["protocolVersion"], "2025-03-26")
        uris = [item["uri"] for item in resources["result"]["resources"]]
        self.assertIn("commons://capabilities", uris)

    def test_mixed_stdio_requests_keep_their_own_response_framing(self):
        initialize = json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
            separators=(",", ":"),
        ).encode("utf-8")
        ping = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "ping"}, separators=(",", ":")).encode("utf-8")
        wire = b"Content-Length: " + str(len(initialize)).encode("ascii") + b"\r\n\r\n" + initialize + ping + b"\n"
        completed = subprocess.run(
            ["node", str(SERVER), "--stdio"], cwd=PLUGIN, input=wire, capture_output=True, check=False
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(completed.stdout.startswith(b"Content-Length: "), completed.stdout)
        header, remainder = completed.stdout.split(b"\r\n\r\n", 1)
        length = int(header.split(b":", 1)[1].strip())
        first = json.loads(remainder[:length])
        second = json.loads(remainder[length:].strip())
        self.assertEqual(first["id"], 1)
        self.assertEqual(second["id"], 2)

    def test_discovery_is_pinned_to_reported_git_head_and_alias_reads(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), _GitTruthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            base = f"http://127.0.0.1:{server.server_port}"
            env = os.environ.copy()
            env.update(
                {
                    "COMMONS_GITHUB_API_BASE": base,
                    "COMMONS_GITHUB_RAW_BASE": base,
                    "COMMONS_GITHUB_REPO": "test-owner/test-repo",
                    "COMMONS_GITHUB_BRANCH": "main",
                    "COMMONS_RAW_BASE": base + "/test-owner/test-repo/main",
                    "COMMONS_PAGES_BASE": "http://127.0.0.1:9",
                }
            )
            discovery, resource = self.run_jsonl(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": "discover_commons_capabilities", "arguments": {"harness": "gemini"}},
                },
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "resources/read",
                    "params": {"uri": "commons://capabilities"},
                },
                env=env,
            )
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        result = discovery["result"]["structuredContent"]
        self.assertEqual(result["git_sha"], GIT_SHA)
        self.assertEqual(result["truth"], "github_branch_head")
        self.assertEqual(result["road"], "raw_github")
        self.assertEqual(result["harnesses"][0]["id"], "gemini-custom")
        content = resource["result"]["contents"][0]
        self.assertEqual(content["uri"], "commons://capabilities")
        self.assertEqual(json.loads(content["text"])["call_first"]["tool"], "discover_commons_capabilities")


if __name__ == "__main__":
    unittest.main()
