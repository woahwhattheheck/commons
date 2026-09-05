"""Synthetic regression cases at the handoff/index boundary; no customer IO.

The production handoff module runs unmodified. Mocked index composition is
intentional: these tests isolate inference/provenance, not ledger loading.
"""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    'weld_test_relationship_handoff', ROOT / 'host' / 'lm_gtm_relationship_handoff.py'
)
assert SPEC and SPEC.loader
handoff = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(handoff)
SUBJECT = 'synthetic-proof-customer'


class HandoffProvenanceRegression(unittest.TestCase):
    def event(self, body, kind='STATUS', *, suffix='one', ts='2026-09-04T21:00:00Z', sources=None):
        return {
            'id': 'synthetic-event-' + suffix,
            'subject_id': SUBJECT,
            'type': kind,
            'ts': ts,
            'body': body,
            'source_paths': ['gmail:synthetic-message'] if sources is None else sources,
        }

    def packet(self, events, *, decision='OWNER_HOLD', next_action='Retain no-new-contact instruction; inspect source.'):
        row = {
            'id': SUBJECT, 'role': 'external_prospect', 'live': True,
            'organization': 'Synthetic customer', 'person': None,
            'decision': decision, 'dnr': True,
            'next_action': next_action,
            'owner': 'UNSEATED', 'due': None,
            'source_paths': ['synthetic:existing-ledger'],
            'overlay_event_ids': [e['id'] for e in events],
            'route_kind': 'EXISTING_CRM_RECORD',
            'route_ref': 'airtable:synthetic-existing-record',
        }
        with patch.object(handoff.idx, 'build_index', return_value={'rows':[row], 'events':events}):
            return handoff.relationship_handoff(SUBJECT, paths={'root':ROOT})

    def test_no_event_means_no_promise(self):
        self.assertEqual(self.packet([])['fields']['promised']['status'], 'ABSENT')

    def test_not_sent_does_not_create_promise(self):
        p = self.packet([self.event('NOT SENT. Draft awaits owner review.')])
        self.assertEqual(p['fields']['promised']['status'], 'ABSENT')

    def test_never_sent_does_not_create_promise(self):
        p = self.packet([self.event('The proposal was never sent.')])
        self.assertEqual(p['fields']['promised']['status'], 'ABSENT')

    def test_question_about_sent_does_not_create_promise(self):
        p = self.packet([self.event('Was the signed proposal sent? Not verified.')])
        self.assertEqual(p['fields']['promised']['status'], 'ABSENT')

    def test_future_sent_does_not_create_promise(self):
        p = self.packet([self.event('The quote will be sent after review.')])
        self.assertEqual(p['fields']['promised']['status'], 'ABSENT')

    def test_transport_is_not_commitment_content(self):
        p = self.packet([self.event('SENT. Requested receipt confirmation.', 'SENT_AWAITING_REPLY')])
        self.assertEqual(p['fields']['promised']['status'], 'ABSENT')

    def test_pointer_does_not_make_summary_an_actual_message(self):
        p = self.packet([self.event('Peer summary: buyer might prefer Tuesday.', 'MATERIAL_REPLY')])
        self.assertNotEqual(p['fields']['wants']['provenance'], 'ACTUAL_MESSAGE')
        self.assertIn('gmail:synthetic-message', p['fields']['wants']['evidence'])

    def test_slack_pointer_does_not_make_summary_an_actual_message(self):
        p = self.packet([self.event('Peer paraphrase, not a verbatim buyer message.', 'MATERIAL_REPLY', sources=['slack:synthetic-thread'])])
        self.assertNotEqual(p['fields']['wants']['provenance'], 'ACTUAL_MESSAGE')

    def test_offset_timestamp_order_uses_actual_time(self):
        later = self.event('Newest request in actual UTC time.', 'MATERIAL_REPLY', suffix='later', ts='2026-09-04T23:50:00-07:00')
        earlier = self.event('Older request in actual UTC time.', 'MATERIAL_REPLY', suffix='earlier', ts='2026-09-05T01:10:00Z')
        p = self.packet([later, earlier])
        self.assertEqual(p['fields']['wants']['value'], later['body'])
        self.assertEqual(p['evidence_chain'][-1]['id'], later['id'])

    def test_all_original_source_pointers_are_retained(self):
        e = self.event('Unverified summary.', 'MATERIAL_REPLY', sources=['gmail:synthetic-message','slack:synthetic-thread'])
        p = self.packet([e])
        self.assertEqual(p['evidence_chain'][0]['source_paths'], e['source_paths'])

    def test_submission_fact_does_not_remove_no_contact(self):
        p = self.packet([self.event('SUBMISSION_SENT; recipient acknowledgement is not established.', 'SENT_AWAITING_REPLY')])
        self.assertEqual(p['decision'], 'OWNER_HOLD')
        self.assertTrue(p['dnr'])
        self.assertIn('no-new-contact', p['fields']['successor_next_action']['value'])
        self.assertEqual(p['transport'], 'NONE')

    def test_summary_without_message_pointer_stays_summary(self):
        p = self.packet([self.event('Summary only.', 'MATERIAL_REPLY', sources=['synthetic:note'])])
        self.assertEqual(p['fields']['wants']['provenance'], 'SUMMARY_POINTER')

    def test_unknown_subject_still_errors(self):
        with patch.object(handoff.idx,'build_index',return_value={'rows':[],'events':[]}):
            with self.assertRaises(handoff.idx.IndexError_):
                handoff.relationship_handoff(SUBJECT, paths={'root':ROOT})

    def test_no_email_projection(self):
        with self.assertRaises(handoff.idx.IndexError_):
            self.packet([self.event('Do not copy person@example.invalid', 'MATERIAL_REPLY')])

    def test_successor_can_read_packet_without_index_io(self):
        p = self.packet([])
        with patch.object(handoff.idx, 'build_index', side_effect=AssertionError('unexpected IO')):
            self.assertEqual(handoff.successor_reads_next_action(p), p['fields']['successor_next_action']['value'])


if __name__ == '__main__':
    unittest.main()
