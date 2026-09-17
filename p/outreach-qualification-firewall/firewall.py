"""Fail-closed pre-send outreach qualification firewall.

The module is decision support only. It never performs transport.

Current authorization has three independent trust domains:
* untrusted candidate facts (strict, closed JSON schema);
* repository-retained source/owner/Muse bytes selected only through digest-pinned
  indexes and read through descriptor-anchored, no-follow traversal; and
* process-owned current UTC.

Explicit historical replay is permanently non-authorizing.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import re
import stat
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit
SCHEMA = 'tjlabs-outreach-qualification/v2'
SOURCE_INDEX_SCHEMA = 'tjlabs-retained-source-index/v1'
AUTHORITY_INDEX_SCHEMA = 'tjlabs-authority-index/v1'
OWNER_RECEIPT_SCHEMA = 'tjlabs-owner-approval-receipt/v1'
MUSE_RECEIPT_SCHEMA = 'tjlabs-muse-writer-lease-receipt/v1'
OWNER_PROVIDER = 'TJLabsOwnerApproval'
OWNER_ROOT = 'tjlabs-owner-root-v1'
MUSE_PROVIDER = 'SlackMuse'
MUSE_ROOT = 'tjlabs-muse-root-v1'
TRUSTED_SOURCE_INDEX_SHA256 = 'd010736c0d1f89ecd96a014547d8d2b1bb7c477ce3e7d4db260280a732f40a7d'
TRUSTED_AUTHORITY_INDEX_SHA256 = '899738b3f3301a0678e0c9596ed380dd612e1dac57d29b6a5d45b435718f2c3a'
HERE = Path(__file__).resolve().parent
SOURCE_ROOT = HERE / 'retained_sources'
AUTHORITY_ROOT = HERE / 'retained_authority'
MAX_RETAINED_BYTES = 1000000
_DIRFD_OPEN_SUPPORTED = os.open in getattr(os, 'supports_dir_fd', set())
_DIRFD_STAT_SUPPORTED = os.stat in getattr(os, 'supports_dir_fd', set())
TERMINAL_BLOCK_RELATIONSHIPS = {'DNR', 'BOUNCE', 'BLOCKED', 'CLOSED'}
OPEN_RELATIONSHIPS = {'OPEN', 'WARM', 'INBOUND', 'REFERRED'}
ELIGIBILITY_PASS = {'PROVEN', 'NOT_REQUIRED'}
ROUTE_KINDS = {'EMAIL', 'GITHUB_PR', 'PORTAL', 'FORM', 'SLACK_CONNECT', 'OTHER'}
COMPENSATION_BASES = {'FIXED_FEE', 'HOURLY', 'BOUNTY'}
PRIOR_BLOCK_STATES = {'PENDING', 'SENT', 'DELIVERED', 'ACCEPTED', 'PAID'}
SHA256_RE = re.compile('^[0-9a-f]{64}$')
ID_RE = re.compile('^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$')
CURRENCY_RE = re.compile('^[A-Z]{3}$')
EMAIL_RE = re.compile('^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$')
PACKET_KEYS = {'schema', 'source', 'opportunity', 'submission', 'eligibility', 'economics', 'target', 'action', 'prior_actions', 'owner_review_receipt_id', 'writer_lease_receipt_id'}

class PacketError(ValueError):
    """Candidate, retained source, or retained authority violates a contract."""

@dataclass(frozen=True)
class Decision:
    mode: str
    evaluated_at_utc: str
    qualified_for_owner_review: bool
    authorized_to_send: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    qualification_digest: str
    action_digest: str
    dedupe_key: str
    runway_seconds: int
    source_sha256: str
    owner_receipt_sha256: str | None
    writer_lease_receipt_sha256: str | None

    def as_dict(self) -> dict[str, Any]:
        return {'schema': 'tjlabs-outreach-qualification-decision/v2', 'mode': self.mode, 'evaluated_at_utc': self.evaluated_at_utc, 'qualified_for_owner_review': self.qualified_for_owner_review, 'authorized_to_send': self.authorized_to_send, 'blockers': list(self.blockers), 'warnings': list(self.warnings), 'qualification_digest': self.qualification_digest, 'action_digest': self.action_digest, 'dedupe_key': self.dedupe_key, 'runway_seconds': self.runway_seconds, 'source_sha256': self.source_sha256, 'owner_receipt_sha256': self.owner_receipt_sha256, 'writer_lease_receipt_sha256': self.writer_lease_receipt_sha256}

def _plain_json(value: Any, name: str='value') -> Any:
    """Freeze programmatic input to exact built-in JSON types.

    Reject Mapping/list subclasses and non-finite floats so stateful/custom
    objects cannot change between validation and hashing.
    """
    t = type(value)
    if t is dict:
        out: dict[str, Any] = {}
        for key, item in value.items():
            if type(key) is not str:
                raise PacketError(f'{name} object keys must be strings')
            out[key] = _plain_json(item, f'{name}.{key}')
        return out
    if t is list:
        return [_plain_json(item, f'{name}[]') for item in value]
    if t is str or t is bool or value is None:
        return value
    if t is int:
        return value
    if t is float:
        if not math.isfinite(value):
            raise PacketError(f'{name} cannot contain NaN/Infinity')
        return value
    raise PacketError(f'{name} must use plain JSON types')

def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise PacketError(f'duplicate JSON key: {key}')
        out[key] = value
    return out

def _reject_constant(token: str) -> Any:
    raise PacketError(f'non-finite JSON constant is forbidden: {token}')

def _strict_json_bytes(data: bytes, name: str) -> Any:
    try:
        text = data.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise PacketError(f'{name} is not UTF-8') from exc
    try:
        value = json.loads(text, object_pairs_hook=_pairs_no_duplicates, parse_constant=_reject_constant)
    except PacketError:
        raise
    except json.JSONDecodeError as exc:
        raise PacketError(f'{name} is not valid JSON') from exc
    return _plain_json(value, name)

def _canonical_bytes(value: Any) -> bytes:
    value = _plain_json(value)
    try:
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')
    except (TypeError, ValueError) as exc:
        raise PacketError('value is not canonical-JSON encodable') from exc

def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _digest(value: Any) -> str:
    return sha256_hex(_canonical_bytes(value))

def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if type(value) is not dict:
        raise PacketError(f'{name} must be an object')
    return value

def _require_list(value: Any, name: str) -> list[Any]:
    if type(value) is not list:
        raise PacketError(f'{name} must be a list')
    return value

def _closed(mapping: dict[str, Any], name: str, required: set[str], optional: set[str] | None=None) -> None:
    optional = optional or set()
    keys = set(mapping)
    missing = required - keys
    unknown = keys - required - optional
    if missing:
        raise PacketError(f'{name} missing required fields: {sorted(missing)}')
    if unknown:
        raise PacketError(f'{name} contains forbidden/unknown fields: {sorted(unknown)}')

def _text(value: Any, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise PacketError(f'{name} must be a non-empty string')
    return value.strip()

def _id(value: Any, name: str) -> str:
    text = _text(value, name)
    if not ID_RE.fullmatch(text):
        raise PacketError(f'{name} must be a simple retained identifier')
    return text

def _enum(value: Any, name: str, allowed: set[str]) -> str:
    text = _text(value, name)
    if text not in allowed:
        raise PacketError(f'{name} must be one of {sorted(allowed)}')
    return text

def _parse_utc(value: Any, name: str) -> datetime:
    text = _text(value, name)
    if not text.endswith('Z'):
        raise PacketError(f'{name} must use canonical UTC Z form')
    try:
        parsed = datetime.fromisoformat(text[:-1] + '+00:00')
    except ValueError as exc:
        raise PacketError(f'{name} is not a valid timestamp') from exc
    parsed = parsed.astimezone(timezone.utc)
    canonical = parsed.isoformat(timespec='seconds').replace('+00:00', 'Z')
    if text != canonical:
        raise PacketError(f'{name} must be canonical to whole seconds: {canonical}')
    return parsed

def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')

def _process_now() -> datetime:
    return datetime.fromtimestamp(time.time(), tz=timezone.utc).replace(microsecond=0)

def _norm_text(value: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', value).strip().casefold().split())

def _norm_route(kind: str, route: str) -> str:
    route = unicodedata.normalize('NFKC', route).strip()
    if kind == 'EMAIL':
        lowered = route.casefold()
        if lowered.startswith('mailto:'):
            lowered = lowered[7:].strip()
        if not EMAIL_RE.fullmatch(lowered):
            raise PacketError('route must be a syntactically valid email address')
        return lowered
    if kind in {'GITHUB_PR', 'PORTAL', 'FORM'}:
        parts = urlsplit(route)
        if parts.scheme.casefold() not in {'https', 'http'} or not parts.netloc:
            raise PacketError('route must be an absolute http(s) URL')
        path = re.sub('/+', '/', parts.path or '/')
        if path != '/':
            path = path.rstrip('/')
        return urlunsplit((parts.scheme.casefold(), parts.netloc.casefold(), path, parts.query, ''))
    return _norm_text(route)

def _decimal_positive(value: Any, name: str) -> Decimal:
    if type(value) is bool or type(value) not in {str, int, float}:
        raise PacketError(f'{name} must be a positive decimal')
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise PacketError(f'{name} must be a positive decimal') from exc
    if not parsed.is_finite() or parsed <= 0:
        raise PacketError(f'{name} must be finite and > 0')
    return parsed

def _relative_parts(relative: str, name: str) -> tuple[str, ...]:
    if type(relative) is not str or not relative or '\x00' in relative or ('\\' in relative):
        raise PacketError(f'{name} path is invalid')
    path = PurePosixPath(relative)
    if path.is_absolute() or any((part in {'', '.', '..'} for part in path.parts)):
        raise PacketError(f'{name} path is invalid')
    return tuple(path.parts)

def _secure_open_support() -> None:
    if not hasattr(os, 'O_NOFOLLOW') or not hasattr(os, 'O_DIRECTORY'):
        raise PacketError('secure retained-file traversal is unsupported on this platform')
    if not _DIRFD_OPEN_SUPPORTED or not _DIRFD_STAT_SUPPORTED:
        raise PacketError('secure retained-file dirfd traversal is unsupported on this platform')

def _read_retained_file(base: Path, relative: str, *, name: str) -> bytes:
    """Read a retained file through descriptor-pinned ancestry.

    Every directory component is opened from the previously pinned dirfd with
    O_DIRECTORY|O_NOFOLLOW. The leaf is lstat-equivalent checked through that
    dirfd, then opened O_NOFOLLOW and compared before/during the read.
    """
    _secure_open_support()
    parts = _relative_parts(relative, name)
    cloexec = getattr(os, 'O_CLOEXEC', 0)
    dir_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | cloexec
    leaf_flags = os.O_RDONLY | os.O_NOFOLLOW | cloexec
    try:
        current_fd = os.open(os.fspath(base), dir_flags)
    except OSError as exc:
        raise PacketError(f'{name} retained root cannot be securely opened') from exc
    leaf_fd: int | None = None
    try:
        root_st = os.fstat(current_fd)
        if not stat.S_ISDIR(root_st.st_mode):
            raise PacketError(f'{name} retained root is not a directory')
        for component in parts[:-1]:
            try:
                next_fd = os.open(component, dir_flags, dir_fd=current_fd)
            except OSError as exc:
                raise PacketError(f'{name} parent path cannot be securely opened') from exc
            next_st = os.fstat(next_fd)
            if not stat.S_ISDIR(next_st.st_mode):
                os.close(next_fd)
                raise PacketError(f'{name} parent path is not a directory')
            os.close(current_fd)
            current_fd = next_fd
        leaf = parts[-1]
        try:
            pre = os.stat(leaf, dir_fd=current_fd, follow_symlinks=False)
        except OSError as exc:
            raise PacketError(f'{name} retained file cannot be inspected') from exc
        if stat.S_ISLNK(pre.st_mode) or not stat.S_ISREG(pre.st_mode):
            raise PacketError(f'{name} must be a non-symlink regular file')
        if pre.st_nlink != 1:
            raise PacketError(f'{name} must have exactly one hard link')
        if pre.st_size > MAX_RETAINED_BYTES:
            raise PacketError(f'{name} exceeds retained size limit')
        try:
            leaf_fd = os.open(leaf, leaf_flags, dir_fd=current_fd)
        except OSError as exc:
            raise PacketError(f'{name} retained file cannot be securely opened') from exc
        opened = os.fstat(leaf_fd)
        before_identity = (pre.st_dev, pre.st_ino, stat.S_IFMT(pre.st_mode), pre.st_nlink, pre.st_size, pre.st_mtime_ns, pre.st_ctime_ns)
        opened_identity = (opened.st_dev, opened.st_ino, stat.S_IFMT(opened.st_mode), opened.st_nlink, opened.st_size, opened.st_mtime_ns, opened.st_ctime_ns)
        if before_identity != opened_identity:
            raise PacketError(f'{name} changed before open')
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise PacketError(f'{name} opened object is not a single-link regular file')
        chunks: list[bytes] = []
        remaining = MAX_RETAINED_BYTES + 1
        while remaining:
            chunk = os.read(leaf_fd, min(65536, remaining))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b''.join(chunks)
        if len(data) > MAX_RETAINED_BYTES:
            raise PacketError(f'{name} exceeds retained size limit')
        post = os.fstat(leaf_fd)
        post_identity = (post.st_dev, post.st_ino, stat.S_IFMT(post.st_mode), post.st_nlink, post.st_size, post.st_mtime_ns, post.st_ctime_ns)
        if opened_identity != post_identity:
            raise PacketError(f'{name} changed during read')
        return data
    finally:
        if leaf_fd is not None:
            os.close(leaf_fd)
        os.close(current_fd)

def _load_pinned_index(path: Path, expected_sha256: str, schema: str, name: str) -> dict[str, Any]:
    data = _read_retained_file(path.parent, path.name, name=name)
    actual = sha256_hex(data)
    if actual != expected_sha256:
        raise PacketError(f'{name} root digest mismatch')
    mapping = _require_mapping(_strict_json_bytes(data, name), name)
    if mapping.get('schema') != schema:
        raise PacketError(f'{name} schema mismatch')
    return mapping

def _load_retained_source(packet: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], str]:
    source = _require_mapping(packet.get('source'), 'source')
    _closed(source, 'source', {'source_id'})
    source_id = _id(source['source_id'], 'source.source_id')
    index = _load_pinned_index(SOURCE_ROOT / 'index.json', TRUSTED_SOURCE_INDEX_SHA256, SOURCE_INDEX_SCHEMA, 'retained source index')
    _closed(index, 'retained source index', {'schema', 'sources'})
    entries = _require_mapping(index['sources'], 'retained source index.sources')
    raw_entry = entries.get(source_id)
    if raw_entry is None:
        raise PacketError('source.source_id is not present in the trusted retained-source index')
    entry = _require_mapping(raw_entry, f'retained source {source_id}')
    _closed(entry, f'retained source {source_id}', {'file', 'sha256'})
    filename = _id(entry['file'], f'retained source {source_id}.file')
    expected = _text(entry['sha256'], f'retained source {source_id}.sha256')
    if not SHA256_RE.fullmatch(expected):
        raise PacketError('retained source index contains invalid sha256')
    data = _read_retained_file(SOURCE_ROOT / 'files', filename, name='retained source')
    actual = sha256_hex(data)
    if actual != expected:
        raise PacketError('retained source digest mismatch')
    source_doc = _require_mapping(_strict_json_bytes(data, 'retained source'), 'retained source')
    _closed(source_doc, 'retained source', {'authority', 'opportunity', 'revision'})
    if source_doc['authority'] != 'retained':
        raise PacketError('retained source authority marker is invalid')
    _text(source_doc['opportunity'], 'retained source.opportunity')
    _text(source_doc['revision'], 'retained source.revision')
    return ({'source_id': source_id, 'sha256': actual}, source_doc, actual)

def _load_authority_receipt(kind: str, receipt_id: str) -> tuple[dict[str, Any], str]:
    if kind not in {'owner', 'muse'}:
        raise PacketError('unknown authority kind')
    index = _load_pinned_index(AUTHORITY_ROOT / 'index.json', TRUSTED_AUTHORITY_INDEX_SHA256, AUTHORITY_INDEX_SCHEMA, 'retained authority index')
    _closed(index, 'retained authority index', {'schema', 'owner', 'muse'})
    entries = _require_mapping(index[kind], f'authority index.{kind}')
    raw_entry = entries.get(receipt_id)
    if raw_entry is None:
        raise PacketError(f'{kind} receipt id is not independently retained')
    entry = _require_mapping(raw_entry, f'authority index.{kind}.{receipt_id}')
    _closed(entry, f'authority index.{kind}.{receipt_id}', {'file', 'sha256'})
    filename = _id(entry['file'], f'authority index.{kind}.{receipt_id}.file')
    expected = _text(entry['sha256'], f'authority index.{kind}.{receipt_id}.sha256')
    if not SHA256_RE.fullmatch(expected):
        raise PacketError('authority index contains invalid receipt sha256')
    data = _read_retained_file(AUTHORITY_ROOT / kind, filename, name=f'retained {kind} receipt')
    actual = sha256_hex(data)
    if actual != expected:
        raise PacketError(f'retained {kind} receipt digest mismatch')
    parsed = _require_mapping(_strict_json_bytes(data, f'retained {kind} receipt'), f'retained {kind} receipt')
    return (parsed, actual)

def _qualification_material(packet: dict[str, Any], source_binding: dict[str, Any], source_doc: dict[str, Any], now: datetime) -> tuple[dict[str, Any], list[str], list[str], int, str]:
    blockers: list[str] = []
    warnings: list[str] = []
    if packet.get('schema') != SCHEMA:
        raise PacketError(f'schema must be {SCHEMA!r}')
    _closed(packet, 'candidate packet', PACKET_KEYS - {'owner_review_receipt_id', 'writer_lease_receipt_id'}, {'owner_review_receipt_id', 'writer_lease_receipt_id'})
    opportunity = _require_mapping(packet['opportunity'], 'opportunity')
    _closed(opportunity, 'opportunity', {'id', 'deadline_utc', 'min_runway_hours'})
    opportunity_id = _text(opportunity['id'], 'opportunity.id')
    if _text(source_doc['opportunity'], 'retained source.opportunity') != opportunity_id:
        blockers.append('SOURCE_OPPORTUNITY_MISMATCH')
    deadline = _parse_utc(opportunity['deadline_utc'], 'opportunity.deadline_utc')
    min_runway_hours = opportunity['min_runway_hours']
    if type(min_runway_hours) is not int or min_runway_hours < 0:
        raise PacketError('opportunity.min_runway_hours must be an integer >= 0')
    runway_seconds = int((deadline - now).total_seconds())
    required_seconds = min_runway_hours * 3600
    if runway_seconds < required_seconds:
        blockers.append('RUNWAY_BELOW_MINIMUM')
    if runway_seconds < 0:
        blockers.append('DEADLINE_PASSED')
    if runway_seconds == required_seconds:
        warnings.append('RUNWAY_EXACTLY_AT_MINIMUM')
    submission = _require_mapping(packet['submission'], 'submission')
    _closed(submission, 'submission', {'route_state', 'kind', 'locator', 'registration_required', 'registration_state'})
    route_state = _enum(submission['route_state'], 'submission.route_state', {'PROVEN', 'UNKNOWN', 'FAILED'})
    route_kind = _enum(submission['kind'], 'submission.kind', ROUTE_KINDS)
    route_locator = _norm_route(route_kind, _text(submission['locator'], 'submission.locator'))
    registration_required = submission['registration_required']
    if type(registration_required) is not bool:
        raise PacketError('submission.registration_required must be boolean')
    registration_state = _enum(submission['registration_state'], 'submission.registration_state', {'PROVEN', 'NOT_REQUIRED', 'UNKNOWN', 'FAILED'})
    if route_state != 'PROVEN':
        blockers.append('SUBMISSION_ROUTE_NOT_PROVEN')
    if registration_required and registration_state != 'PROVEN':
        blockers.append('REGISTRATION_NOT_PROVEN')
    if not registration_required and registration_state not in {'NOT_REQUIRED', 'PROVEN'}:
        blockers.append('REGISTRATION_STATE_INCONSISTENT')
    eligibility = _require_mapping(packet['eligibility'], 'eligibility')
    _closed(eligibility, 'eligibility', {'gates'})
    gates = _require_list(eligibility['gates'], 'eligibility.gates')
    if not gates:
        raise PacketError('eligibility.gates must not be empty')
    normalized_gates: list[dict[str, Any]] = []
    names: set[str] = set()
    for i, raw in enumerate(gates):
        gate = _require_mapping(raw, f'eligibility.gates[{i}]')
        _closed(gate, f'eligibility.gates[{i}]', {'name', 'state', 'evidence_refs'})
        name = _text(gate['name'], f'eligibility.gates[{i}].name')
        folded = _norm_text(name)
        if folded in names:
            raise PacketError(f'duplicate eligibility gate name: {name}')
        names.add(folded)
        state = _enum(gate['state'], f'eligibility.gates[{i}].state', {'PROVEN', 'NOT_REQUIRED', 'UNKNOWN', 'FAILED'})
        refs = [_text(x, f'eligibility.gates[{i}].evidence_refs[]') for x in _require_list(gate['evidence_refs'], f'eligibility.gates[{i}].evidence_refs')]
        if state == 'PROVEN' and (not refs):
            raise PacketError(f'PROVEN eligibility gate {name!r} needs evidence_refs')
        if state not in ELIGIBILITY_PASS:
            blockers.append(f'ELIGIBILITY_{state}:{name}')
        normalized_gates.append({'name': name, 'state': state, 'evidence_refs': refs})
    economics = _require_mapping(packet['economics'], 'economics')
    _closed(economics, 'economics', {'basis', 'amount', 'currency', 'bounded_scope', 'payment_path_state'})
    basis = _enum(economics['basis'], 'economics.basis', COMPENSATION_BASES)
    amount = _decimal_positive(economics['amount'], 'economics.amount')
    currency = _text(economics['currency'], 'economics.currency')
    if not CURRENCY_RE.fullmatch(currency):
        raise PacketError('economics.currency must be uppercase 3-letter code')
    scope = _text(economics['bounded_scope'], 'economics.bounded_scope')
    payment_path_state = _enum(economics['payment_path_state'], 'economics.payment_path_state', {'PROVEN', 'UNKNOWN', 'FAILED'})
    if payment_path_state != 'PROVEN':
        blockers.append('PAYMENT_PATH_NOT_PROVEN')
    target = _require_mapping(packet['target'], 'target')
    _closed(target, 'target', {'organization', 'contact', 'relationship_state'})
    organization = _text(target['organization'], 'target.organization')
    contact = _text(target['contact'], 'target.contact')
    relationship_state = _enum(target['relationship_state'], 'target.relationship_state', OPEN_RELATIONSHIPS | TERMINAL_BLOCK_RELATIONSHIPS)
    if relationship_state in TERMINAL_BLOCK_RELATIONSHIPS:
        blockers.append(f'RELATIONSHIP_{relationship_state}')
    action = _require_mapping(packet['action'], 'action')
    _closed(action, 'action', {'kind', 'route', 'purpose', 'content_sha256'})
    action_kind = _enum(action['kind'], 'action.kind', ROUTE_KINDS)
    normalized_route = _norm_route(action_kind, _text(action['route'], 'action.route'))
    purpose = _text(action['purpose'], 'action.purpose')
    content_sha256 = _text(action['content_sha256'], 'action.content_sha256')
    if not SHA256_RE.fullmatch(content_sha256):
        raise PacketError('action.content_sha256 must be lowercase sha256')
    if action_kind == 'EMAIL' and _norm_route('EMAIL', contact) != normalized_route:
        blockers.append('ACTION_ROUTE_CONTACT_MISMATCH')
    dedupe_material = {'opportunity_id': _norm_text(opportunity_id), 'organization': _norm_text(organization), 'contact': _norm_text(contact), 'action_kind': action_kind, 'route': normalized_route, 'purpose': _norm_text(purpose)}
    dedupe_key = _digest(dedupe_material)
    prior_actions = _require_list(packet['prior_actions'], 'prior_actions')
    normalized_prior: list[dict[str, str]] = []
    for i, raw in enumerate(prior_actions):
        prior = _require_mapping(raw, f'prior_actions[{i}]')
        _closed(prior, f'prior_actions[{i}]', {'dedupe_key', 'state'})
        prior_key = _text(prior['dedupe_key'], f'prior_actions[{i}].dedupe_key')
        if not SHA256_RE.fullmatch(prior_key):
            raise PacketError('prior action dedupe_key must be lowercase sha256')
        state = _enum(prior['state'], f'prior_actions[{i}].state', PRIOR_BLOCK_STATES | {'FAILED', 'VOID'})
        if prior_key == dedupe_key and state in PRIOR_BLOCK_STATES:
            blockers.append(f'DUPLICATE_PRIOR_ACTION:{state}')
        normalized_prior.append({'dedupe_key': prior_key, 'state': state})
    material = {'schema': SCHEMA, 'source': dict(source_binding), 'opportunity': {'id': opportunity_id, 'deadline_utc': opportunity['deadline_utc'], 'min_runway_hours': min_runway_hours}, 'submission': {'kind': route_kind, 'locator': route_locator, 'route_state': route_state, 'registration_required': registration_required, 'registration_state': registration_state}, 'eligibility': {'gates': normalized_gates}, 'economics': {'basis': basis, 'amount': format(amount, 'f'), 'currency': currency, 'bounded_scope': scope, 'payment_path_state': payment_path_state}, 'target': {'organization': organization, 'contact': contact, 'relationship_state': relationship_state}, 'action': {'kind': action_kind, 'route': normalized_route, 'purpose': purpose, 'content_sha256': content_sha256}, 'dedupe_key': dedupe_key, 'prior_actions': normalized_prior}
    return (material, blockers, warnings, runway_seconds, dedupe_key)

def _check_owner_receipt(receipt: dict[str, Any], *, qualification_digest: str, now: datetime) -> list[str]:
    _closed(receipt, 'owner receipt', {'schema', 'provider', 'root_id', 'generation', 'source_ref', 'status', 'reviewer', 'qualification_digest', 'issued_at_utc', 'expires_at_utc'})
    blockers: list[str] = []
    if receipt['schema'] != OWNER_RECEIPT_SCHEMA:
        raise PacketError('owner receipt schema mismatch')
    if receipt['provider'] != OWNER_PROVIDER or receipt['root_id'] != OWNER_ROOT:
        raise PacketError('owner receipt provider/root is not trusted')
    _id(receipt['generation'], 'owner receipt.generation')
    _text(receipt['source_ref'], 'owner receipt.source_ref')
    if _enum(receipt['status'], 'owner receipt.status', {'APPROVED', 'REJECTED'}) != 'APPROVED':
        blockers.append('OWNER_REVIEW_REJECTED')
    bound = _text(receipt['qualification_digest'], 'owner receipt.qualification_digest')
    if not SHA256_RE.fullmatch(bound) or bound != qualification_digest:
        blockers.append('OWNER_REVIEW_STALE_OR_FOREIGN')
    issued = _parse_utc(receipt['issued_at_utc'], 'owner receipt.issued_at_utc')
    expires = _parse_utc(receipt['expires_at_utc'], 'owner receipt.expires_at_utc')
    if issued > now or expires < now or expires < issued:
        blockers.append('OWNER_REVIEW_TIME_INVALID')
    _text(receipt['reviewer'], 'owner receipt.reviewer')
    return blockers

def _check_muse_receipt(receipt: dict[str, Any], *, action_digest: str, writer: str, now: datetime) -> list[str]:
    _closed(receipt, 'Muse receipt', {'schema', 'provider', 'root_id', 'generation', 'source_ref', 'status', 'key', 'selected_writer', 'action_digest', 'issued_at_utc', 'expires_at_utc'})
    blockers: list[str] = []
    if receipt['schema'] != MUSE_RECEIPT_SCHEMA:
        raise PacketError('Muse receipt schema mismatch')
    if receipt['provider'] != MUSE_PROVIDER or receipt['root_id'] != MUSE_ROOT:
        raise PacketError('Muse receipt provider/root is not trusted')
    _id(receipt['generation'], 'Muse receipt.generation')
    _text(receipt['source_ref'], 'Muse receipt.source_ref')
    status = _enum(receipt['status'], 'Muse receipt.status', {'SELECTED', 'HOLD', 'COLLISION', 'VOID'})
    if status != 'SELECTED':
        blockers.append(f'WRITER_LEASE_{status}')
    selected = _text(receipt['selected_writer'], 'Muse receipt.selected_writer')
    if selected != writer:
        blockers.append('WRITER_LEASE_FOREIGN_WRITER')
    bound = _text(receipt['action_digest'], 'Muse receipt.action_digest')
    if not SHA256_RE.fullmatch(bound) or bound != action_digest:
        blockers.append('WRITER_LEASE_STALE_OR_FOREIGN_ACTION')
    issued = _parse_utc(receipt['issued_at_utc'], 'Muse receipt.issued_at_utc')
    expires = _parse_utc(receipt['expires_at_utc'], 'Muse receipt.expires_at_utc')
    if issued > now or expires < now or expires < issued:
        blockers.append('WRITER_LEASE_TIME_INVALID')
    _text(receipt['key'], 'Muse receipt.key')
    return blockers

def _evaluate(packet: Any, *, writer: str, now: datetime, current: bool) -> Decision:
    packet = _require_mapping(_plain_json(packet, 'packet'), 'packet')
    writer = _text(writer, 'writer')
    source_binding, source_doc, source_sha = _load_retained_source(packet)
    material, blockers, warnings, runway_seconds, dedupe_key = _qualification_material(packet, source_binding, source_doc, now)
    qualification_digest = _digest(material)
    action_digest = _digest({'qualification_digest': qualification_digest, 'dedupe_key': dedupe_key, 'action': material['action']})
    qualification_blockers = tuple(sorted(set(blockers)))
    qualified = not qualification_blockers
    owner_sha: str | None = None
    lease_sha: str | None = None
    if not current:
        warnings.append('HISTORICAL_REPLAY_NON_CURRENT')
        warnings.append('OWNER_AND_MUSE_AUTHORITY_NOT_CONSUMED_IN_REPLAY')
        authorized = False
    else:
        owner_id_raw = packet.get('owner_review_receipt_id')
        lease_id_raw = packet.get('writer_lease_receipt_id')
        if owner_id_raw is None:
            warnings.append('OWNER_REVIEW_REQUIRED')
        else:
            owner_id = _id(owner_id_raw, 'owner_review_receipt_id')
            owner_receipt, owner_sha = _load_authority_receipt('owner', owner_id)
            blockers.extend(_check_owner_receipt(owner_receipt, qualification_digest=qualification_digest, now=now))
        if lease_id_raw is None:
            warnings.append('WRITER_LEASE_REQUIRED')
        else:
            lease_id = _id(lease_id_raw, 'writer_lease_receipt_id')
            lease_receipt, lease_sha = _load_authority_receipt('muse', lease_id)
            blockers.extend(_check_muse_receipt(lease_receipt, action_digest=action_digest, writer=writer, now=now))
        if qualification_blockers and owner_id_raw is not None:
            blockers.append('OWNER_REVIEW_CANNOT_OVERRIDE_QUALIFICATION_BLOCKER')
        authorized = qualified and owner_sha is not None and (lease_sha is not None) and (not blockers)
    return Decision(mode='CURRENT_PROCESS_TIME' if current else 'HISTORICAL_REPLAY_NON_CURRENT', evaluated_at_utc=_format_utc(now), qualified_for_owner_review=qualified, authorized_to_send=authorized, blockers=tuple(sorted(set(blockers))), warnings=tuple(sorted(set(warnings))), qualification_digest=qualification_digest, action_digest=action_digest, dedupe_key=dedupe_key, runway_seconds=runway_seconds, source_sha256=source_sha, owner_receipt_sha256=owner_sha, writer_lease_receipt_sha256=lease_sha)

def evaluate_current(packet: Any, *, writer: str) -> Decision:
    """Evaluate current readiness using process-owned UTC. Never sends."""
    return _evaluate(packet, writer=writer, now=_process_now(), current=True)

def evaluate_historical(packet: Any, *, at_utc: str, writer: str) -> Decision:
    """Replay at an explicit instant. Historical mode can never authorize."""
    return _evaluate(packet, writer=writer, now=_parse_utc(at_utc, 'at_utc'), current=False)

def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise PacketError(f'candidate packet cannot be read: {path}') from exc
    return _require_mapping(_strict_json_bytes(data, 'packet'), 'packet')

def main(argv: Sequence[str] | None=None) -> int:
    parser = argparse.ArgumentParser(description='Evaluate outreach readiness; this program never sends anything.')
    parser.add_argument('packet', type=Path)
    parser.add_argument('--writer', required=True)
    parser.add_argument('--historical-at', help='explicit replay instant; forces permanently non-authorizing historical mode')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args(argv)
    try:
        packet = _load_json(args.packet)
        decision = evaluate_historical(packet, at_utc=args.historical_at, writer=args.writer) if args.historical_at else evaluate_current(packet, writer=args.writer)
    except PacketError as exc:
        parser.error(str(exc))
    payload = json.dumps(decision.as_dict(), sort_keys=True, indent=2) + '\n'
    if args.out:
        args.out.write_text(payload, encoding='utf-8')
    else:
        print(payload, end='')
    return 0 if decision.authorized_to_send else 2
if __name__ == '__main__':
    raise SystemExit(main())
