import json
import tempfile
import unittest
from pathlib import Path

from independent_commons_mcp.jobs import JobError
from integrations.grok_executor_queue import GrokExecutorQueue, SCHEMA


T0 = "2026-08-28T10:00:00Z"
T1 = "2026-08-28T10:00:05Z"
T2 = "2026-08-28T10:00:10Z"
T3 = "2026-08-28T10:00:15Z"
T_EXPIRED = "2026-08-28T10:01:00Z"


class GrokExecutorQueueTests(unittest.TestCase):
    def request(self, job_id="grok-queue-job-0001", run_key="grok-run-key-0001", **extra):
        row = {
            "job_id": job_id,
            "run_key": run_key,
            "origin": {
                "task_id": "requester-task-0001",
                "session_id": "requester-session-0001",
                "thread_id": "1787907723.163139",
                "source": "test",
            },
            "exact_prompts": ["exact heavy Grok prompt\nwith bytes"],
            "lease_seconds": 30,
            "max_attempts": 4,
        }
        row.update(extra)
        return row

    @staticmethod
    def capture_ack(run_key="grok-run-key-0001"):
        return {
            "state": "CAPTURE_STARTED",
            "write_ahead_ack": True,
            "capture": {
                "schema": "commons-grok-capture/v1",
                "run_key": run_key,
                "run_id": "a" * 32,
                "revision": 1,
                "state": "CAPTURE_STARTED",
            },
            "persistence": {
                "sha256": "b" * 64,
                "size_bytes": 2048,
            },
        }

    @staticmethod
    def verified_capture(run_key="grok-run-key-0001", url="https://grok.com/c/verified-rid"):
        return {
            "schema": "commons-grok-capture/v1",
            "run_key": run_key,
            "state": "VERIFIED_COMPLETE",
            "completion_state": "COMPLETED",
            "conversation_url": url,
            "conversation_rid": url.rsplit("/", 1)[-1],
            "exact_prompts": ["exact heavy Grok prompt\nwith bytes"],
            "exact_final_result": "lossless Grok result\nbytes",
            "provider": {
                "model": "Heavy",
                "mode": "Build",
                "source_count": 11,
                "token_evidence": "visible only",
                "debit_evidence": "visible only",
            },
            "artifacts": [
                {
                    "path": "candidate/",
                    "provider_private": True,
                    "inspection_state": "PATH_ONLY",
                }
            ],
            "timestamps": {
                "started_at": T0,
                "completed_at": T3,
            },
        }

    def claim(self, queue, executor="executor-alpha", now=T0):
        claimed = queue.claim("grok-queue-job-0001", executor, now=now)
        self.assertEqual(claimed["state"], "CLAIMED", claimed)
        return claimed

    def test_success_start_submit_capture_complete_and_return_to_requester(self):
        with tempfile.TemporaryDirectory() as td:
            queue = GrokExecutorQueue(td)
            submitted = queue.submit(self.request(), now=T0)
            self.assertEqual(submitted["state"], "QUEUED")
            self.assertEqual(submitted["job"]["checkpoint"]["schema"], SCHEMA)
            self.assertEqual(
                submitted["capture_start"]["arguments"]["exact_prompts"],
                ["exact heavy Grok prompt\nwith bytes"],
            )

            claim = self.claim(queue)
            started = queue.acknowledge_capture_start(
                claim["job_id"],
                self.capture_ack(),
                attempt_id=claim["attempt_id"],
                lease_id=claim["lease_id"],
                executor_id=claim["executor_id"],
                now=T1,
            )
            self.assertEqual(started["action"], "PREPARE_ONE_SUBMISSION")
            self.assertFalse(started["submit_allowed"])

            prepared = queue.prepare_submission(
                claim["job_id"],
                attempt_id=claim["attempt_id"],
                lease_id=claim["lease_id"],
                executor_id=claim["executor_id"],
                now=T2,
            )
            self.assertTrue(prepared["submit_allowed"])
            self.assertEqual(prepared["action"], "SUBMIT_EXACT_PROMPTS_NOW_ONCE")
            self.assertEqual(prepared["exact_prompts"], ["exact heavy Grok prompt\nwith bytes"])

            replay = queue.prepare_submission(
                claim["job_id"],
                attempt_id=claim["attempt_id"],
                lease_id=claim["lease_id"],
                executor_id=claim["executor_id"],
                now="2026-08-28T10:00:11Z",
            )
            self.assertFalse(replay["submit_allowed"])
            self.assertEqual(replay["action"], "CAPTURE_OUTPUT_ONLY_DO_NOT_RESUBMIT")

            marked = queue.mark_submitted(
                claim["job_id"],
                attempt_id=claim["attempt_id"],
                lease_id=claim["lease_id"],
                executor_id=claim["executor_id"],
                conversation_url="https://grok.com/c/verified-rid?rid=visible",
                now="2026-08-28T10:00:12Z",
            )
            self.assertFalse(marked["submit_allowed"])

            heartbeat = queue.heartbeat(
                claim["job_id"],
                attempt_id=claim["attempt_id"],
                lease_id=claim["lease_id"],
                executor_id=claim["executor_id"],
                now="2026-08-28T10:00:13Z",
            )
            self.assertEqual(heartbeat["state"], "LEASED")

            done = queue.complete(
                claim["job_id"],
                self.verified_capture(),
                result_address="grok-result-page-0001",
                page_exists=lambda address: address == "grok-result-page-0001",
                attempt_id=claim["attempt_id"],
                lease_id=claim["lease_id"],
                executor_id=claim["executor_id"],
                now=T3,
            )
            self.assertEqual(done["state"], "DONE")
            self.assertEqual(done["conversation_url"], "https://grok.com/c/verified-rid")
            self.assertEqual(done["return_to_requester"]["task_id"], "requester-task-0001")
            self.assertEqual(done["next"], "GPT_REVIEW_THEN_FRESH_MAIN_LANDING")
            recovered = queue.recover(claim["job_id"], now=T3)
            self.assertEqual(recovered["action"], "RETURN_CAPTURE_TO_REQUESTER")
            self.assertFalse(recovered["prompt_replay_allowed"])

    def test_pre_submit_browser_failure_releases_to_different_executor_with_zero_spend(self):
        with tempfile.TemporaryDirectory() as td:
            queue = GrokExecutorQueue(td)
            queue.submit(self.request(), now=T0)
            first = self.claim(queue)
            released = queue.release(
                first["job_id"],
                "BROWSER_UNAVAILABLE",
                "first exact browser error",
                attempt_id=first["attempt_id"],
                lease_id=first["lease_id"],
                executor_id=first["executor_id"],
                now=T1,
            )
            self.assertEqual(released["state"], "QUEUED")
            self.assertTrue(released["zero_spend_before_submission"])
            self.assertEqual(released["action"], "FAILOVER_TO_ANOTHER_HEALTHY_EXECUTOR")

            same = queue.claim(first["job_id"], first["executor_id"], now=T2)
            self.assertEqual(same["state"], "EXECUTOR_RELEASED_FOR_JOB")
            self.assertFalse(same["invoke_grok"])

            second = queue.claim(first["job_id"], "executor-beta", now=T2)
            self.assertEqual(second["state"], "CLAIMED")
            self.assertEqual(second["action"], "START_STRUCTURAL_CAPTURE")
            self.assertTrue(second["invoke_grok"])

    def test_capture_started_failover_preserves_write_ahead_ack_for_next_executor(self):
        with tempfile.TemporaryDirectory() as td:
            queue = GrokExecutorQueue(td)
            queue.submit(self.request(), now=T0)
            first = self.claim(queue)
            queue.acknowledge_capture_start(
                first["job_id"],
                self.capture_ack(),
                attempt_id=first["attempt_id"],
                lease_id=first["lease_id"],
                executor_id=first["executor_id"],
                now=T1,
            )
            released = queue.release(
                first["job_id"],
                "PAGE_UNCONFIRMED",
                "page failed before submit intent",
                attempt_id=first["attempt_id"],
                lease_id=first["lease_id"],
                executor_id=first["executor_id"],
                now=T2,
            )
            self.assertTrue(released["zero_spend_before_submission"])
            self.assertEqual(
                released["job"]["checkpoint"]["execution"]["submission_state"],
                "CAPTURE_STARTED",
            )
            self.assertIsNotNone(
                released["job"]["checkpoint"]["execution"]["capture_ack"]
            )

            second = queue.claim(first["job_id"], "executor-beta", now=T3)
            self.assertEqual(second["action"], "PREPARE_ONE_SUBMISSION")
            prepared = queue.prepare_submission(
                second["job_id"],
                attempt_id=second["attempt_id"],
                lease_id=second["lease_id"],
                executor_id=second["executor_id"],
                now="2026-08-28T10:00:16Z",
            )
            self.assertTrue(prepared["submit_allowed"])

    def test_crash_after_submit_intent_is_output_only_on_failover_and_never_replays(self):
        with tempfile.TemporaryDirectory() as td:
            queue = GrokExecutorQueue(td)
            queue.submit(self.request(), now=T0)
            first = self.claim(queue)
            queue.acknowledge_capture_start(
                first["job_id"],
                self.capture_ack(),
                attempt_id=first["attempt_id"],
                lease_id=first["lease_id"],
                executor_id=first["executor_id"],
                now=T1,
            )
            queue.prepare_submission(
                first["job_id"],
                attempt_id=first["attempt_id"],
                lease_id=first["lease_id"],
                executor_id=first["executor_id"],
                now=T2,
            )

            recovered = queue.recover(first["job_id"], now=T_EXPIRED)
            self.assertEqual(recovered["action"], "CAPTURE_OUTPUT_ONLY_DO_NOT_RESUBMIT")
            self.assertFalse(recovered["prompt_replay_allowed"])

            second = queue.claim(first["job_id"], "executor-beta", now=T_EXPIRED)
            self.assertEqual(second["state"], "CLAIMED", second)
            self.assertEqual(second["action"], "CAPTURE_OUTPUT_ONLY_DO_NOT_RESUBMIT")
            self.assertFalse(second["invoke_grok"])
            self.assertEqual(second["exact_prompts"], ["exact heavy Grok prompt\nwith bytes"])

    def test_post_intent_cloudflare_release_keeps_output_only_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            queue = GrokExecutorQueue(td)
            queue.submit(self.request(), now=T0)
            first = self.claim(queue)
            queue.acknowledge_capture_start(
                first["job_id"],
                self.capture_ack(),
                attempt_id=first["attempt_id"],
                lease_id=first["lease_id"],
                executor_id=first["executor_id"],
                now=T1,
            )
            queue.prepare_submission(
                first["job_id"],
                attempt_id=first["attempt_id"],
                lease_id=first["lease_id"],
                executor_id=first["executor_id"],
                now=T2,
            )
            released = queue.release(
                first["job_id"],
                "CLOUDFLARE",
                "provider challenge after submit intent",
                attempt_id=first["attempt_id"],
                lease_id=first["lease_id"],
                executor_id=first["executor_id"],
                now=T3,
            )
            self.assertEqual(released["state"], "RECOVER_OUTPUT_ONLY")
            self.assertFalse(released["prompt_replay_allowed"])
            self.assertFalse(released["zero_spend_before_submission"])

            next_claim = queue.claim(first["job_id"], "executor-beta", now="2026-08-28T10:00:20Z")
            self.assertEqual(next_claim["action"], "CAPTURE_OUTPUT_ONLY_DO_NOT_RESUBMIT")
            self.assertFalse(next_claim["invoke_grok"])

    def test_run_key_exact_url_and_lineage_dedupe(self):
        with tempfile.TemporaryDirectory() as td:
            queue = GrokExecutorQueue(td)
            first_request = self.request(conversation_url="https://grok.com/c/dedupe-rid")
            queue.submit(first_request, now=T0)
            duplicate = queue.submit(first_request, now=T1)
            self.assertEqual(duplicate["dedupe"], "RUN_KEY")
            self.assertEqual(duplicate["prompt_action"], "DO_NOT_SUBMIT")

            url_duplicate = queue.submit(
                self.request(
                    job_id="grok-queue-job-0002",
                    run_key="grok-run-key-0002",
                    conversation_url="https://grok.com/c/dedupe-rid?rid=other",
                ),
                now=T1,
            )
            self.assertEqual(url_duplicate["dedupe"], "EXACT_URL")

            lineage = queue.submit(
                self.request(
                    job_id="grok-queue-job-0003",
                    run_key="grok-run-key-0003",
                    lineage={
                        "parent_run_key": "grok-run-key-0001",
                        "parent_conversation_url": "https://grok.com/c/dedupe-rid",
                    },
                    conversation_url="",
                    exact_prompts=["new continuation prompt"],
                ),
                now=T1,
            )
            self.assertEqual(lineage["state"], "QUEUED")
            self.assertEqual(
                lineage["capture_start"]["arguments"]["parent_run_key"],
                "grok-run-key-0001",
            )

    def test_run_key_different_bytes_keep_first_writer(self):
        with tempfile.TemporaryDirectory() as td:
            queue = GrokExecutorQueue(td)
            first = queue.submit(self.request(), now=T0)
            self.assertEqual(first["state"], "QUEUED")
            original = Path(td, "grok-queue-job-0001.json").read_text(encoding="utf-8")
            with self.assertRaises(JobError) as raised:
                queue.submit(
                    self.request(exact_prompts=["mutated different exact bytes"]),
                    now=T1,
                )
            self.assertEqual(raised.exception.code, "RUN_KEY_COLLISION")
            self.assertEqual(raised.exception.state, "DUPLICATE")
            self.assertEqual(raised.exception.details.get("job_id"), "grok-queue-job-0001")
            kept = Path(td, "grok-queue-job-0001.json").read_text(encoding="utf-8")
            self.assertEqual(kept, original)
            job = json.loads(kept)
            self.assertEqual(job["checkpoint"]["exact_prompts"], ["exact heavy Grok prompt\nwith bytes"])

    def test_connector_unavailable_and_page_unconfirmed_are_typed(self):
        with tempfile.TemporaryDirectory() as td:
            queue = GrokExecutorQueue(td)
            queue.submit(self.request(), now=T0)
            claim = self.claim(queue)
            for blocker in ("PAGE_UNCONFIRMED",):
                released = queue.release(
                    claim["job_id"],
                    blocker,
                    "exact typed blocker",
                    attempt_id=claim["attempt_id"],
                    lease_id=claim["lease_id"],
                    executor_id=claim["executor_id"],
                    now=T1,
                )
                self.assertEqual(released["state"], "QUEUED")
                self.assertTrue(released["zero_spend_before_submission"])

            second = queue.claim(claim["job_id"], "executor-beta", now=T2)
            queue.acknowledge_capture_start(
                second["job_id"],
                self.capture_ack(),
                attempt_id=second["attempt_id"],
                lease_id=second["lease_id"],
                executor_id=second["executor_id"],
                now=T3,
            )
            queue.prepare_submission(
                second["job_id"],
                attempt_id=second["attempt_id"],
                lease_id=second["lease_id"],
                executor_id=second["executor_id"],
                now="2026-08-28T10:00:16Z",
            )
            connector = queue.release(
                second["job_id"],
                "CONNECTOR_UNAVAILABLE",
                "capture delivery connector unavailable",
                attempt_id=second["attempt_id"],
                lease_id=second["lease_id"],
                executor_id=second["executor_id"],
                now="2026-08-28T10:00:17Z",
            )
            self.assertEqual(connector["state"], "RECOVER_OUTPUT_ONLY")
            self.assertFalse(connector["prompt_replay_allowed"])

    def test_bounded_attempts_leave_durable_terminal_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            queue = GrokExecutorQueue(td)
            queue.submit(self.request(max_attempts=1), now=T0)
            first = self.claim(queue)
            queue.release(
                first["job_id"],
                "PROVIDER_SIGN_IN",
                "executor is not authenticated",
                attempt_id=first["attempt_id"],
                lease_id=first["lease_id"],
                executor_id=first["executor_id"],
                now=T1,
            )
            stopped = queue.claim(first["job_id"], "executor-beta", now=T2)
            self.assertEqual(stopped["reason"], "MAX_ATTEMPTS")
            durable = Path(td) / (first["job_id"] + ".json")
            self.assertTrue(durable.is_file())
            self.assertIn('"status": "EXHAUSTED"', durable.read_text(encoding="utf-8"))

    def test_job_envelope_rejects_secret_fields_but_has_no_identity_gate(self):
        with tempfile.TemporaryDirectory() as td:
            queue = GrokExecutorQueue(td)
            request = self.request()
            request["credentials"] = {"access_token": "do-not-store"}
            with self.assertRaisesRegex(JobError, "not allowed"):
                queue.submit(request, now=T0)

            open_request = self.request(job_id="grok-queue-job-open", run_key="grok-run-key-open")
            open_request["origin"]["source"] = "arbitrary-open-caller"
            queued = queue.submit(open_request, now=T0)
            self.assertEqual(queued["state"], "QUEUED")
            self.assertNotIn("authorized", str(queued).casefold())


if __name__ == "__main__":
    unittest.main()
