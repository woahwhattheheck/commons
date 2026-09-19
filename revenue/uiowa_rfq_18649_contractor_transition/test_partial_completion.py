#!/usr/bin/env python3
"""MERIDIAN-Q7 semantic donor adapted onto the R9V6/Trellis classifier.

Donor: #16363 @ 29e3d3d0bda9571144fa31c55185742d9ffd49ef,
transition blob 3fd81bba864eae457a062fac49d379d182959e37 and
regression blob 1949d33154f7c8c89b0c44691ed68dc21a5baab0.
Partial-action/ownership findings: ZZ-MERIDIAN-Q7, GPT-6 Astra Pro.
Union implementation and expanded regressions: ZZ-KESTREL-R9V6.
This is an adaptation, not a claim that the donor's entire test suite is copied.
"""
import copy
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import transition
from test_completion_integrity import packet

HERE = Path(__file__).resolve().parent


def build(data):
    return transition.build(data)[0]


def add_action(data, status='REQUESTED', action='REVOKE_ACCESS'):
    extra = copy.deepcopy(data['access_changes'][0])
    extra.update(id='SYN-CHG-002', action=action, status=status)
    if status != 'COMPLETED':
        extra.update(completed_at=None, evidence_ref=None)
    else:
        extra['evidence_ref'] = 'synthetic://partial-completion/action-002'
    data['access_changes'].append(extra)


class PartialCompletion(unittest.TestCase):
    def test_completed_action_does_not_name_missing_successor(self):
        for absent in ('missing', None, ''):
            with self.subTest(successor=absent):
                data = packet()
                if absent == 'missing':
                    data['applications'][0].pop('successor_ref')
                else:
                    data['applications'][0]['successor_ref'] = absent
                report = build(data)
                self.assertEqual(report.items[0]['state'], 'UNRESOLVED_OWNERSHIP')
                self.assertEqual(report.items[0]['evidence_refs'],
                                 [data['access_changes'][0]['evidence_ref']])
                self.assertFalse(report.transition_closed())

    def test_departing_owner_cannot_succeed_themselves(self):
        data = packet()
        data['applications'][0]['successor_ref'] = data['applications'][0]['owner_ref']
        report = build(data)
        self.assertEqual(report.items[0]['state'], 'UNRESOLVED_OWNERSHIP')
        self.assertTrue(report.items[0]['evidence_refs'])
        self.assertFalse(report.transition_closed())

    def test_each_valid_action_cannot_erase_pending_action(self):
        cases = 0
        for completed_action in ('REASSIGN_OWNER', 'REVOKE_ACCESS', 'ROTATE_CREDENTIAL', 'UPDATE_RUNBOOK'):
            for pending_status in ('REQUESTED', 'IN_PROGRESS'):
                for pending_action in ('REASSIGN_OWNER', 'REVOKE_ACCESS', 'ROTATE_CREDENTIAL', 'UPDATE_RUNBOOK'):
                    data = packet(); data['access_changes'][0]['action'] = completed_action
                    add_action(data, pending_status, pending_action)
                    for order in itertools.permutations(data['access_changes']):
                        candidate = copy.deepcopy(data); candidate['access_changes'] = list(order)
                        report = build(candidate)
                        with self.subTest(completed=completed_action, status=pending_status,
                                          pending=pending_action, ids=[r['id'] for r in order]):
                            self.assertEqual(report.items[0]['state'], 'NO_EVIDENCE')
                            self.assertEqual(len(report.items[0]['evidence_refs']), 1)
                            self.assertIn('SYN-CHG-002', ' '.join(report.items[0]['reasons']))
                            self.assertFalse(report.transition_closed())
                            self.assertEqual(report.issues, [])
                        cases += 1
        self.assertEqual(cases, 64)

    def test_same_action_pending_record_is_not_assumed_superseded(self):
        data = packet(); add_action(data, action='REASSIGN_OWNER')
        report = build(data)
        self.assertEqual(report.items[0]['state'], 'NO_EVIDENCE')
        self.assertIn('REQUESTED', ' '.join(report.items[0]['reasons']))

    def test_completed_action_and_locatorless_other_action_remain_open(self):
        data = packet(); add_action(data, 'COMPLETED')
        data['access_changes'][1]['evidence_ref'] = ' '
        report = build(data)
        self.assertEqual(report.items[0]['state'], 'NO_EVIDENCE')
        self.assertEqual(report.items[0]['evidence_refs'], [data['access_changes'][0]['evidence_ref']])
        self.assertIn('no evidence locator', ' '.join(report.items[0]['reasons']))

    def test_all_declared_actions_supported_is_closed_control(self):
        data = packet(); add_action(data, 'COMPLETED')
        forward = build(data)
        data['access_changes'].reverse()
        reverse = build(data)
        self.assertTrue(forward.transition_closed())
        self.assertEqual(len(forward.items[0]['evidence_refs']), 2)
        self.assertEqual(forward.as_dict(), reverse.as_dict())

    def test_explicitly_removing_pending_record_restores_closed_control(self):
        data = packet(); add_action(data)
        self.assertFalse(build(data).transition_closed())
        data['access_changes'].pop()
        self.assertTrue(build(data).transition_closed())

    def test_other_subjects_pending_action_does_not_erase_local_completion(self):
        data = packet(); add_action(data)
        data['access_changes'][1]['subject_ref'] = 'SYN-PERSON-002'
        report = build(data)
        self.assertTrue(report.transition_closed())
        self.assertEqual(report.items[0]['state'], 'COMPLETED')

    def test_pending_for_other_item_does_not_erase_local_receipt(self):
        data = packet(); other = copy.deepcopy(data['applications'][0])
        other.update(id='SYN-APP-002', name='Another fictional application')
        data['applications'].append(other); add_action(data)
        data['access_changes'][1]['target_ref'] = other['id']
        report = build(data)
        self.assertEqual({i['item_id']:i['state'] for i in report.items},
                         {'SYN-APP-001':'COMPLETED', 'SYN-APP-002':'NO_EVIDENCE'})
        self.assertFalse(report.transition_closed())

    def test_relationship_diagnostics_still_precede_ownership_classification(self):
        data = packet(); data['applications'][0]['successor_ref'] = None
        data['access_changes'].append(copy.deepcopy(data['access_changes'][0]))
        report = build(data)
        self.assertEqual(report.items[0]['state'], 'NO_EVIDENCE')
        self.assertEqual(report.items[0]['evidence_refs'], [])
        self.assertFalse(report.transition_closed())

    def test_partial_report_is_input_immutable_and_order_invariant(self):
        data = packet(); add_action(data); before = copy.deepcopy(data)
        forward = build(data); self.assertEqual(data, before)
        data['access_changes'].reverse(); reverse = build(data)
        self.assertEqual(forward.as_dict(), reverse.as_dict())
        self.assertEqual(transition.render_markdown(forward), transition.render_markdown(reverse))

    def test_cli_keeps_partial_evidence_and_exits_open_in_both_modes(self):
        data = packet(); add_action(data)
        with tempfile.TemporaryDirectory(prefix='partial-completion-') as temporary:
            root = Path(temporary); source = root/'input.json'
            source.write_text(json.dumps(data), encoding='utf-8')
            flags = ['-O'] if sys.flags.optimize else []
            proc = subprocess.run([sys.executable, '-B', *flags, str(HERE/'transition.py'),
                '--input', str(source), '--outdir', str(root/'out')],
                capture_output=True, text=True, timeout=15)
            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertNotIn('Traceback', proc.stderr)
            rendered = json.loads((root/'out/transition_report.json').read_text())
            self.assertFalse(rendered['transition_closed'])
            self.assertEqual(rendered['items'][0]['state'], 'NO_EVIDENCE')
            self.assertEqual(len(rendered['items'][0]['evidence_refs']), 1)
            self.assertIn('SYN-CHG-002', ' '.join(rendered['items'][0]['reasons']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
