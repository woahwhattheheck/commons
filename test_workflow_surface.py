import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from host import workflow_surface as surface


GOOD = b"name: unit\non:\n  pull_request:\n    paths: ['src/**', '!src/data/**']\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - run: python3 test_unit.py\n"


class WorkflowSurfaceTests(unittest.TestCase):
    def test_yaml_on_is_not_boolean(self):
        self.assertIn('pull_request', surface.workflow(GOOD)['on'])

    def test_bad_yaml_and_nul_fail(self):
        for raw in (GOOD + b'\0', b'on: [broken', b'- not-a-workflow', GOOD + b'jobs: {}\n'):
            with self.subTest(raw=raw), self.assertRaises((ValueError, surface.yaml.YAMLError)):
                surface.workflow(raw)

    def test_duplicate_key_fails(self):
        with self.assertRaises(ValueError):
            surface.workflow(GOOD.replace(b'run: python3 test_unit.py', b'run: first\n        run: second'))

    def test_feature_push_pr_duplicate_fails_main_push_is_distinct(self):
        data = surface.workflow(GOOD)
        data['on']['push'] = {}
        self.assertTrue(surface.duplicate_branch_events(data))
        data['on']['push'] = {'branches': ['main']}
        self.assertFalse(surface.duplicate_branch_events(data))
        data['on']['push']['branches'].append('feature/**')
        self.assertTrue(surface.duplicate_branch_events(data))
        data['on']['push']['branches'] = ['release/one']
        data['on']['pull_request']['branches'] = ['release/one']
        self.assertFalse(surface.duplicate_branch_events(data))
        data['on']['push']['branches'] = ['release/**']
        data['on']['pull_request']['branches'] = ['release/**']
        self.assertTrue(surface.duplicate_branch_events(data))

    def test_ordered_path_filters_and_root_glob(self):
        data = surface.workflow(GOOD)
        self.assertTrue(surface.affected(data, ['src/a.py']))
        self.assertFalse(surface.affected(data, ['src/data/fixture.json']))
        self.assertFalse(surface.affected(data, ['other/a.py']))
        self.assertTrue(surface.glob_match('a.py', '**/*.py'))
        self.assertTrue(surface.glob_match('a/b.py', '**/*.py'))
        self.assertFalse(surface.glob_match('a/b.py', '*.py'))
        self.assertTrue(surface.selected('src/data/a.py', ['src/**', '!src/data/**', 'src/data/*.py']))
        with self.assertRaises(ValueError):
            surface.glob_match('src/a.py', 'src/[ab].py')

    def fixture(self, root):
        (root / '.github/workflows').mkdir(parents=True)
        (root / 'ci/workflow-recipes').mkdir(parents=True)
        (root / '.github/workflows/core.yml').write_bytes(GOOD)
        (root / 'ci/workflow-recipes/unit.yml').write_bytes(GOOD)
        manifest = {'max_active_workflows': 1, 'source_workflows': 2, 'retained': ['.github/workflows/core.yml'],
                    'archived': [{'source': '.github/workflows/unit.yml',
                                  'archive': 'ci/workflow-recipes/unit.yml',
                                  'sha256': hashlib.sha256(GOOD).hexdigest(), 'bytes': len(GOOD)}]}
        (root / 'ci/workflow-surface.json').write_text(json.dumps(manifest), encoding='utf-8')

    def test_preservation_and_retrieval(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            self.assertEqual(surface.check(root)['status'], 'PASS')
            plan = surface.plan(root, ['src/a.py'])
            self.assertEqual(plan['status'], 'PLANNED_NOT_EXECUTED')
            self.assertEqual(plan['recipes'][0]['workflow']['jobs']['test']['steps'][0]['run'], 'python3 test_unit.py')
            self.assertEqual(len(surface.plan(root, [], 'unit.yml')['recipes']), 1)
            with self.assertRaises(ValueError):
                surface.plan(root, [], 'unknown.yml')

    def test_missing_tampered_or_reactivated_recipe_fails(self):
        for mutation in ('missing', 'tampered', 'reactivated'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self.fixture(root)
                path = root / 'ci/workflow-recipes/unit.yml'
                if mutation == 'missing': path.unlink()
                elif mutation == 'tampered': path.write_bytes(GOOD + b'# changed\n')
                else: (root / '.github/workflows/unit.yml').write_bytes(GOOD)
                self.assertEqual(surface.check(root)['status'], 'FAIL')

    def test_excess_active_files_and_missing_reusable_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            (root / '.github/workflows/extra.yml').write_bytes(GOOD)
            self.assertIn('active workflow count exceeds budget', surface.check(root)['errors'])
            (root / '.github/workflows/core.yml').write_text('on: pull_request\njobs:\n  call:\n    uses: ./.github/workflows/missing.yml\n')
            self.assertTrue(any('missing local reusable' in error for error in surface.check(root)['errors']))

    def test_dropped_inventory_entry_and_wrong_byte_count_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.fixture(root)
            path = root / 'ci/workflow-surface.json'
            manifest = json.loads(path.read_text())
            manifest['archived'][0]['bytes'] += 1
            path.write_text(json.dumps(manifest))
            self.assertEqual(surface.check(root)['status'], 'FAIL')
            manifest['archived'] = []
            path.write_text(json.dumps(manifest))
            (root / 'ci/workflow-recipes/unit.yml').unlink()
            self.assertIn('source workflow inventory is incomplete', surface.check(root)['errors'])



    def test_live_inventory_is_json_object_not_placeholder_stub(self):
        raw = Path('ci/workflow-surface.json').read_bytes()
        self.assertNotEqual(raw.strip(), b'PLACEHOLDER')
        data = json.loads(raw.decode('utf-8'))
        self.assertIsInstance(data, dict)
        self.assertEqual(data.get('schema'), 'commons.workflow-surface.v1')
        row = next(item for item in data['archived'] if item['archive'].endswith('service-deal-economics.yml'))
        recipe = Path(row['archive']).read_bytes()
        self.assertEqual(len(recipe), row['bytes'])
        self.assertEqual(hashlib.sha256(recipe).hexdigest(), row['sha256'])

    def test_live_archived_recipes_match_inventory_hashes(self):
        data = json.loads(Path('ci/workflow-surface.json').read_text(encoding='utf-8'))
        mismatches = []
        for row in data['archived']:
            recipe = Path(row['archive']).read_bytes()
            digest = hashlib.sha256(recipe).hexdigest()
            if len(recipe) != row['bytes'] or digest != row['sha256']:
                mismatches.append(row['archive'])
        self.assertEqual(mismatches, [])

    def test_live_checkout_fits_budget_and_passes_structural_check(self):
        result = surface.check(Path('.'))
        self.assertLessEqual(result['active'], json.loads(Path('ci/workflow-surface.json').read_text(encoding='utf-8'))['max_active_workflows'])
        self.assertEqual(result['status'], 'PASS', result['errors'])


if __name__ == '__main__':
    unittest.main()
