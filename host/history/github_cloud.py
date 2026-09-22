"""Bounded GitHub history continuation on a hosted Commons runner.

Private raw JSON and cursors are read from and written to the private Commons
repository through the central publisher. Stdout contains counts/status only.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

import github_collect as collector

REPO = 'woahwhattheheck/commons-ship-enforcer'
PREFIX = 'history-review/2026-09-20/github/'
PUBLISHER = 'https://account-publisher.tjlabs-publisher.workers.dev/v1/publish'
TOKEN = os.environ.get('COMMONS_GITHUB_TOKEN', '')

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('redirect_refused')

OPENER = urllib.request.build_opener(NoRedirect())

def request(url, body=None):
    if not TOKEN:
        raise RuntimeError('commons_token_unbound')
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc not in ('api.github.com', 'account-publisher.tjlabs-publisher.workers.dev'):
        raise RuntimeError('unexpected_host')
    req = urllib.request.Request(url, method='GET' if body is None else 'POST',
        data=None if body is None else json.dumps(body, separators=(',', ':')).encode(),
        headers={'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json',
                 'Content-Type': 'application/json', 'User-Agent': 'Commons-GitHub-History/1.0'})
    try:
        with OPENER.open(req, timeout=30) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404 and body is None: return 404, None
        raise RuntimeError('provider_http_' + str(exc.code)) from None

def private_path(account, filename):
    return PREFIX + account + '/' + filename

def read_private(path):
    url = 'https://api.github.com/repos/' + REPO + '/contents/' + path + '?ref=main'
    _, item = request(url)
    if item is None: return None, None
    if item.get('type') != 'file' or not item.get('sha'):
        raise RuntimeError('private_file_invalid')
    return base64.b64decode(item['content']), item['sha']

def write_private(path, raw, old_sha=None):
    if len(raw) > 350_000:
        raise RuntimeError('private_file_too_large')
    op = 'github-history-' + hashlib.sha256(path.encode() + b'\n' + (old_sha or 'new').encode() + b'\n' + raw).hexdigest()
    payload = {'operation_id': op, 'operation': 'file.put', 'args': {
       'owner': 'woahwhattheheck', 'repo': 'commons-ship-enforcer', 'path': path,
       'message': 'Advance private GitHub history checkpoint',
       'content': base64.b64encode(raw).decode(), **({'sha': old_sha} if old_sha else {})}}
    status, result = request(PUBLISHER, payload)
    if status not in (200, 201) or result.get('allow') is not True or not result.get('receipt'):
        # Do not retry a held exact publication by changing content or carrier.
        raise RuntimeError('publisher_' + str(result.get('reason_code') or status))
    observed, _ = read_private(path)
    if observed != raw:
        raise RuntimeError('private_readback_differs')

def put_immutable_batch(account, path):
    """Land a new batch, or keep the first snapshot of an existing name.

    GitHub notification/search/issue pages are not byte-stable. A retry that
    re-collects an already-named batch must not overwrite it and must not
    abort cursor advancement — otherwise intake stays wedged on the same page.
    """
    raw = path.read_bytes()
    key = private_path(account, path.name)
    existing, _ = read_private(key)
    if existing is None:
        write_private(key, raw)
        return 'written'
    if existing != raw:
        path.write_bytes(existing)
        return 'kept'
    return 'matched'

def run(account):
    if account == collector.ACCOUNTS[1] and not os.environ.get('GH_TOKEN_SECONDARY'):
        return {'account': account, 'status': 'credential_unbound', 'private_readback': False}
    with tempfile.TemporaryDirectory(prefix='commons-github-history-') as temporary:
        root = Path(temporary)
        os.environ['JEV_HISTORY_ROOT'] = str(root)
        collector.ROOT = root / 'github'
        home = collector.ROOT / account
        home.mkdir(parents=True)
        snapshot, sha = read_private(private_path(account, 'checkpoint.json'))
        if snapshot:
            (home / 'checkpoint.json').write_bytes(snapshot)
        reader = collector.Reader(account, budget=3)
        result = reader.run()
        # A batch is immutable. Put every new batch before advancing the cursor.
        # An already-landed name keeps its first snapshot; live re-fetch bytes are discarded.
        files = sorted(home.glob('github-*.json'))
        written = kept = matched = 0
        for path in files:
            status = put_immutable_batch(account, path)
            if status == 'written':
                written += 1
            elif status == 'kept':
                kept += 1
            else:
                matched += 1
        cursor = (home / 'checkpoint.json').read_bytes()
        if cursor != snapshot:
            write_private(private_path(account, 'checkpoint.json'), cursor, sha)
        return {'account': account, 'requests': result['requests'], 'batches': len(files),
                'written': written, 'kept': kept, 'matched': matched,
                'queued_details': result['queued_details'], 'queued_repositories': result['queued_repositories'],
                'gaps': result['gaps'], 'private_readback': True}

def main():
    for account in collector.ACCOUNTS:
        try:
            print(json.dumps(run(account)), flush=True)
        except Exception as exc:
            print(json.dumps({'account': account, 'error': str(exc)}), flush=True)
            return 1
    return 0

if __name__ == '__main__': sys.exit(main())
