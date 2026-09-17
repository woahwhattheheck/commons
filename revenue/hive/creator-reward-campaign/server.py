"""Creator reward campaign desk. Python standard library; local handoff only; no provider calls."""
import argparse
import csv
import hashlib
import io
import json
import re
import sqlite3
import uuid
import zipfile
from contextlib import closing
from datetime import date, datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
PLATFORMS = ('TIKTOK', 'INSTAGRAM', 'YOUTUBE', 'X', 'OTHER')
RULE_KINDS = ('FIXED_PER_APPROVED', 'PER_THOUSAND_VIEWS')
CAMPAIGN_STATES = ('DRAFT', 'OPEN', 'CLOSED')
REVIEWABLE = 'SUBMITTED'
ADMIN_FEE_BPS = 500  # proposed 5% administration fee; PROPOSED_NOT_ACCEPTED
HANDOFF_MODE = 'LOCAL_HANDOFF_ONLY_NOT_PAID'
MAX_MINOR = 10**12
HANDLE = re.compile(r'[A-Za-z0-9][A-Za-z0-9._-]{0,63}')
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9 ._-]{0,119}')
ASSET_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}\.(md|txt)')
# Opaque-reference grammar for payout route and settlement references. It is a
# shape filter owned by this module, not a detector: it refuses obvious contact,
# URL/host, phone, SSN, card/account/IBAN digit shapes, credential keywords,
# well-known secret prefixes and token-shaped runs, so those values never reach
# SQLite, state, handoff records or exports. Operators supply references issued
# by their payout system of record.
OPAQUE_REF = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,79}')
REF_FORBIDDEN_TEXT = re.compile(
    r'(?:@|://|(?<![A-Za-z0-9])www\.|(?<![A-Za-z0-9])(?:mailto|tel|sms|http|https|ftp):|'
    r'(?<![A-Za-z0-9])(?:password|passwd|pwd|secret|api[_-]?key|apikey|token|bearer|auth|oauth|otp|cvv|cvc|pin|'
    r'iban|swift|bic|routing|aba|card|pan|ssn|sin|ein|tin|tax[_-]?id)(?![A-Za-z]))', re.I)
REF_SECRET_PREFIX = re.compile(
    r'(?<![A-Za-z0-9])(?:(?:sk|pk|rk)[_-](?:live|test)[_-]|whsec[_-]|ghp_|gho_|ghu_|ghs_|github_pat_|xox[abpr]-|'
    r'AKIA[0-9A-Z]{12,}|ASIA[0-9A-Z]{12,}|ya29\.|eyJ[A-Za-z0-9_-]{10,}|sq0[a-z]{3}-|SG\.[A-Za-z0-9_-]{10,}|glpat-|npm_)', re.I)
REF_HOST_SHAPE = re.compile(r'[A-Za-z0-9-]+\.[A-Za-z]{2,24}(?:$|[/:.])')
# Phone, SSN and EIN shapes with every separator the identifier grammar admits.
REF_PHONE_OR_SSN_SHAPE = re.compile(r'(?<!\d)(?:\d{3}[-.:/]\d{3}[-.:/]\d{4}|\d{3}[-.:/]\d{2}[-.:/]\d{4}|\d{2}[-.:/]\d{7})(?!\d)')
REF_CARD_GROUP_SHAPE = re.compile(r'(?<!\d)\d{4}(?:[-.:/]\d{4}){2,4}(?!\d)')
REF_DIGIT_ONLY_MINIMUM = 9  # a value with no letters and this many digits is a number, not a reference
OPERATION_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}')
METRIC_KEYS = ('views', 'likes', 'comments', 'shares', 'saves')
REF_DIGIT_RUN = re.compile(r'\d{13,}')
REF_DIGIT_TOKEN = re.compile(r'(?<![A-Za-z0-9])\d{9,}(?![A-Za-z0-9])')
REF_IBAN_SHAPE = re.compile(r'(?<![A-Za-z0-9])[A-Za-z]{2}\d{2}[A-Za-z0-9]{11,30}(?![A-Za-z0-9])')
REF_TOKEN_SHAPE = re.compile(r'[A-Za-z0-9]{32,}')


class DeskError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


def text(value, name, maximum=100000):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise DeskError(f'{name} must be nonempty text (maximum {maximum} characters)')
    return value


def integer(value, name, minimum=0, maximum=MAX_MINOR):
    if type(value) is not int or not minimum <= value <= maximum:
        raise DeskError(f'{name} must be an integer from {minimum} to {maximum}')
    return value


def boolean(value, name):
    if type(value) is not bool:
        raise DeskError(f'{name} must be true or false')
    return value


def day(value, name):
    if not isinstance(value, str):
        raise DeskError(f'{name} must be a YYYY-MM-DD date')
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise DeskError(f'{name} must be a YYYY-MM-DD date') from exc
    if parsed.isoformat() != value:
        raise DeskError(f'{name} must be a canonical YYYY-MM-DD date')
    return value


def numeric_identity_shape(value):
    """True when a value carries a phone, SSN, EIN, card, account or IBAN digit shape under any admitted separator."""
    return bool(REF_PHONE_OR_SSN_SHAPE.search(value) or REF_CARD_GROUP_SHAPE.search(value) or REF_DIGIT_RUN.search(value)
                or REF_DIGIT_TOKEN.search(value) or REF_IBAN_SHAPE.search(value)
                or (sum(ch.isdigit() for ch in value) >= REF_DIGIT_ONLY_MINIMUM and not any(ch.isalpha() for ch in value)))


def opaque_ref(value, name):
    """Validate an opaque reference: ASCII identifier grammar minus contact, URL, account, card and secret shapes."""
    reference = text(value, name, 80)
    if not OPAQUE_REF.fullmatch(reference):
        raise DeskError(f'{name} must be an opaque reference of up to 80 ASCII letters, digits, dots, underscores, colons, slashes or hyphens')
    if (REF_FORBIDDEN_TEXT.search(reference) or REF_SECRET_PREFIX.search(reference) or REF_HOST_SHAPE.search(reference)
            or REF_TOKEN_SHAPE.search(reference) or numeric_identity_shape(reference)):
        raise DeskError(f'{name} must be an opaque reference: no email, link, host, phone, account, card, IBAN, credential or token shapes')
    return reference


def operation_key(value):
    """Validate the client idempotency key and return the digest under which it is retained."""
    key = text(value, 'operation_id', 200)
    if not OPERATION_ID.fullmatch(key):
        raise DeskError('operation_id must be an identifier of up to 200 ASCII letters, digits, dots, underscores, colons, slashes or hyphens')
    return hashlib.sha256(key.encode('utf-8')).hexdigest()


def metrics_block(value):
    """Owner-entered metrics: a fixed allow-list of non-negative integer counts, nothing else."""
    if not isinstance(value, dict):
        raise DeskError('metrics must be an object')
    if set(value) - set(METRIC_KEYS):
        raise DeskError(f'metrics accepts only {list(METRIC_KEYS)}')
    return {key: integer(value[key], f'metrics.{key}', 0) for key in METRIC_KEYS if key in value}


def encoded(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise DeskError('Payload must contain finite JSON values') from exc


def now():
    return datetime.now(timezone.utc).isoformat()


def normalize_url(value):
    """Return the canonical public content URL (scheme, host, path only); it is the only URL form the desk retains.

    Userinfo is refused; query strings and fragments (where signed or tokenized links carry their
    secrets) are dropped before storage, so the duplicate key and the retained URL are the same value.
    """
    raw = text(value, 'url', 2000)
    parts = urlsplit(raw.strip())
    if parts.scheme.lower() not in ('http', 'https') or not parts.netloc or '@' in parts.netloc:
        raise DeskError('url must be an http(s) content link with a host and no credentials')
    host = parts.hostname or ''
    if not host or any(ord(ch) < 0x21 for ch in host):
        raise DeskError('url host is invalid')
    path = parts.path.rstrip('/') or '/'
    return f'{parts.scheme.lower()}://{host.lower()}{path}'


def reward_rule(data):
    if not isinstance(data, dict):
        raise DeskError('rule must be an object')
    kind = data.get('kind')
    if kind not in RULE_KINDS:
        raise DeskError(f'rule.kind must be one of {list(RULE_KINDS)}')
    rule = {'kind': kind, 'allow_partial': boolean(data.get('allow_partial', False), 'rule.allow_partial')}
    if kind == 'FIXED_PER_APPROVED':
        rule['amount_minor'] = integer(data.get('amount_minor'), 'rule.amount_minor', 1)
        allowed = {'kind', 'allow_partial', 'amount_minor'}
    else:
        rule['rate_minor_per_thousand'] = integer(data.get('rate_minor_per_thousand'), 'rule.rate_minor_per_thousand', 1)
        rule['cap_minor'] = integer(data.get('cap_minor'), 'rule.cap_minor', 1)
        rule['minimum_views'] = integer(data.get('minimum_views', 0), 'rule.minimum_views', 0)
        allowed = {'kind', 'allow_partial', 'rate_minor_per_thousand', 'cap_minor', 'minimum_views'}
    if set(data) - allowed:
        raise DeskError(f'rule has unknown fields {sorted(set(data) - allowed)}')
    return rule


def eligibility(data):
    if not isinstance(data, dict):
        raise DeskError('eligibility must be an object')
    platforms = data.get('platforms')
    if not isinstance(platforms, list) or not platforms or any(p not in PLATFORMS for p in platforms) or len(set(platforms)) != len(platforms):
        raise DeskError(f'eligibility.platforms must list distinct values from {list(PLATFORMS)}')
    rules = {
        'platforms': sorted(platforms),
        'disclosure_tag': text(data.get('disclosure_tag', '#ad'), 'eligibility.disclosure_tag', 40),
        'requires_disclosure': boolean(data.get('requires_disclosure', True), 'eligibility.requires_disclosure'),
        'requires_rights_acceptance': boolean(data.get('requires_rights_acceptance', True), 'eligibility.requires_rights_acceptance'),
        'window_start': day(data.get('window_start'), 'eligibility.window_start'),
        'window_end': day(data.get('window_end'), 'eligibility.window_end'),
    }
    if rules['window_end'] < rules['window_start']:
        raise DeskError('eligibility.window_end precedes window_start')
    allowed = {'platforms', 'disclosure_tag', 'requires_disclosure', 'requires_rights_acceptance', 'window_start', 'window_end'}
    if set(data) - allowed:
        raise DeskError(f'eligibility has unknown fields {sorted(set(data) - allowed)}')
    return rules


def compute_reward(rule, metrics):
    """Deterministic integer reward from the campaign rule and owner-entered metrics."""
    if rule['kind'] == 'FIXED_PER_APPROVED':
        return rule['amount_minor'], {'kind': rule['kind'], 'amount_minor': rule['amount_minor']}
    views = integer(metrics.get('views') if isinstance(metrics, dict) else None, 'metrics.views', 0)
    if views < rule['minimum_views']:
        return 0, {'kind': rule['kind'], 'views': views, 'below_minimum_views': True}
    amount = min(rule['cap_minor'], views * rule['rate_minor_per_thousand'] // 1000)
    return amount, {'kind': rule['kind'], 'views': views, 'rate_minor_per_thousand': rule['rate_minor_per_thousand'], 'cap_minor': rule['cap_minor']}


def admin_fee(amount_minor):
    """Proposed administration fee in minor units, round half up at 5%."""
    return (amount_minor * ADMIN_FEE_BPS + 5000) // 10000


class Desk:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS brands (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS campaigns (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
                    brand_id TEXT NOT NULL REFERENCES brands(id), title TEXT NOT NULL, brief TEXT NOT NULL,
                    rights_terms TEXT NOT NULL, currency TEXT NOT NULL, budget_minor INTEGER NOT NULL,
                    rule TEXT NOT NULL, eligibility TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'DRAFT',
                    version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS assets (
                    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL REFERENCES campaigns(id), name TEXT NOT NULL,
                    license TEXT NOT NULL, content TEXT NOT NULL, created TEXT NOT NULL,
                    UNIQUE(campaign_id, name));
                CREATE TABLE IF NOT EXISTS creators (
                    id TEXT PRIMARY KEY, handle TEXT UNIQUE NOT NULL, consent_on TEXT NOT NULL,
                    payout_route_ref TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1);
                CREATE TABLE IF NOT EXISTS submissions (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT, id TEXT UNIQUE NOT NULL,
                    campaign_id TEXT NOT NULL REFERENCES campaigns(id), creator_id TEXT NOT NULL REFERENCES creators(id),
                    platform TEXT NOT NULL, url TEXT NOT NULL, url_key TEXT NOT NULL, posted_on TEXT NOT NULL,
                    disclosure_present INTEGER NOT NULL, rights_accepted INTEGER NOT NULL,
                    metrics TEXT NOT NULL DEFAULT '{}', status TEXT NOT NULL DEFAULT 'SUBMITTED',
                    review_note TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL,
                    UNIQUE(campaign_id, url_key));
                CREATE TABLE IF NOT EXISTS payables (
                    id TEXT PRIMARY KEY, submission_id TEXT UNIQUE NOT NULL REFERENCES submissions(id),
                    campaign_id TEXT NOT NULL REFERENCES campaigns(id), creator_id TEXT NOT NULL REFERENCES creators(id),
                    amount_minor INTEGER NOT NULL, admin_fee_minor INTEGER NOT NULL, basis TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'CALCULATED', handoff_id TEXT NOT NULL DEFAULT '',
                    settlement_ref TEXT NOT NULL DEFAULT '', version INTEGER NOT NULL DEFAULT 1, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS handoffs (
                    id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL REFERENCES campaigns(id),
                    payload TEXT NOT NULL, created TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS operations (
                    id_sha256 TEXT PRIMARY KEY, payload_sha256 TEXT NOT NULL, result TEXT NOT NULL);
            ''')

    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        return db

    @staticmethod
    def row(db, table, identifier):
        # Table names originate only from this module, never from request data.
        row = db.execute(f'SELECT * FROM {table} WHERE id=?', (identifier,)).fetchone()
        if row is None:
            raise DeskError('Item not found', 404)
        return dict(row)

    @staticmethod
    def expected(row, data):
        version = integer(data.get('version'), 'version', 1, 2**53 - 1)
        if version != row['version']:
            raise DeskError('This item changed. Refresh before editing.', 409)

    @staticmethod
    def committed(db, campaign_id):
        value = db.execute('SELECT COALESCE(SUM(amount_minor),0) FROM payables WHERE campaign_id=?', (campaign_id,)).fetchone()[0]
        return int(value)

    def snapshot(self):
        db = self.connect()
        try:
            db.execute('BEGIN')
            brands = [dict(r) for r in db.execute('SELECT * FROM brands ORDER BY name,id')]
            creators = [dict(r) for r in db.execute('SELECT * FROM creators ORDER BY handle')]
            campaigns = [dict(r) for r in db.execute('SELECT * FROM campaigns ORDER BY seq')]
            submissions = [dict(r) for r in db.execute('SELECT * FROM submissions ORDER BY seq')]
            payables = [dict(r) for r in db.execute('SELECT * FROM payables ORDER BY created,id')]
            assets = [dict(r) for r in db.execute('SELECT id,campaign_id,name,license,created,length(content) AS bytes FROM assets ORDER BY campaign_id,name')]
            for campaign in campaigns:
                campaign['rule'] = json.loads(campaign['rule'])
                campaign['eligibility'] = json.loads(campaign['eligibility'])
                committed = sum(p['amount_minor'] for p in payables if p['campaign_id'] == campaign['id'])
                campaign['budget'] = {
                    'budget_minor': campaign['budget_minor'],
                    'committed_minor': committed,
                    'remaining_minor': campaign['budget_minor'] - committed,
                    'payable_count': sum(1 for p in payables if p['campaign_id'] == campaign['id']),
                }
            for submission in submissions:
                submission['metrics'] = json.loads(submission['metrics'])
                submission['disclosure_present'] = bool(submission['disclosure_present'])
                submission['rights_accepted'] = bool(submission['rights_accepted'])
            for payable in payables:
                payable['basis'] = json.loads(payable['basis'])
            return {'brands': brands, 'creators': creators, 'campaigns': campaigns, 'submissions': submissions,
                    'payables': payables, 'assets': assets, 'handoff_mode': HANDOFF_MODE,
                    'admin_fee_bps': ADMIN_FEE_BPS, 'commercial_status': 'PROPOSED_NOT_ACCEPTED'}
        finally:
            db.close()

    def write(self, operation, data):
        if not isinstance(data, dict):
            raise DeskError('Payload must be an object')
        key_digest = operation_key(data.get('operation_id'))
        # Write receipts keep only digests of the idempotency key and the request payload: exact replay
        # still matches and a different payload is still refused, but no raw request text is retained.
        payload_digest = hashlib.sha256(encoded({'operation': operation, 'data': data}).encode('utf-8')).hexdigest()
        db = self.connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            previous = db.execute('SELECT * FROM operations WHERE id_sha256=?', (key_digest,)).fetchone()
            if previous:
                if previous['payload_sha256'] != payload_digest:
                    raise DeskError('operation_id already belongs to a different edit', 409)
                return json.loads(previous['result'])
            result = self._apply(db, operation, data)
            db.execute('INSERT INTO operations VALUES (?,?,?)', (key_digest, payload_digest, encoded(result)))
            db.commit()
            return result
        except sqlite3.IntegrityError as exc:
            db.rollback()
            raise DeskError('This record already exists (duplicate handle, asset name, content URL, or payable).', 409) from exc
        finally:
            db.close()

    def _apply(self, db, operation, data):
        if operation == 'brand/create':
            name = text(data.get('name'), 'name', 120)
            if not NAME.fullmatch(name):
                raise DeskError('name uses letters, digits, spaces, dots, underscores or hyphens')
            identifier = uuid.uuid4().hex
            db.execute('INSERT INTO brands(id,name) VALUES (?,?)', (identifier, name))
            return {'id': identifier}
        if operation == 'creator/create':
            handle = text(data.get('handle'), 'handle', 64)
            if not HANDLE.fullmatch(handle):
                raise DeskError('handle uses letters, digits, dots, underscores or hyphens')
            if numeric_identity_shape(handle):
                raise DeskError('handle must be a creator handle, not a phone, SSN, card, account or IBAN number')
            consent_on = day(data.get('consent_on'), 'consent_on')
            route = opaque_ref(data.get('payout_route_ref'), 'payout_route_ref')
            identifier = uuid.uuid4().hex
            db.execute('INSERT INTO creators(id,handle,consent_on,payout_route_ref) VALUES (?,?,?,?)', (identifier, handle, consent_on, route))
            return {'id': identifier}
        if operation == 'campaign/create':
            brand_id = text(data.get('brand_id'), 'brand_id', 100)
            self.row(db, 'brands', brand_id)
            title = text(data.get('title'), 'title', 200)
            brief = text(data.get('brief'), 'brief', 20000)
            rights = text(data.get('rights_terms'), 'rights_terms', 20000)
            currency = text(data.get('currency', 'USD'), 'currency', 3)
            if not re.fullmatch(r'[A-Z]{3}', currency):
                raise DeskError('currency must be a three-letter uppercase code')
            budget = integer(data.get('budget_minor'), 'budget_minor', 1)
            rule = reward_rule(data.get('rule'))
            rules = eligibility(data.get('eligibility'))
            identifier = uuid.uuid4().hex
            db.execute('INSERT INTO campaigns(id,brand_id,title,brief,rights_terms,currency,budget_minor,rule,eligibility,created) VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (identifier, brand_id, title, brief, rights, currency, budget, encoded(rule), encoded(rules), now()))
            return {'id': identifier}
        if operation == 'campaign/action':
            identifier = text(data.get('id'), 'id', 100)
            campaign = self.row(db, 'campaigns', identifier)
            self.expected(campaign, data)
            action = data.get('action')
            if action == 'open' and campaign['status'] == 'DRAFT':
                db.execute("UPDATE campaigns SET status='OPEN',version=version+1 WHERE id=?", (identifier,))
            elif action == 'close' and campaign['status'] == 'OPEN':
                db.execute("UPDATE campaigns SET status='CLOSED',version=version+1 WHERE id=?", (identifier,))
            elif action == 'asset' and campaign['status'] in ('DRAFT', 'OPEN'):
                name = text(data.get('name'), 'name', 84)
                if not ASSET_NAME.fullmatch(name):
                    raise DeskError('asset names use letters, digits, underscores or hyphens and end in .md or .txt')
                db.execute('INSERT INTO assets(id,campaign_id,name,license,content,created) VALUES (?,?,?,?,?,?)',
                           (uuid.uuid4().hex, identifier, name, text(data.get('license'), 'license', 2000), text(data.get('content'), 'content'), now()))
                db.execute('UPDATE campaigns SET version=version+1 WHERE id=?', (identifier,))
            else:
                raise DeskError(f'Action {action!r} is not available while the campaign is {campaign["status"]}', 409)
            return {'id': identifier}
        if operation == 'submission/create':
            campaign = self.row(db, 'campaigns', text(data.get('campaign_id'), 'campaign_id', 100))
            creator = self.row(db, 'creators', text(data.get('creator_id'), 'creator_id', 100))
            if campaign['status'] != 'OPEN':
                raise DeskError('Submissions are accepted only while the campaign is OPEN', 409)
            rules = json.loads(campaign['eligibility'])
            platform = data.get('platform')
            if platform not in rules['platforms']:
                raise DeskError(f'platform must be one of the campaign platforms {rules["platforms"]}')
            url = normalize_url(data.get('url'))  # canonical public form is the only URL the desk retains
            posted_on = day(data.get('posted_on'), 'posted_on')
            if posted_on < creator['consent_on']:
                raise DeskError('posted_on precedes the recorded creator consent date')
            identifier = uuid.uuid4().hex
            db.execute('INSERT INTO submissions(id,campaign_id,creator_id,platform,url,url_key,posted_on,disclosure_present,rights_accepted,created) VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (identifier, campaign['id'], creator['id'], platform, url, url, posted_on,
                        int(boolean(data.get('disclosure_present'), 'disclosure_present')),
                        int(boolean(data.get('rights_accepted'), 'rights_accepted')), now()))
            return {'id': identifier, 'url': url}
        if operation == 'submission/review':
            identifier = text(data.get('id'), 'id', 100)
            submission = self.row(db, 'submissions', identifier)
            self.expected(submission, data)
            if submission['status'] != REVIEWABLE:
                raise DeskError('This submission was already reviewed; one review and at most one payable per submission.', 409)
            note = text(data.get('note', 'reviewed'), 'note', 5000)
            decision = data.get('decision')
            campaign = self.row(db, 'campaigns', submission['campaign_id'])
            if decision == 'reject':
                db.execute("UPDATE submissions SET status='REJECTED',review_note=?,version=version+1 WHERE id=?", (note, identifier))
                return {'id': identifier, 'status': 'REJECTED', 'payable_id': None}
            if decision != 'approve':
                raise DeskError('decision must be approve or reject')
            if campaign['status'] != 'OPEN':
                raise DeskError('Approvals are recorded only while the campaign is OPEN', 409)
            rules = json.loads(campaign['eligibility'])
            problems = []
            if rules['requires_disclosure'] and not submission['disclosure_present']:
                problems.append(f'missing required disclosure {rules["disclosure_tag"]}')
            if rules['requires_rights_acceptance'] and not submission['rights_accepted']:
                problems.append('creator has not accepted the campaign rights/usage terms')
            if not rules['window_start'] <= submission['posted_on'] <= rules['window_end']:
                problems.append('posted outside the campaign window')
            if problems:
                raise DeskError('Not eligible for approval: ' + '; '.join(problems), 409)
            metrics = metrics_block(data.get('metrics', {}))
            rule = json.loads(campaign['rule'])
            reward, basis = compute_reward(rule, metrics)
            remaining = campaign['budget_minor'] - self.committed(db, campaign['id'])
            status, payable_id, amount = 'APPROVED', None, 0
            if reward <= 0:
                status = 'APPROVED_NO_REWARD'
            elif reward <= remaining:
                amount = reward
            elif rule['allow_partial'] and remaining > 0:
                amount, status = remaining, 'APPROVED_PARTIAL_BUDGET'
            else:
                status = 'APPROVED_BUDGET_EXHAUSTED'
            if amount > 0:
                payable_id = uuid.uuid4().hex
                basis = dict(basis, computed_reward_minor=reward, budget_remaining_before_minor=remaining)
                db.execute('INSERT INTO payables(id,submission_id,campaign_id,creator_id,amount_minor,admin_fee_minor,basis,created) VALUES (?,?,?,?,?,?,?,?)',
                           (payable_id, identifier, campaign['id'], submission['creator_id'], amount, admin_fee(amount), encoded(basis), now()))
            db.execute('UPDATE submissions SET status=?,review_note=?,metrics=?,version=version+1 WHERE id=?',
                       (status, note, encoded(metrics), identifier))
            return {'id': identifier, 'status': status, 'payable_id': payable_id, 'amount_minor': amount,
                    'admin_fee_minor': admin_fee(amount) if amount else 0}
        if operation == 'payable/handoff':
            campaign = self.row(db, 'campaigns', text(data.get('campaign_id'), 'campaign_id', 100))
            rows = [dict(r) for r in db.execute("SELECT p.*, c.handle, c.payout_route_ref FROM payables p JOIN creators c ON c.id=p.creator_id WHERE p.campaign_id=? AND p.status='CALCULATED' ORDER BY p.created,p.id", (campaign['id'],))]
            if not rows:
                raise DeskError('No calculated payables are waiting for handoff', 409)
            handoff_id = uuid.uuid4().hex
            requests = [{
                'request_id': f'{handoff_id}-{index:04d}', 'payable_id': r['id'], 'creator_handle': r['handle'],
                'payout_route_ref': r['payout_route_ref'], 'amount_minor': r['amount_minor'], 'currency': campaign['currency'],
                'proposed_admin_fee_minor': r['admin_fee_minor'], 'memo': f'{campaign["title"]} / {r["submission_id"]}',
                'idempotency_key': r['id'],
            } for index, r in enumerate(rows, start=1)]
            payload = {'mode': HANDOFF_MODE, 'campaign_id': campaign['id'], 'handoff_id': handoff_id, 'created': now(),
                       'provider': 'ADAPTER_CONTRACT_ONLY', 'requests': requests,
                       'total_amount_minor': sum(r['amount_minor'] for r in requests),
                       'note': 'No transfer was executed. A separately authorized operator submits these requests to the payout provider; settlement is recorded here afterwards by reference.'}
            db.execute('INSERT INTO handoffs VALUES (?,?,?,?)', (handoff_id, campaign['id'], encoded(payload), payload['created']))
            for r in rows:
                db.execute("UPDATE payables SET status='HANDED_OFF',handoff_id=?,version=version+1 WHERE id=?", (handoff_id, r['id']))
            return {'handoff_id': handoff_id, 'count': len(requests), 'total_amount_minor': payload['total_amount_minor'], 'mode': HANDOFF_MODE}
        if operation == 'payable/settle':
            identifier = text(data.get('id'), 'id', 100)
            payable = self.row(db, 'payables', identifier)
            self.expected(payable, data)
            if payable['status'] != 'HANDED_OFF':
                raise DeskError('Only handed-off payables can record an external settlement reference', 409)
            reference = opaque_ref(data.get('settlement_ref'), 'settlement_ref')
            db.execute("UPDATE payables SET status='SETTLEMENT_RECORDED',settlement_ref=?,version=version+1 WHERE id=?", (reference, identifier))
            return {'id': identifier, 'status': 'SETTLEMENT_RECORDED'}
        raise DeskError('Unknown operation', 404)

    def export(self, campaign_id):
        db = self.connect()
        try:
            db.execute('BEGIN')
            campaign = self.row(db, 'campaigns', campaign_id)
            campaign['rule'] = json.loads(campaign['rule'])
            campaign['eligibility'] = json.loads(campaign['eligibility'])
            submissions = [dict(r) for r in db.execute('SELECT s.*, c.handle FROM submissions s JOIN creators c ON c.id=s.creator_id WHERE s.campaign_id=? ORDER BY s.seq', (campaign_id,))]
            payables = [dict(r) for r in db.execute('SELECT p.*, c.handle FROM payables p JOIN creators c ON c.id=p.creator_id WHERE p.campaign_id=? ORDER BY p.created,p.id', (campaign_id,))]
            assets = [dict(r) for r in db.execute('SELECT * FROM assets WHERE campaign_id=? ORDER BY name', (campaign_id,))]
            handoff = db.execute('SELECT payload FROM handoffs WHERE campaign_id=? ORDER BY created DESC,id DESC LIMIT 1', (campaign_id,)).fetchone()
        finally:
            db.close()
        committed = sum(p['amount_minor'] for p in payables)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('campaign.json', encoded({**campaign, 'budget': {'budget_minor': campaign['budget_minor'], 'committed_minor': committed, 'remaining_minor': campaign['budget_minor'] - committed}}))
            archive.writestr('submissions.csv', self._csv(['id', 'handle', 'platform', 'url', 'posted_on', 'disclosure_present', 'rights_accepted', 'status', 'metrics', 'review_note'], submissions))
            archive.writestr('payables.csv', self._csv(['id', 'submission_id', 'handle', 'amount_minor', 'admin_fee_minor', 'status', 'handoff_id', 'settlement_ref', 'basis'], payables))
            archive.writestr('payout_handoff.json', handoff['payload'] if handoff else encoded({'mode': HANDOFF_MODE, 'requests': []}))
            for asset in assets:
                archive.writestr(f'assets/{asset["name"]}', asset['content'])
                archive.writestr(f'assets/{asset["name"]}.license.txt', asset['license'])
            archive.writestr('README.txt', 'Local campaign export. ' + HANDOFF_MODE + '. Payables are calculated rewards under the campaign rule and budget cap; '
                             'the proposed administration fee is PROPOSED_NOT_ACCEPTED; no transfer, invoice, or platform action was performed.\n')
        return buffer.getvalue()

    @staticmethod
    def _csv(fields, rows):
        stream = io.StringIO(newline='')
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(fields)
        for row in rows:
            record = []
            for field in fields:
                value = row.get(field, '')
                if isinstance(value, str) and value[:1] in ('=', '+', '-', '@'):
                    value = "'" + value
                record.append(value)
            writer.writerow(record)
        return stream.getvalue()


def load_example(desk, path=ROOT / 'example.json'):
    """Replay the recorded synthetic operations. Re-running with the same database is idempotent."""
    with open(path, encoding='utf-8') as handle:
        script = json.load(handle)
    results = {}

    def resolve(value):
        if isinstance(value, dict):
            if set(value) == {'$ref'}:
                return results[value['$ref']]['id']
            return {k: resolve(v) for k, v in value.items()}
        if isinstance(value, list):
            return [resolve(v) for v in value]
        return value

    for step in script['operations']:
        data = resolve(step['data'])
        if 'version' in data and isinstance(data['version'], dict) and set(data['version']) == {'$current'}:
            table = data['version']['$current']
            state = desk.snapshot()
            current = next(item for item in state[table] if item['id'] == data['id'])
            data['version'] = current['version']
        results[step['operation_id']] = desk.write(step['operation'], {'operation_id': step['operation_id'], **data})
    return results


class Handler(BaseHTTPRequestHandler):
    desk = None
    routes = {
        '/api/brand/create': 'brand/create', '/api/creator/create': 'creator/create',
        '/api/campaign/create': 'campaign/create', '/api/campaign/action': 'campaign/action',
        '/api/submission/create': 'submission/create', '/api/submission/review': 'submission/review',
        '/api/payable/handoff': 'payable/handoff', '/api/payable/settle': 'payable/settle',
    }

    def log_message(self, *args):
        return

    def reply(self, status, body, content_type='application/json; charset=utf-8'):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = urlsplit(self.path).path
        try:
            if path == '/':
                self.reply(200, (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8')
            elif path == '/api/state':
                self.reply(200, encoded(self.desk.snapshot()))
            elif path.startswith('/api/export/'):
                campaign_id = path[len('/api/export/'):]
                if not re.fullmatch(r'[0-9a-f]{32}', campaign_id):
                    raise DeskError('Item not found', 404)
                self.reply(200, self.desk.export(campaign_id), 'application/zip')
            else:
                raise DeskError('Not found', 404)
        except DeskError as exc:
            self.reply(exc.status, encoded({'error': str(exc)}))

    def do_POST(self):
        path = urlsplit(self.path).path
        try:
            length = int(self.headers.get('Content-Length') or 0)
            if length <= 0 or length > 5_000_000:
                raise DeskError('Request body must be JSON up to 5 MB', 413)
            body = self.rfile.read(length)  # drain the request before any reply so the client never sees an aborted socket
            operation = self.routes.get(path)
            if operation is None:
                raise DeskError('Not found', 404)
            try:
                data = json.loads(body.decode('utf-8'))
            except (ValueError, UnicodeDecodeError) as exc:
                raise DeskError('Request body must be a JSON object') from exc
            self.reply(200, encoded(self.desk.write(operation, data)))
        except DeskError as exc:
            self.reply(exc.status, encoded({'error': str(exc)}))


def make_server(desk, host='127.0.0.1', port=0):
    handler = type('BoundHandler', (Handler,), {'desk': desk})
    return ThreadingHTTPServer((host, port), handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description='Creator reward campaign desk (local, standard library).')
    parser.add_argument('--db', default=str(ROOT / 'creator-reward.sqlite3'))
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--demo', action='store_true', help='load the recorded synthetic campaign (idempotent)')
    args = parser.parse_args(argv)
    desk = Desk(args.db)
    if args.demo:
        load_example(desk)
    server = make_server(desk, args.host, args.port)
    print(f'Creator reward campaign desk on http://{args.host}:{server.server_address[1]} ({HANDOFF_MODE})')
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
