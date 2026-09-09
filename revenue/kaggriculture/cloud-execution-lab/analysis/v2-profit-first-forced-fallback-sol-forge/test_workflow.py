from __future__ import annotations

from pathlib import Path
import unittest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
WORKFLOW = (
    ROOT
    / ".github"
    / "workflows"
    / "titan-v2-profit-first-forced-fallback-sol-forge.yml"
)


class WorkflowContracts(unittest.TestCase):
    def test_hosted_carrier_is_exact_head_path_scoped_and_fail_closed(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        required_once = (
            "name: titan-v2-profit-first-forced-fallback-sol-forge",
            'ref: ${{ github.event.pull_request.head.sha || github.sha }}',
            "persist-credentials: false",
            'SEEDS: "539131249,1834999074,2609097301,2611092207"',
            'python -m pip install --disable-pip-version-check "kaggle-environments==1.32.7"',
            'python -B "$CASE/materialize.py"',
            'python -B "$CASE/materialize_evaluator.py"',
            'python -B "$CASE/bind_execution.py"',
            '--candidate "$OUT/arms/control/bound_entry.py::agent"',
            '--candidate "$OUT/arms/ablation/bound_entry.py::agent"',
            'python -B "$CASE/compare_bound.py"',
            "actions/upload-artifact@v4",
            'run: test "${{ steps.classify.outputs.exit_code }}" = "0"',
        )
        for needle in required_once:
            with self.subTest(needle=needle):
                self.assertEqual(source.count(needle), 1)

        self.assertIn(
            'test "$(git hash-object "$LAB/runtime/variants/v1/scheduler.py")" '
            '= "cbc502a92fe9d790cfaf763f6990d1057bc9b82d"',
            source,
        )
        self.assertIn(
            'test "$(git hash-object "$LAB/runtime/variants/v2/scheduler.py")" '
            '= "7c068b7078c3d7c09bb3836590ad42b0af934cdf"',
            source,
        )
        for helper in (
            "bind_execution.py",
            "compare.py",
            "compare_bound.py",
            "materialize_evaluator.py",
        ):
            with self.subTest(parent_helper=helper):
                self.assertIn(
                    f'git hash-object "$PARENT/{helper}"', source
                )

        control = source.index("Run closure-bound frozen V2 control panel")
        candidate = source.index("Run closure-bound profit-first candidate panel")
        classify = source.index(
            "Classify closure-bound candidate-action own-cash signal"
        )
        retain = source.index("Retain exact evidence")
        require = source.index("Require broad own-cash upside")
        self.assertLess(control, candidate)
        self.assertLess(candidate, classify)
        self.assertLess(classify, retain)
        self.assertLess(retain, require)

    def test_scope_does_not_mutate_promotable_or_frozen_paths(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn(
            'CASE: revenue/kaggriculture/cloud-execution-lab/analysis/'
            'v2-profit-first-forced-fallback-sol-forge',
            source,
        )
        self.assertIn(
            'test -z "$(git status --porcelain --untracked-files=all)"',
            source,
        )
        self.assertIn("python -B build_integrated.py --check", source)
        self.assertNotIn("git push", source)
        self.assertNotIn("gh pr merge", source)
        self.assertNotIn("runtime/variants/v3/scheduler.py\" >", source)


if __name__ == "__main__":
    unittest.main()
