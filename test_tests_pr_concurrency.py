#!/usr/bin/env python3
"""tests.yml may coalesce stale PR synchronize, never unique main/dispatch."""

from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKFLOW = ROOT / ".github" / "workflows" / "tests.yml"


def _lookup(ctx, name):
    cur = ctx
    for part in name.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _truthy(value):
    return value not in (None, False, 0, 0.0, "")


def _tokenize(expr):
    token_re = re.compile(
        r"\s*(==|&&|\|\||\(|\)|'[^']*'|[A-Za-z_][A-Za-z0-9_.]*|\d+)"
    )
    pos = 0
    tokens = []
    while pos < len(expr):
        match = token_re.match(expr, pos)
        if not match:
            raise AssertionError(f"unparsed expression at {expr[pos:]!r}")
        tokens.append(match.group(1))
        pos = match.end()
    if pos != len(expr.rstrip()):
        raise AssertionError(f"trailing expression {expr[pos:]!r}")
    return tokens


def _parse_primary(tokens, idx, ctx):
    token = tokens[idx]
    if token == "(":
        value, idx = _parse_or(tokens, idx + 1, ctx)
        if idx >= len(tokens) or tokens[idx] != ")":
            raise AssertionError("missing )")
        return value, idx + 1
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1], idx + 1
    if token.isdigit():
        return int(token), idx + 1
    return _lookup(ctx, token), idx + 1


def _parse_eq(tokens, idx, ctx):
    left, idx = _parse_primary(tokens, idx, ctx)
    while idx < len(tokens) and tokens[idx] == "==":
        right, idx = _parse_primary(tokens, idx + 1, ctx)
        left = left == right
    return left, idx


def _parse_and(tokens, idx, ctx):
    left, idx = _parse_eq(tokens, idx, ctx)
    while idx < len(tokens) and tokens[idx] == "&&":
        right, idx = _parse_eq(tokens, idx + 1, ctx)
        left = right if _truthy(left) else left
    return left, idx


def _parse_or(tokens, idx, ctx):
    left, idx = _parse_and(tokens, idx, ctx)
    while idx < len(tokens) and tokens[idx] == "||":
        right, idx = _parse_and(tokens, idx + 1, ctx)
        left = left if _truthy(left) else right
    return left, idx


def eval_expr(expr, ctx):
    tokens = _tokenize(expr.strip())
    value, idx = _parse_or(tokens, 0, ctx)
    if idx != len(tokens):
        raise AssertionError(f"unused tokens {tokens[idx:]}")
    return value


def interpolate(template, ctx):
    def repl(match):
        value = eval_expr(match.group(1), ctx)
        if isinstance(value, bool):
            return "true" if value else "false"
        if value is None:
            return ""
        return str(value)

    return re.sub(r"\$\{\{(.+?)\}\}", repl, template)


def parse_concurrency(text):
    match = re.search(
        r"(?m)^concurrency:\n"
        r"(?:  #[^\n]*\n)*"
        r"  group: (?P<group>[^\n]+)\n"
        r"  cancel-in-progress: (?P<cancel>[^\n]+)\n",
        text,
    )
    if not match:
        raise AssertionError("missing workflow concurrency block")
    return match.group("group").strip().strip('"'), match.group("cancel").strip()


def github_ctx(event_name, run_id, head_label=None, workflow="tests"):
    event = {}
    if head_label is not None:
        owner, _, ref = head_label.partition(":")
        event["pull_request"] = {
            "head": {"label": head_label, "ref": ref or head_label},
            "number": abs(hash(head_label)) % 10000,
        }
    return {
        "github": {
            "workflow": workflow,
            "event_name": event_name,
            "run_id": str(run_id),
            "event": event,
            "ref": "refs/heads/main" if event_name == "push" else f"refs/pull/{run_id}/merge",
        }
    }


def decide(group_template, cancel_template, ctx):
    group = interpolate(group_template, ctx)
    cancel_raw = interpolate(cancel_template, ctx)
    if cancel_raw in ("true", "false"):
        cancel = cancel_raw == "true"
    else:
        cancel = _truthy(eval_expr(cancel_template.replace("${{", "").replace("}}", ""), ctx))
    return group, cancel


def simulate(events, group_template, cancel_template):
    """GitHub concurrency: newest pending replaces older pending; cancel-in-progress
    may also drop the running occupant of the same group."""
    live = []
    for event in events:
        ctx = github_ctx(
            event["event_name"],
            event["run_id"],
            event.get("head_label"),
        )
        group, cancel = decide(group_template, cancel_template, ctx)
        run = {
            "run_id": str(event["run_id"]),
            "event_name": event["event_name"],
            "head_label": event.get("head_label"),
            "group": group,
            "cancel": cancel,
            "status": "in_progress",
        }
        for occupant in live:
            if occupant["group"] != group or occupant["status"] == "cancelled":
                continue
            if occupant["status"] == "queued":
                occupant["status"] = "cancelled"
            elif occupant["status"] == "in_progress" and cancel:
                occupant["status"] = "cancelled"
            elif occupant["status"] == "in_progress" and not cancel:
                run["status"] = "queued"
        live.append(run)
    return live


class TestsPrConcurrency(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = WORKFLOW.read_text(encoding="utf-8")
        cls.group_template, cls.cancel_template = parse_concurrency(cls.text)

    def test_workflow_keeps_unique_non_pr_triggers(self):
        self.assertRegex(self.text, r"(?m)^  push:\n    branches:\n      - main$")
        self.assertIn("\n  pull_request:\n", self.text)
        self.assertIn("\n  workflow_dispatch:\n", self.text)
        self.assertNotRegex(self.text, r"(?m)^  issues:\n    types: \[opened\]$")
        self.assertIn("github.event.pull_request.head.label", self.group_template)
        self.assertIn("github.run_id", self.group_template)
        self.assertIn("github.event_name == 'pull_request'", self.group_template)
        self.assertNotIn("github.ref", self.group_template)
        self.assertIn("github.event_name == 'pull_request'", self.cancel_template)

    def test_same_head_synchronize_shares_group_and_cancels(self):
        first = github_ctx(
            "pull_request",
            33181739713,
            "woahwhattheheck:codex/trust-after-proof-20260828-01",
        )
        second = github_ctx(
            "pull_request",
            33182645445,
            "woahwhattheheck:codex/trust-after-proof-20260828-01",
        )
        g1, c1 = decide(self.group_template, self.cancel_template, first)
        g2, c2 = decide(self.group_template, self.cancel_template, second)
        self.assertEqual(g1, g2)
        self.assertTrue(c1)
        self.assertTrue(c2)
        self.assertEqual(
            g1,
            "tests-woahwhattheheck:codex/trust-after-proof-20260828-01",
        )

    def test_distinct_pr_heads_do_not_share_a_group(self):
        a = github_ctx("pull_request", 1, "woahwhattheheck:alpha")
        b = github_ctx("pull_request", 2, "woahwhattheheck:beta")
        g1, _ = decide(self.group_template, self.cancel_template, a)
        g2, _ = decide(self.group_template, self.cancel_template, b)
        self.assertNotEqual(g1, g2)

    def test_unique_main_and_dispatch_keep_run_id_groups(self):
        push_a = github_ctx("push", 32984511253)
        push_b = github_ctx("push", 33182674502)
        dispatch = github_ctx("workflow_dispatch", 4001)
        issues = github_ctx("issues", 4002)
        groups = []
        for ctx in (push_a, push_b, dispatch, issues):
            group, cancel = decide(self.group_template, self.cancel_template, ctx)
            groups.append(group)
            self.assertFalse(cancel)
            self.assertTrue(group.startswith("tests-"))
            self.assertIn(ctx["github"]["run_id"], group)
        self.assertEqual(len(set(groups)), 4)

    def test_event_simulation_cancels_only_stale_pr_synchronize(self):
        live = simulate(
            [
                {
                    "event_name": "pull_request",
                    "run_id": 11,
                    "head_label": "woahwhattheheck:codex/trust-after-proof-20260828-01",
                },
                {
                    "event_name": "pull_request",
                    "run_id": 12,
                    "head_label": "woahwhattheheck:codex/trust-after-proof-20260828-01",
                },
                {"event_name": "push", "run_id": 21},
                {"event_name": "push", "run_id": 22},
                {"event_name": "workflow_dispatch", "run_id": 31},
                {"event_name": "issues", "run_id": 41},
                {
                    "event_name": "pull_request",
                    "run_id": 13,
                    "head_label": "woahwhattheheck:other-head",
                },
            ],
            self.group_template,
            self.cancel_template,
        )
        by_id = {row["run_id"]: row for row in live}
        self.assertEqual(by_id["11"]["status"], "cancelled")
        self.assertEqual(by_id["12"]["status"], "in_progress")
        for run_id in ("21", "22", "31", "41", "13"):
            self.assertEqual(by_id[run_id]["status"], "in_progress", run_id)
        self.assertEqual(
            {row["run_id"] for row in live if row["status"] == "cancelled"},
            {"11"},
        )


if __name__ == "__main__":
    unittest.main()
