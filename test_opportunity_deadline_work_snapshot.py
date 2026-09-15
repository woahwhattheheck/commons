"""Recovery regressions and native command-center export contracts (#13799)."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_opportunity_deadline_command import AS_OF, deadline, opportunity, packet, policy, source
from revenue.opportunity_deadline_command import engine
from revenue.opportunity_deadline_command.work_snapshot import build_work_snapshot, main as snapshot_main


class SnapshotTests(unittest.TestCase):
    def build(self, raw=None, ref='portfolio-a', now=AS_OF):
        with patch('revenue.opportunity_deadline_command.work_snapshot._system_now', return_value=now):
            return build_work_snapshot(raw or packet(), policy(), portfolio_ref=ref)

    def test_existing_ingest_top_level_shape(self):
        snap = self.build()
        self.assertEqual(set(snap), {'operation_id', 'source', 'items'})
        self.assertFalse(snap['source']['coverage']['complete'])
        self.assertEqual(snap['source']['scope']['portfolio_ref'], 'portfolio-a')

    def test_clock_is_process_owned(self):
        with self.assertRaises(TypeError):
            build_work_snapshot(packet(), policy(), portfolio_ref='x', as_of=AS_OF)

    def test_deterministic_operation_binds_payload(self):
        a = self.build()
        self.assertEqual(a, self.build())
        core = {k: v for k, v in a.items() if k != 'operation_id'}
        self.assertEqual(a['operation_id'], 'deadline-ingest:' + engine.digest(core))
        self.assertNotEqual(a['operation_id'], self.build(ref='portfolio-b')['operation_id'])

    def test_clock_change_is_distinct_refresh_not_retry(self):
        self.assertNotEqual(self.build()['operation_id'], self.build(now='2026-09-13T12:00:01Z')['operation_id'])

    def test_missing_date_is_attention_without_invented_due_at(self):
        item = self.build(packet(opportunity(deadlines=[])))['items'][0]
        self.assertTrue(item['needs_attention'])
        self.assertIsNone(item['due_at'])
        self.assertEqual(item['status'], 'SOURCE_RECOVERY_REQUIRED')

    def test_no_work_activity_revenue_or_dispatch_invented(self):
        item = self.build()['items'][0]
        self.assertFalse(item['countable'])
        self.assertTrue(item['control'])
        self.assertEqual(item['actions'], [])
        self.assertFalse(item['metadata']['external_action_authorized'])
        for field in ['amount', 'currency', 'created_at', 'updated_at', 'activity_observed_at']:
            self.assertNotIn(field, item)
        self.assertNotIn('activity_as_of', self.build()['source'])

    def test_terminal_is_retained_not_active(self):
        item = self.build(packet(opportunity(route_state='NO_BID')))['items'][0]
        self.assertFalse(item['needs_attention'])
        self.assertEqual(item['status'], 'TERMINAL_NO_BID')

    def test_source_capture_and_evaluation_are_distinct(self):
        snap = self.build()
        self.assertEqual(snap['source']['observed_at'], AS_OF)
        self.assertEqual(snap['items'][0]['metadata']['declared_controlling_source']['captured_at'], '2026-09-13T10:00:00Z')
        self.assertIn('not a buyer-source refresh', snap['source']['metadata']['observed_at_means'])

    def test_thousand_rows_do_not_expand_source_metadata(self):
        raw = packet(*(opportunity(f'fleet-{i:04d}') for i in range(1000)))
        snap = self.build(raw)
        self.assertEqual(len(snap['items']), 1000)
        self.assertLess(len(json.dumps(snap['source'])), 1500)

    def test_freshness_budget_never_exceeds_five_minutes(self):
        self.assertLessEqual(self.build()['source']['stale_after_seconds'], 300)

    def test_freshness_budget_expires_before_deadline(self):
        snap = self.build(packet(opportunity(deadlines=[deadline(at='2026-09-13T12:00:10Z')])))
        self.assertEqual(snap['source']['stale_after_seconds'], 9)
        self.assertIn('2026-09-13T12:00:10Z', snap['items'][0]['next_action'])

    def test_freshness_budget_covers_priority_boundary(self):
        snap = self.build(packet(opportunity(deadlines=[deadline(at='2026-09-14T12:00:31Z')])))
        self.assertEqual(snap['source']['stale_after_seconds'], 30)

    def test_freshness_budget_covers_source_age_boundary(self):
        snap = self.build(packet(opportunity(sources=[source(captured_at='2026-09-06T12:00:11Z')])))
        self.assertEqual(snap['source']['stale_after_seconds'], 11)

    def test_freshness_budget_covers_opening_boundary(self):
        snap = self.build(packet(opportunity(deadlines=[deadline(opens_at='2026-09-13T12:00:01Z')])))
        self.assertEqual(snap['source']['stale_after_seconds'], 0)

    def test_opaque_portfolio_ref_only(self):
        for ref in ['', '../bad', 'person@example.com', 'a' * 65, True]:
            with self.subTest(ref=ref), self.assertRaises(engine.EvidenceError):
                self.build(ref=ref)

    def test_cli_publishes_once_without_dispatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'input.json').write_bytes(engine.canonical_bytes(packet()))
            (root / 'policy.json').write_bytes(engine.canonical_bytes(policy()))
            args = ['--input', str(root / 'input.json'), '--policy', str(root / 'policy.json'),
                    '--portfolio-ref', 'unit-test', '--snapshot-out', str(root / 'out.json')]
            with patch('revenue.opportunity_deadline_command.work_snapshot._system_now', return_value=AS_OF):
                self.assertEqual(snapshot_main(args), 0)
                first = (root / 'out.json').read_bytes()
                self.assertEqual(snapshot_main(args), 2)
                self.assertEqual((root / 'out.json').read_bytes(), first)


class NativeStoreTests(unittest.TestCase):
    def setUp(self):
        from integrations.command_center.workstreams import WorkstreamStore
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = WorkstreamStore(self.tmp.name)

    def build(self, *opps, now=AS_OF):
        with patch('revenue.opportunity_deadline_command.work_snapshot._system_now', return_value=now):
            return build_work_snapshot(packet(*opps), policy(), portfolio_ref='native-test')

    def test_native_ingest_and_control_counts(self):
        payload = self.build(opportunity(), opportunity('opp-2', deadlines=[]))
        receipt = self.store.ingest(payload)
        self.assertEqual(receipt['status'], 'ingested')
        self.assertEqual(receipt['received'], 2)
        state = self.store.state()
        self.assertEqual(state['counts']['work_items'], 0)
        self.assertEqual(state['counts']['control_rows'], 2)
        self.assertFalse(state['dispatch']['implemented'])
        self.assertFalse(state['sources'][0]['coverage']['complete'])

    def test_exact_retry_replays_without_duplicate_rows(self):
        payload = self.build()
        first = self.store.ingest(payload)
        again = self.store.ingest(copy.deepcopy(payload))
        self.assertFalse(first['replayed'])
        self.assertTrue(again['replayed'])
        self.assertEqual(len(self.store.state()['items']), 1)

    def test_reused_operation_with_changed_payload_is_rejected(self):
        from integrations.command_center.schema import CoreError
        payload = self.build()
        self.store.ingest(payload)
        payload['items'][0]['priority'] = 'NORMAL'
        with self.assertRaises(CoreError) as exc:
            self.store.ingest(payload)
        self.assertEqual(exc.exception.status, 409)

    def test_partial_refresh_retains_unselected_opportunities(self):
        self.store.ingest(self.build(opportunity(), opportunity('opp-2')))
        receipt = self.store.ingest(self.build(opportunity(), now='2026-09-13T12:01:00Z'))
        self.assertEqual(receipt['removed'], 0)
        self.assertEqual(receipt['retained'], 1)
        self.assertEqual({x['id'] for x in self.store.state()['items']}, {'opp-1', 'opp-2'})

    def test_owner_direction_survives_source_refresh(self):
        payload = self.build()
        self.store.ingest(payload)
        self.store.update_work({'operation_id': 'owner-direction-1',
                                'source_id': payload['source']['id'], 'item_id': 'opp-1',
                                'next_action': 'Owner-selected next step', 'priority': 'urgent'})
        self.store.ingest(self.build(now='2026-09-13T12:01:00Z'))
        item = self.store.state()['items'][0]
        self.assertEqual(item['owner_work']['next_action'], 'Owner-selected next step')
        self.assertEqual(item['owner_work']['priority'], 'urgent')

    def test_scope_collision_does_not_repurpose_existing_source(self):
        from integrations.command_center.schema import CoreError
        payload = self.build()
        self.store.ingest(payload)
        changed = self.build(now='2026-09-13T12:01:00Z')
        changed['source']['scope'] = {'different': 'scope'}
        with self.assertRaises(CoreError) as exc:
            self.store.ingest(changed)
        self.assertEqual(exc.exception.status, 409)


if __name__ == '__main__':
    unittest.main()

