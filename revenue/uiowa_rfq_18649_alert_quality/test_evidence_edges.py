"""Additional traceability and numeric input regression cases."""
import copy
import json
import unittest

import alert_quality as aq
from synthetic_history import packet


class EvidenceEdgesTests(unittest.TestCase):
    def test_specialized_evidence_survives_into_recommendations(self):
        data = packet()
        data['sources'].append({'id': 'RUNBOOK-TASK', 'locator': 'synthetic:walkthrough#2',
                                'excerpt': 'FICTIONAL independent task failed on an obsolete diagnostic location.'})
        inc = next(i for i in data['incidents'] if i['id'] == 'I1')
        inc['runbook']['source_refs'] = ['RUNBOOK-TASK']
        result = aq.analyze(data)
        rec = next(r for r in result['recommendations'] if r['id'] == 'AQ-I1-RUNBOOK')
        self.assertIn('RUNBOOK-TASK', rec['source_refs'])
        row = next(r for r in result['incidents'] if r['id'] == 'I1')
        self.assertIn('RUNBOOK-TASK', row['source_refs'])

    def test_large_json_exponent_rejected_at_parse(self):
        with self.assertRaises(aq.InputError):
            aq.loads('{"extra": 1e999}')

    def test_nonfinite_aggregate_is_explicit_input_error(self):
        data = packet()
        for n in data['notifications']:
            if n['id'] in ('N02', 'N03'):
                n['triage_seconds'] = 1e308
        with self.assertRaises(aq.InputError):
            aq.analyze(data)

    def test_direct_api_nonobject_is_input_error(self):
        with self.assertRaises(aq.InputError):
            aq.analyze([])

    def test_csv_both_null_and_numeric_zero_remain_distinct(self):
        content = aq.csv_text([{'x': None}, {'x': 0}], ['x'])
        self.assertEqual(content, 'x\nUNKNOWN\n0\n')

    def test_rendered_incident_view_has_ack_and_useful_times(self):
        rendered = aq.render(aq.analyze(packet()))
        self.assertIn('ACK / useful seconds', rendered)
        self.assertIn('0.0 / 720.0', rendered)


if __name__ == '__main__':
    unittest.main()
