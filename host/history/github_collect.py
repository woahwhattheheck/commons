"""Read-only, resumable GitHub history intake for the owner's two accounts.

Outputs batches for work/jev-bounty-recovery/read_history.py. Never marks
notifications read, mutates GitHub, or prints credentials/message bodies.
"""
from __future__ import annotations

import argparse
import base64
from datetime import date, timedelta
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ACCOUNTS = ('woahwhattheheck', 'tokenjunkielabs')
ROOT = Path(os.environ.get('JEV_HISTORY_ROOT', str(Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'.local/share'))) / 'TJLabs/JevMailReview/2026-09-20'))) / 'github'
API = 'https://api.github.com'
TOKEN = re.compile(r'(?i)\b(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)[A-Za-z0-9_]{12,}\b|\bsk-proj-[A-Za-z0-9_-]{16,}\b')

def clean(value):
    if isinstance(value, str):
        return TOKEN.sub('[REDACTED_TOKEN]', value)
    if isinstance(value, list):
        return [clean(x) for x in value]
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k.lower() not in ('authorization', 'access_token', 'refresh_token')}
    return value

def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.pending')
    with temp.open('x', encoding='utf-8') as out:
        json.dump(clean(data), out, ensure_ascii=False, separators=(',', ':'))
        out.flush(); os.fsync(out.fileno())
    os.replace(temp, path)

def token_for(account):
    value=os.environ.get('GH_TOKEN_PRIMARY' if account==ACCOUNTS[0] else 'GH_TOKEN_SECONDARY')
    if value:return value
    executable=shutil.which('gh') or str(Path.home()/'AppData/Local/Programs/GitHub CLI/gh.exe')
    proc = subprocess.run([executable, 'auth', 'token', '--hostname', 'github.com', '--user', account],
                          capture_output=True, text=True, timeout=30, check=True)
    token = proc.stdout.strip()
    if not token:
        raise RuntimeError('shared GitHub credential unavailable for ' + account)
    return token

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('GitHub API redirect refused')

class Reader:
    def __init__(self, account, budget):
        self.account, self.token, self.budget = account, token_for(account), budget
        self.calls = 0
        self.home = ROOT / account
        self.state_path = self.home / 'checkpoint.json'
        self.state = json.loads(self.state_path.read_text(encoding='utf-8')) if self.state_path.exists() else {
            'schema': 'github-history-checkpoint-v1', 'account': account, 'roads': {},
            'details': [], 'detail_keys': [], 'repositories': [], 'repository_keys': [], 'gaps': []}
        self.opener = urllib.request.build_opener(NoRedirect())

    def save(self):
        atomic_json(self.state_path, self.state)

    def get(self, path, params=None, accept='application/vnd.github+json'):
        if self.calls >= self.budget:
            raise StopIteration('request budget reached')
        if path.startswith(API + '/'):
            url = path
        elif path.startswith('/'):
            url = API + path
        else:
            raise ValueError('Non-GitHub API path')
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != 'https' or parsed.netloc != 'api.github.com':
            raise ValueError('Non-GitHub API URL')
        if params:
            url += ('&' if parsed.query else '?') + urllib.parse.urlencode(params)
        request = urllib.request.Request(url, method='GET', headers={
            'Authorization': 'Bearer ' + self.token, 'Accept': accept,
            'User-Agent': 'TJLabs-JevHistory/1.0', 'X-GitHub-Api-Version': '2022-11-28'})
        self.calls += 1
        try:
            with self.opener.open(request, timeout=25) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
                if len(raw) > 8 * 1024 * 1024:
                    raise RuntimeError('GitHub page exceeds intake byte bound')
                body = json.loads(raw)
                headers = dict(response.headers)
        except urllib.error.HTTPError as exc:
            # Store only code and rate metadata, never provider prose or token.
            self.state['gaps'].append({'road': self.state.get('active_road'), 'status': exc.code,
                 'at': url.split('?')[0], 'rate_reset': exc.headers.get('X-RateLimit-Reset')})
            self.save()
            raise RuntimeError(f'GitHub read returned HTTP {exc.code}') from None
        links = {}
        for piece in headers.get('Link', '').split(','):
            match = re.search(r'<([^>]+)>;\s*rel="([^"]+)"', piece)
            if match:
                links[match[2]] = match[1]
        return body, links, url

    def emit(self, road, key, records, coverage):
        safe = re.sub(r'[^A-Za-z0-9_.-]', '-', key)[:100]
        path = self.home / f'github-{self.account}-{road}-{safe}.json'
        if not path.exists():
            atomic_json(path, {'source': 'github', 'account': self.account, 'road': road,
                 'coverage': coverage, 'records': records})
        return path

    def enqueue_detail(self, url, kind='subject'):
        if not url or not url.startswith(API + '/'): return
        if url in self.state['detail_keys']: return
        self.state['detail_keys'].append(url)
        self.state['details'].append({'url': url, 'kind': kind, 'next': url})

    @staticmethod
    def record(obj, kind, account, thread=None):
        who = (obj.get('user') or obj.get('author') or {}).get('login') if isinstance(obj, dict) else None
        body = obj.get('body') or obj.get('message') or obj.get('commit', {}).get('message') or ''
        title = obj.get('title') or obj.get('subject', {}).get('title') or ''
        return {'id': str(obj.get('id') or obj.get('sha') or obj.get('node_id') or ''),
                'thread_id': str(thread or obj.get('url') or obj.get('html_url') or ''),
                'date': obj.get('updated_at') or obj.get('submitted_at') or obj.get('created_at') or obj.get('commit', {}).get('author', {}).get('date'),
                'url': obj.get('html_url') or obj.get('url'), 'body': (title + '\n\n' + body).strip(),
                'metadata': {'kind': kind, 'account': account, 'author': who,
                   'state': obj.get('state'), 'number': obj.get('number'), 'type': obj.get('type')}}

    def simple_road(self, road, path, params, transform, per_page=100):
        slot = self.state['roads'].setdefault(road, {'next': path, 'pages': 0, 'complete': False})
        if slot['complete']: return None
        self.state['active_road'] = road
        query = params if slot['pages'] == 0 else None
        data, links, url = self.get(slot['next'], query)
        if not isinstance(data, list): raise ValueError('Expected GitHub list for ' + road)
        records = transform(data)
        out = self.emit(road, str(slot['pages'] + 1).zfill(5), records,
                        {'api_url': url, 'next': bool(links.get('next')), 'count': len(data)})
        slot['next'] = links.get('next')
        slot['pages'] += 1
        slot['complete'] = not bool(slot['next'])
        self.save()
        return out

    def notifications(self):
        def build(items):
            records = []
            for obj in items:
                subject = obj.get('subject') or {}
                url = subject.get('url')
                self.enqueue_detail(url, 'notification_subject')
                self.enqueue_detail(subject.get('latest_comment_url'), 'notification_latest_comment')
                records.append({'id': str(obj['id']), 'thread_id': url or str(obj['id']),
                   'date': obj.get('updated_at'), 'url': url,
                   'body': subject.get('title') or '',
                   'metadata': {'kind': 'notification', 'account': self.account,
                      'reason': obj.get('reason'), 'unread': obj.get('unread'),
                      'subject_type': subject.get('type'), 'repository': (obj.get('repository') or {}).get('full_name'),
                      'latest_comment_url': subject.get('latest_comment_url'),
                      'body_status': 'subject_only_pending_hydration'}})
            return records
        return self.simple_road('notifications', '/notifications',
                {'all': 'true', 'participating': 'false', 'per_page': 50}, build)

    def events(self):
        def build(items):
            return [{'id': str(x.get('id')), 'thread_id': str(x.get('repo', {}).get('name')),
                     'date': x.get('created_at'), 'url': None,
                     'body': json.dumps(clean({'type': x.get('type'), 'action': x.get('payload', {}).get('action'),
                           'repo': x.get('repo', {}).get('name')})),
                     'metadata': {'kind': 'event', 'account': self.account,
                           'event_type': x.get('type'), 'repo': x.get('repo', {}).get('name')}} for x in items]
        return self.simple_road('events', f'/users/{self.account}/events', {'per_page': 100}, build)

    def init_search(self, kind):
        road = 'search_' + kind
        if road in self.state['roads']: return
        self.state['active_road'] = road
        profile, _, _ = self.get('/users/' + self.account)
        first = profile['created_at'][:10]
        self.state['roads'][road] = {'jobs': [{'start': first, 'end': date.today().isoformat(),
                                              'page': 1}], 'pages': 0, 'complete': False}
        self.save()

    def search(self, kind):
        self.init_search(kind)
        road = 'search_' + kind
        slot = self.state['roads'][road]
        if not slot['jobs']:
            slot['complete'] = True; self.save(); return None
        self.state['active_road'] = road
        job = slot['jobs'][0]
        qualifier = 'type:pr' if kind == 'pulls' else 'type:issue'
        q = f'author:{self.account} {qualifier} created:{job["start"]}..{job["end"]}'
        data, links, url = self.get('/search/issues', {'q': q, 'per_page': 100, 'page': job['page']})
        total = data.get('total_count', 0)
        if total > 1000:
            start, end = date.fromisoformat(job['start']), date.fromisoformat(job['end'])
            if start == end:
                self.state['gaps'].append({'road': road, 'date': job['start'], 'reason': 'search_1000_cap'})
                slot['jobs'].pop(0); self.save(); return None
            middle = start + (end - start) // 2
            slot['jobs'][:1] = [{'start': start.isoformat(), 'end': middle.isoformat(), 'page': 1},
                                {'start': (middle + timedelta(days=1)).isoformat(), 'end': end.isoformat(), 'page': 1}]
            self.save(); return None
        items = data.get('items') or []
        for obj in items:
            self.enqueue_detail(obj.get('url'), kind)
        records = [self.record(x, kind, self.account) for x in items]
        key = f'{job["start"]}-{job["end"]}-p{job["page"]}'
        out = self.emit(road, key, records, {'query': q, 'page': job['page'],
                       'total_count': total, 'incomplete_results': data.get('incomplete_results'),
                       'next': bool(links.get('next'))})
        if data.get('incomplete_results'):
            self.state['gaps'].append({'road': road, 'range': key, 'reason': 'incomplete_results'})
        if links.get('next'): job['page'] += 1
        else: slot['jobs'].pop(0)
        slot['pages'] += 1
        slot['complete'] = not bool(slot['jobs'])
        self.save()
        return out

    def repositories(self):
        def build(items):
            for obj in items:
                name = obj.get('full_name')
                if name and name not in self.state['repository_keys']:
                    self.state['repository_keys'].append(name)
                    self.state['repositories'].append({'name': name, 'next': f'/repos/{name}/commits?author={self.account}&per_page=100'})
            return [self.record({**x, 'body': x.get('description')}, 'repository', self.account) for x in items]
        return self.simple_road('repositories', '/user/repos',
              {'affiliation': 'owner,collaborator,organization_member', 'per_page': 100}, build)

    def commits(self):
        if not self.state['repositories']: return None
        job = self.state['repositories'][0]
        self.state['active_road'] = 'commits'
        try:
            data, links, url = self.get(job['next'])
        except RuntimeError:
            # Some listed repositories refuse commit listing; record the gap and continue.
            self.state['repositories'].pop(0); self.save(); return None
        if not isinstance(data, list): raise ValueError('Expected commit list')
        page = job.get('page', 1)
        out = self.emit('commits', hashlib.sha256((job['name'] + str(page)).encode()).hexdigest()[:18],
              [self.record(x, 'commit', self.account, job['name']) for x in data],
              {'repository': job['name'], 'page': page, 'next': bool(links.get('next')), 'api_url': url})
        if links.get('next'):
            job['next'] = links['next']; job['page'] = page + 1
        else: self.state['repositories'].pop(0)
        self.save(); return out

    def details(self):
        if not self.state['details']: return None
        job = self.state['details'][0]
        self.state['active_road'] = 'details'
        try:
            obj, links, url = self.get(job['next'], accept='application/vnd.github+json')
        except RuntimeError:
            self.state['details'].pop(0); self.save(); return None
        objs = obj if isinstance(obj, list) else [obj]
        records = [self.record(x, job['kind'], self.account, job['url']) for x in objs if isinstance(x, dict)]
        key = hashlib.sha256((job['url'] + str(job.get('page', 1))).encode()).hexdigest()[:20]
        out = self.emit('details', key, records, {'api_url': url, 'kind': job['kind'], 'next': bool(links.get('next'))})
        if job['kind'] in ('pulls', 'issues', 'notification_subject') and isinstance(obj, dict):
            endpoint = obj.get('url') or job['url']
            match = re.search(r'/repos/([^/]+/[^/]+)/(issues|pulls)/(\d+)$', endpoint)
            if match:
                repo, _, number = match.groups()
                for suffix, name in ((f'issues/{number}/comments', 'issue_comment'),
                                     (f'issues/{number}/timeline', 'timeline_event'),
                                     (f'pulls/{number}/reviews', 'review'),
                                     (f'pulls/{number}/comments', 'review_comment')):
                    self.enqueue_detail(f'{API}/repos/{repo}/{suffix}?per_page=100', name)
        if links.get('next'):
            job['next'] = links['next']; job['page'] = job.get('page', 1) + 1
        else: self.state['details'].pop(0)
        self.save(); return out

    def run(self):
        paths = []
        order = [self.notifications, lambda: self.search('pulls'), lambda: self.search('issues'),
                 self.repositories, self.events, self.details, self.commits]
        while self.calls < self.budget:
            progressed = False
            for action in order:
                if self.calls >= self.budget: break
                before = self.calls
                try:
                    path = action()
                except StopIteration:
                    # An action may need several reads; the budget is a normal
                    # checkpoint boundary, even when reached inside that action.
                    self.save()
                    return self.summary(paths)
                if path: paths.append(str(path))
                if self.calls > before: progressed = True
            if not progressed: break
        self.save()
        return self.summary(paths)

    def summary(self, paths):
        return {'account': self.account, 'requests': self.calls, 'files': len(paths),
                'road_pages': {k: v.get('pages') for k, v in self.state['roads'].items()},
                'queued_details': len(self.state['details']), 'queued_repositories': len(self.state['repositories']),
                'gaps': len(self.state['gaps']), 'output': str(self.home)}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--account', choices=ACCOUNTS, action='append')
    parser.add_argument('--max-requests', type=int, default=12)
    args = parser.parse_args()
    if args.max_requests < 1 or args.max_requests > 200: parser.error('max-requests must be 1..200')
    for account in args.account or ACCOUNTS:
        try:
            print(json.dumps(Reader(account, args.max_requests).run()), flush=True)
        except Exception as exc:
            print(json.dumps({'account': account, 'error': type(exc).__name__ + ': ' + str(exc)}), flush=True)
            return 1
    return 0

if __name__ == '__main__': sys.exit(main())
