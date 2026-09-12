import tempfile
import unittest
from pathlib import Path

from host.defect_lints import lint_workflow, lint_paths


class DefectLintTests(unittest.TestCase):
    def lint(self, text):
        return lint_workflow(Path(".github/workflows/test.yml"), text)

    def ids(self, text):
        return [item.defect_id for item in self.lint(text)]

    def test_multiline_run_expression_is_flagged(self):
        text = """jobs:\n  x:\n    steps:\n      - run: |\n          echo '${{ github.sha }}'\n"""
        self.assertIn("workflow.run_block_expression", self.ids(text))

    def test_inline_run_expression_is_not_this_defect_class(self):
        text = """jobs:\n  x:\n    steps:\n      - run: echo '${{ github.sha }}'\n"""
        self.assertNotIn("workflow.run_block_expression", self.ids(text))

    def test_pycompile_then_clean_tree_is_flagged(self):
        text = """jobs:\n  x:\n    steps:\n      - run: |\n          python -m py_compile host/a.py\n          git diff --exit-code\n"""
        self.assertIn("workflow.py_compile_clean_tree", self.ids(text))

    def test_pycompile_with_dash_b_is_clean(self):
        text = """jobs:\n  x:\n    steps:\n      - run: |\n          python -B -m py_compile host/a.py\n          git diff --exit-code\n"""
        self.assertNotIn("workflow.py_compile_clean_tree", self.ids(text))

    def test_pycompile_with_env_suppression_is_clean(self):
        text = """jobs:\n  x:\n    steps:\n      - run: |\n          PYTHONDONTWRITEBYTECODE=1 python -m py_compile host/a.py\n          test -z \"$(git status --porcelain)\"\n"""
        self.assertNotIn("workflow.py_compile_clean_tree", self.ids(text))

    def test_upload_artifact_always_is_flagged(self):
        text = """jobs:\n  x:\n    steps:\n      - name: proof\n        if: always()\n        uses: actions/upload-artifact@v4\n        with:\n          path: proof.json\n      - run: echo done\n"""
        self.assertIn("workflow.artifact_always", self.ids(text))

    def test_success_only_upload_is_clean(self):
        text = """jobs:\n  x:\n    steps:\n      - name: proof\n        if: success()\n        uses: actions/upload-artifact@v4\n        with:\n          path: proof.json\n"""
        self.assertNotIn("workflow.artifact_always", self.ids(text))

    def test_directory_scan_is_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wf = root / "a.yml"
            wf.write_text("jobs:\n  x:\n    steps:\n      - run: |\n          echo '${{ github.sha }}'\n", encoding="utf-8")
            findings = lint_paths([root, wf])
            self.assertEqual(1, len(findings))


if __name__ == "__main__":
    unittest.main()
