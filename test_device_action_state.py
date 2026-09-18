#!/usr/bin/env python3
import contextlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import action_executor as ae
import device_action_state as ds


SOURCE_ROOT = Path(__file__).resolve().parent
ACTION_ID = "gpt-device-action-0001"
RUN_ID = "90000000001"
RUN_ATTEMPT = 1
WORKFLOW_REF = "woahwhattheheck/commons/.github/workflows/commons-device-executor.yml@refs/heads/main"


def github_env(**extra: str) -> dict[str, str]:
    return {
        "GITHUB_ACTIONS": "true",
        "GITHUB_RUN_ID": RUN_ID,
        "GITHUB_RUN_ATTEMPT": str(RUN_ATTEMPT),
        **extra,
    }


def run(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(args), cwd=root, text=True, capture_output=True, check=check)


class DeviceStateHarness:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.remote = self.base / "origin.git"
        self.root = self.base / "worker"
        run(self.base, "git", "init", "--bare", "-q", str(self.remote))
        self.root.mkdir()
        run(self.root, "git", "init", "-q", "-b", "main")
        run(self.root, "git", "config", "user.email", "test@example.invalid")
        run(self.root, "git", "config", "user.name", "device-state-test")
        run(self.root, "git", "remote", "add", "origin", str(self.remote))
        for rel in ds.PROTOCOL_FILES:
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SOURCE_ROOT / rel, target)
        action = self.root / "p" / (ACTION_ID + ".md")
        action.parent.mkdir(parents=True)
        action.write_text(
            "from: GPT\n"
            "to: TOOLS\n"
            "id: %s\n"
            "kind: ACTION\n"
            "act: RUN\n"
            "target: DEVICE\n"
            "\n---\n\n"
            "RUN\n"
            "target: DEVICE\n\n"
            "echo harmless\n" % ACTION_ID,
            encoding="utf-8",
        )
        (self.root / "seed.txt").write_text("seed\n", encoding="utf-8")
        run(self.root, "git", "add", "--all")
        run(self.root, "git", "commit", "-qm", "seed device action")
        run(self.root, "git", "push", "-q", "-u", "origin", "main")
        run(self.root, "git", "fetch", "-q", "origin", "main")
        self.source_commit = run(self.root, "git", "rev-parse", "HEAD").stdout.strip()

    def close(self):
        self.temp.cleanup()

    def add_action(self, ident: str):
        action = self.root / "p" / (ident + ".md")
        action.write_text(
            "from: GPT\nto: TOOLS\nid: %s\nkind: ACTION\nact: RUN\ntarget: DEVICE\n"
            "\n---\n\nRUN\ntarget: DEVICE\n\necho second\n" % ident,
            encoding="utf-8",
        )
        run(self.root, "git", "add", str(action.relative_to(self.root)))
        run(self.root, "git", "commit", "-qm", "add second device action")
        run(self.root, "git", "push", "-q", "origin", "main")
        run(self.root, "git", "fetch", "-q", "origin", "main")
        self.source_commit = run(self.root, "git", "rev-parse", "HEAD").stdout.strip()

    def add_actions(self, idents: list[str]):
        for ident in idents:
            action = self.root / "p" / (ident + ".md")
            action.write_text(
                "from: GPT\nto: TOOLS\nid: %s\nkind: ACTION\nact: RUN\ntarget: DEVICE\n"
                "\n---\n\nRUN\ntarget: DEVICE\n\necho bounded\n" % ident,
                encoding="utf-8",
            )
        run(self.root, "git", "add", "p")
        run(self.root, "git", "commit", "-qm", "add bounded device actions")
        run(self.root, "git", "push", "-q", "origin", "main")
        run(self.root, "git", "fetch", "-q", "origin", "main")
        self.source_commit = run(self.root, "git", "rev-parse", "HEAD").stdout.strip()

    def patches(self):
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(ds, "ROOT", self.root))
        stack.enter_context(mock.patch.object(ds, "RESERVATIONS", self.root / "actions/device-reservations"))
        stack.enter_context(mock.patch.object(ds, "BATCHES", self.root / "actions/device-batches"))
        stack.enter_context(mock.patch.object(ds, "RESULTS", self.root / "actions/results"))
        stack.enter_context(mock.patch.object(ae, "ROOT", self.root))
        stack.enter_context(mock.patch.object(ae, "POSTS", self.root / "p"))
        stack.enter_context(mock.patch.object(ae, "RESULTS", self.root / "actions/results"))
        stack.enter_context(mock.patch.object(ae, "DEVICE_RESERVATIONS", self.root / "actions/device-reservations"))
        return stack

    def prepare(self):
        output = self.base / "prepare.out"
        with self.patches(), mock.patch.dict(os.environ, github_env(), clear=False):
            code = ds.prepare_once(
                RUN_ID, RUN_ATTEMPT, self.source_commit, WORKFLOW_REF, output,
            )
        if code != 0:
            raise AssertionError("prepare failed with %s" % code)
        values = {}
        for line in output.read_text(encoding="utf-8").splitlines():
            key, value = line.split("=", 1)
            values[key] = value
        values["matrix"] = json.loads(values["matrix"])
        return values

    def execute(self, values, *, side_effect=None):
        runner_temp = self.base / "runner-temp"
        runner_temp.mkdir(exist_ok=True)
        effect = side_effect if side_effect is not None else {
            "ok": True, "changed": [], "executed_at": "2026-08-24T00:00:00Z"
        }
        with (
            self.patches(),
            mock.patch.dict(os.environ, github_env(RUNNER_TEMP=str(runner_temp)), clear=False),
            mock.patch.object(ae, "execute", side_effect=effect if isinstance(effect, Exception) else None,
                              return_value=None if isinstance(effect, Exception) else effect),
        ):
            code = ds.execute_one(
                ACTION_ID, RUN_ID, RUN_ATTEMPT, values["prepared_commit"],
                values["batch_path"], values["batch_sha256"],
                self.source_commit, WORKFLOW_REF,
            )
        if code != 0:
            raise AssertionError("execute failed with %s" % code)
        return (
            runner_temp / "device-receipts"
            / ds.artifact_name(ACTION_ID, RUN_ID, RUN_ATTEMPT) / "receipt.json"
        )

    def artifact(self, receipt: Path):
        source = self.base / "downloaded"
        name = ds.artifact_name(ACTION_ID, RUN_ID, RUN_ATTEMPT)
        target = source / name
        target.mkdir(parents=True)
        shutil.copyfile(receipt, target / "receipt.json")
        return source

    def finalize(self, values, source: Path):
        with self.patches(), mock.patch.dict(os.environ, github_env(), clear=False):
            return ds.finalize_once(
                source, RUN_ID, RUN_ATTEMPT, values["prepared_commit"],
                values["batch_path"], values["batch_sha256"],
                self.source_commit, WORKFLOW_REF,
            )


class DeviceActionStateTests(unittest.TestCase):
    def setUp(self):
        self.h = DeviceStateHarness()

    def tearDown(self):
        self.h.close()

    def test_prepare_execute_finalize_success_is_exact_and_history_latched(self):
        values = self.h.prepare()
        self.assertEqual(values["reservation_count"], "1")
        self.assertEqual(values["matrix"][0]["id"], ACTION_ID)
        prepared = values["prepared_commit"]
        self.assertNotEqual(prepared, self.h.source_commit)
        receipt = self.h.execute(values)
        row = json.loads(receipt.read_text(encoding="utf-8"))
        self.assertEqual(row["state"], ds.REPORTED_SUCCEEDED)
        self.assertTrue(row["ok"])
        self.assertEqual(set(row), ds.RESULT_KEYS)
        self.assertFalse(set(row) & {"output", "changed", "payload", "error"})
        source = self.h.artifact(receipt)
        self.assertEqual(self.h.finalize(values, source), 0)
        shutil.rmtree(source)
        self.assertEqual(self.h.finalize(values, source), 0)
        terminal = self.h.root / ds.result_rel(ACTION_ID)
        self.assertEqual(terminal.read_bytes(), receipt.read_bytes())
        with self.h.patches():
            self.assertEqual(ae.pending("device"), [])
            self.assertEqual(ae.pending("github"), [])

    def test_runner_failure_receipt_never_leaks_exception_text(self):
        values = self.h.prepare()
        receipt = self.h.execute(values, side_effect=RuntimeError("SECRET-SENTINEL"))
        raw = receipt.read_bytes()
        self.assertNotIn(b"SECRET-SENTINEL", raw)
        row = json.loads(raw)
        self.assertEqual(row["state"], ds.REPORTED_FAILED)
        self.assertFalse(row["ok"])
        self.assertEqual(row["error_code"], "EXECUTION_FAILED")

    def test_any_extra_artifact_member_rejects_all_terminals(self):
        values = self.h.prepare()
        receipt = self.h.execute(values)
        source = self.h.artifact(receipt)
        (next(source.iterdir()) / "extra.txt").write_text("hostile", encoding="utf-8")
        with self.assertRaisesRegex(ds.StateError, "only receipt.json"):
            self.h.finalize(values, source)
        self.assertFalse((self.h.root / ds.result_rel(ACTION_ID)).exists())
        with self.h.patches():
            self.assertEqual(ae.pending("device"), [])

    def test_incomplete_multi_action_artifact_lands_zero_terminals(self):
        second = "gpt-device-action-0002"
        self.h.add_action(second)
        values = self.h.prepare()
        self.assertEqual(values["reservation_count"], "2")
        receipt = self.h.execute(values)
        source = self.h.artifact(receipt)
        with self.assertRaisesRegex(ds.StateError, "directory set mismatch"):
            self.h.finalize(values, source)
        self.assertFalse((self.h.root / ds.result_rel(ACTION_ID)).exists())
        self.assertFalse((self.h.root / ds.result_rel(second)).exists())

    def test_missing_artifact_leaves_permanent_unknown_reservation(self):
        values = self.h.prepare()
        missing = self.h.base / "missing-artifact"
        with self.assertRaisesRegex(ds.StateError, "artifact root is missing"):
            self.h.finalize(values, missing)
        self.assertTrue((self.h.root / ds.reservation_rel(ACTION_ID)).is_file())
        self.assertFalse((self.h.root / ds.result_rel(ACTION_ID)).exists())
        with self.h.patches():
            self.assertEqual(ae.pending("device"), [])

    def test_deleted_latches_and_target_flip_do_not_reopen_either_scope(self):
        values = self.h.prepare()
        receipt = self.h.execute(values)
        self.assertEqual(self.h.finalize(values, self.h.artifact(receipt)), 0)
        run(self.h.root, "git", "rm", "-q", ds.reservation_rel(ACTION_ID), ds.result_rel(ACTION_ID))
        action = self.h.root / "p" / (ACTION_ID + ".md")
        action.write_text(action.read_text(encoding="utf-8").replace("target: DEVICE", "target: GITHUB"), encoding="utf-8")
        run(self.h.root, "git", "add", str(action.relative_to(self.h.root)))
        run(self.h.root, "git", "commit", "-qm", "hostile latch deletion and target flip")
        with self.h.patches():
            self.assertTrue(ae.ever_latched(ACTION_ID))
            self.assertEqual(ae.pending("device"), [])
            self.assertEqual(ae.pending("github"), [])

    def test_side_branch_add_delete_is_still_a_reachable_history_latch(self):
        run(self.h.root, "git", "checkout", "-qb", "latch-side")
        reservation = self.h.root / ds.reservation_rel(ACTION_ID)
        reservation.parent.mkdir(parents=True)
        reservation.write_text("historical latch\n", encoding="utf-8")
        run(self.h.root, "git", "add", ds.reservation_rel(ACTION_ID))
        run(self.h.root, "git", "commit", "-qm", "add side-branch latch")
        run(self.h.root, "git", "rm", "-q", ds.reservation_rel(ACTION_ID))
        run(self.h.root, "git", "commit", "-qm", "delete side-branch latch")
        run(self.h.root, "git", "checkout", "-q", "main")
        run(self.h.root, "git", "merge", "--no-ff", "-qm", "merge hidden latch", "latch-side")
        with self.h.patches():
            self.assertTrue(ds.git_path_ever("HEAD", ds.reservation_rel(ACTION_ID)))
            self.assertTrue(ae.ever_latched(ACTION_ID))
            self.assertEqual(ae.pending("device"), [])

    def test_prepare_caps_batch_before_latching_later_open_actions(self):
        extra = ["gpt-device-action-%04d" % number for number in range(2, 19)]
        self.h.add_actions(extra)
        values = self.h.prepare()
        self.assertEqual(int(values["reservation_count"]), ds.MAX_BATCH_ACTIONS)
        reserved = [row["id"] for row in values["matrix"]]
        self.assertEqual(reserved, sorted([ACTION_ID, *extra])[:ds.MAX_BATCH_ACTIONS])
        later = sorted([ACTION_ID, *extra])[ds.MAX_BATCH_ACTIONS:]
        for ident in later:
            self.assertFalse((self.h.root / ds.reservation_rel(ident)).exists())
        with self.h.patches():
            self.assertEqual(
                [row["meta"]["id"] for row in ae.pending("device")], later,
            )

    def test_duplicate_or_noncanonical_source_is_unknown(self):
        duplicate = self.h.root / "p" / "other-device-action.md"
        shutil.copyfile(self.h.root / "p" / (ACTION_ID + ".md"), duplicate)
        with self.h.patches():
            self.assertEqual(ae.pending("device"), [])

    def test_any_symlink_in_action_namespace_fails_the_scan_closed(self):
        os.symlink(ACTION_ID + ".md", self.h.root / "p" / "alias-action.md")
        with self.h.patches():
            self.assertEqual(ae.pending("device"), [])

    def test_prepare_push_race_is_discarded_and_recomputed_from_winning_main(self):
        original_workflow_sha = self.h.source_commit
        output = self.h.base / "first-prepare.out"
        real_git = ds.git
        fired = False
        winner = ""

        def racing_git(*args, **kwargs):
            nonlocal fired, winner
            if args == ("push", "origin", "HEAD:main") and not fired:
                fired = True
                racer = self.h.base / "racer"
                run(self.h.base, "git", "clone", "-q", str(self.h.remote), str(racer))
                run(racer, "git", "checkout", "-q", "-B", "main", "origin/main")
                run(racer, "git", "config", "user.email", "racer@example.invalid")
                run(racer, "git", "config", "user.name", "racer")
                (racer / "race.txt").write_text("winner\n", encoding="utf-8")
                run(racer, "git", "add", "race.txt")
                run(racer, "git", "commit", "-qm", "moving main wins")
                run(racer, "git", "push", "-q", "origin", "main")
                winner = run(racer, "git", "rev-parse", "HEAD").stdout.strip()
            return real_git(*args, **kwargs)

        with (
            self.h.patches(),
            mock.patch.dict(os.environ, github_env(), clear=False),
            mock.patch.object(ds, "git", side_effect=racing_git),
        ):
            self.assertEqual(
                ds.prepare_once(RUN_ID, RUN_ATTEMPT, original_workflow_sha, WORKFLOW_REF, output),
                ds.CAS_RETRY,
            )
        self.assertFalse(output.exists())
        run(self.h.root, "git", "reset", "--hard", "origin/main")
        self.h.source_commit = original_workflow_sha
        values = self.h.prepare()
        reservation = json.loads((self.h.root / ds.reservation_rel(ACTION_ID)).read_text(encoding="utf-8"))
        self.assertEqual(reservation["prepared_from_main"], winner)
        self.assertTrue((self.h.root / "race.txt").is_file())
        self.assertEqual(values["reservation_count"], "1")

    def test_finalize_push_race_retries_from_winning_main_without_losing_it(self):
        values = self.h.prepare()
        receipt = self.h.execute(values)
        source = self.h.artifact(receipt)
        real_git = ds.git
        fired = False
        winner = ""

        def racing_git(*args, **kwargs):
            nonlocal fired, winner
            if args == ("push", "origin", "HEAD:main") and not fired:
                fired = True
                racer = self.h.base / "finalize-racer"
                run(self.h.base, "git", "clone", "-q", "--no-checkout", str(self.h.remote), str(racer))
                run(racer, "git", "checkout", "-q", "-B", "main", "origin/main")
                run(racer, "git", "config", "user.email", "racer@example.invalid")
                run(racer, "git", "config", "user.name", "racer")
                (racer / "finalize-race.txt").write_text("winner\n", encoding="utf-8")
                run(racer, "git", "add", "finalize-race.txt")
                run(racer, "git", "commit", "-qm", "moving main wins finalizer race")
                run(racer, "git", "push", "-q", "origin", "main")
                winner = run(racer, "git", "rev-parse", "HEAD").stdout.strip()
            return real_git(*args, **kwargs)

        with (
            self.h.patches(),
            mock.patch.dict(os.environ, github_env(), clear=False),
            mock.patch.object(ds, "git", side_effect=racing_git),
        ):
            self.assertEqual(
                ds.finalize_once(
                    source, RUN_ID, RUN_ATTEMPT, values["prepared_commit"],
                    values["batch_path"], values["batch_sha256"],
                    self.h.source_commit, WORKFLOW_REF,
                ),
                ds.CAS_RETRY,
            )
        run(self.h.root, "git", "reset", "--hard", "origin/main")
        self.assertEqual(run(self.h.root, "git", "rev-parse", "HEAD").stdout.strip(), winner)
        self.assertEqual(self.h.finalize(values, source), 0)
        self.assertTrue((self.h.root / "finalize-race.txt").is_file())
        self.assertTrue((self.h.root / ds.result_rel(ACTION_ID)).is_file())

    def test_strict_json_rejects_duplicate_keys_noncanonical_and_nan(self):
        for raw, pattern in (
            (b'{"a":1,"a":2}\n', "duplicate"),
            (b'{"a": 1}\n', "canonical"),
            (b'{"a":NaN}\n', "non-finite"),
        ):
            with self.subTest(raw=raw), self.assertRaisesRegex(ds.StateError, pattern):
                ds.strict_json(raw, label="hostile")

    def test_generated_state_size_cap_writes_nothing(self):
        path = self.h.root / "actions" / "device-batches" / "oversize.json"
        with self.h.patches(), self.assertRaisesRegex(ds.StateError, "size limit"):
            ds._write_json(path, {"oversize": "x" * ds.MAX_JSON_BYTES})
        self.assertFalse(os.path.lexists(path))

    def test_payload_cannot_replace_receipt_path_after_execution(self):
        values = self.h.prepare()
        runner_temp = self.h.base / "race-runner-temp"
        runner_temp.mkdir()
        outside = self.h.base / "outside.txt"
        outside.write_text("safe\n", encoding="utf-8")

        def race_receipt(_rec, _scope):
            receipt_dir = (
                runner_temp / "device-receipts"
                / ds.artifact_name(ACTION_ID, RUN_ID, RUN_ATTEMPT)
            )
            receipt_dir.mkdir(parents=True)
            os.symlink(outside, receipt_dir / "receipt.json")
            return {"ok": True, "changed": [], "executed_at": "2026-08-24T00:00:00Z"}

        with (
            self.h.patches(),
            mock.patch.dict(os.environ, github_env(RUNNER_TEMP=str(runner_temp)), clear=False),
            mock.patch.object(ae, "execute", side_effect=race_receipt),
            self.assertRaisesRegex(ds.StateError, "overwrite state path"),
        ):
            ds.execute_one(
                ACTION_ID, RUN_ID, RUN_ATTEMPT, values["prepared_commit"],
                values["batch_path"], values["batch_sha256"],
                self.h.source_commit, WORKFLOW_REF,
            )
        self.assertEqual(outside.read_text(encoding="utf-8"), "safe\n")

    def test_payload_cannot_replace_receipt_parent_with_a_symlink(self):
        values = self.h.prepare()
        runner_temp = self.h.base / "parent-race-runner-temp"
        runner_temp.mkdir()
        outside = self.h.base / "outside-dir"
        outside.mkdir()

        def race_parent(_rec, _scope):
            os.symlink(
                outside, runner_temp / "device-receipts",
                target_is_directory=True,
            )
            return {"ok": True, "changed": [], "executed_at": "2026-08-24T00:00:00Z"}

        with (
            self.h.patches(),
            mock.patch.dict(os.environ, github_env(RUNNER_TEMP=str(runner_temp)), clear=False),
            mock.patch.object(ae, "execute", side_effect=race_parent),
            self.assertRaisesRegex(ds.StateError, "symlink or non-directory"),
        ):
            ds.execute_one(
                ACTION_ID, RUN_ID, RUN_ATTEMPT, values["prepared_commit"],
                values["batch_path"], values["batch_sha256"],
                self.h.source_commit, WORKFLOW_REF,
            )
        self.assertEqual(list(outside.iterdir()), [])

    def test_oversize_artifact_is_rejected_before_reading_contents(self):
        values = self.h.prepare()
        receipt = self.h.execute(values)
        source = self.h.artifact(receipt)
        artifact_receipt = next(source.iterdir()) / "receipt.json"
        artifact_receipt.write_bytes(b"x" * (ds.MAX_JSON_BYTES + 1))
        with self.assertRaisesRegex(ds.StateError, "size limit"):
            self.h.finalize(values, source)

    def test_clean_crlf_checkout_executes_the_lf_bound_commit(self):
        values = self.h.prepare()
        original_root = self.h.root
        runner = self.h.base / "crlf-runner"
        run(
            self.h.base, "git", "clone", "-q", "--no-checkout",
            str(self.h.remote), str(runner),
        )
        run(runner, "git", "config", "core.autocrlf", "true")
        run(runner, "git", "checkout", "-q", "--detach", values["prepared_commit"])
        self.assertEqual(run(runner, "git", "status", "--porcelain=v1").stdout, "")
        self.assertIn(b"\r\n", (runner / "action_executor.py").read_bytes())
        try:
            self.h.root = runner
            receipt = self.h.execute(values)
            self.assertTrue(receipt.is_file())
            self.assertTrue(json.loads(receipt.read_text(encoding="utf-8"))["ok"])
        finally:
            self.h.root = original_root

    def test_nonreservable_device_record_does_not_starve_later_valid_action(self):
        bad_target_id = "aaaaaaaa-target-too-long"
        bad_verb_id = "aaaaaaab-verb-too-long"
        target = "DEVICE:" + ("x" * ae.MAX_DEVICE_TARGET_CHARS)
        verb = "V" * (ae.MAX_ACTION_VERB_CHARS + 1)
        for ident, act, action_target in (
            (bad_target_id, "RUN", target),
            (bad_verb_id, verb, "DEVICE"),
        ):
            path = self.h.root / "p" / (ident + ".md")
            path.write_text(
                "from: GPT\nto: TOOLS\nid: %s\nkind: ACTION\nact: %s\ntarget: %s\n"
                "\n---\n\n%s\ntarget: %s\n\necho ignored\n"
                % (ident, act, action_target, act, action_target),
                encoding="utf-8",
            )
        run(self.h.root, "git", "add", "p")
        run(self.h.root, "git", "commit", "-qm", "add nonreservable device records")
        run(self.h.root, "git", "push", "-q", "origin", "main")
        run(self.h.root, "git", "fetch", "-q", "origin", "main")
        self.h.source_commit = run(self.h.root, "git", "rev-parse", "HEAD").stdout.strip()
        with self.h.patches():
            self.assertEqual(
                [row["meta"]["id"] for row in ae.pending("device")], [ACTION_ID],
            )
        values = self.h.prepare()
        self.assertEqual([row["id"] for row in values["matrix"]], [ACTION_ID])

    def test_cli_reads_workflow_identity_from_default_github_environment(self):
        argv = [
            "device_action_state.py", "execute-one", "--id", ACTION_ID,
            "--run-id", RUN_ID, "--run-attempt", str(RUN_ATTEMPT),
            "--prepared-commit", "1" * 40,
            "--batch-path", ds.batch_rel(RUN_ID, RUN_ATTEMPT),
            "--batch-sha256", "2" * 64,
        ]
        with (
            mock.patch.object(sys, "argv", argv),
            mock.patch.dict(
                os.environ,
                {
                    "GITHUB_WORKFLOW_SHA": "3" * 40,
                    "GITHUB_WORKFLOW_REF": WORKFLOW_REF,
                },
                clear=False,
            ),
            mock.patch.object(ds, "execute_one", return_value=0) as execute,
        ):
            self.assertEqual(ds.main(), 0)
        self.assertEqual(execute.call_args.args[-2:], ("3" * 40, WORKFLOW_REF))

    def test_execute_batch_preserves_sorted_reservation_order(self):
        second = "gpt-device-action-0002"
        self.h.add_action(second)
        values = self.h.prepare()
        runner_temp = self.h.base / "batch-runner-temp"
        runner_temp.mkdir()
        seen: list[str] = []
        first_receipt = (
            runner_temp / "device-receipts"
            / ds.artifact_name(ACTION_ID, RUN_ID, RUN_ATTEMPT)
            / "receipt.json"
        )

        def execute_in_order(rec, _scope):
            seen.append(rec["meta"]["id"])
            if rec["meta"]["id"] == second and first_receipt.exists():
                first_receipt.write_text("forged by later action\n", encoding="utf-8")
            return {"ok": True, "changed": [], "executed_at": "2026-08-24T00:00:00Z"}

        with (
            self.h.patches(),
            mock.patch.dict(os.environ, github_env(RUNNER_TEMP=str(runner_temp)), clear=False),
            mock.patch.object(ae, "execute", side_effect=execute_in_order),
        ):
            self.assertEqual(
                ds.execute_batch(
                    RUN_ID, RUN_ATTEMPT, values["prepared_commit"],
                    values["batch_path"], values["batch_sha256"],
                    self.h.source_commit, WORKFLOW_REF,
                ),
                0,
            )
        self.assertEqual(seen, [ACTION_ID, second])
        self.assertEqual(json.loads(first_receipt.read_text(encoding="utf-8"))["id"], ACTION_ID)
        for ident in seen:
            self.assertTrue(
                (
                    runner_temp / "device-receipts"
                    / ds.artifact_name(ident, RUN_ID, RUN_ATTEMPT)
                    / "receipt.json"
                ).is_file()
            )
        artifact_root = runner_temp / "device-receipts"
        self.assertEqual(self.h.finalize(values, artifact_root), 0)
        for ident in seen:
            self.assertTrue((self.h.root / ds.result_rel(ident)).is_file())

    def test_same_job_workspace_cannot_start_same_reservation_twice(self):
        values = self.h.prepare()
        receipt = self.h.execute(values)
        receipt.unlink()
        with self.assertRaisesRegex(ds.StateError, "already started"):
            self.h.execute(values)


if __name__ == "__main__":
    unittest.main()
