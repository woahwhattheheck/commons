"""Retained integration regressions: a completion record is not whole-transition proof.

All inputs are synthetic. Tests invoke the real classifier and CLI. The existing
34-test suite and its fixtures remain unchanged; negative cases start with its
known-good closed packet and alter one fact at a time.
"""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import scenario
import transition
from test_transition import minimal_closed_packet, item

HERE = Path(__file__).resolve().parent


def assess(packet):
    return transition.build(packet)[0]


class CompletionIntegrity(unittest.TestCase):
    def test_absent_completion_date_is_not_completion(self):
        packet = minimal_closed_packet()
        del packet['access_changes'][0]['completed_at']
        report = assess(packet)
        self.assertEqual(item(report, 'SYN-APP-001')['state'], 'NO_EVIDENCE')
        self.assertFalse(report.transition_closed())
        self.assertIn('date', ' '.join(item(report, 'SYN-APP-001')['reasons']))

    def test_invalid_completion_dates_are_not_completion(self):
        for value in (None, '', ' ', True, 12, [], {}, 'yesterday', '2026-02-30', '2026-09-15junk'):
            with self.subTest(value=value):
                packet = minimal_closed_packet()
                packet['access_changes'][0]['completed_at'] = value
                report = assess(packet)
                self.assertFalse(report.transition_closed())
                self.assertEqual(item(report, 'SYN-APP-001')['state'], 'NO_EVIDENCE')

    def test_valid_dates_and_timestamps_keep_positive_completion(self):
        for value in ('2026-09-15', '2026-09-15T09:30:00Z', '2026-09-15T09:30:00-04:00'):
            with self.subTest(value=value):
                packet = minimal_closed_packet()
                packet['access_changes'][0]['completed_at'] = value
                self.assertTrue(assess(packet).transition_closed())

    def test_nontext_locator_is_reported_not_executed(self):
        for value in (True, 12, ['synthetic://example'], {'path': 'synthetic://example'}):
            with self.subTest(value=value):
                packet = minimal_closed_packet()
                packet['access_changes'][0]['evidence_ref'] = value
                report = assess(packet)
                self.assertFalse(report.transition_closed())
                self.assertEqual(item(report, 'SYN-APP-001')['state'], 'NO_EVIDENCE')

    def test_unknown_action_cannot_prove_completion(self):
        packet = minimal_closed_packet()
        packet['access_changes'][0]['action'] = 'DONE_BY_REQUEST'
        report = assess(packet)
        self.assertFalse(report.transition_closed())
        self.assertEqual(item(report, 'SYN-APP-001')['state'], 'NO_EVIDENCE')
        self.assertTrue(any(i.code == 'UNKNOWN_VOCABULARY_VALUE' for i in report.issues))

    def test_duplicate_change_id_cannot_prove_completion(self):
        packet = minimal_closed_packet()
        duplicate = copy.deepcopy(packet['access_changes'][0])
        duplicate['status'] = 'REQUESTED'
        packet['access_changes'].append(duplicate)
        report = assess(packet)
        self.assertFalse(report.transition_closed())
        self.assertEqual(item(report, 'SYN-APP-001')['state'], 'NO_EVIDENCE')
        self.assertTrue(any(i.code == 'DUPLICATE_RECORD_ID' for i in report.issues))

    def test_dangling_reference_on_change_cannot_prove_completion(self):
        packet = minimal_closed_packet()
        packet['access_changes'][0]['successor_ref'] = 'SYN-PERSON-999'
        report = assess(packet)
        self.assertFalse(report.transition_closed())
        self.assertEqual(item(report, 'SYN-APP-001')['state'], 'NO_EVIDENCE')

    def test_successor_must_reference_person_not_application(self):
        packet = minimal_closed_packet()
        packet['applications'][0]['successor_ref'] = 'SYN-APP-001'
        report = assess(packet)
        self.assertFalse(report.transition_closed())
        self.assertEqual(item(report, 'SYN-APP-001')['state'], 'NO_EVIDENCE')
        self.assertTrue(any(i.code == 'REFERENCE_KIND_MISMATCH' for i in report.issues))

    def test_departing_reference_must_be_a_person(self):
        packet = minimal_closed_packet()
        packet['transition']['departing_ref'] = 'SYN-APP-001'
        report = assess(packet)
        self.assertFalse(report.transition_closed())
        self.assertTrue(any(i.code == 'REFERENCE_KIND_MISMATCH' and i.record_id == 'transition'
                            for i in report.issues))

    def test_successor_missing_stays_unresolved_even_with_completed_action(self):
        packet = minimal_closed_packet()
        packet['applications'][0]['successor_ref'] = None
        report = assess(packet)
        self.assertFalse(report.transition_closed())
        row = item(report, 'SYN-APP-001')
        self.assertEqual(row['state'], 'UNRESOLVED_OWNERSHIP')
        self.assertTrue(row['evidence_refs'], 'retain the completed action; do not erase evidence')

    def test_departing_person_cannot_succeed_themselves(self):
        packet = minimal_closed_packet()
        packet['applications'][0]['successor_ref'] = 'SYN-PERSON-001'
        report = assess(packet)
        self.assertFalse(report.transition_closed())
        self.assertEqual(item(report, 'SYN-APP-001')['state'], 'UNRESOLVED_OWNERSHIP')

    def test_another_pending_action_is_not_hidden_by_one_complete_action(self):
        packet = minimal_closed_packet()
        packet['access_changes'].append({
            'id': 'SYN-CHG-002', 'subject_ref': 'SYN-PERSON-001', 'target_ref': 'SYN-APP-001',
            'action': 'REVOKE_ACCESS', 'status': 'REQUESTED', 'synthetic': True,
        })
        report = assess(packet)
        self.assertFalse(report.transition_closed())
        row = item(report, 'SYN-APP-001')
        self.assertEqual(row['state'], 'NO_EVIDENCE')
        self.assertTrue(row['evidence_refs'], 'partial action evidence remains available')
        self.assertIn('SYN-CHG-002', ' '.join(row['reasons']))

    def test_unindexable_record_keeps_whole_packet_open(self):
        packet = minimal_closed_packet()
        packet['runbooks'].append('unreadable record')
        report = assess(packet)
        self.assertTrue(scenario.is_deliverable(report.issues))
        self.assertFalse(report.transition_closed())
        self.assertIn('Packet issues', transition.render_markdown(report))

    def test_build_does_not_mutate_inputs(self):
        packet = minimal_closed_packet()
        before = copy.deepcopy(packet)
        assess(packet)
        self.assertEqual(packet, before)

    def test_structurally_bad_json_exits_two_without_output_or_traceback(self):
        cases = [[], None, 'text', {'transition': []}, {'people': 5},
                 {'people': [{'id': ['SYN-PERSON-001']}]},
                 {'people': [{'id': 'SYN-PERSON-001', 'owner_ref': {}}]}]
        for packet in cases:
            with self.subTest(packet=packet), tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'input.json'
                path.write_text(json.dumps(packet), encoding='utf-8')
                out = Path(tmp) / 'out'
                proc = subprocess.run([sys.executable, str(HERE / 'transition.py'),
                                       '--input', str(path), '--outdir', str(out)],
                                      capture_output=True, text=True, timeout=10)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertNotIn('Traceback', proc.stderr)
                self.assertFalse(out.exists())

    def test_integrity_failure_cli_reports_open_not_success(self):
        packet = minimal_closed_packet()
        packet['access_changes'].append(copy.deepcopy(packet['access_changes'][0]))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'input.json'
            path.write_text(json.dumps(packet), encoding='utf-8')
            proc = subprocess.run([sys.executable, str(HERE / 'transition.py'), '--input', str(path)],
                                  capture_output=True, text=True, timeout=10)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertIn('DUPLICATE_RECORD_ID', proc.stdout)
            self.assertNotIn('Traceback', proc.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
