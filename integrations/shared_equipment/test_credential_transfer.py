"""Real encryption/transport contracts; dedicated CI installs the optional crypto dependency."""
import io
import json
import subprocess
import tempfile
import threading
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from integrations.shared_equipment import credential_transfer as ct
from integrations.shared_equipment.credential_client import CredentialRequest, retrieve_http
from integrations.shared_equipment.services import CombinedCatalog, ServiceEquipment, build_capability_manifest
from integrations.shared_equipment.slack_carrier import SlackEquipmentCarrier
from integrations.gemini_slack.peer_tool_gateway import EventStore, ToolCallStore, ToolGateway, ToolLoop

SENTINEL = "synthetic unpatterned value / snowman \u2603 / deliberately no token prefix"


class EmptyCatalog:
    def tools(self, **kwargs):
        return []


class CredentialTransferTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.sources = ct.CredentialSources(
            config_path=self.root / "sources.json", claude_path=self.root / "claude.json",
            slack_reader=lambda: {"bot_token": SENTINEL, "app_token": "synthetic-app"})
        self.equipment = ServiceEquipment(credential_sources=self.sources)

    def test_roundtrip_generic_sender_newcomer_and_no_cleartext_outputs(self):
        first, second = CredentialRequest("remote/example"), CredentialRequest("remote/example")
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            sealed = ct.seal_credential(first.arguments(), {"token": SENTINEL})
            self.assertEqual(first.open(sealed), {"token": SENTINEL})
        self.assertEqual(output.getvalue(), "")
        self.assertNotIn(SENTINEL, json.dumps(sealed))
        self.assertNotIn(SENTINEL, first.slack_request())
        self.assertNotIn("private", first.slack_request())
        self.assertNotIn("private", repr(first))
        with self.assertRaisesRegex(ct.CredentialTransferError, "credential_delivery_invalid"):
            second.open(sealed)

    def test_tampering_wrong_key_and_every_context_field_fail(self):
        pending = CredentialRequest("slack/bot")
        sealed = self.sources.retrieve_sealed(pending.arguments())
        for field in ct.HEADER_FIELDS + ("ciphertext",):
            bad = dict(sealed)
            bad[field] = ("0" if bad[field][0] != "0" else "1") + bad[field][1:]
            with self.subTest(field=field), self.assertRaises(ct.CredentialTransferError):
                pending.open(bad)
        for field in ct.CONTEXT_FIELDS:
            expected = pending.arguments()
            expected[field] = "0" * 64 if field == "recipient_public_key" else "different"
            with self.subTest(expected=field), self.assertRaises(ct.CredentialTransferError):
                ct.open_credential(sealed, pending._private_key, expected)

    def test_http_wrapper_ids_must_match_retained_request(self):
        pending = CredentialRequest("slack/bot")
        result = self.equipment.call("credential_retrieve_sealed", pending.arguments())
        for field in ("request_id", "call_id"):
            wrapped = {"ok": True, "request_id": pending.arguments()["request_id"],
                       "call_id": pending.arguments()["call_id"], "result": result}
            wrapped[field] = "different"
            with self.assertRaises(ct.CredentialTransferError):
                pending.open(wrapped)

    def test_replay_same_ciphertext_no_reread_and_rotation_new_ids(self):
        effects = []
        self.sources.slack_reader = lambda: effects.append(1) or {"bot_token": SENTINEL + str(len(effects))}
        pending = CredentialRequest("slack/bot")
        calls = ToolCallStore(self.root / "calls.db")
        self.addCleanup(calls.close)
        args = pending.arguments()
        def run(a):
            return calls.execute_journaled("equipment:r", "c", "credential_retrieve_sealed", a, self.equipment.call)
        first, second = run(args), run(args)
        self.assertEqual(first, second)
        self.assertEqual(len(effects), 1)
        self.assertEqual(pending.open(first), SENTINEL + "1")
        changed = CredentialRequest("slack/bot").arguments()
        self.assertEqual(run(changed)["error"], "call_id_reused_with_different_arguments")
        fresh = CredentialRequest("slack/bot")
        third = calls.execute_journaled("equipment:new", "c", "credential_retrieve_sealed", fresh.arguments(), self.equipment.call)
        self.assertEqual(fresh.open(third), SENTINEL + "2")
        self.assertNotIn(SENTINEL.encode(), (self.root / "calls.db").read_bytes())

    def test_secret_bearing_loader_and_timeout_errors_never_reach_journal(self):
        calls = ToolCallStore(self.root / "calls.db")
        self.addCleanup(calls.close)
        failures = [RuntimeError(SENTINEL), subprocess.TimeoutExpired([SENTINEL], 1, output=SENTINEL, stderr=SENTINEL)]
        for index, failure in enumerate(failures):
            def bad():
                raise failure
            self.sources.slack_reader = bad
            pending = CredentialRequest("slack/bot")
            result = calls.execute_journaled(str(index), "c", "credential_retrieve_sealed", pending.arguments(), self.equipment.call)
            self.assertTrue(result["isError"])
            self.assertNotIn(SENTINEL, json.dumps(result))
        self.assertNotIn(SENTINEL.encode(), (self.root / "calls.db").read_bytes())

    def test_missing_crypto_or_invalid_key_does_not_read_custody(self):
        pending = CredentialRequest("slack/bot")
        with patch.object(self.sources, "read", side_effect=AssertionError("must not read")):
            with patch.object(ct, "crypto", side_effect=ct.CredentialTransferError(ct.CRYPTO_HELP)):
                result = self.equipment.call("credential_retrieve_sealed", pending.arguments())
                self.assertIn("credential_crypto_unavailable", result["message"])
                refs = self.equipment.call("credential_references", {})
                self.assertFalse(refs["isError"])
                self.assertIn("slack_read_channel", {t["name"] for t in self.equipment.tools()})
            for key in ("", "not hex", "00" * 32):
                args = pending.arguments()
                args["recipient_public_key"] = key
                self.assertTrue(self.equipment.call("credential_retrieve_sealed", args)["isError"])

    def test_local_read_needs_no_crypto_or_gateway(self):
        with patch.object(ct, "crypto", side_effect=AssertionError("no dependency")):
            self.assertEqual(self.sources.read("slack/bot"), SENTINEL)

    def test_gh_existing_store_capture_no_shell_no_window_and_generic_failure(self):
        seen = []
        def runner(command, **kwargs):
            seen.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0, SENTINEL + "\n", "")
        self.sources.gh_runner = runner
        self.assertEqual(self.sources.read("github/token"), SENTINEL)
        command, kwargs = seen[0]
        self.assertEqual(command, ["gh", "auth", "token", "--hostname", "github.com"])
        self.assertTrue(kwargs["capture_output"])
        self.assertEqual(kwargs["creationflags"], getattr(subprocess, "CREATE_NO_WINDOW", 0))
        self.assertNotIn("shell", kwargs)
        def failing(*args, **kwargs):
            raise subprocess.TimeoutExpired([SENTINEL], 1, output=SENTINEL)
        self.sources.gh_runner = failing
        with self.assertRaises(ct.CredentialTransferError) as caught:
            self.sources.read("github/token")
        self.assertNotIn(SENTINEL, str(caught.exception))

    def test_configured_sources_and_runtime_registration_expand_catalog(self):
        source = self.root / "existing.json"
        source.write_text(json.dumps({"nested": {"field/with/slash": SENTINEL}}), encoding="utf-8")
        self.sources.config_path.write_text(json.dumps({"sources": {"future/provider": {
            "type": "json_file", "path": str(source), "pointer": "/nested/field~1with~1slash"}}}), encoding="utf-8")
        self.sources.register("runtime/remote", lambda: SENTINEL)
        refs = self.sources.describe()
        self.assertNotIn(SENTINEL, json.dumps(refs))
        names = {row["credential_ref"] for row in refs["references"]}
        self.assertTrue({"future/provider", "runtime/remote"}.issubset(names))
        for ref in ("future/provider", "runtime/remote"):
            pending = CredentialRequest(ref)
            self.assertEqual(pending.open(self.sources.retrieve_sealed(pending.arguments())), SENTINEL)

    def test_claude_index_reports_empty_without_inventing_stripe_and_reads_populated(self):
        self.sources.claude_path.write_text(json.dumps({"mcpOAuth": {
            "plugin:example|entry": {"accessToken": SENTINEL, "refreshToken": ""},
            "plugin:small-business:stripe|example": {"accessToken": "", "refreshToken": ""}}}), encoding="utf-8")
        described = self.sources.describe()
        self.assertNotIn(SENTINEL, json.dumps(described))
        rows = {row["credential_ref"]: row for row in described["references"]}
        self.assertEqual(rows["claude/mcp/plugin%3Aexample%7Centry/access"]["availability"], "present")
        self.assertEqual(rows["claude/mcp/plugin%3Asmall-business%3Astripe%7Cexample/access"]["availability"], "empty")
        self.assertEqual(self.sources.read("claude/mcp/plugin%3Aexample%7Centry/access"), SENTINEL)
        with self.assertRaises(ct.CredentialTransferError):
            self.sources.read("claude/mcp/plugin%3Asmall-business%3Astripe%7Cexample/access")

    def test_broken_optional_config_keeps_existing_direct_sources_working(self):
        self.sources.config_path.write_text('{"sources": []}', encoding="utf-8")
        self.assertIn("credential_source_config_unavailable", self.sources.describe()["errors"])
        self.assertEqual(self.sources.read("slack/bot"), SENTINEL)
        self.sources.gh_runner = lambda command, **kwargs: subprocess.CompletedProcess(command, 0, SENTINEL, "")
        self.assertEqual(self.sources.read("github/token"), SENTINEL)

    def test_manifest_keeps_same_newcomer_inventory_without_reading_values(self):
        catalog = CombinedCatalog(EmptyCatalog(), self.equipment)
        first = build_capability_manifest(catalog=catalog, peer="NEW")
        second = build_capability_manifest(catalog=catalog, peer="ESTABLISHED")
        self.assertEqual(first, second)
        self.assertIn("credential_retrieve_sealed", [row["name"] for row in first["operations"]])

    def test_real_http_gateway_returns_actual_value_only_to_client(self):
        catalog = CombinedCatalog(EmptyCatalog(), self.equipment)
        calls = ToolCallStore(self.root / "http.db")
        events = EventStore(self.root / "events.jsonl")
        gateway = ToolGateway(("127.0.0.1", 0), ToolLoop(None, catalog, calls), events, None, catalog)
        worker = threading.Thread(target=gateway.serve_forever, daemon=True)
        worker.start()
        try:
            base = "http://%s:%s" % gateway.server_address
            self.assertEqual(retrieve_http("slack/bot", base_url=base), SENTINEL)
            self.assertNotIn(SENTINEL.encode(), (self.root / "http.db").read_bytes())
            self.assertFalse((self.root / "events.jsonl").exists())
        finally:
            gateway.shutdown()
            gateway.server_close()
            worker.join(2)
            calls.close()

    def test_real_slack_carrier_and_model_loop_keep_only_sealed_results(self):
        pending = CredentialRequest("slack/bot")
        calls = ToolCallStore(self.root / "carrier.db")
        self.addCleanup(calls.close)
        sent = []
        class Delivery:
            def call(self, name, args):
                sent.append(args["text"])
                return {"result": {"ok": True, "ts": "2.1"}}
        catalog = CombinedCatalog(EmptyCatalog(), self.equipment)
        carrier_catalog = type("CarrierCatalog", (), {"services": Delivery(), "call": catalog.call})()
        carrier = SlackEquipmentCarrier(carrier_catalog, calls, {"channel_id": "C-SYNTHETIC"}, self.root / "cursor.json")
        message = {"ts": "1.1", "text": pending.slack_request()}
        carrier.process(message)
        carrier.process(message)
        self.assertEqual(len(sent), 1)
        body = sent[0].split(">", 1)[1].rsplit("</", 1)[0].strip()
        self.assertEqual(pending.open(json.loads(body)), SENTINEL)
        self.assertNotIn(SENTINEL, sent[0])
        prompts = []
        class Model:
            def turn(self, peer, prompt):
                prompts.append(prompt)
                if len(prompts) == 1:
                    return '<commons_tool_call>' + json.dumps({"call_id": "loop", "name": "credential_retrieve_sealed", "arguments": pending.arguments()}) + '</commons_tool_call>'
                return prompt  # worst case: the model repeats its entire tool result
        reply = ToolLoop(Model(), catalog, calls).run("model", "newcomer", "retrieve")
        events = EventStore(self.root / "events.jsonl")
        events.append(status="completed", reply=reply)
        for path in (self.root / "carrier.db", self.root / "events.jsonl"):
            self.assertNotIn(SENTINEL.encode(), path.read_bytes())
        self.assertNotIn(SENTINEL, "".join(prompts))


if __name__ == "__main__":
    unittest.main()
