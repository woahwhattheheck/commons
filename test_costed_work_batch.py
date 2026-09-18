"""Run and retain the costed-work-batch suite through Commons' root CI battery."""
from pathlib import Path
import unittest

from tools.costed_work_batch.test_planner import *  # noqa: F401,F403


_WORKFLOW = Path(__file__).parent / ".github" / "workflows" / "tests.yml"
_ENROLLMENT = "      - 'tools/costed_work_batch/**'"


class CostedWorkBatchRetainedCiContractTests(unittest.TestCase):
    def test_product_changes_wake_push_and_pull_request_batteries(self):
        workflow = _WORKFLOW.read_text(encoding="utf-8")
        push_section, separator, remainder = workflow.partition("  pull_request:\n")
        self.assertTrue(separator, "tests workflow is missing pull_request trigger")
        pull_section, separator, _ = remainder.partition("  workflow_dispatch:\n")
        self.assertTrue(separator, "tests workflow is missing workflow_dispatch boundary")
        self.assertEqual(
            workflow.count(_ENROLLMENT),
            2,
            "costed-work-batch source must be enrolled once in push and once in pull_request",
        )
        self.assertIn(_ENROLLMENT, push_section)
        self.assertIn(_ENROLLMENT, pull_section)


if __name__ == "__main__":
    unittest.main()
