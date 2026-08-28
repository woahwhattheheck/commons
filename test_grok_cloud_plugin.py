import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PLUGIN = ROOT / "plugins" / "commons-grok-cloud"
MCP_URL = "https://commons-spark-mcp.vercel.app/mcp"


class GrokCloudPluginTests(unittest.TestCase):
    def call_capture_tools(self, capture_dir, *calls):
        server = PLUGIN / "scripts" / "server.mjs"
        requests = [
            {
                "jsonrpc": "2.0",
                "id": index,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
            for index, (name, arguments) in enumerate(calls, start=1)
        ]
        env = os.environ.copy()
        env["COMMONS_GROK_CAPTURE_DIR"] = str(capture_dir)
        completed = subprocess.run(
            ["node", str(server), "--stdio"],
            cwd=ROOT,
            env=env,
            input="\n".join(json.dumps(request, ensure_ascii=False) for request in requests) + "\n",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        responses = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
        self.assertEqual(len(responses), len(requests), completed.stdout + completed.stderr)
        results = []
        for response in responses:
            result = response["result"]
            self.assertNotIn("isError", result, result)
            results.append(result["structuredContent"])
        return results

    @staticmethod
    def start_args(run_key, prompt="exact prompt", conversation_url=""):
        args = {
            "run_key": run_key,
            "origin": {
                "task_id": "task-capture-tests",
                "session_id": "session-capture-tests",
                "thread_id": "thread-capture-tests",
                "source": "test",
                "event_id": "event-capture-tests",
            },
            "exact_prompts": [prompt],
            "started_at": "2026-08-28T09:00:00Z",
        }
        if conversation_url:
            args["conversation_url"] = conversation_url
        return args

    def test_marketplace_installs_exact_plugin(self):
        market = json.loads((ROOT / ".agents" / "plugins" / "marketplace.json").read_text(encoding="utf-8"))
        self.assertEqual(market["name"], "commons")
        row = market["plugins"][0]
        self.assertEqual(row["name"], "commons-grok-cloud")
        self.assertEqual(row["source"]["path"], "./plugins/commons-grok-cloud")
        self.assertEqual(row["policy"]["installation"], "AVAILABLE")

    def test_manifest_and_companion_files_are_complete(self):
        manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], PLUGIN.name)
        self.assertEqual(manifest["version"], "1.2.0")
        self.assertEqual(manifest["mcpServers"], "./.mcp.json")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertTrue((PLUGIN / "skills" / "commons-grok-cloud" / "SKILL.md").is_file())
        self.assertTrue((PLUGIN / "scripts" / "server.mjs").is_file())
        self.assertNotIn("[TODO:", json.dumps(manifest))

    def test_plugin_composes_shared_mcp_and_cloud_bridge(self):
        config = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))
        servers = config["mcpServers"]
        self.assertEqual(servers["commons"]["url"], MCP_URL)
        self.assertEqual(servers["commons"]["type"], "http")
        self.assertEqual(servers["commons-grok-cloud"]["command"], "node")
        self.assertIn("--stdio", servers["commons-grok-cloud"]["args"])

    def test_skill_requires_real_browser_url_and_dedup(self):
        text = (PLUGIN / "skills" / "commons-grok-cloud" / "SKILL.md").read_text(encoding="utf-8")
        for marker in (
            "control-browser",
            "C0BRGMDQB6G",
            "grok.com/c/...",
            "Do not mint a parallel queue",
            "verify_durability",
            "Gemini remains a distinct client",
            "build_grok_commons_client",
            "Grok may originate work",
        ):
            self.assertIn(marker, text)

    def test_carrier_catalog_keeps_mcp_clients_and_adds_grok_surface(self):
        catalog = json.loads((ROOT / "carriers" / "catalog.json").read_text(encoding="utf-8"))
        carrier_ids = [row["id"] for row in catalog["carriers"]]
        self.assertEqual(carrier_ids[:4], ["gemini-spark", "cursor-grok", "grokcom-revenue", "chatgpt-codex"])
        self.assertIn("grokcom-revenue", carrier_ids)
        self.assertIn("route_grokcom_revenue_work", catalog["shared_tools"])
        self.assertEqual(catalog["plugins"]["grok_cloud"], "plugins/commons-grok-cloud")
        card = json.loads((ROOT / "carriers" / "grokcom-revenue.json").read_text(encoding="utf-8"))
        self.assertEqual(card["mcp_url"], MCP_URL)
        self.assertEqual(card["tool"], "route_grokcom_revenue_work")
        self.assertIn("grok.com/c/...", card["cloud_executor"]["receipt"])
        self.assertIn("build_grok_artifact", card["cloud_executor"]["helper_tools"])
        self.assertIn("build_grok_commons_client", card["cloud_executor"]["helper_tools"])
        self.assertEqual(card["cloud_executor"]["direction"], "bidirectional")


    def test_lossless_success_capture_builds_receipts_only_after_verified_completion(self):
        with tempfile.TemporaryDirectory() as td:
            started, completed = self.call_capture_tools(
                td,
                ("start_grok_capture", self.start_args("run-success-001", "prompt\nbytes")),
                ("capture_grok_run", {
                    "run_key": "run-success-001",
                    "state": "COMPLETED",
                    "observed_at": "2026-08-28T09:01:00Z",
                    "conversation_url": "https://grok.com/c/success-rid?rid=visible",
                    "exact_final_result": "result\nbytes",
                    "completion_verified": True,
                    "provider": {
                        "model": "Heavy",
                        "mode": "Build",
                        "source_count": 13,
                        "token_evidence": "visible: 123",
                        "debit_evidence": "visible debit: 2",
                    },
                }),
            )
            self.assertEqual(started["state"], "CAPTURE_STARTED")
            self.assertTrue(started["write_ahead_ack"])
            self.assertNotIn("dispatch", started)
            self.assertEqual(completed["state"], "VERIFIED_COMPLETE")
            self.assertEqual(completed["capture"]["conversation_url"], "https://grok.com/c/success-rid")
            self.assertEqual(completed["capture"]["conversation_rid"], "success-rid")
            self.assertEqual(completed["capture"]["exact_prompts"], ["prompt\nbytes"])
            self.assertEqual(completed["capture"]["exact_final_result"], "result\nbytes")
            self.assertEqual(completed["capture"]["provider"]["source_count"], 13)
            self.assertEqual(completed["dispatch"]["state"], "READY_TO_EMIT_AFTER_VERIFIED_COMPLETION")
            self.assertEqual(completed["dispatch"]["slack_receipt"]["thread_ts"], "thread-capture-tests")
            self.assertEqual(
                completed["dispatch"]["slack_receipt"]["dedupe_key"],
                completed["dispatch"]["commons_post"]["id"],
            )
            artifact = json.loads(completed["dispatch"]["github_file"]["content"])
            self.assertEqual(artifact["exact_final_result"], "result\nbytes")
            self.assertEqual(completed["zero_token_boundary"]["prompt_submissions_by_capture"], 0)
            self.assertEqual(completed["zero_token_boundary"]["repository_mutations_by_capture"], 0)

    def test_partial_capture_creates_new_lineage_linked_continuation_and_page_unconfirmed_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            started, partial = self.call_capture_tools(
                td,
                ("start_grok_capture", self.start_args(
                    "run-partial-001", "first prompt", "https://grok.com/c/lineage-rid"
                )),
                ("capture_grok_run", {
                    "run_key": "run-partial-001",
                    "state": "PARTIAL",
                    "observed_at": "2026-08-28T09:02:00Z",
                    "partial_result": "unfinished exact bytes",
                    "continuation_prompt": "new continuation prompt",
                }),
            )
            self.assertEqual(started["state"], "CAPTURE_STARTED")
            self.assertEqual(partial["state"], "PARTIAL")
            self.assertEqual(partial["next_run"]["state"], "GROK_CONTINUE")
            next_run = partial["next_run"]
            continued = self.call_capture_tools(
                td,
                ("start_grok_capture", {
                    **self.start_args(next_run["run_key"], "new continuation prompt"),
                    "parent_run_key": next_run["parent_run_key"],
                    "conversation_url": next_run["parent_conversation_url"],
                }),
            )[0]
            self.assertEqual(continued["state"], "GROK_CONTINUE")
            self.assertEqual(continued["capture"]["lineage"]["parent_run_key"], "run-partial-001")

            continued_partial = self.call_capture_tools(
                td,
                ("capture_grok_run", {
                    "run_key": next_run["run_key"],
                    "state": "PARTIAL",
                    "observed_at": "2026-08-28T09:02:30Z",
                    "partial_result": "still unfinished",
                    "continuation_prompt": "second new continuation prompt",
                }),
            )[0]
            second_next = continued_partial["next_run"]
            second_continued = self.call_capture_tools(
                td,
                ("start_grok_capture", {
                    **self.start_args(second_next["run_key"], "second new continuation prompt"),
                    "parent_run_key": second_next["parent_run_key"],
                    "conversation_url": second_next["parent_conversation_url"],
                }),
            )[0]
            self.assertEqual(second_continued["state"], "GROK_CONTINUE")
            self.assertEqual(
                second_continued["capture"]["lineage"]["parent_run_key"],
                next_run["run_key"],
            )

            self.call_capture_tools(
                td,
                ("start_grok_capture", self.start_args("run-page-unconfirmed-001", "page prompt")),
            )
            page = self.call_capture_tools(
                td,
                ("capture_grok_run", {
                    "run_key": "run-page-unconfirmed-001",
                    "state": "PAGE_UNCONFIRMED",
                    "observed_at": "2026-08-28T09:03:00Z",
                    "failure_detail": "first exact browser error",
                }),
            )[0]
            self.assertEqual(page["state"], "PAGE_UNCONFIRMED")
            self.assertFalse(page["capture"]["failure"]["prompt_resubmission_allowed"])
            self.assertNotIn("dispatch", page)

    def test_crash_recovery_is_output_only_and_never_replays_prompt(self):
        with tempfile.TemporaryDirectory() as td:
            self.call_capture_tools(
                td,
                ("start_grok_capture", self.start_args("run-crash-001", "crash prompt")),
            )
            recovered = self.call_capture_tools(
                td,
                ("recover_grok_capture", {"run_key": "run-crash-001"}),
            )[0]
            self.assertEqual(recovered["runs"][0]["state"], "INTERRUPTED_RECOVERABLE")
            self.assertEqual(recovered["runs"][0]["prompt_action"], "DO_NOT_RESUBMIT")
            self.assertEqual(
                recovered["runs"][0]["recovery_action"],
                "CAPTURE_OUTPUT_ONLY_FROM_EXISTING_CONVERSATION",
            )
            self.assertEqual(recovered["runs"][0]["capture"]["exact_prompts"], ["crash prompt"])

    def test_run_key_and_exact_url_duplicates_do_not_spend_again(self):
        with tempfile.TemporaryDirectory() as td:
            first, same_key, same_url = self.call_capture_tools(
                td,
                ("start_grok_capture", self.start_args(
                    "run-dedupe-001", "first", "https://grok.com/c/dedupe-rid"
                )),
                ("start_grok_capture", self.start_args(
                    "run-dedupe-001", "first", "https://grok.com/c/dedupe-rid"
                )),
                ("start_grok_capture", self.start_args(
                    "run-dedupe-002", "second", "https://grok.com/c/dedupe-rid?rid=another"
                )),
            )
            self.assertEqual(first["state"], "CAPTURE_STARTED")
            self.assertEqual(same_key["dedupe"], "RUN_KEY")
            self.assertEqual(same_url["dedupe"], "EXACT_URL")
            self.assertEqual(same_key["prompt_action"], "DO_NOT_SUBMIT")
            self.assertEqual(same_url["prompt_action"], "DO_NOT_SUBMIT")

    def test_provider_private_artifacts_preserve_only_exposed_hashes_and_sizes(self):
        with tempfile.TemporaryDirectory() as td:
            self.call_capture_tools(
                td,
                ("start_grok_capture", self.start_args("run-artifact-001", "artifact prompt")),
            )
            completed = self.call_capture_tools(
                td,
                ("capture_grok_run", {
                    "run_key": "run-artifact-001",
                    "state": "COMPLETED",
                    "observed_at": "2026-08-28T09:04:00Z",
                    "conversation_url": "https://grok.com/c/artifact-rid",
                    "exact_final_result": "artifact result",
                    "completion_verified": True,
                    "artifacts": [
                        {
                            "path": "candidate/",
                            "provider_private": True,
                            "inspection_state": "INSPECTED",
                            "sha256": "a" * 64,
                            "size_bytes": 4096,
                        },
                        {
                            "path": "candidate/private.bin",
                            "provider_private": True,
                            "inspection_state": "PATH_ONLY",
                        },
                    ],
                }),
            )[0]
            artifacts = completed["capture"]["artifacts"]
            self.assertEqual(artifacts[0]["sha256"], "a" * 64)
            self.assertEqual(artifacts[0]["size_bytes"], 4096)
            self.assertNotIn("sha256", artifacts[1])
            self.assertNotIn("size_bytes", artifacts[1])

    def test_connector_unavailable_keeps_raw_transcript_and_pending_dispatch(self):
        with tempfile.TemporaryDirectory() as td:
            self.call_capture_tools(
                td,
                ("start_grok_capture", self.start_args("run-connector-001", "connector prompt")),
                ("capture_grok_run", {
                    "run_key": "run-connector-001",
                    "state": "COMPLETED",
                    "observed_at": "2026-08-28T09:05:00Z",
                    "conversation_url": "https://grok.com/c/connector-rid",
                    "exact_final_result": "lossless raw result",
                    "completion_verified": True,
                }),
                ("capture_grok_run", {
                    "run_key": "run-connector-001",
                    "state": "CONNECTOR_UNAVAILABLE",
                    "observed_at": "2026-08-28T09:06:00Z",
                    "connector": "slack",
                    "failure_detail": "connector unavailable",
                }),
            )
            recovered = self.call_capture_tools(
                td,
                ("recover_grok_capture", {"run_key": "run-connector-001"}),
            )[0]
            row = recovered["runs"][0]
            self.assertEqual(row["state"], "RECEIPT_PENDING")
            self.assertEqual(row["capture"]["exact_final_result"], "lossless raw result")
            self.assertEqual(row["dispatch"]["github_file"]["path"].split("/")[1], "grok-captures")
            self.assertEqual(row["prompt_action"], "DO_NOT_RESUBMIT")

    def test_node_server_syntax_and_self_test(self):
        server = PLUGIN / "scripts" / "server.mjs"
        for command in (["node", "--check", str(server)], ["node", str(server), "--self-test"]):
            completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("PASS", completed.stdout)


if __name__ == "__main__":
    unittest.main()
