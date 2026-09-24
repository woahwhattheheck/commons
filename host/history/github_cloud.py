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
import time
import unicodedata
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

def error_payload(exc):
    try:
        payload = json.load(exc)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}

def request(url, body=None):
    if not TOKEN:
        raise RuntimeError('commons_token_unbound')
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.netloc not in ('api.github.com', 'account-publisher.tjlabs-publisher.workers.dev'):
        raise RuntimeError('unexpected_host')
    publisher = parsed.netloc.endswith('workers.dev')
    headers = {'Authorization': 'Bearer ' + TOKEN,
               'Accept': 'application/json' if publisher else 'application/vnd.github+json',
               'Content-Type': 'application/json', 'User-Agent': 'Commons-GitHub-History/1.0'}
    attempts = 1 if body is not None else 4
    last = None
    for attempt in range(attempts):
        req = urllib.request.Request(url, method='GET' if body is None else 'POST',
            data=None if body is None else json.dumps(body, separators=(',', ':')).encode(),
            headers=headers)
        try:
            with OPENER.open(req, timeout=30) as response:
                return response.status, json.load(response)
        except urllib.error.HTTPError as exc:
            last = exc
            payload = error_payload(exc)
            if exc.code == 404 and body is None:
                return 404, None
            if body is not None:
                # Return the held publication as-is. write_private names the
                # publisher reason and retries only RESOURCE_BUSY.
                return exc.code, payload
            retryable = (
                exc.code in (500, 502, 503, 504) or
                (exc.code in (403, 429) and (
                    exc.headers.get('X-RateLimit-Remaining') == '0' or
                    bool(exc.headers.get('Retry-After')))))
            if retryable and attempt + 1 < attempts:
                try:
                    delay = float(exc.headers.get('Retry-After') or 0)
                except ValueError:
                    delay = 0
                time.sleep(max(1, min(delay or 2 ** attempt, 20)))
                continue
            raise RuntimeError('provider_http_' + str(exc.code) + '_github') from None
    raise RuntimeError('provider_http_' + str(getattr(last, 'code', 0)) + '_github')

MAX_CHECKPOINT_BYTES = 240_000
DETAIL_SHARD_SCHEMA = 'github-history-detail-shard-v1'
HOLD_CODES = {'self_fault_admission', 'invalid_candidate', 'agent_caused_damage', 'authored_attribution'}

class PublisherHold(RuntimeError):
    def __init__(self, code, path):
        super().__init__('publisher_' + code)
        self.code = code
        self.path = path

def _fallback_identity_terms(value):
    terms = ('Codex', '\u0043laude', 'Opus', 'Fable', 'Astra', 'Sol', '\u0047rok')
    normalized = ''.join(character for character in unicodedata.normalize('NFKC', value)
                         if unicodedata.category(character) != 'Cf').casefold()
    found = []
    for term in terms:
        needle = term.casefold()
        offset = 0
        while True:
            start = normalized.find(needle, offset)
            if start < 0:
                break
            end = start + len(needle)
            before = normalized[start - 1] if start else ''
            after = normalized[end] if end < len(normalized) else ''
            before_ok = unicodedata.category((before or ' ')[:1])[0] not in {'L', 'M', 'N'}
            after_ok = unicodedata.category((after or ' ')[:1])[0] not in {'L', 'M', 'N'}
            if before_ok and after_ok:
                found.append(term)
                break
            offset = start + 1
    return tuple(found)

def identity_terms_in(value):
    return _fallback_identity_terms(value)

def publisher_failure(result, status, path):
    code = str((result or {}).get('reason_code') or (result or {}).get('error') or status)
    if code in HOLD_CODES:
        raise PublisherHold(code, path)
    raise RuntimeError('publisher_' + code)

def dumps(data):
    return json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode()

def pair_details(details):
    """Return [kind, url] pairs when every row is the redundant {url,kind,next} shape."""
    if not isinstance(details, list):
        return None
    pairs = []
    for item in details:
        if isinstance(item, dict):
            if set(item) != {'url', 'kind', 'next'}:
                return None
            url, kind, nxt = item['url'], item['kind'], item['next']
            if nxt != url or not isinstance(url, str) or not isinstance(kind, str):
                return None
            pairs.append([kind, url])
        elif (isinstance(item, list) and len(item) == 2 and
              all(isinstance(part, str) for part in item)):
            pairs.append([item[0], item[1]])
        else:
            return None
    return pairs

def compact_document(data):
    if not isinstance(data, dict):
        return None
    pairs = pair_details(data.get('details', []))
    if pairs is None:
        return None
    urls = [url for _, url in pairs]
    if data.get('detail_keys', urls) != urls:
        return None
    compact = dict(data)
    compact['details'] = pairs
    compact.pop('detail_keys', None)
    compact.pop('detail_shards', None)
    return compact

def plan_checkpoint_files(raw):
    """Fit a checkpoint under the publisher accept ceiling without dropping queue URLs.

    The expanded document stores every URL three times. Pair rows drop that
    repetition. If the compact document is still over the ceiling, detail pairs
    move into sibling files and the checkpoint keeps only their names.
    """
    data = json.loads(raw)
    compact = compact_document(data)
    if compact is None:
        if len(raw) > MAX_CHECKPOINT_BYTES:
            raise RuntimeError('checkpoint_over_publisher_ceiling')
        return [('checkpoint.json', raw if isinstance(raw, bytes) else raw.encode())]
    blob = dumps(compact)
    if len(blob) <= MAX_CHECKPOINT_BYTES:
        return [('checkpoint.json', blob)]
    files = []
    current = []

    def flush():
        if not current:
            return
        name = 'details-%04d.json' % len(files)
        shard = dumps({'schema': DETAIL_SHARD_SCHEMA, 'details': list(current)})
        if len(shard) > MAX_CHECKPOINT_BYTES:
            raise RuntimeError('checkpoint_over_publisher_ceiling')
        files.append((name, shard))

    for pair in compact['details']:
        trial = dumps({'schema': DETAIL_SHARD_SCHEMA, 'details': current + [pair]})
        if current and len(trial) > MAX_CHECKPOINT_BYTES:
            flush()
            current = [pair]
        else:
            current.append(pair)
    flush()
    if any(len(shard) > MAX_CHECKPOINT_BYTES for _, shard in files):
        raise RuntimeError('checkpoint_over_publisher_ceiling')
    head = dict(compact)
    head['details'] = []
    head['detail_shards'] = [name for name, _ in files]
    head_raw = dumps(head)
    if len(head_raw) > MAX_CHECKPOINT_BYTES:
        raise RuntimeError('checkpoint_over_publisher_ceiling')
    return files + [('checkpoint.json', head_raw)]

def expand_checkpoint(raw, read_shard):
    """Restore the collector's {url,kind,next} rows and detail_keys list."""
    data = json.loads(raw)
    prior = {}
    shards = data.get('detail_shards')
    if shards:
        if data.get('details') not in ([], None) or not isinstance(shards, list):
            raise RuntimeError('checkpoint_shard_invalid')
        pairs = []
        for name in shards:
            if not isinstance(name, str) or name != Path(name).name or not name.endswith('.json'):
                raise RuntimeError('checkpoint_shard_invalid')
            loaded = read_shard(name)
            if not loaded or loaded[0] is None:
                raise RuntimeError('checkpoint_shard_missing')
            sraw, ssha = loaded
            shard = json.loads(sraw)
            part = shard.get('details') if shard.get('schema') == DETAIL_SHARD_SCHEMA else None
            if not isinstance(part, list):
                raise RuntimeError('checkpoint_shard_invalid')
            for item in part:
                if not (isinstance(item, list) and len(item) == 2 and
                        all(isinstance(piece, str) for piece in item)):
                    raise RuntimeError('checkpoint_shard_invalid')
                pairs.append(item)
            prior[name] = (sraw, ssha)
        data.pop('detail_shards', None)
        data['details'] = [{'url': url, 'kind': kind, 'next': url} for kind, url in pairs]
        data['detail_keys'] = [url for _, url in pairs]
        return dumps(data), prior
    pairs = pair_details(data.get('details', []))
    if pairs is not None and data.get('details') and isinstance(data['details'][0], list):
        urls = [url for _, url in pairs]
        if 'detail_keys' in data and data['detail_keys'] != urls:
            raise RuntimeError('checkpoint_detail_keys_mismatch')
        data['details'] = [{'url': url, 'kind': kind, 'next': url} for kind, url in pairs]
        data['detail_keys'] = urls
        return dumps(data), prior
    body = raw if isinstance(raw, bytes) else raw.encode()
    return body, prior

def hold_gap(batch_raw, code):
    """Remember a held page by URL only. Never copy the rejected record body."""
    batch = json.loads(batch_raw)
    coverage = batch.get('coverage') if isinstance(batch, dict) else None
    at = coverage.get('api_url') if isinstance(coverage, dict) else None
    return {'road': batch.get('road') if isinstance(batch, dict) else None,
            'at': at, 'reason': 'publisher_hold', 'code': code}

def apply_holds(checkpoint_raw, gaps):
    state = json.loads(checkpoint_raw)
    if not isinstance(state, dict):
        raise RuntimeError('checkpoint_invalid')
    current = state.get('gaps')
    if not isinstance(current, list):
        current = []
    for gap in gaps:
        if gap not in current:
            current.append(gap)
    state['gaps'] = current
    return dumps(state)

def publish_checkpoint(account, expanded, prior_raw, prior_sha, prior_shards):
    planned = plan_checkpoint_files(expanded)
    for name, blob in planned:
        if name == 'checkpoint.json':
            continue
        path = private_path(account, name)
        old = prior_shards.get(name)
        if not old:
            existing, existing_sha = read_private(path)
            if existing is not None:
                old = (existing, existing_sha)
        if old and old[0] == blob:
            continue
        write_private(path, blob, old[1] if old else None)
    checkpoint = dict(planned)['checkpoint.json']
    if prior_raw is not None and checkpoint == prior_raw:
        return
    write_private(private_path(account, 'checkpoint.json'), checkpoint, prior_sha)

def read_account_checkpoint(account):
    raw, sha = read_private(private_path(account, 'checkpoint.json'))
    if raw is None:
        return None, None, None, {}
    def read_shard(name):
        return read_private(private_path(account, name))
    expanded, prior = expand_checkpoint(raw, read_shard)
    return expanded, raw, sha, prior


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
    status = result = None
    for attempt in range(8):
        status, result = request(PUBLISHER, payload)
        if status == 409 and (result or {}).get('error') == 'RESOURCE_BUSY':
            time.sleep(min(2 ** attempt, 30))
            continue
        break
    if status not in (200, 201) or not result or result.get('allow') is not True or not result.get('receipt'):
        # Do not retry a held exact publication by changing content or carrier.
        publisher_failure(result, status, path)
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
        snapshot, prior_raw, sha, prior_shards = read_account_checkpoint(account)
        if snapshot:
            (home / 'checkpoint.json').write_bytes(snapshot)
        reader = collector.Reader(account, budget=3)
        result = reader.run()
        # A batch is immutable. Put every new batch before advancing the cursor.
        # An already-landed name keeps its first snapshot; live re-fetch bytes are discarded.
        files = sorted(home.glob('github-*.json'))
        written = kept = matched = 0
        holds = []
        for path in files:
            raw = path.read_bytes()
            if identity_terms_in(raw.decode('utf-8', 'replace')):
                holds.append(hold_gap(raw, 'blocked_identity_term'))
                continue
            try:
                status = put_immutable_batch(account, path)
            except PublisherHold as exc:
                holds.append(hold_gap(raw, exc.code))
                continue
            if status == 'written':
                written += 1
            elif status == 'kept':
                kept += 1
            else:
                matched += 1
        cursor = (home / 'checkpoint.json').read_bytes()
        if holds:
            cursor = apply_holds(cursor, holds)
        publish_checkpoint(account, cursor, prior_raw, sha, prior_shards)
        return {'account': account, 'requests': result['requests'], 'batches': len(files),
                'written': written, 'kept': kept, 'matched': matched, 'held': len(holds),
                'queued_details': result['queued_details'], 'queued_repositories': result['queued_repositories'],
                'gaps': result['gaps'] + len(holds), 'private_readback': True}

def main():
    for account in collector.ACCOUNTS:
        try:
            print(json.dumps(run(account)), flush=True)
        except Exception as exc:
            print(json.dumps({'account': account, 'error': str(exc)}), flush=True)
            return 1
    return 0

if __name__ == '__main__': sys.exit(main())
