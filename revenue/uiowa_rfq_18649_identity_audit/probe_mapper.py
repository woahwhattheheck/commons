#!/usr/bin/env python3
"""Run source-pinned mapper CLI and conservation checks on temporary fiction.

This explicitly executes the supplied Python source. Inspect it first and bind
--expected-blob to the reviewed Git blob. It never reads live University data.
Exit 0: all cases passed; 1: a case failed; 2: invalid configuration or IO error.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

try:
    from .report_audit import AuditInputError, audit, load
    from .sample_packet import packet
except ImportError:
    from report_audit import AuditInputError, audit, load
    from sample_packet import packet


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()


def run(mapper: Path, expected_blob: str) -> dict:
    mapper = mapper.resolve(strict=True)
    actual_blob = git_blob(mapper.read_bytes())
    if actual_blob != expected_blob:
        raise AuditInputError(f'Mapper blob mismatch: expected {expected_blob}, found {actual_blob}')
    spec = importlib.util.spec_from_file_location('uiowa103_probed_' + actual_blob, mapper)
    if spec is None or spec.loader is None:
        raise AuditInputError('Mapper source is not importable')
    module = importlib.util.module_from_spec(spec)
    # Execute only the explicitly supplied, previously inspected and pinned file.
    spec.loader.exec_module(module)
    cases = []

    def case(name, passed, observed):
        cases.append({'name': name, 'status': 'PASS' if passed else 'FAIL', 'observed': observed})

    source = packet()
    produced = module.reconcile(deepcopy(source))
    checked = audit(source, produced)
    case('api_conservation', checked['status'] == 'PASS', checked)
    with tempfile.TemporaryDirectory(prefix='uiowa103-audit-') as directory:
        root = Path(directory)
        input_path = root / 'source.json'
        raw = (json.dumps(source, sort_keys=True, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        input_path.write_bytes(raw)

        def invoke(*arguments, optimized=False):
            return subprocess.run([sys.executable, *(['-O'] if optimized else []), str(mapper), str(input_path),
                                   *map(str, arguments)], capture_output=True, text=True, encoding='utf-8',
                                  errors='replace', timeout=12)

        normal_json, normal_md = root/'normal.json', root/'normal.md'
        done = invoke('--output', normal_json, '--markdown', normal_md)
        output = load(normal_json) if normal_json.exists() else {}
        check = audit(source, output)
        case('cli_conservation_and_unresolved_exit', done.returncode == 1 and check['status'] == 'PASS' and input_path.read_bytes() == raw,
             {'exit': done.returncode, 'audit_status': check['status'], 'input_preserved': input_path.read_bytes() == raw})
        optimized_json, optimized_md = root/'optimized.json', root/'optimized.md'
        done = invoke('--output', optimized_json, '--markdown', optimized_md, optimized=True)
        same = normal_json.exists() and optimized_json.exists() and normal_md.exists() and optimized_md.exists() and normal_json.read_bytes() == optimized_json.read_bytes() and normal_md.read_bytes() == optimized_md.read_bytes()
        case('optimized_byte_replay', done.returncode == 1 and same, {'exit': done.returncode, 'byte_identical': same})
        alias = root/'linked-source.json'
        os.link(input_path, alias)
        done = invoke('--output', alias)
        preserved = input_path.read_bytes() == raw
        case('hardlinked_input_preserved', done.returncode == 2 and preserved,
             {'exit': done.returncode, 'input_preserved': preserved})
        # Restore only our generated temporary fixture after a defective producer.
        alias.unlink(); input_path.write_bytes(raw)
        target = root/'partial.json'
        done = invoke('--output', target, '--markdown', root/'missing-parent'/'report.md')
        case('invalid_second_destination_no_partial_report', done.returncode == 2 and not target.exists(),
             {'exit': done.returncode, 'json_report_exists': target.exists()})
        done = invoke('--markdown', root/'another-missing-parent'/'report.md')
        case('invalid_markdown_no_partial_stdout', done.returncode == 2 and not done.stdout,
             {'exit': done.returncode, 'stdout_bytes': len(done.stdout.encode('utf-8'))})
        input_path.write_text('['*1200 + '0' + ']'*1200, encoding='utf-8')
        done = invoke()
        case('deep_input_clean_invalid_exit', done.returncode == 2 and 'Traceback' not in done.stderr and not done.stdout,
             {'exit': done.returncode, 'traceback': 'Traceback' in done.stderr})
        input_path.write_text('{"schema":1,"schema":2}', encoding='utf-8')
        done = invoke()
        case('duplicate_json_keys_rejected', done.returncode == 2 and 'Traceback' not in done.stderr,
             {'exit': done.returncode, 'traceback': 'Traceback' in done.stderr})
        literal = '*[literal](synthetic://identifier)*'
        special = {'schema': module.SCHEMA, 'records': [{'namespace': 'audit', 'kind': 'source', 'id': literal,
                   'revision': 'v1', 'synthetic': True, 'source_locators': ['synthetic://source'], 'payload': {}}]}
        rendered = module.render_markdown(module.reconcile(special))
        row = next((line for line in rendered.splitlines() if line.startswith('|audit|source|')), '')
        cell = row.split('|')[3] if row else ''
        escaped = html.unescape(cell) == literal and not any(char in cell for char in '*[]()')
        case('markdown_identifier_literal_entities', escaped,
             {'literal_roundtrip': html.unescape(cell) == literal, 'raw_markdown_punctuation_remains': any(char in cell for char in '*[]()')})
    return {'schema': 'uiowa.identity-probe.v1', 'mapper_blob': actual_blob, 'synthetic_only': True,
            'status': 'PASS' if all(c['status'] == 'PASS' for c in cases) else 'FAIL',
            'passed': sum(c['status'] == 'PASS' for c in cases), 'total': len(cases), 'cases': cases,
            'limits': ['These cases are not a filesystem-wide transaction proof or a security certification.',
                       'The Markdown case checks literal numeric-entity rendering for the supplied punctuation fixture.',
                       'Equivalence semantics and source authenticity are outside this probe.']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mapper', type=Path, required=True)
    parser.add_argument('--expected-blob', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    try:
        result = run(args.mapper, args.expected_blob)
        text = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + '\n'
        if args.output:
            with args.output.open('x', encoding='utf-8', newline='\n') as target:
                target.write(text)
        else:
            sys.stdout.write(text)
        return 0 if result['status'] == 'PASS' else 1
    except (AuditInputError, OSError, ValueError, RecursionError, subprocess.TimeoutExpired) as exc:
        print(f'identity-probe: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
