from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parent / 'host' / 'moving_main_preimage.py'


def git(repo: Path, *args: str) -> str:
    proc = subprocess.run(['git', '-C', str(repo), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {proc.stderr}")
    return proc.stdout.strip()


class MovingMainPreimageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / 'repo'
        self.repo.mkdir()
        git(self.repo, 'init', '-q')
        git(self.repo, 'config', 'user.email', 'test@example.test')
        git(self.repo, 'config', 'user.name', 'Test')
        (self.repo / 'owned.txt').write_text('base\n')
        (self.repo / 'other.txt').write_text('base-other\n')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'base')
        self.base = git(self.repo, 'rev-parse', 'HEAD')
        git(self.repo, 'branch', 'base-point')

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def commit(self, branch: str, changes: dict[str, str | None], message: str) -> str:
        git(self.repo, 'checkout', '-q', branch)
        for name, value in changes.items():
            path = self.repo / name
            if value is None:
                path.unlink()
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(value)
        git(self.repo, 'add', '-A')
        git(self.repo, 'commit', '-qm', message)
        return git(self.repo, 'rev-parse', 'HEAD')

    def branch(self, name: str, start: str | None = None) -> None:
        git(self.repo, 'branch', name, start or self.base)

    def run_check(self, *, base='base-point', head='candidate', current='mainline', paths=('owned.txt',)):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), '--repo', str(self.repo), '--base', base,
             '--head', head, '--current-main', current,
             *sum((['--path', p] for p in paths), [])],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        )
        return proc.returncode, json.loads(proc.stdout)

    def test_disjoint_main_advance_passes(self):
        self.branch('candidate')
        self.commit('candidate', {'owned.txt': 'candidate\n'}, 'candidate')
        self.branch('mainline')
        self.commit('mainline', {'other.txt': 'main-new\n'}, 'main')
        rc, out = self.run_check()
        self.assertEqual(rc, 0)
        self.assertEqual(out['status'], 'PASS')
        self.assertTrue(out['paths'][0]['preimage_unchanged'])
        self.assertFalse(out['mutation_performed'])

    def test_owned_preimage_drift_holds(self):
        self.branch('candidate')
        self.commit('candidate', {'owned.txt': 'candidate\n'}, 'candidate')
        self.branch('mainline')
        self.commit('mainline', {'owned.txt': 'main-changed\n'}, 'main')
        rc, out = self.run_check()
        self.assertEqual(rc, 2)
        self.assertIn('OWNED_PREIMAGE_CHANGED:owned.txt', out['reasons'])

    def test_independent_new_path_holds(self):
        self.branch('candidate')
        self.commit('candidate', {'new.txt': 'candidate\n'}, 'candidate')
        self.branch('mainline')
        self.commit('mainline', {'new.txt': 'main\n'}, 'main')
        rc, out = self.run_check(paths=('new.txt',))
        self.assertEqual(rc, 2)
        self.assertIn('OWNED_PREIMAGE_CHANGED:new.txt', out['reasons'])
        self.assertEqual(out['paths'][0]['base']['state'], 'ABSENT')

    def test_candidate_extra_path_holds(self):
        self.branch('candidate')
        self.commit('candidate', {'owned.txt': 'candidate\n', 'extra.txt': 'extra\n'}, 'candidate')
        self.branch('mainline')
        self.commit('mainline', {'other.txt': 'main-new\n'}, 'main')
        rc, out = self.run_check()
        self.assertEqual(rc, 2)
        self.assertIn('CANDIDATE_SCOPE_MISMATCH', out['reasons'])

    def test_deletion_with_unchanged_preimage_passes(self):
        self.branch('candidate')
        self.commit('candidate', {'owned.txt': None}, 'candidate')
        self.branch('mainline')
        self.commit('mainline', {'other.txt': 'main-new\n'}, 'main')
        rc, out = self.run_check()
        self.assertEqual(rc, 0)
        self.assertEqual(out['paths'][0]['head']['state'], 'ABSENT')

    def test_diverged_current_main_holds(self):
        self.branch('candidate')
        self.commit('candidate', {'owned.txt': 'candidate\n'}, 'candidate')
        git(self.repo, 'checkout', '--orphan', 'mainline')
        git(self.repo, 'rm', '-rf', '.')
        (self.repo / 'other.txt').write_text('orphan\n')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '-qm', 'orphan')
        rc, out = self.run_check()
        self.assertEqual(rc, 2)
        self.assertIn('BASE_NOT_ANCESTOR_OF_CURRENT_MAIN', out['reasons'])

    def test_unsafe_and_duplicate_paths_fail_closed(self):
        self.branch('candidate')
        self.commit('candidate', {'owned.txt': 'candidate\n'}, 'candidate')
        self.branch('mainline')
        self.commit('mainline', {'other.txt': 'main-new\n'}, 'main')
        rc, out = self.run_check(paths=('../owned.txt',))
        self.assertEqual(rc, 64)
        self.assertEqual(out['status'], 'ERROR')
        rc, out = self.run_check(paths=('owned.txt', 'owned.txt'))
        self.assertEqual(rc, 64)
        self.assertEqual(out['status'], 'ERROR')


if __name__ == '__main__':
    unittest.main()
