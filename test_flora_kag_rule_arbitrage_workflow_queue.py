#!/usr/bin/env python3
"""Guard rule-arbitrage CI against stale queued-push comparisons to moving main."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKFLOW = ROOT / ".github" / "workflows" / "flora-kag-rule-arbitrage.yml"


class RuleArbitrageWorkflowQueueTests(unittest.TestCase):
    def test_push_uses_landed_ancestry_not_subtree_equality_to_future_main(self) -> None:
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("git diff --exit-code HEAD origin/main --", yml)
        self.assertIn("git fetch --filter=blob:none --depth=100 origin main", yml)
        self.assertIn(
            'audit_git_terminal.py --target-ref origin/main --expected-commit "$EXPECTED_COMMIT"',
            yml,
        )
        self.assertIn(
            "--required-path revenue/kaggriculture/cloud-rule-arbitrage/candidate.py",
            yml,
        )

    def test_pull_request_diff_check_is_preserved(self) -> None:
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            'git diff --check "${{ github.event.pull_request.base.sha }}" HEAD',
            yml,
        )

    def test_regression_contract_is_watched_and_executed(self) -> None:
        yml = WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(yml.count('"test_flora_kag_rule_arbitrage_workflow_queue.py"'), 2)
        self.assertEqual(
            yml.count("python -B test_flora_kag_rule_arbitrage_workflow_queue.py"),
            1,
        )


if __name__ == "__main__":
    unittest.main()
