#!/usr/bin/env python3
"""Focused board bake-reset convergence regressions.

These tests execute the real commit_and_push function with only its git/process
boundaries substituted. No board records, carrier events, or remote refs change.
Unrelated renderer modules are stubbed only while importing this boundary; the
production commit_and_push bytecode is loaded directly from the requested file.
"""
from __future__ import annotations

import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

B = None
OPTIONS = None


class Proc:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = int(returncode)
        self.stdout = stdout
        self.stderr = stderr


def install_import_stubs():
    """Supply only attributes evaluated while board_ingest is imported."""
    plain = (
        "builds_ledger",
        "chunk_board",
        "panel",
        "memory_board",
        "capability_declaration",
        "model_language",
        "commons_publication_policy",
        "exact_body_redact",
    )
    for name in plain:
        sys.modules[name] = types.ModuleType(name)

    hub = types.ModuleType("hub_pages")
    hub.nav_html = lambda *args, **kwargs: ""
    hub.CSS_TAG = ""
    hub.ASSET_V = "test"
    hub.CSS_V = "test"
    sys.modules["hub_pages"] = hub

    relay = types.ModuleType("relay_manifest")
    relay.NTFY_HOSTS = ("https://ntfy.invalid",)
    relay.NTFY_TOPIC = "test"
    sys.modules["relay_manifest"] = relay

    host = types.ModuleType("host")
    host.__path__ = []
    correction = types.ModuleType("host.correction_link")
    host.correction_link = correction
    sys.modules["host"] = host
    sys.modules["host.correction_link"] = correction


def load_source(path: Path):
    install_import_stubs()
    name = "board_ingest_bake_convergence_under_test"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class BakeConvergenceTests(unittest.TestCase):
    def run_case(
        self,
        *,
        second_push: str,
        projection_state: str,
        record: bool = False,
        retry_commit_noop: bool = False,
    ):
        record_paths = ["p/test-source.md"] if record else []
        commit_results = [Proc(0)]
        if record:
            commit_results.append(Proc(0))
        commit_results.append(
            Proc(1, stdout="nothing to commit\n") if retry_commit_noop else Proc(0)
        )
        commit_iter = iter(commit_results)
        git_calls = []

        def fake_git(args, _env=None, timeout=90):
            del timeout
            args = list(args)
            git_calls.append(tuple(args))
            if "commit" in args:
                return next(commit_iter)
            if args[:2] == ["rev-parse", "HEAD"]:
                return Proc(0, stdout="same-head\n")
            if args[:2] == ["rev-parse", "origin/main"]:
                return Proc(0, stdout="same-head\n")
            if args[:3] == ["diff", "--cached", "--quiet"]:
                return Proc(1 if record else 0)
            return Proc(0)

        pushes = (["pushed"] if record else []) + ["bake-reset", second_push]
        push_mock = mock.Mock(side_effect=pushes)
        rebuild_mock = mock.Mock()
        stage_mock = mock.Mock()
        refresh_mock = mock.Mock()

        def refresh(_env):
            status = {
                "state": projection_state,
                "source_sha256": "source-sha",
                "projection_sha256": "projection-sha" if projection_state == "CONVERGED_IN_GIT" else "",
            }
            B.PROJECTION_STATUS.clear()
            B.PROJECTION_STATUS.update(status)
            refresh_mock(status)
            return copy.deepcopy(status)

        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output), \
             mock.patch.object(B, "ingest_lock", side_effect=lambda: contextlib.nullcontext()), \
             mock.patch.object(B, "git_env", side_effect=lambda env=None: dict(env or {})), \
             mock.patch.object(B, "_record_paths", return_value=record_paths), \
             mock.patch.object(B, "_git", side_effect=fake_git), \
             mock.patch.object(B, "_head_has", return_value=True), \
             mock.patch.object(B, "post_source_snapshot", return_value={
                 "sha256": "source-sha", "files": 1, "bytes": 1,
             }), \
             mock.patch.object(B, "rebuild", rebuild_mock), \
             mock.patch.object(B, "_stage_board", stage_mock), \
             mock.patch.object(B, "push_origin_main", push_mock), \
             mock.patch.object(B, "refresh_projection_status", side_effect=refresh):
            result = B.commit_and_push("board ingest", env={})

        return types.SimpleNamespace(
            result=result,
            output=output.getvalue(),
            push=push_mock,
            rebuild=rebuild_mock,
            stage=stage_mock,
            refresh=refresh_mock,
            git_calls=git_calls,
        )

    def test_second_bake_reset_accepts_exact_converged_origin(self):
        got = self.run_case(
            second_push="bake-reset",
            projection_state="CONVERGED_IN_GIT",
        )
        self.assertEqual(got.result, "unchanged")
        self.assertEqual(got.rebuild.call_count, 1)
        self.assertEqual(got.push.call_count, 2)
        self.assertEqual(got.refresh.call_count, 1)
        self.assertIn("bake retry converged on refreshed origin; no push needed", got.output)
        self.assertNotIn("bake retry failed after one bounded attempt", got.output)

    def test_second_bake_reset_stays_failure_when_projection_pending(self):
        got = self.run_case(
            second_push="bake-reset",
            projection_state="PENDING_REBAKE",
        )
        self.assertEqual(got.result, "push-fail")
        self.assertEqual(got.rebuild.call_count, 1)
        self.assertEqual(got.push.call_count, 2)
        self.assertEqual(got.refresh.call_count, 1)
        self.assertIn("bake retry failed after one bounded attempt", got.output)
        self.assertNotIn("converged on refreshed origin", got.output)

    def test_non_bake_push_failure_is_not_upgraded_by_local_convergence(self):
        got = self.run_case(
            second_push="push-fail",
            projection_state="CONVERGED_IN_GIT",
        )
        self.assertEqual(got.result, "push-fail")
        self.assertEqual(got.rebuild.call_count, 1)
        self.assertEqual(got.refresh.call_count, 1)
        self.assertIn("bake retry failed after one bounded attempt", got.output)
        self.assertNotIn("converged on refreshed origin", got.output)

    def test_clean_retry_commit_still_checks_refreshed_origin(self):
        got = self.run_case(
            second_push="bake-reset",
            projection_state="CONVERGED_IN_GIT",
            retry_commit_noop=True,
        )
        self.assertEqual(got.result, "unchanged")
        self.assertEqual(got.rebuild.call_count, 1)
        self.assertEqual(got.push.call_count, 2)
        self.assertIn("bake rebuild made no additional commit; checking refreshed HEAD", got.output)
        self.assertIn("bake retry converged on refreshed origin; no push needed", got.output)

    def test_durable_record_keeps_pushed_status_after_converged_reset(self):
        got = self.run_case(
            second_push="bake-reset",
            projection_state="CONVERGED_IN_GIT",
            record=True,
        )
        self.assertEqual(got.result, "pushed")
        self.assertEqual(got.rebuild.call_count, 2)
        self.assertEqual(got.push.call_count, 3)
        self.assertEqual(got.refresh.call_count, 1)
        self.assertNotIn("bake retry failed after one bounded attempt", got.output)


def main() -> int:
    global B, OPTIONS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", type=Path, default=Path("board_ingest.py"))
    parser.add_argument("--report", type=Path)
    OPTIONS = parser.parse_args()
    module_path = OPTIONS.module.resolve()
    B = load_source(module_path)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(BakeConvergenceTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    report = {
        "schema": "commons-board-bake-convergence-v1",
        "module": str(module_path),
        "module_sha256": hashlib.sha256(module_path.read_bytes()).hexdigest(),
        "tests_run": result.testsRun,
        "failures": [{"test": test.id(), "traceback": trace} for test, trace in result.failures],
        "errors": [{"test": test.id(), "traceback": trace} for test, trace in result.errors],
        "skipped": [{"test": test.id(), "reason": reason} for test, reason in result.skipped],
        "successful": result.wasSuccessful(),
        "scope": "real commit_and_push; mocked git/process boundaries; no records, carrier events, or remote refs",
    }
    if OPTIONS.report:
        OPTIONS.report.parent.mkdir(parents=True, exist_ok=True)
        OPTIONS.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
