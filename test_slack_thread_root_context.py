"""Synthetic root-resolution and actual collector/budget regressions; no Slack I/O."""
from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import types
import unittest

from integrations.command_center.collectors import LiveCollectors
from integrations.command_center.slack_threads import (
    SlackReadFailure, read_channel, read_thread_context, resolve_thread_root,
)

CHANNEL = 'CDEMO'
ROOT = '1700000000.000001'
FIRST = '1700000010.000002'
CHILD = '1700000020.000003'
OTHER = '1699999900.000004'


def parent(count=2):
    return {'ts': ROOT, 'reply_count': count,
            **({'latest_reply': CHILD} if count else {}), 'text': 'Synthetic work order'}


def child(**fields):
    return {'ts': CHILD, 'subtype': 'thread_broadcast', 'text': 'Synthetic receipt', **fields}


def replies():
    return [parent(), {'ts': FIRST, 'thread_ts': ROOT, 'text': 'Synthetic prior work'},
            child(thread_ts=ROOT)]


def page(rows, cursor='', **fields):
    return {'ok': True, 'messages': rows, 'response_metadata': {'next_cursor': cursor}, **fields}


def permalink(stamp=CHILD, root=ROOT, channel=CHANNEL):
    return ('https://fixture.slack.com/archives/' + channel + '/p' + stamp.replace('.', '')
            + '?thread_ts=' + root + '&cid=' + channel)


class Provider:
    def __init__(self, pages):
        self.pages, self.calls = copy.deepcopy(pages), []

    def slack(self, method, params):
        if method not in ('conversations.history', 'conversations.replies'):
            raise AssertionError('Unexpected provider write')
        self.calls.append((method, copy.deepcopy(params)))
        result = self.pages.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class RootResolutionTests(unittest.TestCase):
    def test_explicit_thread_id(self):
        result = resolve_thread_root(child(thread_ts=ROOT), CHANNEL)
        self.assertEqual((result['state'], result['thread_ts']), ('RESOLVED', ROOT))

    def test_nested_broadcast_root(self):
        result = resolve_thread_root(child(root={'ts': ROOT}), CHANNEL)
        self.assertEqual(result['thread_ts'], ROOT)
        self.assertEqual(result['sources'], ['root.ts'])

    def test_same_message_permalink(self):
        result = resolve_thread_root(child(permalink=permalink()), CHANNEL)
        self.assertEqual(result['thread_ts'], ROOT)
        self.assertEqual(result['sources'], ['permalink.thread_ts'])

    def test_agreeing_metadata_is_retained(self):
        result = resolve_thread_root(child(thread_ts=ROOT, root={'ts': ROOT}, permalink=permalink()), CHANNEL)
        self.assertEqual(result['state'], 'RESOLVED')
        self.assertEqual(len(result['sources']), 3)

    def test_conflicting_metadata_is_not_first_wins(self):
        for fields in ({'thread_ts': ROOT, 'root': {'ts': OTHER}},
                       {'thread_ts': ROOT, 'permalink': permalink(root=OTHER)}):
            with self.subTest(fields=fields):
                result = resolve_thread_root(child(**fields), CHANNEL)
                self.assertEqual(result['state'], 'CONFLICT')
                self.assertIsNone(result['thread_ts'])

    def test_missing_root_cannot_be_self_broadcast(self):
        result = resolve_thread_root(child(), CHANNEL)
        self.assertEqual(result['state'], 'UNKNOWN')
        self.assertIsNone(result['thread_ts'])

    def test_root_reply_count_is_an_explicit_anchor_including_zero(self):
        for count in (0, 2):
            result = resolve_thread_root(parent(count), CHANNEL)
            self.assertEqual(result['thread_ts'], ROOT)
            self.assertEqual(result['sources'], ['reply_count'])

    def test_broadcast_reply_count_is_not_a_parent_anchor(self):
        self.assertEqual(resolve_thread_root(child(reply_count=0), CHANNEL)['state'], 'UNKNOWN')

    def test_message_text_is_never_root_metadata(self):
        result = resolve_thread_root({'ts': CHILD, 'text': 'Parent ' + ROOT + ' ' + permalink()}, CHANNEL)
        self.assertIsNone(result['thread_ts'])

    def test_bare_permalink_does_not_prove_parenthood(self):
        result = resolve_thread_root(child(permalink=permalink().split('?')[0]), CHANNEL)
        self.assertEqual(result['state'], 'UNKNOWN')

    def test_permalink_must_bind_message_and_channel(self):
        for link in (permalink(stamp=FIRST), permalink(channel='COTHER'),
                     permalink().replace('cid=CDEMO', 'cid=COTHER')):
            with self.subTest(link=link):
                self.assertEqual(resolve_thread_root(child(permalink=link), CHANNEL)['state'], 'CONFLICT')

    def test_duplicate_or_empty_permalink_root_is_rejected(self):
        for link in (permalink() + '&thread_ts=' + ROOT,
                     permalink().replace('thread_ts=' + ROOT, 'thread_ts=')):
            with self.subTest(link=link):
                self.assertEqual(resolve_thread_root(child(permalink=link), CHANNEL)['state'], 'CONFLICT')

    def test_malformed_permalink_never_gets_fetched(self):
        for link in (None, 1, [], 'http://fixture.slack.com/archives/CDEMO/p1700000020000003',
                     permalink().replace('fixture.slack.com', 'fixture.example.com'),
                     permalink().replace('fixture.slack.com', 'fixture.slack.com:443'),
                     permalink() + '#fragment', permalink() + '\n',
                     'https://[malformed', 'x' * 4097):
            with self.subTest(link=link):
                self.assertEqual(resolve_thread_root(child(permalink=link), CHANNEL)['state'], 'CONFLICT')

    def test_future_and_self_root_are_not_broadcast_parents(self):
        for root in (CHILD, '1700000099.000001'):
            self.assertEqual(resolve_thread_root(child(thread_ts=root), CHANNEL)['state'], 'CONFLICT')

    def test_nested_root_cannot_itself_point_to_a_third_root(self):
        result = resolve_thread_root(child(root={'ts': ROOT, 'thread_ts': OTHER}), CHANNEL)
        self.assertEqual(result['state'], 'CONFLICT')

    def test_malformed_nested_metadata_cannot_disappear(self):
        for root in (None, [], {}, {'ts': True}, {'ts': 'nan'}):
            self.assertEqual(resolve_thread_root(child(root=root), CHANNEL)['state'], 'CONFLICT')

    def test_invalid_message_identity_is_unknown(self):
        for target in (None, [], {'ts': True}, {'ts': 1.0}, {'ts': 'nan'}):
            self.assertEqual(resolve_thread_root(target, CHANNEL)['reason'], 'message_identity_invalid')

    def test_resolver_does_not_mutate_provider_observation(self):
        target = child(root={'ts': ROOT}, permalink=permalink())
        before = copy.deepcopy(target)
        resolve_thread_root(target, CHANNEL)
        self.assertEqual(target, before)


class ContextReadTests(unittest.TestCase):
    def read(self, target, pages, **options):
        provider = Provider(pages)
        result = read_thread_context(provider.slack, CHANNEL, target, **options)
        return result, provider

    def test_direct_read_uses_root_not_broadcast_child(self):
        (rows, meta, complete), provider = self.read(child(permalink=permalink()), [page(replies())])
        self.assertTrue(complete)
        self.assertEqual(len(rows), 3)
        self.assertEqual(provider.calls, [('conversations.replies', {'channel': CHANNEL, 'ts': ROOT, 'limit': 100})])
        self.assertEqual(meta['observed_replies'], 2)

    def test_unknown_or_conflicting_target_spends_no_requests(self):
        for target in (child(), child(thread_ts=ROOT, root={'ts': OTHER}), {'ts': CHILD, 'text': 'No thread messages'}):
            (_, meta, complete), provider = self.read(target, [])
            self.assertFalse(complete)
            self.assertEqual(provider.calls, [])
            self.assertEqual(meta['pages_read'], 0)

    def test_empty_child_reply_echo_cannot_prove_root_context(self):
        (_, meta, complete), _ = self.read(child(thread_ts=ROOT), [page([child(reply_count=0)])])
        self.assertFalse(complete)
        self.assertEqual(meta['error']['code'], 'slack_thread_identity')

    def test_zero_count_after_known_child_is_incomplete(self):
        (_, meta, complete), _ = self.read(child(thread_ts=ROOT), [page([parent(0)])])
        self.assertFalse(complete)
        self.assertEqual(meta['reason'], 'reply_evidence_mismatch')

    def test_count_agreement_does_not_replace_selected_reply_identity(self):
        (_, _, complete), _ = self.read(child(thread_ts=ROOT), [page([
            {'ts': ROOT, 'reply_count': 1, 'latest_reply': FIRST},
            {'ts': FIRST, 'thread_ts': ROOT}])])
        self.assertFalse(complete)

    def test_multiple_pages_deduplicate_root_and_replies(self):
        items = replies()
        (rows, meta, complete), provider = self.read(child(thread_ts=ROOT),
            [page(items[:2], 'next'), page(items[1:])])
        self.assertTrue(complete)
        self.assertEqual(len(rows), 3)
        self.assertEqual(meta['pages_read'], 2)
        self.assertEqual(provider.calls[1][1]['cursor'], 'next')

    def test_page_limit_retains_continuation_not_a_claim_clearance(self):
        (_, meta, complete), _ = self.read(child(thread_ts=ROOT), [page(replies(), 'next')], max_pages=1)
        self.assertFalse(complete)
        self.assertEqual((meta['reason'], meta['next_cursor']), ('page_limit', 'next'))

    def test_no_cursor_with_has_more_is_incomplete(self):
        (_, meta, complete), _ = self.read(parent(), [page(replies(), has_more=True)])
        self.assertFalse(complete)
        self.assertEqual(meta['reason'], 'cursor_missing')

    def test_provider_limited_snapshot_remains_incomplete(self):
        (_, meta, complete), _ = self.read(parent(), [page(replies(), is_limited=True)])
        self.assertFalse(complete)
        self.assertEqual(meta['reason'], 'history_limited')

    def test_cursor_cycle_is_bounded(self):
        (_, meta, complete), provider = self.read(parent(), [page(replies(), 'same'), page(replies(), 'same')])
        self.assertFalse(complete)
        self.assertEqual(meta['reason'], 'cursor_cycle')
        self.assertEqual(len(provider.calls), 2)

    def test_changed_claim_text_between_pages_invalidates_snapshot(self):
        items = replies()
        revised = copy.deepcopy(items)
        revised[1]['text'] = 'Synthetic withdrawal'
        (_, meta, complete), _ = self.read(parent(), [page(items, 'next'), page(revised)])
        self.assertFalse(complete)
        self.assertEqual(meta['reason'], 'thread_evidence_changed')

    def test_changed_edit_stamp_between_pages_invalidates_snapshot(self):
        items = replies()
        revised = copy.deepcopy(items)
        revised[1]['edited'] = {'ts': '1700000080.000001'}
        (_, meta, complete), _ = self.read(parent(), [page(items, 'next'), page(revised)])
        self.assertFalse(complete)
        self.assertEqual(meta['reason'], 'thread_evidence_changed')

    def test_wrong_thread_does_not_poison_prior_valid_page(self):
        wrong = {'ts': '1700000040.000001', 'thread_ts': OTHER}
        (rows, meta, complete), _ = self.read(parent(), [page(replies(), 'next'), page([wrong])])
        self.assertFalse(complete)
        self.assertEqual(len(rows), 3)
        self.assertEqual(meta['error']['code'], 'slack_thread_identity')

    def test_transport_failure_retains_rows_and_sanitizes_metadata(self):
        (rows, meta, complete), _ = self.read(parent(), [page(replies(), 'next'), TimeoutError('private marker')])
        self.assertFalse(complete)
        self.assertEqual(len(rows), 3)
        self.assertNotIn('private marker', json.dumps(meta))
        self.assertEqual(meta['error']['code'], 'slack_read_failed')

    def test_resolved_empty_root_is_valid_observation_not_authority(self):
        (_, meta, complete), _ = self.read(parent(0), [page([parent(0)])])
        self.assertTrue(complete)
        self.assertIs(meta['claim_authority'], False)
        self.assertIs(meta['provider_write_authority'], False)

    def test_bounds_fail_before_provider_call(self):
        for options in ({'page_size': True}, {'page_size': 0}, {'page_size': 101},
                        {'max_pages': 0}, {'max_pages': 11}):
            provider = Provider([])
            with self.subTest(options=options), self.assertRaises(ValueError):
                read_thread_context(provider.slack, CHANNEL, parent(), **options)
            self.assertEqual(provider.calls, [])

    def test_wrong_channel_and_malformed_target_fail_before_read(self):
        provider = Provider([])
        with self.assertRaises(ValueError):
            read_thread_context(provider.slack, 'not-a-channel', parent())
        with self.assertRaises(SlackReadFailure):
            read_thread_context(provider.slack, CHANNEL, {'ts': ROOT, 'reply_count': True})
        self.assertEqual(provider.calls, [])


class ChannelCoverageTests(unittest.TestCase):
    def read(self, pages, **options):
        provider = Provider(pages)
        result = read_channel(provider.slack, CHANNEL, page_size=100, max_pages=2, **options)
        return result, provider

    def test_missing_broadcast_root_is_not_complete_history(self):
        (rows, meta, complete), provider = self.read([page([child()])], max_threads=1)
        self.assertFalse(complete)
        self.assertTrue(meta['history_complete'])
        self.assertEqual(meta['unresolved_thread_roots_count'], 1)
        self.assertEqual(meta['unresolved_thread_roots'][0]['state'], 'UNKNOWN')
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(provider.calls), 1)

    def test_nested_root_expands_without_mutating_provider_payload(self):
        original = child(root={'ts': ROOT})
        provider = Provider([page([original]), page(replies())])
        saved = provider.pages[0]['messages'][0]
        (_, meta, complete) = read_channel(provider.slack, CHANNEL, page_size=100, max_pages=1, max_threads=1)
        self.assertTrue(complete)
        self.assertEqual(provider.calls[1][1]['ts'], ROOT)
        self.assertEqual(saved, original)
        self.assertEqual(meta['unresolved_thread_roots_count'], 0)

    def test_known_broadcast_cannot_disappear_behind_zero_count(self):
        (_, meta, complete), _ = self.read([page([child(thread_ts=ROOT)]), page([parent(0)])], max_threads=1)
        self.assertFalse(complete)
        self.assertEqual(meta['thread_coverage'][0]['reason'], 'reply_evidence_mismatch')

    def test_conflicting_root_is_retained_not_silently_routed(self):
        (_, meta, complete), provider = self.read([page([child(thread_ts=ROOT, root={'ts': OTHER})])], max_threads=1)
        self.assertFalse(complete)
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(meta['unresolved_thread_roots'][0]['state'], 'CONFLICT')

    def test_normal_message_keeps_bounded_history_behavior(self):
        (_, meta, complete), _ = self.read([page([{'ts': ROOT, 'text': 'ordinary'}])])
        self.assertTrue(complete)
        self.assertEqual(meta['threads_read_count'], 0)

    def test_unexpanded_known_thread_stays_pending(self):
        (_, meta, complete), _ = self.read([page([parent()])])
        self.assertFalse(complete)
        self.assertEqual(meta['threads_pending_count'], 1)

    def test_unresolved_metadata_is_bounded_and_has_no_message_body(self):
        items = [child(ts=str(1700000000+i), text='private marker') for i in range(101)]
        (_, meta, complete), _ = self.read([page(items[:100], 'next'), page(items[100:])])
        self.assertFalse(complete)
        self.assertEqual(meta['unresolved_thread_roots_count'], 101)
        self.assertEqual(len(meta['unresolved_thread_roots']), 100)
        self.assertTrue(meta['unresolved_thread_roots_truncated'])
        self.assertNotIn('private marker', json.dumps(meta))


class ActualCollectorBatchTests(unittest.TestCase):
    """Execute real LiveCollectors._slack and RequestBudget, not a substitute mapper.

    Does not claim execution of WorkstreamStore ingestion or UI rendering.
    """
    def collector(self, pages):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        provider = Provider(pages)
        store = types.SimpleNamespace(state_dir=directory.name)
        collector = LiveCollectors(store, {'github': {'enabled': False},
            'slack': {'max_threads_per_channel': 1, 'workspace_url': 'https://fixture.slack.com'}},
            equipment=provider, clock=lambda: '2026-09-19T14:00:00Z')
        return collector, provider

    def test_unknown_root_persists_as_null_not_child_and_degrades_source(self):
        collector, provider = self.collector([page([child()])])
        result = collector._slack({'id': CHANNEL})
        ref = result['items'][0]['refs']
        self.assertIsNone(ref['thread_ts'])
        self.assertIsNone(ref['reply_count'])
        self.assertEqual(ref['root_resolution'], 'UNKNOWN')
        self.assertEqual(result['source']['status'], 'degraded')
        self.assertFalse(result['source']['coverage']['complete'])
        self.assertIsNone(result['source']['error'])
        self.assertEqual(collector.request_budget.metrics()['observed_attempts'], 1)
        self.assertEqual(len(provider.calls), 1)

    def test_resolved_broadcast_ref_and_real_budget_survive_batch(self):
        collector, provider = self.collector([page([child(root={'ts': ROOT})]), page(replies())])
        result = collector._slack({'id': CHANNEL})
        ref = next(item['refs'] for item in result['items'] if item['refs']['message_ts'] == CHILD)
        self.assertEqual(ref['thread_ts'], ROOT)
        self.assertEqual(ref['root_resolution'], 'RESOLVED')
        self.assertTrue(result['source']['coverage']['complete'])
        self.assertEqual(collector.request_budget.metrics()['observed_attempts'], 2)
        self.assertEqual(len(provider.calls), 2)

    def test_rate_limit_remains_actual_budgeted_read_failure(self):
        collector, provider = self.collector([page([child(thread_ts=ROOT)]),
                                            {'ok': False, 'error': 'ratelimited', 'retry_after': 60}])
        result = collector._slack({'id': CHANNEL})
        self.assertFalse(result['source']['coverage']['complete'])
        self.assertEqual(result['source']['metadata']['thread_coverage'][0]['error']['code'], 'slack_rate_limited')
        self.assertEqual(collector.request_budget.metrics()['rate_limit_responses'], 1)
        self.assertEqual(len(provider.calls), 2)

    def test_actual_batch_digest_includes_resolution_and_degraded_state(self):
        collector, _ = self.collector([page([child()])])
        result = collector._slack({'id': CHANNEL})
        payload = {key: value for key, value in result.items() if key != 'operation_id'}
        expected = 'collect:' + hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()
        self.assertEqual(result['operation_id'], expected)


class ReplayTests(unittest.TestCase):
    def test_replay_executes_consistent_synthetic_cases(self):
        from integrations.command_center.slack_thread_root_replay import run_replay
        result = run_replay()
        self.assertIs(result['synthetic_only'], True)
        self.assertFalse(result['missing_root']['complete'])
        self.assertTrue(result['resolved_root']['complete'])
        self.assertFalse(result['contradictory_zero_count']['complete'])
        self.assertEqual(result['resolved_root']['calls'][0]['payload']['ts'], ROOT)
        self.assertIn(FIRST, result['resolved_root']['observed_message_ids'])
        self.assertEqual(result, run_replay())


if __name__ == '__main__':
    unittest.main()
