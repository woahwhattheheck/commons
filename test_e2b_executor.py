from __future__ import annotations

import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tools.e2b_executor.executor import (
    JOB_SCHEMA,
    JobValidationError,
    execute_job,
    validate_job,
)


class FakeFiles:
    def __init__(self, events):
        self.events = events
        self.writes = {}

    def write(self, path, data):
        self.events.append(("write", path))
        self.writes[path] = data


class FakeCommands:
    def __init__(
        self,
        events,
        archive_digest,
        *,
        manifest_ok=True,
        user_results=None,
        explode_stage=None,
    ):
        self.events = events
        self.archive_digest = archive_digest
        self.manifest_ok = manifest_ok
        self.user_results = list(user_results or [])
        self.explode_stage = explode_stage

    def run(self, command, **kwargs):
        self.events.append(("run", command, kwargs.get("cwd")))
        if "E2B_STAGE_ARCHIVE_DIGEST" in command:
            if self.explode_stage == "digest":
                raise RuntimeError("provider digest boom")
            return SimpleNamespace(
                exit_code=0,
                stdout=self.archive_digest + "\n",
                stderr="",
            )
        if "E2B_STAGE_SAFE_EXTRACT" in command:
            if self.explode_stage == "extract":
                raise RuntimeError("provider extract boom")
            return SimpleNamespace(exit_code=0, stdout="", stderr="")
        if "E2B_STAGE_MANIFEST" in command:
            if self.explode_stage == "manifest":
                raise RuntimeError("provider manifest boom")
            code = 0 if self.manifest_ok else 83
            return SimpleNamespace(
                exit_code=code,
                stdout="manifest-ok\n" if code == 0 else "",
                stderr="" if code == 0 else "mismatch",
            )
        if not self.user_results:
            raise AssertionError("unexpected user command")
        item = self.user_results.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item


class FakeSandbox:
    def __init__(
        self,
        archive_digest,
        *,
        manifest_ok=True,
        user_results=None,
        explode_stage=None,
        kill_error=None,
    ):
        self.events = []
        self.files = FakeFiles(self.events)
        self.commands = FakeCommands(
            self.events,
            archive_digest,
            manifest_ok=manifest_ok,
            user_results=user_results,
            explode_stage=explode_stage,
        )
        self.sandbox_id = "sbx-fixed-123"
        self.kill_error = kill_error

    def kill(self):
        self.events.append(("kill",))
        if self.kill_error:
            raise self.kill_error


class Factory:
    def __init__(self, sandbox):
        self.sandbox = sandbox
        self.calls = []

    def __call__(self, template, timeout_seconds, api_key):
        self.calls.append((template, timeout_seconds, api_key))
        return self.sandbox


class E2BExecutorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.archive = Path(self.tmp.name) / "source.tar.gz"
        payload = b"print('ok')\n"
        with tarfile.open(self.archive, "w:gz") as tf:
            info = tarfile.TarInfo("pkg/test_sample.py")
            info.size = len(payload)
            tf.addfile(info, io.BytesIO(payload))
        self.digest = hashlib.sha256(self.archive.read_bytes()).hexdigest()
        self.packet = {
            "schema": JOB_SCHEMA,
            "repository": "owner/repo",
            "commit_sha": "a" * 40,
            "source_archive_sha256": self.digest,
            "archive_path": str(self.archive),
            "template": "base",
            "sandbox_timeout_seconds": 120,
            "commands": [
                {
                    "argv": ["python", "-m", "unittest", "-q"],
                    "timeout_seconds": 30,
                },
                {
                    "argv": ["python", "-O", "-m", "unittest", "-q"],
                    "timeout_seconds": 30,
                },
            ],
            "manifest": [],
        }

    def run_job(
        self,
        sandbox,
        *,
        packet=None,
        api_key="e2b_secret_value_123",
    ):
        factory = Factory(sandbox)
        receipt = execute_job(
            self.packet if packet is None else packet,
            sandbox_factory=factory,
            environ={"E2B_API_KEY": api_key},
        )
        return receipt, factory

    def test_digest_mismatch_blocks_before_provider_construction(self):
        packet = dict(self.packet, source_archive_sha256="0" * 64)
        factory = Factory(FakeSandbox(self.digest))
        with self.assertRaisesRegex(JobValidationError, "digest"):
            execute_job(
                packet,
                sandbox_factory=factory,
                environ={"E2B_API_KEY": "secret"},
            )
        self.assertEqual(factory.calls, [])

    def test_noncanonical_sha_and_raw_shell_input_reject(self):
        bad_sha = dict(self.packet, commit_sha="A" * 40)
        with self.assertRaises(JobValidationError):
            validate_job(bad_sha)

        bad_shell = dict(self.packet)
        bad_shell["commands"] = [
            {"command": "python -m unittest", "timeout_seconds": 10}
        ]
        with self.assertRaisesRegex(JobValidationError, "unsupported keys"):
            validate_job(bad_shell)

    def test_upload_digest_extract_manifest_then_commands(self):
        packet = dict(self.packet)
        file_digest = hashlib.sha256(b"print('ok')\n").hexdigest()
        packet["manifest"] = [
            {"path": "pkg/test_sample.py", "sha256": file_digest}
        ]
        sandbox = FakeSandbox(
            self.digest,
            user_results=[
                SimpleNamespace(exit_code=0, stdout="one", stderr=""),
                SimpleNamespace(exit_code=0, stdout="two", stderr=""),
            ],
        )
        receipt, factory = self.run_job(sandbox, packet=packet)
        self.assertTrue(receipt["green"])
        self.assertEqual(len(factory.calls), 1)

        event_text = "\n".join(str(event) for event in sandbox.events)
        self.assertLess(
            event_text.index("/tmp/e2b-exact-head-source.archive"),
            event_text.index("E2B_STAGE_ARCHIVE_DIGEST"),
        )
        self.assertLess(
            event_text.index("E2B_STAGE_ARCHIVE_DIGEST"),
            event_text.index("E2B_STAGE_SAFE_EXTRACT"),
        )
        self.assertLess(
            event_text.index("E2B_STAGE_SAFE_EXTRACT"),
            event_text.index("E2B_STAGE_MANIFEST"),
        )
        self.assertLess(
            event_text.index("E2B_STAGE_MANIFEST"),
            event_text.index("python -m unittest -q"),
        )
        self.assertTrue(receipt["kill_attempted"])
        self.assertTrue(receipt["kill_succeeded"])

    def test_manifest_mismatch_blocks_user_commands_and_kills(self):
        packet = dict(
            self.packet,
            manifest=[
                {"path": "pkg/test_sample.py", "sha256": "1" * 64}
            ],
        )
        sandbox = FakeSandbox(self.digest, manifest_ok=False)
        receipt, _ = self.run_job(sandbox, packet=packet)
        self.assertFalse(receipt["green"])
        self.assertEqual(receipt["commands"], [])
        self.assertTrue(receipt["kill_attempted"])
        self.assertTrue(receipt["kill_succeeded"])

    def test_failing_command_stops_later_commands(self):
        sandbox = FakeSandbox(
            self.digest,
            user_results=[
                SimpleNamespace(
                    exit_code=7,
                    stdout="bad",
                    stderr="failed",
                ),
                SimpleNamespace(
                    exit_code=0,
                    stdout="must-not-run",
                    stderr="",
                ),
            ],
        )
        receipt, _ = self.run_job(sandbox)
        self.assertFalse(receipt["green"])
        self.assertEqual(len(receipt["commands"]), 1)
        self.assertEqual(receipt["commands"][0]["exit_code"], 7)
        self.assertTrue(receipt["kill_succeeded"])

    def test_provider_exception_is_non_green_and_kill_is_attempted(self):
        sandbox = FakeSandbox(
            self.digest,
            explode_stage="extract",
        )
        receipt, _ = self.run_job(sandbox)
        self.assertFalse(receipt["green"])
        self.assertEqual(receipt["error"]["kind"], "RuntimeError")
        self.assertTrue(receipt["kill_attempted"])
        self.assertTrue(receipt["kill_succeeded"])

    def test_missing_provider_configuration_is_structured_non_green(self):
        receipt = execute_job(
            self.packet,
            sandbox_factory=lambda *_: self.fail(
                "provider must not be constructed"
            ),
            environ={},
        )
        self.assertFalse(receipt["green"])
        self.assertEqual(
            receipt["error"]["kind"],
            "MISSING_E2B_API_KEY",
        )
        self.assertFalse(receipt["kill_attempted"])

    def test_kill_failure_revokes_green(self):
        sandbox = FakeSandbox(
            self.digest,
            user_results=[
                SimpleNamespace(exit_code=0, stdout="one", stderr=""),
                SimpleNamespace(exit_code=0, stdout="two", stderr=""),
            ],
            kill_error=RuntimeError("kill unavailable"),
        )
        receipt, _ = self.run_job(sandbox)
        self.assertFalse(receipt["green"])
        self.assertEqual(
            receipt["error"]["kind"],
            "SANDBOX_KILL_FAILED",
        )
        self.assertTrue(receipt["kill_attempted"])
        self.assertFalse(receipt["kill_succeeded"])

    def test_receipt_is_deterministic_and_redacts_api_key(self):
        secret = "e2b_live_SUPER_SECRET"

        def one():
            sandbox = FakeSandbox(
                self.digest,
                user_results=[
                    SimpleNamespace(
                        exit_code=0,
                        stdout=f"ok {secret}",
                        stderr="",
                    ),
                    SimpleNamespace(
                        exit_code=0,
                        stdout="done",
                        stderr=f"echo {secret}",
                    ),
                ],
            )
            receipt, _ = self.run_job(
                sandbox,
                api_key=secret,
            )
            return receipt

        first = one()
        second = one()
        self.assertEqual(first, second)
        rendered = json.dumps(first, sort_keys=True)
        self.assertNotIn(secret, rendered)
        self.assertEqual(first["sandbox_id"], "sbx-fixed-123")
        self.assertEqual(first["commit_sha"], "a" * 40)
        self.assertEqual(
            first["source_archive_sha256"],
            self.digest,
        )
        self.assertRegex(first["job_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(first["receipt_sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
