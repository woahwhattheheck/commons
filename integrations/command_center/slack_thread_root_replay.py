"""Run a synthetic, offline replay of the broadcast-root collision. No credentials."""
from __future__ import annotations

import copy
import json

from .slack_threads import read_channel, read_thread_context

ROOT = '1700000000.000001'
EARLIER = '1700000010.000002'
CHILD = '1700000020.000003'
CHANNEL = 'CDEMO'


class ReplayProvider:
    def __init__(self, pages):
        self.pages = copy.deepcopy(pages)
        self.calls = []

    def read(self, method, payload):
        if method not in ('conversations.history', 'conversations.replies'):
            raise ValueError('Replay permits read callbacks only.')
        self.calls.append({'method': method, 'payload': dict(payload)})
        return self.pages.pop(0)


def page(messages):
    return {'ok': True, 'messages': messages, 'response_metadata': {'next_cursor': ''}}


def run_replay():
    broadcast = {'ts': CHILD, 'subtype': 'thread_broadcast', 'text': 'Synthetic receipt'}
    missing = ReplayProvider([page([broadcast])])
    _, missing_meta, missing_complete = read_channel(missing.read, CHANNEL,
        page_size=100, max_pages=1, max_threads=1)
    target = {**broadcast, 'permalink': 'https://fixture.slack.com/archives/CDEMO/p'
              + CHILD.replace('.', '') + '?thread_ts=' + ROOT + '&cid=CDEMO'}
    root = {'ts': ROOT, 'reply_count': 2, 'latest_reply': CHILD, 'text': 'Synthetic order'}
    resolved = ReplayProvider([page([root,
        {'ts': EARLIER, 'thread_ts': ROOT, 'text': 'Synthetic earlier work announcement'},
        {**broadcast, 'thread_ts': ROOT}])])
    rows, resolved_meta, resolved_complete = read_thread_context(resolved.read, CHANNEL, target)
    contradictory = ReplayProvider([page([{**broadcast, 'thread_ts': ROOT}]),
                                    page([{'ts': ROOT, 'reply_count': 0}])])
    _, contradictory_meta, contradictory_complete = read_channel(contradictory.read, CHANNEL,
        page_size=100, max_pages=1, max_threads=1)
    return {
        'schema': 'commons.slack-thread-root-replay.v1', 'synthetic_only': True,
        'missing_root': {'complete': missing_complete, 'coverage': missing_meta, 'calls': missing.calls},
        'resolved_root': {'complete': resolved_complete, 'coverage': resolved_meta,
                          'observed_message_ids': sorted(row['ts'] for row in rows), 'calls': resolved.calls},
        'contradictory_zero_count': {'complete': contradictory_complete,
                                   'coverage': contradictory_meta, 'calls': contradictory.calls},
        'limits': ['No live Slack calls or deployed connector change.',
                   'Complete means observed coverage, not proof of no claimant or atomic ownership.'],
    }


def main():
    print(json.dumps(run_replay(), sort_keys=True, indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
