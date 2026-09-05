import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from integrations.gemini_slack.peer_tool_gateway import ToolCallStore, ToolLoop
from integrations.shared_equipment.services import CombinedCatalog, ServiceEquipment, redacted
from integrations.shared_equipment.slack_carrier import SlackEquipmentCarrier, parse_request


class EquipmentTests(unittest.TestCase):
    def test_slack_reads_use_query_and_secret_stays_in_header(self):
        requests = []
        def opener(request, **kwargs):
            requests.append(request)
            return io.BytesIO(b'{"ok":true,"messages":[]}')
        tool = ServiceEquipment(slack_token_loader=lambda: "xoxb-synthetic-only", opener=opener)
        result = tool.call("slack_read_thread", {"channel_id": "C123", "thread_ts": "1.2"})
        self.assertFalse(result["isError"])
        request = requests[0]
        self.assertEqual(request.get_method(), "GET")
        self.assertIn("channel=C123", request.full_url)
        self.assertIn("ts=1.2", request.full_url)
        self.assertNotIn("synthetic", request.full_url)
        self.assertIsNone(request.data)
        self.assertNotIn("synthetic", json.dumps(result))

    def test_provider_secret_fields_and_token_strings_are_scrubbed(self):
        result = redacted({"nested": [{"bot_token": "example", "text": "ghp_SYNTHETIC xoxb-SYNTHETIC"}], "normal": "read_count"})
        self.assertNotIn("SYNTHETIC", json.dumps(result))
        self.assertEqual(result["normal"], "read_count")

    def test_gh_uses_fixed_host_stdin_and_no_shell(self):
        calls = []
        def runner(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, '{"sha":"abc"}', '')
        equipment = ServiceEquipment(gh_runner=runner)
        equipment.github("repos/owner/repo/git/trees", method="POST", payload={"tree": []})
        command, kwargs = calls[0]
        self.assertEqual(command[2:4], ["--hostname", "github.com"])
        self.assertEqual(json.loads(kwargs["input"]), {"tree": []})
        self.assertNotIn("shell", kwargs)

    def test_external_url_cannot_replace_repository_shape(self):
        equipment = ServiceEquipment(gh_runner=lambda *a, **k: self.fail("provider must not run"))
        result = equipment.call("github_read_file", {"repository": "https://elsewhere.invalid/x", "path": "a"})
        self.assertTrue(result["isError"])

    def test_same_logical_call_is_not_executed_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = ToolCallStore(Path(directory) / "calls.db")
            effects = []
            runner = lambda n, a: effects.append(a) or {"ok": True}
            first = calls.execute_journaled("equipment:r", "c", "slack_post_message", {"text": "same"}, runner)
            second = calls.execute_journaled("equipment:r", "c", "slack_post_message", {"text": "same"}, runner)
            conflict = calls.execute_journaled("equipment:r", "c", "slack_post_message", {"text": "different"}, runner)
            self.assertEqual(first, second)
            self.assertEqual(len(effects), 1)
            self.assertEqual(conflict["error"], "call_id_reused_with_different_arguments")
            calls.close()

    def test_interrupted_effect_is_reported_unknown_and_not_repeated(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = ToolCallStore(Path(directory) / "calls.db")
            import hashlib
            digest = hashlib.sha256(b'{}').hexdigest()
            calls._db.execute("INSERT INTO tool_calls VALUES(?,?,?,?,?,?,?)", ("r", "c", "write", digest, "started", None, 1))
            calls._db.commit()
            result = calls.execute_journaled("r", "c", "write", {}, lambda n,a: self.fail("must reconcile first"))
            self.assertEqual(result["error"], "tool_effect_unknown_after_interruption")
            calls.close()

    def test_catalog_is_injected_into_actual_model_loop(self):
        class Public:
            def tools(self, **kwargs): return [{"name": "read_observatory", "inputSchema": {}}]
            def call(self, name, args): return {"public": True}
        class Model:
            def turn(self, peer, prompt):
                self.prompt = prompt
                return "done"
        model = Model()
        catalog = CombinedCatalog(Public())
        with tempfile.TemporaryDirectory() as directory:
            calls = ToolCallStore(Path(directory) / "calls.db")
            self.assertEqual(ToolLoop(model, catalog, calls).run("r", "any-role", "work"), "done")
            self.assertIn('"name":"slack_post_message"', model.prompt)
            self.assertIn('"name":"github_commit_files"', model.prompt)
            self.assertEqual(len(Public().tools()), 1)
            calls.close()

    def test_slack_envelope_accepts_connector_footer_not_quoted_prose(self):
        envelope = '<commons_equipment_request>{"request_id":"r","call_id":"c","name":"equipment_catalog"}</commons_equipment_request>'
        self.assertEqual(parse_request(envelope + '\nSent using connector')["name"], "equipment_catalog")
        self.assertIsNone(parse_request("Example: " + envelope))

    def test_carrier_replay_shares_http_call_key_and_returns_exact_result(self):
        class Services:
            def __init__(self): self.sent = []
            def call(self, n, a): self.sent.append(a); return {"result": {"ok": True, "ts": "4.1"}}
        class Catalog:
            def __init__(self): self.services = Services(); self.effects = 0
            def call(self, n, a): self.effects += 1; return {"answer": "useful"}
        with tempfile.TemporaryDirectory() as directory:
            calls = ToolCallStore(Path(directory) / "calls.db")
            catalog = Catalog()
            carrier = SlackEquipmentCarrier(catalog, calls, {"channel_id": "C123"}, Path(directory)/"cursor.json")
            message = {"ts": "1.1", "text": '<commons_equipment_request>{"request_id":"r","call_id":"c","name":"read"}</commons_equipment_request>'}
            carrier.process(message)
            carrier.process(message)
            self.assertEqual(catalog.effects, 1)
            self.assertEqual(len(catalog.services.sent), 1)
            self.assertIn('"answer": "useful"', catalog.services.sent[0]["text"])
            calls.close()


if __name__ == "__main__":
    unittest.main()
