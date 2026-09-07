import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from host.inbox_slack_relay import (
    Delivery, Event, Providers, RelayError, RunLock, State, clean,
    github_events, github_pages, gmail_events, mail_body, run,
)

CONFIG = {
    'github_login': 'example', 'gmail_address': 'work@example.com',
    'slack_workspace': 'example.slack.com', 'github_channel': 'CGH',
    'gmail_channel': 'CMAIL', 'health_channel': 'CHEALTH',
    'health_thread': '1.1', 'coordination_repository': 'example/commons',
    'min_post_interval': 0, 'work_sender_domains': ['sponsor.example'],
}

class FakeSlack:
    def __init__(self):
        self.messages = []
        self.calls = []
        self.fail_after_effect = False
    def __call__(self, method, data):
        self.calls.append((method, dict(data)))
        if method == 'auth.test':
            return {'ok': True, 'url': 'https://example.slack.com/'}
        if method in {'conversations.history', 'conversations.replies'}:
            rows = [m for m in self.messages if m['channel'] == data['channel']]
            if method.endswith('replies'):
                rows = [m for m in rows if m.get('thread_ts') == data['ts'] or m['ts'] == data['ts']]
            else:
                rows = [m for m in rows if not m.get('thread_ts')]
            return {'ok': True, 'messages': rows, 'has_more': False}
        if method == 'chat.update':
            for m in self.messages:
                if m['ts'] == data['ts']:
                    m.update(data)
            return {'ok': True, 'ts': data['ts']}
        if method == 'chat.postMessage':
            ts = f'{100 + len(self.messages)}.000001'
            self.messages.append({**data, 'ts': ts})
            if self.fail_after_effect and data.get('thread_ts'):
                self.fail_after_effect = False
                raise RelayError('timeout', uncertain=True)
            return {'ok': True, 'ts': ts}
        raise AssertionError(method)


def notice(n=1, private=False, title='Fix parser'):
    return {'id': str(n), 'updated_at': '2026-09-07T01:00:00Z', 'reason': 'review_requested',
            'repository': {'full_name': 'example/app', 'private': private},
            'subject': {'title': title, 'type': 'PullRequest',
                        'url': f'https://api.github.com/repos/example/app/pulls/{n}'}}

class FakeGithub:
    def __init__(self, notices=None):
        self.notices = notices if notices is not None else [notice()]
        self.calls = []
        self.deleted = False
    def __call__(self, path):
        self.calls.append(path)
        if path == 'user':
            return {'login': 'example'}
        if path.startswith('notifications?'):
            return self.notices
        if '/pulls/2' in path and self.deleted:
            raise RelayError('http_404')
        if '/reviews?' in path:
            return [{'id': 21, 'body': 'Fix the error path. Outside-diff nitpick matters.',
                     'state': 'CHANGES_REQUESTED', 'user': {'login': 'maintainer'},
                     'submitted_at': '2026-09-07T01:00:00Z'}]
        if '/pulls/' in path and '/comments?' in path:
            return [{'id': 31, 'body': 'Check None before accessing value', 'path': 'app.py',
                     'line': 8, 'diff_hunk': '@@ -1 +1 @@\n+ value.x', 'user': {'login': 'maintainer'}}]
        if '/issues/' in path and '/comments?' in path:
            return [{'id': 41, 'body': 'Please include a regression test', 'user': {'login': 'maintainer'}}]
        if '/pulls/' in path:
            return {'number': int(path.rsplit('/',1)[1]), 'body': 'Functional parser patch', 'state': 'open',
                    'html_url': 'https://github.com/example/app/pull/1', 'user': {'login': 'author'}}
        raise AssertionError(path)


def encoded(text):
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip('=')


def message(mid='a1', title='Review deadline', sender='Person <work@sponsor.example>', body='Please respond Monday.', labels=None):
    return {'id': mid, 'threadId': 'thread1', 'labelIds': labels or ['INBOX'],
            'payload': {'mimeType': 'text/plain', 'headers': [
                {'name': 'Subject', 'value': title}, {'name': 'From', 'value': sender}],
                'body': {'data': encoded(body)}}}

class FakeGmail:
    def __init__(self, messages=None):
        self.messages = messages if messages is not None else [message()]
        self.calls = []
    def __call__(self, resource, params=None):
        self.calls.append((resource, params))
        if resource == 'profile':
            return {'emailAddress': 'work@example.com'}
        if resource == 'messages':
            return {'messages': [{'id': m['id']} for m in self.messages]}
        return next(m for m in self.messages if resource == 'messages/' + m['id'])

class RelayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/'ledger.sqlite3'
        self.state = State(self.path)
        self.slack = FakeSlack()
        self.delivery = Delivery(self.state, self.slack, min_interval=0)
        self.event = Event('github', 'example/app/1', 'review:1', 'Fix parser', 'Please test None.', 'https://github.com/example/app/pull/1')
    def tearDown(self):
        self.state.close()
        self.temp.cleanup()
    def test_readable_body_not_only_link(self):
        self.delivery.deliver(self.event, 'CGH')
        self.assertIn('Please test None.', self.slack.messages[1]['text'])
        self.assertFalse(self.slack.messages[1]['mrkdwn'])
        self.assertFalse(self.slack.messages[1]['unfurl_links'])
    def test_repeat_is_noop(self):
        self.assertEqual(self.delivery.deliver(self.event, 'CGH'), 1)
        self.assertEqual(self.delivery.deliver(self.event, 'CGH'), 0)
        self.assertEqual(len(self.slack.messages), 2)
    def test_edited_comment_new_part_same_thread(self):
        self.delivery.deliver(self.event, 'CGH')
        updated = Event(**{**self.event.__dict__, 'body': 'Now test empty input too.'})
        self.delivery.deliver(updated, 'CGH')
        self.assertEqual(len(self.slack.messages), 3)
        self.assertEqual(self.slack.messages[1]['thread_ts'], self.slack.messages[2]['thread_ts'])
    def test_large_body_complete(self):
        body = 'abc' * 7000
        event = Event(**{**self.event.__dict__, 'body': body})
        self.delivery.deliver(event, 'CGH')
        chunks = [m['text'].split('):\n', 1)[1].rsplit('\n\nrelay.part=',1)[0] for m in self.slack.messages[1:]]
        self.assertEqual(''.join(chunks), body)
    def test_ambiguous_write_recovers_without_duplicate(self):
        self.slack.fail_after_effect = True
        with self.assertRaises(RelayError): self.delivery.deliver(self.event, 'CGH')
        self.assertEqual(self.delivery.deliver(self.event, 'CGH'), 0)
        self.assertEqual(len(self.slack.messages), 2)
    def test_lost_ledger_recovers_slack_markers(self):
        self.delivery.deliver(self.event, 'CGH')
        self.state.db.execute('DELETE FROM items')
        self.state.db.execute('DELETE FROM parts')
        self.state.db.commit()
        self.assertEqual(self.delivery.deliver(self.event, 'CGH'), 0)
        self.assertEqual(len(self.slack.messages), 2)
    def test_page_limit_never_assumes_absent(self):
        provider = lambda method, data: {'ok': True, 'messages': [], 'has_more': True, 'response_metadata': {'next_cursor': 'more'}}
        with self.assertRaisesRegex(RelayError, 'page_limit'):
            Delivery(self.state, provider, max_pages=2).find('C', 'marker', 0)
    def test_bounded_delivery_replays(self):
        d = Delivery(self.state, self.slack, max_posts=1, min_interval=0)
        with self.assertRaisesRegex(RelayError, 'budget'): d.deliver(self.event, 'CGH')
        self.assertEqual(self.delivery.deliver(self.event, 'CGH'), 1)
        self.assertEqual(len(self.slack.messages), 2)
    def test_source_contents_not_stored_in_ledger(self):
        self.delivery.deliver(self.event, 'CGH')
        self.assertNotIn(b'Please test None', self.path.read_bytes())
    def test_provider_account_mismatch(self):
        with self.assertRaisesRegex(RelayError, 'account_mismatch'):
            github_events(lambda path: {'login':'other'}, CONFIG, '2026-09-01T00:00:00Z')
    def test_all_three_github_conversation_surfaces(self):
        events, info = github_events(FakeGithub(), CONFIG, '2026-09-01T00:00:00Z')
        self.assertEqual(len(events), 4)
        self.assertIn('Outside-diff', events[2].body)
        self.assertIn('app.py', events[3].body)
        self.assertIn('ACTION REQUIRED', events[2].action)
    def test_private_notification_never_fetches_body(self):
        gh = FakeGithub([notice(private=True)])
        events, info = github_events(gh, CONFIG, '2026-09-01T00:00:00Z')
        self.assertFalse(events)
        self.assertEqual(info['private_omitted'], 1)
        self.assertFalse(any(p.startswith('repos/') for p in gh.calls))
    def test_deleted_subject_does_not_hide_valid_subject(self):
        gh = FakeGithub([notice(2), notice(1)])
        gh.deleted = True
        events, info = github_events(gh, CONFIG, '2026-09-01T00:00:00Z')
        self.assertEqual(len(events), 4)
        self.assertEqual(info['source_items_pending'], 1)
    def test_unchanged_notification_does_not_fetch_comments(self):
        gh = FakeGithub()
        events, info = github_events(gh, CONFIG, '2026-09-01T00:00:00Z', lambda key:'1')
        self.assertFalse(events)
        self.assertEqual(info['unchanged'], 1)
        self.assertEqual(len(gh.calls), 3)
    def test_github_pagination_is_complete_or_error(self):
        with self.assertRaisesRegex(RelayError, 'page_limit'):
            github_pages(lambda _: [{}]*100, 'notifications?all=true', max_pages=2)
    def test_mail_auth_and_promotions_and_unknown_are_not_published(self):
        gmail = FakeGmail([message('a','Your sign-in code',body='123456'),
                           message('b','Review sale',labels=['CATEGORY_PROMOTIONS']),
                           message('c','Private lunch',sender='friend@example.net'),
                           message('d')])
        events, info = gmail_events(gmail, CONFIG, '')
        self.assertEqual([e.event_id for e in events], ['d'])
        self.assertEqual(info['private_or_auth_omitted'], 1)
        self.assertEqual(info['unclassified_pending'], 1)
    def test_email_to_github_duplicate_suppressed(self):
        events, info = gmail_events(FakeGmail([message(sender='notifications@github.com')]),CONFIG,'')
        self.assertFalse(events)
        self.assertEqual(info['github_mail_deduped'],1)
    def test_mail_prefers_plain_alternative(self):
        payload={'mimeType':'multipart/alternative','parts':[
            {'mimeType':'text/plain','body':{'data':encoded('plain body')}},
            {'mimeType':'text/html','body':{'data':encoded('<p>duplicate</p>')}}]}
        self.assertEqual(mail_body(payload), 'plain body')
    def test_html_does_not_fetch_images_or_keep_script(self):
        payload={'mimeType':'text/html','body':{'data':encoded('<head>hidden</head><p>Deadline</p><script>evil()</script><img src="https://tracker.example/pixel">')}}
        self.assertEqual(mail_body(payload).strip(), 'Deadline')
    def test_tokens_mentions_and_codes_scrubbed(self):
        value=clean('xoxb-123-SECRET <@U123> @channel\nYour verification code is 123456\nhttps://site.test/path?token=secret')
        for forbidden in ['xoxb-','<@','@channel','123456','token=secret']:
            self.assertNotIn(forbidden,value)
    def test_slack_read_adapter_uses_get(self):
        with patch.dict(os.environ, {'SLACK_BOT_TOKEN':'test-only'}, clear=True):
            p=Providers()
        with patch('host.inbox_slack_relay.request_json',return_value={'ok':True}) as req:
            p.slack('conversations.history', {'channel':'C','limit':100})
        self.assertNotIn('data', req.call_args.kwargs)
        self.assertIn('channel=C', req.call_args.args[0])
    def test_run_is_read_only_and_heartbeat_updates(self):
        class P: pass
        p=P(); p.github=FakeGithub(); p.gmail=FakeGmail(); p.slack=self.slack
        first=run(CONFIG,self.state,p)
        second=run(CONFIG,self.state,p)
        self.assertEqual(first['status'],'LIVE')
        self.assertEqual(second['posted_parts'],0)
        self.assertEqual(second['sources']['github']['unchanged'],1)
        self.assertEqual(sum(1 for m in self.slack.messages if m['channel']=='CHEALTH'),1)
        self.assertFalse(any('mark' in c[0] or 'modify' in c[0] for c in p.gmail.calls))
    def test_source_failure_does_not_hide_other_source(self):
        class P: pass
        p=P(); p.github=lambda _: (_ for _ in ()).throw(RelayError('github_denied'))
        p.gmail=FakeGmail(); p.slack=self.slack
        result=run(CONFIG,self.state,p)
        self.assertEqual(result['status'],'DEGRADED')
        self.assertEqual(result['last_success']['github'],'never')
        self.assertTrue(any(m['channel']=='CMAIL' for m in self.slack.messages))
    def test_overlapping_jobs_fail_without_running(self):
        with RunLock(self.path):
            with self.assertRaisesRegex(RelayError,'another_poll'):
                with RunLock(self.path): pass

if __name__ == '__main__':
    unittest.main()
