"""Execute the actual pilot proof-scope YAML shell against disposable Git objects.

Standard-library only; no provider credentials, network, GitHub statuses or
repository source writes. The real workflow's Bash is extracted, never copied
as the test's implementation. Run from the repository root:
  python -m unittest -v test_pilot_proof_scope
  python -O -m unittest -v test_pilot_proof_scope

PILOT_SCOPE_WORKFLOW may select a predecessor workflow for red/green comparison.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import tempfile
import textwrap
import unittest

WORKFLOW = Path(os.environ.get('PILOT_SCOPE_WORKFLOW', '.github/workflows/source-parses.yml'))
EVENT_TOKEN = '${{ github.event_name }}'
BASE_TOKEN = '${{ github.event.pull_request.base.sha }}'
HEAD_TOKEN = '${{ github.event.pull_request.head.sha }}'
BEFORE_TOKEN = '${{ github.event.before }}'
SHA_TOKEN = '${{ github.sha }}'
ZERO_SHA = '0' * 40
MISSING_SHA = 'f' * 40


def production_scope() -> str:
    """Select exactly one named YAML step; fail rather than silently test a stub."""
    text = WORKFLOW.read_text(encoding='utf-8')
    marker = '      - name: Detect pilot-renewal proof-surface changes\n'
    if text.count(marker) != 1:
        raise ValueError('Expected exactly one pilot proof-scope step')
    step = text.split(marker, 1)[1].split('\n      - name:', 1)[0]
    if step.count('        run: |\n') != 1:
        raise ValueError('Expected one literal Bash block')
    raw = step.split('        run: |\n', 1)[1]
    if any(line and not line.startswith('          ') for line in raw.splitlines()):
        raise ValueError('Unexpected proof-scope block indentation')
    script = textwrap.dedent(raw)
    if not script.strip() or 'git diff' not in script or 'GITHUB_OUTPUT' not in script:
        raise ValueError('Missing actual proof-scope implementation')
    return script


class PilotProofScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.script = production_scope()
        cls.temporary = tempfile.TemporaryDirectory(prefix='pilot-proof-scope-')
        cls.root = Path(cls.temporary.name)
        cls.repo = cls.root / 'repo'
        cls.repo.mkdir()
        cls.env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        cls.env.update({
            'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
            'GIT_AUTHOR_NAME': 'Scope regression', 'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
            'GIT_COMMITTER_NAME': 'Scope regression', 'GIT_COMMITTER_EMAIL': 'fixture@example.invalid',
            'GIT_TERMINAL_PROMPT': '0', 'LC_ALL': 'C',
        })
        cls.git('init', '-q')
        (cls.repo / 'README.md').write_text('isolated test fixture\n')
        cls.base = cls.commit('base')
        cls.heads: dict[str, str] = {}
        paths = {
            'engine': 'revenue/pilot_delivery_renewal_expansion_gate/engine.py',
            'nested': 'revenue/pilot_delivery_renewal_expansion_gate/sub/deep.py',
            'contract': 'test_pilot_delivery_renewal_expansion_gate.py',
            'reload': 'test_pilot_delivery_renewal_reload_trust_root.py',
            'scope_tests': 'test_pilot_proof_scope.py',
            'old_workflow': '.github/workflows/pilot-delivery-renewal-expansion-gate.yml',
            'workflow': '.github/workflows/source-parses.yml',
            'unrelated': 'unrelated/example.py',
            'near_prefix': 'revenue/pilot_delivery_renewal_expansion_gate_extra/example.py',
            'newline': 'revenue/pilot_delivery_renewal_expansion_gate/line\nbreak.py',
        }
        for label, name in paths.items():
            cls.git('reset', '--hard', '-q', cls.base)
            p = cls.repo / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('# fixture\n')
            cls.heads[label] = cls.commit(label)
        cls.git('reset', '--hard', '-q', cls.heads['engine'])
        (cls.repo / paths['engine']).unlink()
        cls.heads['delete'] = cls.commit('delete relevant source')
        cls.git('reset', '--hard', '-q', cls.heads['engine'])
        (cls.repo / paths['engine']).rename(cls.repo / 'moved_out.py')
        cls.heads['rename'] = cls.commit('rename relevant source out of scope')
        cls.git('reset', '--hard', '-q', cls.base)
        target = cls.repo / 'revenue/pilot_delivery_renewal_expansion_gate'
        target.mkdir(parents=True, exist_ok=True)
        for i in range(3000):
            (target / f'{i:06d}_{"scope" * 16}.py').write_text('')
        cls.heads['large'] = cls.commit('large relevant change exceeding pipe buffer')
        cls.blob = cls.git('hash-object', '-w', '--stdin', input_text='not a commit\n')
        corrupt = ('tree ' + MISSING_SHA + '\nparent ' + cls.base +
                   '\nauthor Scope <fixture@example.invalid> 1 +0000\n'
                   'committer Scope <fixture@example.invalid> 1 +0000\n\nmissing tree\n')
        cls.missing_tree_commit = cls.git('hash-object', '-t', 'commit', '--literally', '-w', '--stdin', input_text=corrupt)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    @classmethod
    def git(cls, *args: str, input_text: str | None = None) -> str:
        result = subprocess.run(['git', *args], cwd=cls.repo, env=cls.env,
                                input=input_text, text=True, capture_output=True, timeout=30)
        if result.returncode:
            raise RuntimeError(f'Git fixture failed: {args!r}: {result.stderr}')
        return result.stdout.strip()

    @classmethod
    def commit(cls, message: str) -> str:
        cls.git('add', '-A')
        cls.git('commit', '-qm', message)
        return cls.git('rev-parse', 'HEAD')

    def evaluate(self, *, event: str = 'pull_request', base: str | None = None,
                 head: str | None = None, prefix: str = '') -> tuple[subprocess.CompletedProcess[str], str]:
        base = self.base if base is None else base
        head = self.heads['engine'] if head is None else head
        # Only known event scalar expressions in the predecessor block are
        # rendered. The patched workflow passes the same values through env.
        values = {EVENT_TOKEN: event, BASE_TOKEN: base, HEAD_TOKEN: head,
                  BEFORE_TOKEN: base, SHA_TOKEN: head}
        script = self.script
        for token, value in values.items():
            script = script.replace(token, value)
        self.assertNotIn('${{', script, 'Unresolved event expression')
        with tempfile.TemporaryDirectory(dir=self.root) as temp:
            output = Path(temp) / 'github-output'
            output.write_text(prefix)
            env = {**self.env, 'EVENT_NAME': event, 'BASE_SHA': base,
                   'HEAD_SHA': head, 'GITHUB_OUTPUT': str(output)}
            result = subprocess.run(['bash', '-c', script], cwd=self.repo, env=env,
                                    text=True, capture_output=True, timeout=30)
            return result, output.read_text()

    def expect(self, expected: bool, **kwargs: str) -> None:
        result, output = self.evaluate(**kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, f'run={str(expected).lower()}\n', result.stderr)

    def reject(self, **kwargs: str) -> None:
        result, output = self.evaluate(**kwargs)
        self.assertNotEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, '', 'Errors must never emit a successful scope decision')

    def test_source_binding_and_no_extra_workflow_slot(self):
        text = WORKFLOW.read_text()
        self.assertEqual(text.count('      - name: Detect pilot-renewal proof-surface changes'), 1)
        self.assertIn("python: ['3.11', '3.13']", text)
        self.assertIn('persist-credentials: false', text)
        self.assertIn('test_pilot_proof_scope.py', text)
        self.assertIn('python3 -O -m unittest -v test_pilot_proof_scope.py', text)

    def test_environment_matches_provider_expressions(self):
        text = WORKFLOW.read_text()
        self.assertIn('EVENT_NAME: ${{ github.event_name }}', text)
        self.assertIn("BASE_SHA: ${{ github.event_name == 'pull_request' && github.event.pull_request.base.sha || github.event.before }}", text)
        self.assertIn('HEAD_SHA: ${{ github.event.pull_request.head.sha || github.sha }}', text)

    def test_bash_syntax(self):
        result = subprocess.run(['bash', '-n'], input=self.script, text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_pr_engine_change(self): self.expect(True, head=self.heads['engine'])
    def test_pr_nested_change(self): self.expect(True, head=self.heads['nested'])
    def test_contract_change(self): self.expect(True, head=self.heads['contract'])
    def test_reload_test_change(self): self.expect(True, head=self.heads['reload'])
    def test_scope_test_change(self): self.expect(True, head=self.heads['scope_tests'])
    def test_old_workflow_change(self): self.expect(True, head=self.heads['old_workflow'])
    def test_parent_workflow_change(self): self.expect(True, head=self.heads['workflow'])
    def test_relevant_push(self): self.expect(True, event='push')
    def test_unrelated_python_change(self): self.expect(False, head=self.heads['unrelated'])
    def test_similar_directory_is_not_relevant(self): self.expect(False, head=self.heads['near_prefix'])
    def test_identical_commits(self): self.expect(False, head=self.base)
    def test_deletion_is_relevant(self): self.expect(True, base=self.heads['engine'], head=self.heads['delete'])
    def test_rename_out_of_scope_is_relevant(self): self.expect(True, base=self.heads['engine'], head=self.heads['rename'])
    def test_newline_in_path(self): self.expect(True, head=self.heads['newline'])
    def test_large_relevant_diff(self): self.expect(True, head=self.heads['large'])
    def test_manual_dispatch_runs_proof(self): self.expect(True, event='workflow_dispatch', base='', head=self.base)
    def test_new_branch_push_runs_proof(self): self.expect(True, event='push', base=ZERO_SHA)
    def test_zero_base_pr_is_rejected(self): self.reject(base=ZERO_SHA)
    def test_missing_base_object_is_rejected(self): self.reject(base=MISSING_SHA)
    def test_missing_head_object_is_rejected(self): self.reject(head=MISSING_SHA)
    def test_empty_base_is_rejected(self): self.reject(base='')
    def test_empty_head_is_rejected(self): self.reject(head='')
    def test_branch_name_base_is_rejected(self): self.reject(base='HEAD')
    def test_branch_name_head_is_rejected(self): self.reject(head='HEAD')
    def test_non_commit_base_is_rejected(self): self.reject(base=self.blob)
    def test_non_commit_head_is_rejected(self): self.reject(head=self.blob)
    def test_unknown_event_is_rejected(self): self.reject(event='schedule')
    def test_missing_tree_is_rejected(self): self.reject(head=self.missing_tree_commit)
    def test_manual_dispatch_still_requires_real_head(self): self.reject(event='workflow_dispatch', head=MISSING_SHA)

    def test_prior_github_outputs_are_preserved(self):
        result, output = self.evaluate(prefix='other=preserved\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output, 'other=preserved\nrun=true\n')


if __name__ == '__main__':
    unittest.main()
