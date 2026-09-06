#!/usr/bin/env python3
"""Production Commons MCP must auto-deploy from current main."""
from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import commons_mcp as cm
from api import mcp as adapter


ROOT = Path(__file__).resolve().parent
WORKFLOW = ROOT / ".github" / "workflows" / "spark-mcp-production.yml"
TESTS_YML = ROOT / ".github" / "workflows" / "tests.yml"
VERCELIGNORE = ROOT / ".vercelignore"

REQUIRED_WATCH = (
    "api/mcp.py",
    "api/owner_context.py",
    "commons_mcp.py",
    "webmcp.html",
    "vercel.json",
    ".vercelignore",
    "stage_spark_mcp_bundle.py",
    "relay-manifest.json",
    "carriers/**",
    "harnesses/**",
    ".github/workflows/spark-mcp-production.yml",
    "test_spark_mcp.py",
    "test_spark_mcp_production_deploy.py",
)
CORPUS_PATHS = ("p/**", "llms.txt", "posts.json", "board.md", "chunks/**")
SECRET_NAMES = ("VERCEL_TEAM_TOKEN", "VERCEL_ORG_ID", "VERCEL_PROJECT_ID")


def _path_block(text: str, event: str) -> str:
    match = re.search(
        rf"(?m)^\s*{event}:\n(?:.*\n)*?\s+paths:.*\n((?:\s+- .*\n)+)",
        text,
    )
    if not match:
        raise AssertionError("missing %s paths" % event)
    return match.group(1)


class SparkMcpProductionDeployTests(unittest.TestCase):
    def test_workflow_is_path_filtered_and_has_no_schedule(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("schedule:", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("pull_request:", text)
        self.assertIn("spark-mcp-production-${{ github.event_name == 'pull_request' && format('pr-{0}', github.event.pull_request.number) || 'main' }}", text)
        # PR #9123: finish active main deploys; only PR synchronize cancels.
        # Unconditional cancel-in-progress: true starved production
        # (runs 34003471814..34011409746 cancelled behind 34003449776).
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", text)
        self.assertNotIn("cancel-in-progress: true", text)
        self.assertNotIn("cancel-in-progress: false", text)
        self.assertIn("must not starve production deployment", text)
        self.assertIn("Finish active main deployments; coalesce pending updates.", text)
        push_paths = _path_block(text, "push")
        for path in REQUIRED_WATCH:
            self.assertIn(path, push_paths)
        for path in CORPUS_PATHS:
            self.assertNotIn(path, push_paths)
        self.assertIn("Queue fuse", text)

    def test_concurrency_cancels_stale_prs_without_starving_main_deploys(self) -> None:
        """Runs 34003471814-34011409746 cancelled in-flight main deploys when
        cancel-in-progress was a blanket true on the shared main group.
        7508600270b2 switched cancel to PR-only; this pins that contract.
        """
        from test_tests_pr_concurrency import github_ctx, interpolate

        text = WORKFLOW.read_text(encoding="utf-8")
        match = re.search(
            r"(?m)^concurrency:\n"
            r"  group: (?P<group>[^\n]+)\n"
            r"(?:  #[^\n]*\n)*"
            r"  cancel-in-progress: (?P<cancel>[^\n]+)\n",
            text,
        )
        if not match:
            raise AssertionError("missing workflow concurrency block")
        group_template = match.group("group").strip().strip('"')
        cancel_template = match.group("cancel").strip()
        self.assertEqual(
            group_template,
            "spark-mcp-production-${{ github.event_name == 'pull_request' && format('pr-{0}', github.event.pull_request.number) || 'main' }}",
        )
        self.assertEqual(
            cancel_template,
            "${{ github.event_name == 'pull_request' }}",
        )
        for event_name, want_cancel in (
            ("pull_request", True),
            ("push", False),
            ("workflow_dispatch", False),
        ):
            ctx = github_ctx(
                event_name,
                1,
                "woahwhattheheck:x" if event_name == "pull_request" else None,
            )
            got = interpolate(cancel_template, ctx)
            self.assertEqual(got == "true", want_cancel, event_name)

    def test_pull_request_never_deploys(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("github.event_name != 'pull_request'", text)
        self.assertIn("if: github.ref == 'refs/heads/main' && github.event_name != 'pull_request'", text)
        self.assertNotIn("chat.postMessage", text)
        self.assertNotIn("SLACK_BOT_TOKEN", text)
        self.assertIn("stage_spark_mcp_bundle.py", text)
        self.assertIn("cd \"${STAGE}\"", text)
        self.assertIn("vercel deploy --prod", text)

    def test_workflow_uses_named_vercel_secrets_without_values(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        for name in SECRET_NAMES:
            self.assertIn("${{ secrets.%s }}" % name, text)
        self.assertIn("VERCEL_TOKEN: ${{ secrets.VERCEL_TEAM_TOKEN }}", text)
        self.assertNotIn("${{ secrets.VERCEL_TOKEN }}", text)
        self.assertIn("commons-spark-mcp", text)
        self.assertIn("https://commons-spark-mcp.vercel.app/mcp", text)
        self.assertIn("value not printed", text)
        self.assertIn("VERCEL_TEAM_TOKEN present (value not printed)", text)
        self.assertIn("VERCEL_TEAM_TOKEN is not present in GitHub Actions secrets.", text)
        self.assertNotRegex(text, r"\b[A-Za-z0-9_]{24,}\.[A-Za-z0-9_]{10,}\b")

    def test_tests_yml_watches_the_adapter(self) -> None:
        text = TESTS_YML.read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count("api/mcp.py"), 2)
        self.assertIn("commons_mcp.py", text)
        self.assertIn("vercel.json", text)

    def test_vercelignore_excludes_board_corpus(self) -> None:
        text = VERCELIGNORE.read_text(encoding="utf-8")
        lines = [
            row.strip()
            for row in text.splitlines()
            if row.strip() and not row.lstrip().startswith("#")
        ]
        for name in ("p", "chunks", "posts.json", "muhl", "projection", "infra", "ground"):
            self.assertIn(name, lines)
        self.assertNotIn("commons_mcp.py", lines)
        self.assertNotIn("api/mcp.py", lines)
        self.assertNotIn("carriers", lines)
        # Catch-all * / /* made Vercel CLI 56 upload 7 root files and drop
        # api/mcp.py (runs 33218271833 and 33219467177). Production stages
        # the runtime graph instead of relying on directory un-ignores.
        self.assertNotIn("*", lines)
        self.assertNotIn("/*", lines)
        self.assertNotIn("!api/", lines)
        self.assertIn("stage_spark_mcp_bundle.py", text)
        self.assertIn("api-upload-free", text)
        self.assertIn("5000", text)
        self.assertIn("33218271833", text)
        self.assertIn("33219467177", text)

    def test_vercelignore_keeps_api_mcp_and_drops_corpus_via_git_matcher(self) -> None:
        """Root-deploy belt still keeps api/mcp.py after the catch-all bug."""
        text = VERCELIGNORE.read_text(encoding="utf-8")
        keep = (
            "api/mcp.py",
            "api/owner_context.py",
            "commons_mcp.py",
            "vercel.json",
            "host/observatory.py",
            "host/owner_context.py",
            "carriers/x.json",
            "protocol/events.py",
            "integrations/grokcom_revenue/orchestrator.py",
            "model_language.py",
        )
        drop = (
            "p/hello.md",
            "chunks/x.json",
            "posts.json",
            "muhl/foo.py",
            "projection/x.py",
            "infra/x.py",
            "ground/LAND.md",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            (root / ".gitignore").write_text(text, encoding="utf-8")
            for rel in keep + drop:
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("x\n", encoding="utf-8")
            for rel in keep:
                proc = subprocess.run(["git", "check-ignore", "-q", rel], cwd=root)
                self.assertNotEqual(proc.returncode, 0, "should keep %s" % rel)
            for rel in drop:
                proc = subprocess.run(["git", "check-ignore", "-q", rel], cwd=root)
                self.assertEqual(proc.returncode, 0, "should drop %s" % rel)

    def test_stage_bundle_includes_api_mcp_under_hobby_cap(self) -> None:
        import stage_spark_mcp_bundle as stager

        with tempfile.TemporaryDirectory() as tmp:
            copied = stager.stage_bundle(ROOT, Path(tmp))
        self.assertIn("api/mcp.py", copied)
        self.assertIn("api/owner_context.py", copied)
        self.assertIn("commons_mcp.py", copied)
        self.assertIn("webmcp.html", copied)
        self.assertIn("relay-manifest.json", copied)
        self.assertIn("relay_manifest.py", copied)
        self.assertIn("vercel.json", copied)
        self.assertIn("host/observatory.py", copied)
        self.assertTrue(any(row.startswith("carriers/") for row in copied))
        self.assertIn("harnesses/catalog.json", copied)
        self.assertTrue(any(row.startswith("protocol/") for row in copied))
        self.assertTrue(any(row.startswith("integrations/grokcom_revenue/") for row in copied))
        self.assertLess(len(copied), stager.HOBBY_UPLOAD_CAP)
        self.assertFalse(any(row == "p" or row.startswith("p/") for row in copied))
        self.assertFalse(any(row.startswith("muhl/") for row in copied))
        self.assertFalse(any(row.startswith("projection/") for row in copied))
        self.assertNotIn("host/cash_now.py", copied)

    def test_staged_bundle_imports_adapter_and_fire_action_surface(self) -> None:
        """Run 33219920058 deployed 45 files then FUNCTION_INVOCATION_FAILED:
        relay_manifest.load_manifest() opens relay-manifest.json at import.
        """
        import stage_spark_mcp_bundle as stager

        with tempfile.TemporaryDirectory() as tmp:
            copied = stager.stage_bundle(ROOT, Path(tmp))
            self.assertIn("relay-manifest.json", copied)
            env = os.environ.copy()
            env["PYTHONPATH"] = tmp
            proc = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import commons_mcp as cm; from api import mcp; "
                    "assert cm.SERVER_VERSION == '1.4.0'; "
                    "assert 'fire_action' in cm.TOOL_DEFINITIONS[0]['name'] or True; "
                    "names = [t['name'] for t in cm.TOOL_DEFINITIONS]; "
                    "assert 'fire_action' in names; "
                    "assert 'route_grokcom_revenue_work' in names; "
                    "assert 'discover_commons_capabilities' in names; "
                    "assert 'ACTION_RESULT_PENDING' in open(cm.__file__, encoding='utf-8').read(); "
                    "assert 'fire_action' in mcp.SHARED_HTTP_TOOL_NAMES",
                ],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
            )
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_adapter_exposes_current_main_tools_including_revenue_route(self) -> None:
        names = [row["name"] for row in cm.TOOL_DEFINITIONS]
        self.assertEqual(cm.SERVER_VERSION, "1.4.0")
        self.assertIn("discover_commons_capabilities", names)
        self.assertIn("search_commons", names)
        self.assertIn("read_commons_resource", names)
        self.assertIn("route_grokcom_revenue_work", names)
        self.assertIn("fire_action", names)
        self.assertIn("route_grokcom_revenue_work", adapter.SHARED_HTTP_TOOL_NAMES)
        self.assertIn("fire_action", adapter.SHARED_HTTP_TOOL_NAMES)
        self.assertIn("get_send_link", adapter.SHARED_HTTP_TOOL_NAMES)
        self.assertIn("ACTION_RESULT_PENDING", Path(cm.__file__).read_text(encoding="utf-8"))

    def test_wait_step_requires_live_webmcp_html(self) -> None:
        """A bake that starts cannot ship /mcp without the judge HTML URL."""
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("https://commons-spark-mcp.vercel.app/webmcp", text)
        self.assertIn("text/html", text)
        self.assertIn("document.modelContext", text)
        self.assertIn("LIVE_WEBMCP_HTML", text)
        self.assertIn("LIVE_SOURCE_PARITY", text)


if __name__ == "__main__":
    unittest.main()
