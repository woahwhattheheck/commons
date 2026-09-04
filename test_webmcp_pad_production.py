#!/usr/bin/env python3
"""webmcp-pad-production must expand abbreviated SHAs before actions/checkout.

Measured: commons run 33849697120 dispatched ref=ec8961c (current pad main).
actions/checkout@v4 fetch-depth:1 fetched refs/heads/ec8961c* three times,
git fetch exited 1, and the deploy never started. The same commit as a
40-char SHA depth-1 fetch succeeds. Branch `main` already worked.
"""
from __future__ import annotations

import io
import json
import os
import subprocess
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock
from urllib.request import Request

from host.webmcp_pad_ref import (
    MEASURED_RUN,
    MEASURED_SHORT,
    checkout_ref,
    classify_ref,
    commits_api_url,
    fetch_commit_sha,
    main as pad_ref_main,
)


ROOT = Path(__file__).resolve().parent
WORKFLOW = ROOT / ".github" / "workflows" / "webmcp-pad-production.yml"
HELPER = ROOT / "host" / "webmcp_pad_ref.py"
MEASURED_FULL = "ec8961cf84d54bac5fb2755d40177f59aeebc252"
PAD_REPO = "woahwhattheheck/webmcp-pad"


class FakeResponse:
    def __init__(self, payload: dict, status: int = 200) -> None:
        self.status = status
        self._raw = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._raw

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None


class WebmcpPadRefTests(unittest.TestCase):
    def test_classify_measured_short_sha_vs_main_vs_full(self) -> None:
        self.assertEqual(classify_ref(MEASURED_SHORT), "abbrev_sha")
        self.assertEqual(classify_ref(MEASURED_FULL), "full_sha")
        self.assertEqual(classify_ref("main"), "named_ref")
        self.assertEqual(classify_ref("v1.4.2"), "named_ref")
        with self.assertRaises(ValueError):
            classify_ref("")
        with self.assertRaises(ValueError):
            classify_ref("   ")

    def test_named_ref_and_full_sha_do_not_hit_the_network(self) -> None:
        def boom(*args: object, **kwargs: object) -> None:
            raise AssertionError("urlopen should not run")

        kind, value = checkout_ref(PAD_REPO, "main", urlopen=boom)
        self.assertEqual((kind, value), ("named_ref", "main"))
        kind, value = checkout_ref(PAD_REPO, MEASURED_FULL, urlopen=boom)
        self.assertEqual((kind, value), ("full_sha", MEASURED_FULL))

    def test_abbrev_sha_expands_via_commits_api(self) -> None:
        calls: list[str] = []

        def urlopen(req: Request, timeout: int = 20) -> FakeResponse:
            calls.append(req.full_url)
            self.assertIn("/commits/" + MEASURED_SHORT, req.full_url)
            return FakeResponse({"sha": MEASURED_FULL})

        kind, value = checkout_ref(PAD_REPO, MEASURED_SHORT, urlopen=urlopen)
        self.assertEqual(kind, "abbrev_sha")
        self.assertEqual(value, MEASURED_FULL)
        self.assertEqual(len(calls), 1)
        self.assertEqual(
            commits_api_url(PAD_REPO, MEASURED_SHORT),
            "https://api.github.com/repos/woahwhattheheck/webmcp-pad/commits/ec8961c",
        )

    def test_abbrev_sha_http_error_names_the_measured_checkout_failure(self) -> None:
        def urlopen(req: Request, timeout: int = 20) -> FakeResponse:
            raise urllib.error.HTTPError(
                req.full_url, 404, "Not Found", hdrs=None, fp=io.BytesIO(b'{"message":"Not Found"}')
            )

        with self.assertRaises(RuntimeError) as visc:
            fetch_commit_sha(PAD_REPO, "deadbeef", urlopen=urlopen)
        msg = str(visc.exception)
        self.assertIn("HTTP 404", msg)
        self.assertIn("refs/heads/deadbeef*", msg)
        self.assertIn(MEASURED_RUN, msg)

    def test_cli_writes_github_output_for_abbrev_sha(self) -> None:
        def urlopen(req: Request, timeout: int = 20) -> FakeResponse:
            return FakeResponse({"sha": MEASURED_FULL})

        with tempfile.TemporaryDirectory() as tmp:
            out_path = str(Path(tmp) / "github_output")
            buf = io.StringIO()
            with mock.patch("host.webmcp_pad_ref.urllib.request.urlopen", urlopen):
                code = pad_ref_main(
                    [
                        "--repo",
                        PAD_REPO,
                        "--ref",
                        MEASURED_SHORT,
                        "--github-output",
                        out_path,
                    ],
                    stdout=buf,
                )
            self.assertEqual(code, 0)
            text = Path(out_path).read_text(encoding="utf-8")
            self.assertIn("kind=abbrev_sha\n", text)
            self.assertIn("ref=%s\n" % MEASURED_FULL, text)
            self.assertIn("sha=%s\n" % MEASURED_FULL, text)
        self.assertIn(MEASURED_FULL, buf.getvalue())

    def test_cli_passthrough_named_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out_path = str(Path(tmp) / "github_output")
            buf = io.StringIO()
            code = pad_ref_main(
                ["--repo", PAD_REPO, "--ref", "main", "--github-output", out_path],
                stdout=buf,
            )
            self.assertEqual(code, 0)
            text = Path(out_path).read_text(encoding="utf-8")
            self.assertIn("kind=named_ref\n", text)
            self.assertIn("ref=main\n", text)
            self.assertNotIn("sha=", text)


class WebmcpPadProductionWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_dispatch_only_and_never_targets_commons_mcp(self) -> None:
        self.assertIn("workflow_dispatch:", self.text)
        self.assertNotIn("pull_request:", self.text)
        self.assertNotRegex(self.text, r"(?m)^on:\n(?:  .*\n)*  push:")
        self.assertNotIn("commons-spark-mcp.vercel.app", self.text)
        self.assertIn("refusing to deploy webmcp-pad into commons-spark-mcp", self.text)
        self.assertIn("FORBIDDEN_PROJECT_ID", self.text)
        self.assertNotIn("VERCEL_PROJECT_ID: ${{ secrets.VERCEL_PROJECT_ID }}", self.text)
        self.assertIn("path: webmcp-pad", self.text)
        self.assertIn("persist-credentials: false", self.text)

    def test_pad_checkout_uses_resolved_ref_not_raw_input(self) -> None:
        self.assertIn("id: padref", self.text)
        self.assertIn("host/webmcp_pad_ref.py", self.text)
        self.assertIn("application/vnd.github.raw", self.text)
        self.assertIn("steps.padref.outputs.ref", self.text)
        self.assertIn(MEASURED_RUN, self.text)
        self.assertIn("abbreviated SHA", self.text)
        checkout = self.text.split("checkout woahwhattheheck/webmcp-pad at the requested ref", 1)[1]
        checkout = checkout.split("- name:", 1)[0]
        self.assertIn("ref: ${{ steps.padref.outputs.ref }}", checkout)
        self.assertNotIn("ref: ${{ inputs.ref }}", checkout)
        self.assertIn("repository: woahwhattheheck/webmcp-pad", checkout)
        self.assertIn("fetch-depth: 1", checkout)

    def test_input_description_accepts_abbreviated_sha(self) -> None:
        self.assertIn("abbreviated SHA", self.text)
        self.assertIn('default: "main"', self.text)

    def test_helper_is_the_file_the_workflow_fetches(self) -> None:
        self.assertTrue(HELPER.is_file())
        helper = HELPER.read_text(encoding="utf-8")
        self.assertIn(MEASURED_SHORT, helper)
        self.assertIn(MEASURED_RUN, helper)
        self.assertIn("abbrev_sha", helper)


class MeasuredGitFetchRegressionTests(unittest.TestCase):
    """Reproduce the exact fetch from run 33849697120 against the live pad repo."""

    def test_branch_wildcard_fetch_of_short_sha_exits_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "https://github.com/%s" % PAD_REPO],
                cwd=tmp,
                check=True,
            )
            proc = subprocess.run(
                [
                    "git",
                    "-c",
                    "protocol.version=2",
                    "fetch",
                    "--no-tags",
                    "--prune",
                    "--no-recurse-submodules",
                    "--depth=1",
                    "origin",
                    "+refs/heads/%s*:refs/remotes/origin/%s*" % (MEASURED_SHORT, MEASURED_SHORT),
                    "+refs/tags/%s*:refs/tags/%s*" % (MEASURED_SHORT, MEASURED_SHORT),
                ],
                cwd=tmp,
                capture_output=True,
                text=True,
            )
        self.assertNotEqual(
            proc.returncode,
            0,
            "short SHA wildcard fetch should fail the way checkout@v4 failed: %s %s"
            % (proc.stdout, proc.stderr),
        )

    def test_full_sha_depth1_fetch_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            subprocess.run(
                ["git", "remote", "add", "origin", "https://github.com/%s" % PAD_REPO],
                cwd=tmp,
                check=True,
            )
            proc = subprocess.run(
                [
                    "git",
                    "-c",
                    "protocol.version=2",
                    "fetch",
                    "--no-tags",
                    "--prune",
                    "--no-recurse-submodules",
                    "--depth=1",
                    "origin",
                    MEASURED_FULL,
                ],
                cwd=tmp,
                capture_output=True,
                text=True,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(MEASURED_FULL, proc.stdout + proc.stderr)

    def test_live_commits_api_expands_the_measured_short_sha(self) -> None:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        sha = fetch_commit_sha(PAD_REPO, MEASURED_SHORT, token=token)
        self.assertTrue(sha.startswith(MEASURED_SHORT))
        self.assertEqual(len(sha), 40)
        kind, value = checkout_ref(PAD_REPO, MEASURED_SHORT, token=token)
        self.assertEqual(kind, "abbrev_sha")
        self.assertEqual(value, sha)


if __name__ == "__main__":
    unittest.main()
