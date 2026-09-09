#!/usr/bin/env python3
"""Build a private, runnable partner installation from a Parcel deployment JSON.

Uses only supplied files; does not fetch, deploy, send, or create customer records.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import zipfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FIELDS = ('name', 'email', 'phone', 'address', 'service', 'preferred_date', 'notes')
PRESETS = ('client-intake', 'quote-request', 'service-request')


def text(value, label, maximum=6000):
    if not isinstance(value, str) or len(value) > maximum:
        raise ValueError(f'{label} must be text of at most {maximum} characters')
    return value


def validate(raw):
    if not isinstance(raw, dict) or raw.get('format') != 'parcel.intake-handoff' or raw.get('version') != 1:
        raise ValueError('Expected a version 1 Parcel deployment JSON')
    if raw.get('preset') not in PRESETS:
        raise ValueError('Unknown intake preset')
    for key in ('agency', 'client', 'title', 'support', 'scope'):
        text(raw.get(key), key)
    if not re.fullmatch(r'#[0-9a-fA-F]{6}', text(raw.get('brand'), 'brand', 7)):
        raise ValueError('Invalid brand color')
    mapping = raw.get('fieldMapping')
    if not isinstance(mapping, dict) or set(mapping) != set(FIELDS):
        raise ValueError('Supply the seven canonical destination fields')
    if any(not text(v, 'Source field', 120).strip() for v in mapping.values()) or len(set(mapping.values())) != len(FIELDS):
        raise ValueError('Source fields must be distinct, non-empty text')
    tasks = raw.get('tasks')
    if not isinstance(tasks, list) or len(tasks) != 3 or any(not text(t, 'Task', 500).strip() for t in tasks):
        raise ValueError('Supply three task titles')
    example = raw.get('exampleIntake')
    if not isinstance(example, dict) or not isinstance(example.get('payload'), dict):
        raise ValueError('Missing example intake')
    if not re.fullmatch(r'[A-Za-z0-9._:-]{1,120}', text(example.get('id'), 'Example intake ID', 120)):
        raise ValueError('Invalid example intake ID')
    for key in FIELDS:
        value = text(example['payload'].get(mapping[key]), key, 4000)
        if key in ('name', 'email', 'address', 'service') and not value.strip():
            raise ValueError(f'Example {key} cannot be blank')
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', example['payload'][mapping['email']]):
        raise ValueError('Example email must be valid')
    value = example['payload'][mapping['preferred_date']]
    if value and date.fromisoformat(value).isoformat() != value:
        raise ValueError('Example preferred date must use YYYY-MM-DD')
    return raw


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def build(deployment: Path, runner_dir: Path, output: Path, source_revision='not-supplied') -> dict:
    if deployment.stat().st_size > 12_000_000:
        raise ValueError('Deployment input exceeds 12 MB')
    raw = validate(json.loads(deployment.read_text(encoding='utf-8')))
    if source_revision != 'not-supplied' and not re.fullmatch(r'[0-9a-f]{40}', source_revision):
        raise ValueError('Source revision must be a full Git commit SHA or not-supplied')
    files = {}
    # Only runtime source files are packaged, never the runner's database or exports.
    for name in ('workflow.py', 'index.html'):
        files[name] = (runner_dir / name).read_bytes()
    compile(files['workflow.py'], 'workflow.py', 'exec')
    if not re.search(rb'<(?:body|header)\b', files['index.html'], re.I):
        raise ValueError('Runner dashboard needs an explicit body or leading header')
    if (runner_dir / 'README.md').is_file():
        files['UPSTREAM-README.md'] = (runner_dir / 'README.md').read_bytes()
    files['run.py'] = (ROOT / 'run_bundle.py').read_bytes()
    files['parcel.json'] = json_bytes(raw)
    files['config.local.json'] = json_bytes({'mapping': raw['fieldMapping'], 'endpoint': ''})
    files['example-intake.json'] = json_bytes(raw['exampleIntake'])
    files['START-HERE.txt'] = (
        raw['agency'] + ' — ' + raw['title'] + '\n\n'
        'A private installation package, not a running service. Python 3.11+ is required.\n'
        'Extract into the intended existing private environment and run from this directory:\n\n'
        '  python run.py --db client.sqlite3 configure config.local.json\n'
        '  python run.py --db client.sqlite3 serve\n\n'
        'Open http://127.0.0.1:8789 in that environment. This is a trusted single-workspace\n'
        'operator service, not an internet-facing or multi-tenant deployment.\n\n'
        'Exercise the sample in a SEPARATE throwaway database, not the client database:\n'
        '  python run.py --db smoke.sqlite3 configure config.local.json\n'
        '  python run.py --db smoke.sqlite3 ingest example-intake.json\n'
        '  python run.py --db smoke.sqlite3 ingest example-intake.json\n'
        '  python run.py --db smoke.sqlite3 work --limit 20\n'
        '  python run.py --db smoke.sqlite3 export\n\n'
        'The duplicate sample ID should yield one customer, one job, three tasks and one\n'
        'local notification. Real intake IDs must be stable for retries and new for new jobs.\n'
        'This launcher reuses the supplied workflow.py without editing its bytes; it selects\n'
        'the three task titles for this preset and adds a branded dashboard header.\n'
        'The existing event type remains cleaning.job.created for interface compatibility.\n'
        'Task instructions are operator work, not automatic quoting, sending or scheduling.\n'
        'Worker delivery is explicit. Provider-specific writes and email are not included.\n'
        'The receiver endpoint starts empty (local notifications). HTTP receivers need\n'
        'durable event-ID deduplication; an acknowledgement is not a universal CRM guarantee.\n'
        'Reconfiguring an existing database is explicit; preserve its data and mapping.\n'
        'Keep databases, sidecars, this client package and exports private. Preserve the\n'
        'database with SQLite backup or a stopped-service copy including required sidecars.\n\n'
        'Scope: ' + raw['scope'] + '\nSupport: ' + (raw['support'] or 'Not yet recorded') + '\n\n'
        'Record the actual installation and client walkthrough in the Parcel checklist.\n'
        'No deployment, customer contact or payment happened merely by building this ZIP.\n'
    ).encode('utf-8')
    manifest = {'format': 'parcel.bundle-manifest', 'version': 1,
                'sourceRevisionSupplied': source_revision,
                'sourceRevisionIndependentlyVerified': False,
                'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)} for name, data in sorted(files.items())}}
    files['MANIFEST.json'] = json_bytes(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation preserves an existing customer package.
    with output.open('xb') as stream:
        try:
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                for name, data in sorted(files.items()):
                    info = zipfile.ZipInfo(name, date_time=(2026, 9, 8, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o600 << 16
                    archive.writestr(info, data)
        except BaseException:
            output.unlink(missing_ok=True)
            raise
    return {'output': str(output), 'bytes': output.stat().st_size, 'sha256': hashlib.sha256(output.read_bytes()).hexdigest(), 'files': len(files)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('deployment', type=Path)
    parser.add_argument('--runner-dir', type=Path, default=ROOT.parent / 'intake-crm-workflow')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-revision', default='not-supplied')
    args = parser.parse_args()
    try:
        result = build(args.deployment, args.runner_dir, args.output, args.source_revision)
    except (OSError, ValueError, TypeError, SyntaxError) as exc:
        parser.exit(1, f'Bundle not created: {exc}\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
