#!/usr/bin/env python3
"""Production Commons MCP must auto-deploy from current main."""
from __future__ import annotations

import re
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
    "vercel.json",
    ".vercelignore",
    "carriers/**",
    ".github/workflows/spark-mcp-production.yml",
    "test_spark_mcp.py",
    "test_spark_mcp_production_deploy.py",
)
CORPUS_PATHS = ("p/**", "llms.txt", "posts.json", "board.md", "chunks/**")
SECRET_NAMES = ("VERCEL_TOKEN", "VERCEL_ORG_ID", "VERCEL_PROJECT_ID")


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
        self.assertIn("cancel-in-progress: true", text)
        push_paths = _path_block(text, "push")
        for path in REQUIRED_WATCH:
            self.assertIn(path, push_paths)
        for path in CORPUS_PATHS:
            self.assertNotIn(path, push_paths)
        self.assertIn("Queue fuse", text)

    def test_pull_request_never_deploys(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("github.event_name != 'pull_request'", text)
        self.assertIn("if: github.ref == 'refs/heads/main' && github.event_name != 'pull_request'", text)
        self.assertNotIn("chat.postMessage", text)
        self.assertNotIn("SLACK_BOT_TOKEN", text)

    def test_workflow_uses_named_vercel_secrets_without_values(self) -> None:
        text = WORKFLOW.read_text(encoding="utf-8")
        for name in SECRET_NAMES:
            self.assertIn("${{ secrets.%s }}" % name, text)
        self.assertIn("commons-spark-mcp", text)
        self.assertIn("https://commons-spark-mcp.vercel.app/mcp", text)
        self.assertIn("value not printed", text)
        self.assertNotRegex(text, r"\b[A-Za-z0-9_]{24,}\.[A-Za-z0-9_]{10,}\b")

    def test_tests_yml_watches_the_adapter(self) -> None:
        text = TESTS_YML.read_text(encoding="utf-8")
        self.assertGreaterEqual(text.count("api/mcp.py"), 2)
        self.assertIn("commons_mcp.py", text)
        self.assertIn("vercel.json", text)

    def test_vercelignore_excludes_board_corpus(self) -> None:
        lines = [
            row.strip()
            for row in VERCELIGNORE.read_text(encoding="utf-8").splitlines()
            if row.strip() and not row.lstrip().startswith("#")
        ]
        for name in ("p", "chunks", "posts.json"):
            self.assertIn(name, lines)
        self.assertNotIn("commons_mcp.py", lines)
        self.assertNotIn("api/mcp.py", lines)
        self.assertNotIn("carriers", lines)

    def test_adapter_exposes_current_main_tools_including_revenue_route(self) -> None:
        names = [row["name"] for row in cm.TOOL_DEFINITIONS]
        self.assertEqual(cm.SERVER_VERSION, "1.3.0")
        self.assertIn("route_grokcom_revenue_work", names)
        self.assertIn("fire_action", names)
        self.assertIn("route_grokcom_revenue_work", adapter.SHARED_HTTP_TOOL_NAMES)
        self.assertIn("fire_action", adapter.SHARED_HTTP_TOOL_NAMES)
        self.assertIn("get_send_link", adapter.SHARED_HTTP_TOOL_NAMES)
        self.assertIn("ACTION_RESULT_PENDING", Path(cm.__file__).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
