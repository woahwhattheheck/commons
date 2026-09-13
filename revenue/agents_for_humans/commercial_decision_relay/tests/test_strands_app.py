from __future__ import annotations

import importlib.metadata
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from decision_relay import DecisionRelayError, RelayEngine


HAS_STRANDS = importlib.util.find_spec("strands") is not None
FIXTURE = Path(__file__).parents[1] / "fixtures" / "demo-batch.json"
TRUSTED_TIME = "2026-09-13T12:00:00Z"


@unittest.skipUnless(HAS_STRANDS, "pinned strands-agents SDK is not installed")
class StrandsSdkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from decision_relay.strands_app import AuditHooks, RelayToolbox

        cls.AuditHooks = AuditHooks
        cls.RelayToolbox = RelayToolbox

    def batch(self):
        return json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_exact_sdk_version(self):
        self.assertEqual(importlib.metadata.version("strands-agents"), "1.55.1")

    def test_decorated_tool_ingest_reconcile_queue_smoke(self):
        toolbox = self.RelayToolbox(
            RelayEngine(),
            trusted_evaluated_at=TRUSTED_TIME,
        )
        ingested = json.loads(toolbox.ingest_batch(json.dumps(self.batch())))
        reconciled = json.loads(toolbox.reconcile_evidence())
        decisions = json.loads(toolbox.decision_queue())

        self.assertEqual(ingested["event_count"], 7)
        self.assertEqual(reconciled["summary"]["decision_count"], 2)
        self.assertEqual(
            [row["series_id"] for row in decisions],
            ["alpha-renewal", "beta-pilot"],
        )


    def test_mock_provider_executes_ingest_reconcile_queue_through_agent(self):
        from strands.models import Model
        from decision_relay.strands_app import build_agent

        class ScriptedModel(Model):
            def __init__(self, batch_json):
                self._config = {"model_id": "decision-relay-test-model"}
                self.batch_json = batch_json
                self.calls = 0
                self.last_messages = None

            def update_config(self, **model_config):
                self._config.update(model_config)

            def get_config(self):
                return dict(self._config)

            async def structured_output(self, output_model, prompt, system_prompt=None, **kwargs):
                if False:
                    yield {}

            async def stream(self, messages, tool_specs=None, system_prompt=None, **kwargs):
                self.calls += 1
                self.last_messages = messages
                script = [
                    ("ingest_batch", {"batch_json": self.batch_json}),
                    ("reconcile_evidence", {}),
                    ("decision_queue", {}),
                ]
                yield {"messageStart": {"role": "assistant"}}
                if self.calls <= len(script):
                    name, args = script[self.calls - 1]
                    yield {
                        "contentBlockStart": {
                            "start": {"toolUse": {"name": name, "toolUseId": f"tool-{self.calls}"}}
                        }
                    }
                    yield {"contentBlockDelta": {"delta": {"toolUse": {"input": json.dumps(args)}}}}
                    yield {"contentBlockStop": {}}
                    yield {"messageStop": {"stopReason": "tool_use"}}
                else:
                    yield {"contentBlockStart": {"start": {}}}
                    yield {"contentBlockDelta": {"delta": {"text": "done"}}}
                    yield {"contentBlockStop": {}}
                    yield {"messageStop": {"stopReason": "end_turn"}}
                yield {
                    "metadata": {
                        "usage": {"inputTokens": 1, "outputTokens": 1, "totalTokens": 2},
                        "metrics": {"latencyMs": 1},
                    }
                }

        model = ScriptedModel(json.dumps(self.batch()))
        with tempfile.TemporaryDirectory() as directory:
            agent = build_agent(
                model=model,
                evaluated_at=TRUSTED_TIME,
                audit_path=Path(directory) / "audit.jsonl",
            )
            result = agent("Process the trusted test fixture.")
            audit_rows = [
                json.loads(line)
                for line in (Path(directory) / "audit.jsonl").read_text(encoding="utf-8").splitlines()
            ]

        self.assertIn("done", str(result))
        self.assertEqual(model.calls, 4)
        self.assertIn("alpha-renewal", str(model.last_messages))
        self.assertIn("beta-pilot", str(model.last_messages))
        self.assertEqual(
            [row["tool"] for row in audit_rows if row["phase"] == "after"],
            ["ingest_batch", "reconcile_evidence", "decision_queue"],
        )
        self.assertTrue(all(row["ok"] for row in audit_rows if row["phase"] == "after"))

    def test_trusted_preload_cannot_be_replaced_by_model_tool_input(self):
        engine = RelayEngine()
        engine.ingest(self.batch())
        engine.reconcile(evaluated_at=TRUSTED_TIME)
        toolbox = self.RelayToolbox(
            engine,
            trusted_evaluated_at=TRUSTED_TIME,
            ingest_locked=True,
        )
        with self.assertRaises(DecisionRelayError) as ctx:
            toolbox.ingest_batch(json.dumps(self.batch()))
        self.assertEqual(ctx.exception.code, "preloaded_batch_locked")

    def test_after_hook_marks_sdk_exception_as_failed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            hooks = self.AuditHooks(path)
            hooks.after_tool(SimpleNamespace(
                tool_use={"name": "decision_queue"},
                result=object(),
                exception=RuntimeError("boom"),
                cancel_message=None,
                duration=0.125,
            ))
            row = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
        self.assertFalse(row["ok"])
        self.assertFalse(row["cancelled"])
        self.assertEqual(row["exception_type"], "RuntimeError")

    def test_after_hook_marks_sdk_cancellation_as_failed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            hooks = self.AuditHooks(path)
            hooks.after_tool(SimpleNamespace(
                tool_use={"name": "ingest_batch"},
                result=object(),
                exception=None,
                cancel_message="blocked by before hook",
                duration=None,
            ))
            row = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
        self.assertFalse(row["ok"])
        self.assertTrue(row["cancelled"])
        self.assertIsNone(row["exception_type"])


if __name__ == "__main__":
    unittest.main()
