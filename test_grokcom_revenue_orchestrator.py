import unittest

import commons_mcp as cm
from integrations.grokcom_revenue.orchestrator import CONNECTOR_ORIGIN, REVIEW_CHECKS, orchestrate


EVENT = {
    "event_id": "Ev-1787871538",
    "channel": "C0BRGMDQB6G",
    "message_ts": "1787871538.126989",
    "author": "BRYCE",
    "text": "research current prospects, build the fix, and push revenue forward",
}
ARTIFACT = {
    "head_sha": "1" * 40,
    "paths": ["host/example.py"],
    "tests": ["7 passed"],
    "run_key": "captured-parent-run-001",
    "conversation_url": "https://grok.com/c/captured-parent-rid",
    "exact_prompts": ["finished parent prompt"],
}


class GrokcomRevenueOrchestratorTests(unittest.TestCase):
    def test_every_message_gets_a_stable_grokcom_work_packet(self):
        first = orchestrate({"event": EVENT})
        second = orchestrate({"event": EVENT})
        self.assertEqual(first, second)
        self.assertEqual(first["state"], "GROKCOM_WORK")
        self.assertEqual(first["next"], "WRITE_CAPTURE_START_THEN_SEND_TO_GROKCOM_ONCE")
        self.assertEqual(first["connector"]["reply_mode"], "ALL_MESSAGES")
        self.assertTrue(first["connector"]["post_reply"])
        self.assertEqual(first["grokcom"]["surface"], "grok.com")
        self.assertEqual(first["grokcom"]["commons_mcp_url"], "https://commons-spark-mcp.vercel.app/mcp")
        self.assertIn("authenticated grok.com only", first["grokcom"]["prompt"])
        self.assertEqual(first["grokcom"]["capture_start"]["tool"], "start_grok_capture")
        executor_job = first["grokcom"]["executor_job"]
        self.assertEqual(executor_job["submit_tool"], "fire_action")
        self.assertEqual(executor_job["run_key"], first["grokcom"]["run_key"])
        self.assertEqual(executor_job["arguments"]["target"], "GROK.COM")
        self.assertEqual(executor_job["arguments"]["payload"], first["grokcom"]["prompt"])
        self.assertEqual(
            executor_job["durable_path"],
            "wake_jobs/%s.json" % executor_job["job_id"],
        )
        capture_args = first["grokcom"]["capture_start"]["arguments"]
        self.assertEqual(capture_args["run_key"], first["grokcom"]["run_key"])
        self.assertEqual(capture_args["exact_prompts"], [first["grokcom"]["prompt"]])
        self.assertFalse(first["cash_claimed"])

    def test_empty_and_free_form_calls_stay_open(self):
        empty = orchestrate({})
        free_form = orchestrate({"stage": "MAKE_MORE_MONEY", "mode": "ANY_MODEL", "future_field": True})
        self.assertEqual(empty["state"], "GROKCOM_WORK")
        self.assertEqual(empty["dedupe_key"], "slack-C0BRGMDQB6G-open-call")
        self.assertEqual(free_form["state"], "GROKCOM_WORK")
        self.assertEqual(free_form["mode"], "SALES")

    def test_connector_echo_is_processed_without_an_infinite_reply_loop(self):
        event = {**EVENT, "connector_origin": CONNECTOR_ORIGIN}
        result = orchestrate({"event": event})
        self.assertEqual(result["state"], "ECHO_PROCESSED")
        self.assertFalse(result["connector"]["post_reply"])
        self.assertEqual(result["connector"]["loop_disposition"], "OWN_ECHO_NO_POST")

    def test_research_packet_contains_sales_process_and_zero_fabrication_truth(self):
        result = orchestrate({
            "event": EVENT,
            "mode": "RESEARCH",
            "revenue": {"stage": "QUALIFY", "prospects": 11, "contacts": 0},
        })
        self.assertEqual(result["mode"], "RESEARCH")
        self.assertEqual(result["sales"]["current_stage"], "QUALIFY")
        self.assertEqual(result["sales"]["next_stage"], "DRAFT")
        self.assertEqual(result["sales"]["truth"]["evidence_state"], "NO_EVIDENCE_ATTACHED")
        self.assertEqual(result["sales"]["truth"]["cash_state"], "NOT_LANDED")
        self.assertFalse(result["sales"]["truth"]["cash_claimed"])

    def test_grokcom_result_routes_exact_artifact_to_gpt(self):
        result = orchestrate({"stage": "GROKCOM_RESULT", "event": EVENT, "artifact": ARTIFACT})
        self.assertEqual(result["state"], "GPT_REVIEW")
        self.assertEqual(result["gpt_review"]["artifact"], ARTIFACT)
        self.assertEqual(result["gpt_review"]["required_checks"], list(REVIEW_CHECKS))

    def test_approval_missing_any_check_returns_precise_revision(self):
        checks = {name: True for name in REVIEW_CHECKS}
        checks["zero_fabrication_check"] = False
        result = orchestrate({
            "stage": "GPT_REVIEW",
            "event": EVENT,
            "artifact": ARTIFACT,
            "review": {"decision": "APPROVE", "checks": checks},
        })
        self.assertEqual(result["state"], "GROK_CONTINUE")
        self.assertIn("zero_fabrication_check", result["review"]["issues"][0])
        self.assertEqual(result["grokcom"]["parent_run_key"], ARTIFACT["run_key"])
        self.assertTrue(result["grokcom"]["no_replay"])
        self.assertEqual(
            result["grokcom"]["capture_start"]["arguments"]["parent_run_key"],
            ARTIFACT["run_key"],
        )

    def test_explicit_continuation_is_new_lineage_linked_and_idempotent(self):
        arguments = {
            "stage": "GPT_REVIEW",
            "event": EVENT,
            "artifact": ARTIFACT,
            "review": {
                "decision": "CONTINUE",
                "checks": {name: True for name in REVIEW_CHECKS},
                "continuation_prompt": "new continuation prompt",
                "issues": ["candidate bytes remain provider-private"],
            },
        }
        first = orchestrate(arguments)
        second = orchestrate(arguments)
        self.assertEqual(first, second)
        self.assertEqual(first["state"], "GROK_CONTINUE")
        self.assertEqual(first["grokcom"]["prompt"], "new continuation prompt")
        self.assertEqual(first["grokcom"]["parent_conversation_url"], ARTIFACT["conversation_url"])
        self.assertEqual(first["grokcom"]["capture_start"]["arguments"]["exact_prompts"], ["new continuation prompt"])
        executor_job = first["grokcom"]["executor_job"]
        self.assertTrue(executor_job["no_replay"])
        self.assertEqual(
            executor_job["arguments"]["parent_run_key"],
            ARTIFACT["run_key"],
        )
        self.assertEqual(
            executor_job["arguments"]["parent_conversation_url"],
            ARTIFACT["conversation_url"],
        )
        self.assertNotEqual(executor_job["job_id"], first["task_id"])

    def test_continuation_cannot_replay_a_finished_prompt(self):
        with self.assertRaisesRegex(ValueError, "never replayed"):
            orchestrate({
                "stage": "GPT_REVIEW",
                "event": EVENT,
                "artifact": ARTIFACT,
                "review": {
                    "decision": "CONTINUE",
                    "checks": {name: True for name in REVIEW_CHECKS},
                    "continuation_prompt": "finished parent prompt",
                },
            })

    def test_review_cannot_detach_from_the_grokcom_artifact(self):
        with self.assertRaisesRegex(ValueError, "exact artifact manifest"):
            orchestrate({
                "stage": "GPT_REVIEW",
                "event": EVENT,
                "review": {"decision": "APPROVE", "checks": {name: True for name in REVIEW_CHECKS}},
            })

    def test_complete_review_routes_to_non_force_fresh_main_landing(self):
        result = orchestrate({
            "stage": "GPT_REVIEW",
            "event": EVENT,
            "artifact": ARTIFACT,
            "review": {"decision": "APPROVE", "checks": {name: True for name in REVIEW_CHECKS}},
        })
        self.assertEqual(result["state"], "GIT_LAND")
        self.assertFalse(result["git"]["force_push"])
        self.assertTrue(result["git"]["preserve_unrelated_dirt"])

    def test_landing_receipt_continues_instead_of_stopping(self):
        result = orchestrate({
            "stage": "GIT_LAND",
            "event": EVENT,
            "landing": {
                "base_sha": "1" * 40,
                "head_sha": "2" * 40,
                "main_sha": "3" * 40,
                "pr_url": "https://github.com/woahwhattheheck/commons/pull/9999",
                "blobs": {"host/example.py": "4" * 64},
                "tests": ["PASS"],
            },
        })
        self.assertEqual(result["state"], "CONTINUE")
        self.assertEqual(result["next"], "TAKE_NEXT_SLACK_OR_REVENUE_ACTION")
        self.assertEqual(result["landing"]["main_sha"], "3" * 40)

    def test_canonical_mcp_exposes_and_calls_the_orchestrator(self):
        class Gateway:
            def route_grokcom_revenue_work(self, arguments):
                return orchestrate(arguments)

        server = cm.MCPServer(Gateway())
        listed = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})[1]
        names = [row["name"] for row in listed["result"]["tools"]]
        self.assertIn("route_grokcom_revenue_work", names)
        response = server.handle({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "route_grokcom_revenue_work", "arguments": {"event": EVENT}},
        })[1]
        self.assertEqual(response["result"]["structuredContent"]["state"], "GROKCOM_WORK")


if __name__ == "__main__":
    unittest.main()
