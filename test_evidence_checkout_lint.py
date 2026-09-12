import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("host").joinpath("evidence_checkout_lint.py")
SPEC = importlib.util.spec_from_file_location("evidence_checkout_lint", MODULE_PATH)
lint = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = lint
SPEC.loader.exec_module(lint)


class EvidenceCheckoutLintTests(unittest.TestCase):
    def lint(self, name: str, body: str):
        return lint.lint_text(Path(".github/workflows") / name, body)

    def test_marker_bare_checkout_is_rejected(self):
        body = """# evidence-workflow: true
jobs:
  proof:
    steps:
      - uses: actions/checkout@v4
      - run: echo proof
"""
        violations = self.lint("plain.yml", body)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].line, 5)

    def test_named_step_bare_checkout_is_rejected(self):
        body = """# evidence-workflow: true
jobs:
  proof:
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - run: echo proof
"""
        violations = self.lint("plain.yml", body)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].line, 6)

    def test_evidence_named_workflow_bare_checkout_is_rejected(self):
        body = """jobs:
  proof:
    steps:
      - name: Checkout
        uses: actions/checkout@v4
"""
        violations = self.lint("titan-proof.yml", body)
        self.assertEqual(len(violations), 1)

    def test_checkout_with_ref_is_accepted(self):
        body = """# evidence-workflow: true
jobs:
  proof:
    steps:
      - name: Checkout exact PR head
        uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.sha }}
          fetch-depth: 1
"""
        self.assertEqual(self.lint("proof.yml", body), [])

    def test_quoted_checkout_with_ref_is_accepted(self):
        body = """# evidence-workflow: true
jobs:
  proof:
    steps:
      - uses: "actions/checkout@v4"
        with:
          persist-credentials: false
          ref: "0123456789012345678901234567890123456789"
"""
        self.assertEqual(self.lint("proof.yml", body), [])

    def test_non_evidence_workflow_is_ignored(self):
        body = """jobs:
  build:
    steps:
      - uses: actions/checkout@v4
"""
        self.assertEqual(self.lint("build.yml", body), [])

    def test_comment_does_not_count_as_checkout(self):
        body = """# evidence-workflow: true
jobs:
  proof:
    steps:
      # - uses: actions/checkout@v4
      - run: echo ok
"""
        self.assertEqual(self.lint("proof.yml", body), [])

    def test_one_safe_and_one_bare_checkout_reports_bare_only(self):
        body = """# evidence-workflow: true
jobs:
  proof:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ inputs.expected_sha }}
      - uses: actions/checkout@v4
"""
        violations = self.lint("proof.yml", body)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].line, 8)

    def test_empty_ref_is_rejected(self):
        body = """# evidence-workflow: true
jobs:
  proof:
    steps:
      - uses: actions/checkout@v4
        with:
          ref:
          fetch-depth: 1
"""
        self.assertEqual(len(self.lint("proof.yml", body)), 1)

    def test_comment_only_ref_is_rejected(self):
        body = """# evidence-workflow: true
jobs:
  proof:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: # no identity
          fetch-depth: 1
"""
        self.assertEqual(len(self.lint("proof.yml", body)), 1)

    def test_quoted_empty_double_ref_is_rejected(self):
        body = """# evidence-workflow: true
jobs:
  proof:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ""
          fetch-depth: 1
"""
        self.assertEqual(len(self.lint("proof.yml", body)), 1)

    def test_quoted_empty_single_ref_is_rejected(self):
        body = """# evidence-workflow: true
jobs:
  proof:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ''
          fetch-depth: 1
"""
        self.assertEqual(len(self.lint("proof.yml", body)), 1)

    def test_empty_block_scalar_ref_is_rejected(self):
        body = """# evidence-workflow: true
jobs:
  proof:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: |
          fetch-depth: 1
"""
        self.assertEqual(len(self.lint("proof.yml", body)), 1)

    def test_null_ref_is_rejected(self):
        body = """# evidence-workflow: true
jobs:
  proof:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: null
          fetch-depth: 1
"""
        self.assertEqual(len(self.lint("proof.yml", body)), 1)

    def test_nested_ref_inside_path_block_does_not_count(self):
        body = """# evidence-workflow: true
jobs:
  proof:
    steps:
      - uses: actions/checkout@v4
        with:
          path: |
            some
            ref: fake
          fetch-depth: 1
"""
        self.assertEqual(len(self.lint("proof.yml", body)), 1)

    def test_reusable_exact_head_job_is_not_mistaken_for_checkout(self):
        body = """# evidence-workflow: true
jobs:
  identity:
    uses: ./.github/workflows/exact-head-checkout.yml
    with:
      expected_sha: ${{ github.event.pull_request.head.sha }}
"""
        self.assertEqual(self.lint("proof.yml", body), [])

    def test_reusable_workflow_binds_and_verifies_expected_sha(self):
        workflow = Path(".github/workflows/exact-head-checkout.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("workflow_call:", workflow)
        self.assertIn("ref: ${{ inputs.expected_sha }}", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertIn('actual="$(git rev-parse HEAD)"', workflow)
        self.assertIn('if [[ "$actual" != "$expected" ]]', workflow)


if __name__ == "__main__":
    unittest.main()
