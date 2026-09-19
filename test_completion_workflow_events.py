"""Source-bound close/reopen workflow regressions; no network or Actions dispatch.

The small evaluator handles only the expression subset used by this workflow.
It interprets an AST, never evals workflow code or executes embedded scripts.
Queue cases model GitHub's default one-running/one-pending replacement rule;
they are not a claim of live provider execution.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path
import re
import unittest

WORKFLOW = Path(__file__).resolve().parent / ".github/workflows/commons-board.yml"
TOKEN = re.compile(r"'(?:[^']|'')*'|&&|\|\||==|!=|!|[A-Za-z_][A-Za-z_0-9.]*|[(),]")


def expression(source, context, status="success"):
    """Interpret the actual source expression with a deliberately narrow grammar."""
    pieces = []
    position = 0
    for match in TOKEN.finditer(source):
        if source[position:match.start()].strip():
            raise ValueError("unsupported expression token")
        token = match.group()
        pieces.append({"&&": "and", "||": "or", "!": "not"}.get(token, token))
        position = match.end()
    if source[position:].strip():
        raise ValueError("unsupported expression suffix")
    tree = ast.parse(" ".join(pieces), mode="eval")

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name) and node.id == "github":
            return context
        if isinstance(node, ast.Attribute):
            value = visit(node.value)
            return value.get(node.attr, "") if isinstance(value, dict) else ""
        if isinstance(node, ast.BoolOp):
            result = visit(node.values[0])
            for value in node.values[1:]:
                if isinstance(node.op, ast.And) and not result:
                    break
                if isinstance(node.op, ast.Or) and result:
                    break
                result = visit(value)
            return result
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not visit(node.operand)
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right = visit(node.left), visit(node.comparators[0])
            if isinstance(left, str) and isinstance(right, str):
                left, right = left.casefold(), right.casefold()
            if isinstance(node.ops[0], ast.Eq):
                return left == right
            if isinstance(node.ops[0], ast.NotEq):
                return left != right
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
            name = node.func.id
            if name in ("success", "failure", "always") and not node.args:
                return name == "always" or name == status
            if name == "contains" and len(node.args) == 2:
                haystack, needle = map(visit, node.args)
                return str(needle).casefold() in str(haystack).casefold()
        raise ValueError("unsupported workflow expression node: " + type(node).__name__)

    return visit(tree)


def event(action="opened", number=100, carrier=True, name="issues"):
    return {"event_name": name, "event": {"action": action, "issue": {
        "number": number, "body": "carrier: slack-connector" if carrier else "ordinary post",
    }}}


def group(source, context):
    matches = re.findall(r'^  group: ("[^\n]+")$', source, re.M)
    if len(matches) != 1:
        raise ValueError("expected one workflow concurrency group")
    template = json.loads(matches[0])
    return re.sub(r"\$\{\{(.*?)\}\}", lambda m: str(expression(m[1], context)), template)


def condition(source, step_name):
    lines = source.splitlines()
    start = lines.index("      - name: " + step_name)
    for line in lines[start + 1:]:
        if line.startswith("      - "):
            break
        if line.startswith("        if: "):
            return line.split("if: ", 1)[1]
    raise ValueError("missing condition for " + step_name)


def pending_after(source, running, arrivals):
    """Groups with a running job retain the newest pending job, not every event."""
    active = {group(source, row): row for row in running}
    pending = {}
    for label, row in arrivals:
        key = group(source, row)
        if key not in active:
            active[key] = row
        else:
            pending[key] = label
    return set(pending.values())


class CompletionWorkflowEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = WORKFLOW.read_text(encoding="utf-8")

    def test_opened_carrier_bursts_still_coalesce(self):
        self.assertEqual("commons-board-ingest-slack-batch-v2-queue", group(self.source, event()))
        self.assertEqual(group(self.source, event(number=100)), group(self.source, event(number=200)))

    def test_completion_events_are_issue_scoped_not_global_intake(self):
        for action in ("closed", "reopened"):
            for number in (100, 200):
                with self.subTest(action=action, number=number):
                    self.assertEqual("commons-board-ingest-issues-" + str(number),
                                     group(self.source, event(action, number)))

    def test_changed_carrier_text_does_not_change_completion_group(self):
        for action in ("closed", "reopened"):
            self.assertEqual(group(self.source, event(action)),
                             group(self.source, event(action, carrier=False)))

    def test_one_issue_reopen_and_close_share_state_group(self):
        self.assertEqual(group(self.source, event("closed")), group(self.source, event("reopened")))

    def test_unrelated_issue_completion_groups_are_distinct(self):
        self.assertNotEqual(group(self.source, event("reopened", 100)),
                            group(self.source, event("closed", 200)))

    def test_pending_reopen_survives_unrelated_opened_burst(self):
        active = [event("closed", 100), event("opened", 300)]
        arrivals = [("reopen-100", event("reopened", 100)), ("open-200", event("opened", 200))]
        self.assertEqual({"reopen-100", "open-200"}, pending_after(self.source, active, arrivals))

    def test_distinct_pending_completions_survive_each_other(self):
        active = [event("closed", 100), event("opened", 200, carrier=False)]
        arrivals = [("reopen-100", event("reopened", 100)), ("close-200", event("closed", 200))]
        self.assertEqual({"reopen-100", "close-200"}, pending_after(self.source, active, arrivals))

    def test_intake_coalescing_keeps_only_latest_pending_opened(self):
        arrivals = [("old", event(number=200)), ("latest", event(number=300))]
        self.assertEqual({"latest"}, pending_after(self.source, [event()], arrivals))

    def test_nonissue_recovery_groups_unchanged(self):
        for name in ("push", "schedule", "workflow_dispatch", "repository_dispatch"):
            context = {"event_name": name, "event": {}}
            self.assertEqual("commons-board-ingest-" + name + "-poll", group(self.source, context))

    def test_ordinary_issue_intake_is_not_coalesced(self):
        self.assertEqual("commons-board-ingest-issues-100", group(self.source, event(carrier=False)))

    def test_both_post_receipts_are_opened_only(self):
        for step, status in (("exact success or rejection receipt on issue", "success"),
                             ("durable failure receipt on issue", "failure")):
            actual = condition(self.source, step)
            for action in ("opened", "closed", "reopened"):
                for carrier in (False, True):
                    with self.subTest(step=step, action=action, carrier=carrier):
                        self.assertEqual(action == "opened", bool(expression(actual, event(action, carrier=carrier), status)))
            self.assertFalse(expression(actual, {"event_name": "schedule", "event": {}}, status))

    def test_receipts_still_require_matching_result(self):
        self.assertFalse(expression(condition(self.source, "durable failure receipt on issue"), event(), "success"))
        self.assertFalse(expression(condition(self.source, "exact success or rejection receipt on issue"), event(), "failure"))

    def test_default_queue_does_not_cancel_running_work(self):
        self.assertRegex(self.source, r"(?m)^  cancel-in-progress: false$")
        self.assertRegex(self.source, r"(?m)^    types: \[opened, closed, reopened\]$")

    def test_expression_interpreter_rejects_unsupported_code(self):
        for source in ("__import__('os')", "github['event']", "github.event.issue.body()", "contains('x','y', 'z')"):
            with self.subTest(source=source):
                with self.assertRaises((ValueError, SyntaxError)):
                    expression(source, event())

    def test_expression_subset_short_circuits_and_preserves_values(self):
        self.assertEqual("fallback", expression("github.missing || 'fallback'", event()))
        self.assertEqual("", expression("github.missing && unknown()", event()))
        self.assertTrue(expression("github.event_name == 'ISSUES' && !contains(github.event.issue.body, 'never')", event()))


if __name__ == "__main__":
    unittest.main()
