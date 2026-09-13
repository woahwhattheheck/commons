#!/usr/bin/env python3
"""Thin branded launcher for the existing intake-crm-workflow package.

Copied to run.py by bundle.py. No alternate CRM engine is implemented here.
"""
from __future__ import annotations
import hashlib
import html
import importlib.util
import json
import os
import re
import stat
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
MAX_MANIFEST_BYTES = 2_000_000
MAX_IMMUTABLE_BYTES = 8_000_000
_SHA256 = re.compile(r'[0-9a-f]{64}')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'Duplicate JSON key: {key}')
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f'Non-finite JSON value is not allowed: {value}')


def strict_json_bytes(data: bytes, label: str):
    try:
        source = data.decode('utf-8')
    except UnicodeDecodeError as exc:
        raise ValueError(f'{label} must be UTF-8 JSON') from exc
    try:
        return json.loads(source, object_pairs_hook=_pairs, parse_constant=_constant)
    except json.JSONDecodeError as exc:
        raise ValueError(f'{label} is not valid JSON: {exc.msg}') from exc


def _fingerprint(info):
    return (
        info.st_mode,
        info.st_dev,
        info.st_ino,
        info.st_size,
        getattr(info, 'st_mtime_ns', int(info.st_mtime * 1_000_000_000)),
        getattr(info, 'st_ctime_ns', int(info.st_ctime * 1_000_000_000)),
    )


def read_regular(path: Path, label: str, maximum: int) -> bytes:
    flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NONBLOCK', 0)
    flags |= getattr(os, 'O_NOFOLLOW', 0)
    fd = os.open(os.fspath(path), flags)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError(f'{label} must be a regular file')
        if before.st_size > maximum:
            raise ValueError(f'{label} exceeds {maximum} bytes')
        chunks = []
        total = 0
        while True:
            chunk = os.read(fd, min(65536, maximum + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum:
                raise ValueError(f'{label} exceeds {maximum} bytes')
        after = os.fstat(fd)
        if _fingerprint(before) != _fingerprint(after) or total != after.st_size:
            raise ValueError(f'{label} changed while it was being read')
        return b''.join(chunks)
    finally:
        os.close(fd)


def _file_meta(value, name):
    if not isinstance(value, dict) or set(value) != {'sha256', 'bytes'}:
        raise ValueError(f'Invalid manifest metadata for {name}')
    digest = value.get('sha256')
    size = value.get('bytes')
    if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
        raise ValueError(f'Invalid manifest SHA-256 for {name}')
    if isinstance(size, bool) or not isinstance(size, int) or not 0 <= size <= MAX_IMMUTABLE_BYTES:
        raise ValueError(f'Invalid manifest byte count for {name}')
    return digest, size


def verify_package(root: Path = ROOT):
    """Verify immutable package members before workflow.py is loaded.

    This is an internal consistency gate rooted in the packaged launcher/manifest, not a
    signature or independently authenticated provenance mechanism.
    """
    manifest_raw = read_regular(root / 'MANIFEST.json', 'MANIFEST.json', MAX_MANIFEST_BYTES)
    manifest = strict_json_bytes(manifest_raw, 'MANIFEST.json')
    expected_keys = {
        'format', 'version', 'sourceRevisionSupplied', 'sourceRevisionIndependentlyVerified',
        'runtimeImmutable', 'operatorEditable', 'files',
    }
    if not isinstance(manifest, dict) or set(manifest) != expected_keys:
        raise ValueError('Unsupported or malformed Parcel manifest')
    if manifest['format'] != 'parcel.bundle-manifest' or manifest['version'] != 1:
        raise ValueError('Unsupported Parcel manifest version')
    revision = manifest['sourceRevisionSupplied']
    if revision != 'not-supplied' and (
        not isinstance(revision, str) or not re.fullmatch(r'[0-9a-f]{40}', revision)
    ):
        raise ValueError('Invalid source revision in manifest')
    if manifest['sourceRevisionIndependentlyVerified'] is not False:
        raise ValueError('Parcel manifest cannot self-assert independent source verification')

    files = manifest['files']
    immutable = manifest['runtimeImmutable']
    editable = manifest['operatorEditable']
    if not isinstance(files, dict) or not isinstance(immutable, list) or not isinstance(editable, list):
        raise ValueError('Malformed Parcel manifest file inventory')
    if any(not isinstance(name, str) for name in immutable + editable):
        raise ValueError('Manifest member names must be text')
    if len(set(immutable)) != len(immutable) or len(set(editable)) != len(editable):
        raise ValueError('Manifest member inventory contains duplicates')
    if set(immutable) & set(editable) or set(immutable) | set(editable) != set(files):
        raise ValueError('Manifest immutable/editable inventory does not match file inventory')
    if editable != ['config.local.json']:
        raise ValueError('Unexpected Parcel editable-file contract')
    required = {
        'workflow.py', 'index.html', 'run.py', 'parcel.json',
        'example-intake.json', 'START-HERE.txt',
    }
    if not required <= set(immutable):
        raise ValueError('Parcel manifest is missing a required immutable runtime member')

    for name in files:
        if (
            not name
            or name in {'.', '..', 'MANIFEST.json'}
            or '/' in name
            or '\\' in name
            or '\x00' in name
        ):
            raise ValueError('Unsafe manifest member name')
        _file_meta(files[name], name)

    verified = {}
    for name in immutable:
        expected_sha, expected_bytes = _file_meta(files[name], name)
        data = read_regular(root / name, name, min(MAX_IMMUTABLE_BYTES, expected_bytes + 1))
        if len(data) != expected_bytes or hashlib.sha256(data).hexdigest() != expected_sha:
            raise ValueError(f'Package integrity mismatch: {name}')
        verified[name] = data

    config = strict_json_bytes(verified['parcel.json'], 'parcel.json')
    if not isinstance(config, dict) or config.get('format') != 'parcel.intake-handoff' or config.get('version') != 1:
        raise ValueError('parcel.json is not a supported Parcel handoff')
    return config


def _load_workflow(root: Path):
    path = root / 'workflow.py'
    spec = importlib.util.spec_from_file_location('parcel_packaged_workflow', path)
    if spec is None or spec.loader is None:
        raise RuntimeError('Could not load packaged workflow.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compose(config: dict, workflow_module) -> None:
    """Select this installation's task preset and decorate the existing dashboard."""
    workflow_module.TASKS = tuple(config['tasks'])
    workflow_module.DEFAULT_MAPPING = workflow_module.mapping_value(config['fieldMapping'])
    original = workflow_module.Handler

    class BrandedHandler(original):
        def do_GET(self):
            if urlsplit(self.path).path != '/':
                return super().do_GET()
            page = (ROOT / 'index.html').read_text(encoding='utf-8')
            agency = html.escape(config['agency'])
            title = html.escape(config['title'])
            support = html.escape(config.get('support', ''))
            color = config['brand']
            if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
                raise ValueError('Invalid brand color in parcel.json')
            banner = ('<section data-parcel="brand" style="padding:20px 28px;border-bottom:4px solid '
                      + color + ';background:#fff;color:#172b25;font-family:system-ui">'
                      + '<strong>' + agency + '</strong><h1>' + title + '</h1><p>' + support
                      + '</p><small>Client intake, task tracking and delivery · Powered by the existing intake workflow</small></section>')
            if re.search(r'<body\b', page, flags=re.I):
                page = re.sub(r'(<body\b[^>]*>)', lambda m: m.group(1) + banner, page, count=1, flags=re.I)
            else:
                # The supplied dashboard uses a valid implicit HTML body.
                page = re.sub(r'(?=<header\b)', lambda _: banner, page, count=1, flags=re.I)
            page = page.replace('Hive / service operations', agency, 1)
            page = page.replace('One cleaning intake.', 'One client intake.', 1)
            page = page.replace('New cleaning request', 'New client request', 1)
            service = config['exampleIntake']['payload'][config['fieldMapping']['service']]
            page = page.replace('value="Standard residential clean"', 'value="' + html.escape(service, quote=True) + '"', 1)
            page = re.sub(r'<title>.*?</title>', lambda _: '<title>' + title + '</title>', page, count=1, flags=re.I | re.S)
            self.send_value(page.encode('utf-8'), content_type='text/html; charset=utf-8')

    workflow_module.Handler = BrandedHandler


def main() -> None:
    try:
        config = verify_package(ROOT)
        workflow_module = _load_workflow(ROOT)
    except (OSError, ValueError, TypeError, RuntimeError) as exc:
        raise SystemExit(f'Package integrity check failed: {exc}') from exc
    compose(config, workflow_module)
    workflow_module.main()


if __name__ == '__main__':
    main()
