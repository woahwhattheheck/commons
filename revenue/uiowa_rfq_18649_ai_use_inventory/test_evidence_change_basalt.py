"""Actual-engine acceptance for the fixed fictional UIOWA-071 walkthrough."""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

if __package__:
    from . import replay_evidence_change_basalt as replay
else:
    import replay_evidence_change_basalt as replay

HERE = Path(__file__).resolve().parent


class TestEvidenceChangeWalkthrough(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = replay.run_replay()
        cls.cases = {c['scenario']: c for c in cls.result['scenarios']}

    def test_seven_real_engine_interpretations(self):
        self.assertEqual({k: c['target_entry']['classification'] for k,c in self.cases.items()}, {
            'baseline': 'UNSUPPORTED_CLAIM', 'locator_only': 'INFORMAL_EXPERIMENT',
            'named_output': 'ACTIVE_USE', 'explicit_standalone': 'INFORMAL_EXPERIMENT',
            'workflow_recorded': 'ACTIVE_USE', 'benefit_example': 'ACTIVE_USE',
            'still_declared_planned': 'PLANNED_USE'})

    def test_each_variant_is_exactly_baseline_plus_declared_overrides(self):
        baseline = self.cases['baseline']['input_record']
        for case in self.cases.values():
            with self.subTest(case=case['scenario']):
                expected = copy.deepcopy(baseline)
                expected.update(case['changes_from_baseline'])
                self.assertEqual(case['input_record'], expected)

    def test_all_records_and_all_fifteen_function_cells_are_retained(self):
        for case in self.cases.values():
            with self.subTest(case=case['scenario']):
                self.assertEqual(sum(case['counts'].values()), 10)
                self.assertEqual(len(case['coverage']), 15)
                self.assertEqual(sum(c['entries'] for c in case['coverage']), 10)
                self.assertEqual(case['validation_issues'], [])

    def test_unknown_integration_and_explicit_none_are_not_equivalent(self):
        named = self.cases['named_output']['target_entry']
        alone = self.cases['explicit_standalone']['target_entry']
        self.assertEqual(named['integrations_state'], 'UNKNOWN')
        self.assertIn('UNKNOWN_INTEGRATION', [g['gap'] for g in named['gaps']])
        self.assertEqual(alone['integrations_state'], 'NONE_REPORTED')
        self.assertNotEqual(named['classification'], alone['classification'])

    def test_active_does_not_erase_unsupported_benefit_or_unknown_user_count(self):
        active = self.cases['workflow_recorded']['target_entry']
        self.assertEqual(active['classification'], 'ACTIVE_USE')
        self.assertEqual(active['user_count'], 'UNKNOWN')
        self.assertEqual(active['benefits_with_example'], 0)
        self.assertIn('UNSUPPORTED_BENEFIT', [g['gap'] for g in active['gaps']])
        for case in self.cases.values():
            self.assertEqual(case['target_entry']['user_count'], 'UNKNOWN')

    def test_reported_benefit_locator_does_not_invent_quantified_savings(self):
        row = self.cases['benefit_example']['target_entry']
        self.assertEqual(row['benefits_with_example'], 1)
        self.assertEqual(row['observed_benefits'][0]['claim'],
                         self.cases['baseline']['input_record']['observed_benefits'][0]['claim'])
        for key in ('hours_saved', 'savings', 'adoption_rate', 'maturity_rank'):
            self.assertNotIn(key, row)
        self.assertEqual(len(row['gaps']), 2)

    def test_planned_declaration_and_contradiction_survive_together(self):
        row = self.cases['still_declared_planned']['target_entry']
        self.assertEqual(row['declared_status'], 'PLANNED')
        self.assertEqual(row['classification'], 'PLANNED_USE')
        self.assertTrue(row['outputs'])
        self.assertIn('STATUS_EVIDENCE_MISMATCH', [g['gap'] for g in row['gaps']])
        self.assertIn('P-MIS-01', [q['id'] for q in self.cases['still_declared_planned']['follow_up_probes']])

    def test_actual_questions_and_gap_counts_match_each_variant(self):
        self.assertEqual([c['total_gaps'] for c in self.result['scenarios']], [19,17,17,16,16,15,16])
        self.assertEqual([len(c['target_entry']['gaps']) for c in self.result['scenarios']], [6,4,4,3,3,2,3])
        self.assertIn('P-EX-01', [q['id'] for q in self.cases['baseline']['follow_up_probes']])
        self.assertNotIn('P-EX-01', [q['id'] for q in self.cases['locator_only']['follow_up_probes']])

    def test_source_and_fixture_are_bound_to_the_executed_capture(self):
        for name, digest in self.result['source_blobs'].items():
            self.assertEqual(digest, replay.git_blob((HERE/name).read_bytes()))
        self.assertEqual(self.result['runner_sha256'], hashlib.sha256(replay.CHILD.encode()).hexdigest())
        self.assertEqual(self.result['optimize'], sys.flags.optimize)

    def test_post_capture_original_edit_does_not_relabel_executed_source(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)
            for name in (*replay.ENGINE_FILES, replay.FIXTURE):
                p = source/name; p.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(HERE/name, p)
            before = (source/'inventory.py').read_bytes()
            real_run = subprocess.run
            def mutate_original_then_run(*args, **kwargs):
                (source/'inventory.py').write_bytes(before+b'\n# changed only after capture\n')
                return real_run(*args, **kwargs)
            with mock.patch.object(replay.subprocess, 'run', side_effect=mutate_original_then_run):
                result = replay.run_replay(source)
            self.assertEqual(result['source_blobs']['inventory.py'], replay.git_blob(before))
            self.assertNotEqual(result['source_blobs']['inventory.py'], replay.git_blob((source/'inventory.py').read_bytes()))
            self.assertEqual(result['scenarios'], self.result['scenarios'])

    def test_changed_fixture_is_not_relabelled_as_the_known_fiction(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)
            for name in (*replay.ENGINE_FILES,replay.FIXTURE):
                p=source/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(HERE/name,p)
            (source/replay.FIXTURE).write_text('{"entries": []}',encoding='utf-8')
            with mock.patch.object(replay.subprocess, 'run') as child:
                with self.assertRaisesRegex(ValueError, 'original synthetic fixture'):
                    replay.run_replay(source)
                child.assert_not_called()

    def test_rendered_explanation_retains_interpretation_limits(self):
        rendered = replay.render_markdown(self.result)
        self.assertIn('ACTIVE_USE while integration remains UNKNOWN',rendered)
        self.assertIn('does not verify the locator',rendered)
        for name in self.cases:
            self.assertIn('### '+name,rendered)
        self.assertIn('P-MIS-01',rendered)


if __name__ == '__main__':
    unittest.main()
