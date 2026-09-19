import copy
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import alert_quality as aq

ROOT = Path(__file__).resolve().parent


class AlertQualityTest(unittest.TestCase):
    def setUp(self):
        self.p = aq.strict_load(ROOT / 'synthetic.json')

    def report(self):
        return aq.analyze(self.p)

    def episode(self, name):
        return next(e for e in self.report()['episodes'] if e['episode_id'] == name)

    def test_known_sample(self):
        s = self.report()['summary']
        self.assertEqual(s['notifications'], 12)
        self.assertEqual(s['observed_episodes'], 6)
        self.assertEqual(s['confirmed_duplicates'], 4)
        self.assertEqual(s['reviewed_redundant'], 5)
        self.assertEqual(s['reviewed_useful'], 5)
        self.assertEqual(s['unreviewed'], 2)
        self.assertEqual(s['redundant_share_of_reviewed'], .5)
        self.assertEqual(s['explicitly_unowned_episodes'], 1)
        self.assertEqual(s['unknown_owner_episodes'], 1)
        self.assertEqual(s['completed_response_sample_n'], 3)
        self.assertEqual(s['median_action_minutes_completed_only'], 4)

    def test_identical_rule_separate_incidents(self):
        self.assertEqual(self.episode('ESS-102')['confirmed_duplicates'], 0)
        self.assertNotEqual(self.episode('ESS-102')['incident_id'], self.episode('ESS-101')['incident_id'])

    def test_escalation_is_not_duplicate(self):
        self.assertEqual(self.episode('ESS-101')['escalation_notifications'], 1)
        self.p['notifications'][3]['duplicate_of'] = 'N01'
        with self.assertRaises(aq.EvidenceError): self.report()

    def test_cross_incident_duplicate_rejected(self):
        n = self.p['notifications'][4]
        n.update(kind='repeat', value='redundant', duplicate_of='N01')
        with self.assertRaises(aq.EvidenceError): self.report()

    def test_different_route_duplicate_rejected(self):
        self.p['notifications'][1]['route'] = 'other'
        with self.assertRaises(aq.EvidenceError): self.report()

    def test_duplicate_requires_review(self):
        self.p['notifications'][1]['review_ref'] = None
        with self.assertRaises(aq.EvidenceError): self.report()

    def test_temporal_duplicate_cycle_rejected(self):
        self.p['notifications'][1]['duplicate_of'] = 'N03'
        with self.assertRaises(aq.EvidenceError): self.report()

    def test_ack_is_not_action(self):
        r = self.episode('IAM-301')
        self.assertEqual(r['ack_minutes'], 1)
        self.assertIsNone(r['action_minutes'])
        self.assertEqual(r['response_state'], 'not_observed_by_window_end')

    def test_incomplete_responses_unknown_not_absent(self):
        self.assertEqual(self.episode('RIS-201')['response_state'], 'unknown_missing_response_coverage')

    def test_action_can_precede_acknowledgement(self):
        r = self.episode('IAM-302')
        self.assertEqual((r['action_minutes'], r['ack_minutes']), (3, 5))

    def test_partial_notification_sample_not_in_completed_median(self):
        self.p['coverage'][0]['notifications'] = 'partial'
        s = self.report()['summary']
        self.assertEqual(s['completed_response_sample_n'], 1)
        self.assertEqual(s['median_action_minutes_completed_only'], 3)

    def test_unknown_is_not_zero(self):
        for e in self.p['episodes']:
            e['action_at'] = e['action_ref'] = None
        self.assertIsNone(self.report()['summary']['median_action_minutes_completed_only'])
        for n in self.p['notifications']:
            n.update(value='unknown', review_ref=None, duplicate_of=None)
        self.assertIsNone(self.report()['summary']['redundant_share_of_reviewed'])

    def test_same_incident_must_not_split(self):
        self.p['episodes'][1]['incident_id'] = 'incident-101'
        with self.assertRaises(aq.EvidenceError): self.report()

    def test_multiple_unlinked_notifications_need_correlation_evidence(self):
        n = copy.deepcopy(self.p['notifications'][-1])
        n['id'] = 'N13'
        self.p['notifications'].append(n)
        with self.assertRaises(aq.EvidenceError): self.report()

    def test_explicit_absence_needs_evidence(self):
        self.p['episodes'][2]['owner_ref'] = None
        with self.assertRaises(aq.EvidenceError): self.report()

    def test_action_time_needs_evidence(self):
        self.p['episodes'][0]['action_ref'] = None
        with self.assertRaises(aq.EvidenceError): self.report()

    def test_invalid_temporal_data(self):
        for at in ('2026-09-14T08:59:00Z', '2026-09-16T00:00:00Z', '2026-09-14T09:12:00'):
            with self.subTest(at=at):
                self.p['episodes'][0]['action_at'] = at
                with self.assertRaises(aq.EvidenceError): self.report()

    def test_offsets_are_normalized(self):
        self.p['episodes'][0]['action_at'] = '2026-09-14T05:12:00-04:00'
        self.assertEqual(self.episode('ESS-101')['action_minutes'], 12)

    def test_half_open_window(self):
        self.p['notifications'][0]['at'] = self.p['window']['end']
        with self.assertRaises(aq.EvidenceError): self.report()

    def test_permutations_preserve_report_and_digest(self):
        expected = self.report()
        for field in ('episodes', 'notifications', 'coverage', 'evidence'):
            self.p[field].reverse()
        self.assertEqual(expected, self.report())

    def test_duplicate_identifiers(self):
        self.p['notifications'].append(copy.deepcopy(self.p['notifications'][0]))
        with self.assertRaises(aq.EvidenceError): self.report()

    def test_evidence_reference_integrity(self):
        self.p['notifications'][0]['source_ref'] = 'nonexistent'
        with self.assertRaises(aq.EvidenceError): self.report()

    def test_real_evidence_not_accepted_by_preparation_kit(self):
        self.p['evidence_class'] = 'UNIVERSITY'
        with self.assertRaises(aq.EvidenceError): self.report()

    def test_strict_json(self):
        with tempfile.TemporaryDirectory() as td:
            f = Path(td)/'bad.json'
            for content in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}', 'not json'):
                f.write_text(content)
                with self.assertRaises(aq.EvidenceError): aq.strict_load(f)

    def test_every_recommendation_traces_and_measures_outcome(self):
        report = self.report()
        evidence = {e['id'] for e in report['evidence']}
        self.assertGreater(len(report['recommendations']), 8)
        for r in report['recommendations']:
            self.assertTrue(set(r['evidence_ids']) <= evidence)
            self.assertTrue(r['evidence_ids'])
            self.assertGreater(len(r['outcome_check']), 30)

    def test_display_export_neutralizes_formula_text(self):
        for text in ('=1+1', ' @SUM(A1)', '+2', '-2', '\tformula'):
            self.assertTrue(aq.cell(text).startswith("'"))
        self.assertEqual(aq.cell(None), 'UNKNOWN')

    def test_real_cli_and_csv_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)/'out'
            run = subprocess.run([sys.executable, str(ROOT/'alert_quality.py'), str(ROOT/'synthetic.json'), '--out', str(out)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(json.loads((out/'report.json').read_text()), self.report())
            with (out/'notifications.csv').open(encoding='utf-8-sig', newline='') as f:
                self.assertEqual(len(list(csv.DictReader(f))), 12)
            self.assertIn('SYNTHETIC', (out/'report.md').read_text())

    def test_empty_export_replaces_stale_rows(self):
        with tempfile.TemporaryDirectory() as td:
            aq.export(self.p, Path(td))
            self.p['episodes'] = []
            self.p['notifications'] = []
            aq.export(self.p, Path(td))
            for name in ('episodes', 'notifications', 'recommendations'):
                with (Path(td)/(name+'.csv')).open(encoding='utf-8-sig', newline='') as f:
                    self.assertEqual(list(csv.DictReader(f)), [])

    def test_csv_export_is_order_independent(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = Path(td)/'a', Path(td)/'b'
            aq.export(self.p, a)
            for name in ('episodes','notifications','evidence','coverage'):
                self.p[name].reverse()
            aq.export(self.p, b)
            for name in ('episodes','notifications','recommendations','evidence'):
                self.assertEqual((a/(name+'.csv')).read_bytes(), (b/(name+'.csv')).read_bytes())

    def test_unlinked_episode_is_not_an_incident_claim(self):
        self.assertIsNone(self.episode('RIS-fragment')['incident_id'])
        self.assertEqual(self.episode('RIS-fragment')['impact'], 'unknown')

    def test_unicode_multiline_source_is_retained(self):
        self.p['evidence'][0]['excerpt'] += '\nRésumé | two lines'
        with tempfile.TemporaryDirectory() as td:
            aq.export(self.p, Path(td))
            with (Path(td)/'evidence.csv').open(encoding='utf-8-sig', newline='') as f:
                self.assertTrue(any('Résumé | two lines' in r['excerpt'] for r in csv.DictReader(f)))
            self.assertIn('&#124;', (Path(td)/'report.md').read_text())


if __name__ == '__main__':
    unittest.main()
