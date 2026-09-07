# SPDX-License-Identifier: Apache-2.0
"""Read one existing TITAN validation ZIP; never execute its contents or rerun tests."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any
import zipfile

ROOT = 'revenue/kaggriculture/'
LAB = ROOT + 'cloud-execution-lab/'
PROJECTION = ROOT + 'cloud-selected-projection/'
MARKET = ROOT + 'cloud-selected-market-checks/'
ENGINE_FILES = ('kaggriculture.py', 'kaggriculture.json', 'utils.py')
RUNTIME_FILES = ('selected_action_sell.py', 'selected_sell_core.py', 'mechanics.py',
                 'reference/decision/decision.py')
SUITES = {
    'original': ('original-seller-tests.log', None, 16, LAB + 'test_selected_action_sell.py'),
    'projection': ('projection-tests.log', 'projection-results.json', 21, PROJECTION + 'test_projection.py'),
    'market': ('market-tests.log', 'market-results.json', 14, MARKET + 'check_market_contracts.py'),
}
MAX_MEMBER = 8 * 1024 * 1024
MAX_TOTAL = 32 * 1024 * 1024


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def read_members(path: Path) -> dict[str, bytes]:
    """Read bounded text evidence only, without extracting archive paths."""
    with zipfile.ZipFile(path) as archive:
        infos = [info for info in archive.infolist() if not info.is_dir()]
        if sum(info.file_size for info in infos) > MAX_TOTAL:
            raise ValueError('archive uncompressed size exceeds 32 MiB')
        result: dict[str, bytes] = {}
        for info in infos:
            parts = PurePosixPath(info.filename)
            if parts.is_absolute() or '..' in parts.parts or '\\' in info.filename:
                raise ValueError('ambiguous archive member path')
            name = parts.name
            if name in result:
                raise ValueError(f'duplicate or ambiguous member basename: {name}')
            if info.file_size > MAX_MEMBER:
                raise ValueError(f'member exceeds 8 MiB: {name}')
            result[name] = archive.read(info)
        return result


def integer(value: Any) -> bool:
    return type(value) is int and value >= 0


def inspect_archive(path: Path, *, expected_sha256: str | None = None,
                    expected_checkout: str | None = None,
                    expected_run_id: str | None = None,
                    expected_attempt: str | None = None,
                    market_report: str = 'market-results.json',
                    market_log: str = 'market-tests.log') -> dict[str, Any]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    problems: list[dict[str, str]] = []
    summaries: dict[str, Any] = {}
    reports: dict[str, dict[str, Any]] = {}
    sources: dict[str, Any] = {}
    snapshot: dict[str, Any] = {}

    def problem(level: str, detail: str) -> None:
        problems.append({'level': level, 'detail': detail})

    expected = expected_sha256.removeprefix('sha256:').lower() if expected_sha256 else None
    digest_ok = None if expected is None else expected == digest
    if expected is None:
        problem('missing', 'provider artifact digest was not supplied')
    elif not re.fullmatch(r'[0-9a-f]{64}', expected):
        problem('failure', 'invalid expected SHA-256')
    elif not digest_ok:
        problem('failure', 'artifact SHA-256 differs from supplied provider digest')

    try:
        members = read_members(path)
    except (ValueError, OSError, zipfile.BadZipFile, RuntimeError) as exc:
        members = {}
        problem('failure', f'cannot read evidence ZIP: {exc}')

    def obj(name: str) -> dict[str, Any] | None:
        if name not in members:
            problem('missing', f'missing {name}')
            return None
        try:
            value = json.loads(members[name].decode('utf-8'), object_pairs_hook=unique_object)
            if not isinstance(value, dict):
                raise ValueError('expected a JSON object')
            return value
        except (ValueError, UnicodeError) as exc:
            problem('failure', f'invalid {name}: {exc}')
            return None

    snapshot = obj('SOURCE-SNAPSHOT.json') or {}
    files = snapshot.get('files', {})
    if not isinstance(files, dict):
        problem('failure', 'snapshot files is not an object')
        files = {}
    for field, pattern in (('checkout', r'[0-9a-f]{40}'), ('run_id', r'[1-9][0-9]*'),
                           ('attempt', r'[1-9][0-9]*')):
        value = snapshot.get(field)
        if value is None:
            problem('missing', f'snapshot has no {field}')
        elif not re.fullmatch(pattern, str(value)):
            problem('failure', f'invalid snapshot {field}')
    for field, expected_value in (('checkout', expected_checkout), ('run_id', expected_run_id),
                                  ('attempt', expected_attempt)):
        if expected_value is not None and str(snapshot.get(field)) != str(expected_value):
            problem('failure', f'snapshot {field} differs from expected value')

    def source(name: str) -> str | None:
        entry = files.get(name)
        if entry is None:
            problem('missing', f'snapshot has no source: {name}')
            return None
        sha = entry.get('sha256') if isinstance(entry, dict) else None
        if not isinstance(sha, str) or not re.fullmatch(r'[0-9a-f]{64}', sha):
            problem('failure', f'invalid source SHA-256: {name}')
            return None
        sources[name] = sha
        return sha

    for name in RUNTIME_FILES:
        source(LAB + name)
    source(PROJECTION + 'projection.py')
    for name in ENGINE_FILES:
        source(LAB + 'reference/engine/' + name)

    def match_source(value: Any, name: str, description: str) -> None:
        expected_source = sources.get(name) or source(name)
        if value is None:
            problem('missing', f'{description}: no reported hash')
        elif not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
            problem('failure', f'{description}: invalid reported hash')
        elif expected_source is not None and value != expected_source:
            problem('failure', f'{description}: source differs from snapshot')

    for label, (log_name, report_name, minimum, test_path) in SUITES.items():
        if label == 'market':
            log_name, report_name = market_log, market_report
        source(test_path)
        summary: dict[str, Any] = {'minimum_methods': minimum, 'test_methods': None,
                                   'log': log_name, 'reported_pass': False}
        summaries[label] = summary
        text = ''
        if log_name not in members:
            problem('missing', f'missing {log_name}')
        else:
            try:
                text = members[log_name].decode('utf-8')
            except UnicodeError:
                problem('failure', f'invalid UTF-8: {log_name}')
            counts = re.findall(r'^Ran (\d+) tests? in [^\n]+$', text, re.MULTILINE)
            endings = re.findall(r'^(OK(?: \([^\n]*\))?|FAILED(?: \([^\n]*\))?)$', text, re.MULTILINE)
            if re.search(r'^FAILED(?: |$)', text, re.MULTILINE):
                problem('failure', f'{label}: unittest failure footer is present')
            if len(counts) != 1 or len(endings) != 1:
                problem('missing', f'{label}: missing or ambiguous unittest completion')
            else:
                count = int(counts[0])
                summary['test_methods'] = count
                summary['reported_pass'] = endings[0] == 'OK'
                if count < minimum:
                    problem('failure', f'{label}: {count} methods is below required coverage {minimum}')
                if endings[0].startswith('FAILED'):
                    problem('failure', f'{label}: unittest reports failure')
                elif endings[0] != 'OK':
                    problem('missing', f'{label}: skipped/qualified completion is not full coverage')
        if report_name is None:
            continue
        report = obj(report_name)
        if report is None:
            continue
        reports[label] = report
        count_key = 'tests_run' if label == 'projection' else 'test_methods'
        for key in (count_key, 'failures', 'errors'):
            if not integer(report.get(key)):
                problem('failure', f'{label}: invalid {key}')
        if integer(report.get(count_key)):
            if report[count_key] < minimum:
                problem('failure', f'{label}: report omits required methods')
            if summary['test_methods'] is not None and report[count_key] != summary['test_methods']:
                problem('failure', f'{label}: report and log method counts differ')
        if report.get('failures') != 0 or report.get('errors') != 0:
            problem('failure', f'{label}: report contains failures/errors')
        engine = report.get('engine_sha256')
        if not isinstance(engine, dict):
            problem('missing', f'{label}: engine hashes absent')
            engine = {}
        for name in ENGINE_FILES:
            match_source(engine.get(name), LAB + 'reference/engine/' + name, f'{label} engine {name}')
        if label == 'projection':
            match_source(report.get('seller_sha256'), LAB + 'selected_action_sell.py', 'projection seller')
            match_source(report.get('projection_sha256'), PROJECTION + 'projection.py', 'projection implementation')
            for key in ('differential_cases', 'interpreter_transitions'):
                if not integer(report.get(key)) or report[key] == 0:
                    problem('failure', f'projection: missing positive {key}')
                else:
                    summary[key] = report[key]
        else:
            reported_sources = report.get('sources', {})
            if not isinstance(reported_sources, dict):
                problem('failure', 'market: sources is not an object')
                reported_sources = {}
            for name in RUNTIME_FILES:
                match_source(reported_sources.get(name), LAB + name, f'market {name}')
            if report.get('schema') != 'titan.selected-market-checks.v1':
                problem('failure', 'market: unexpected report schema')
            if report.get('successful') is not True:
                problem('failure', 'market: successful is not true')
            if report.get('game_panels') != 0 or report.get('seeds_consumed') != []:
                problem('failure', 'market: unexpected gameplay/seed scope')
            cases = report.get('official_market_cases')
            if not integer(cases) or cases == 0:
                problem('failure', 'market: no positive official market-case count')
            else:
                summary['official_market_cases'] = cases

    # Repeated source lookup diagnostics are rendered once, preserving order.
    problems = [dict(pair) for pair in dict.fromkeys(tuple(item.items()) for item in problems)]
    status = ('FAIL' if any(item['level'] == 'failure' for item in problems) else
              'INCOMPLETE' if problems else 'COMPLETE_PASS')
    return {
        'schema': 'titan.selected-joint-receipt.v1', 'status': status,
        'artifact_sha256': digest, 'provider_digest_matched': digest_ok,
        'checkout': snapshot.get('checkout'), 'run_id': snapshot.get('run_id'),
        'attempt': snapshot.get('attempt'), 'sources': sources, 'suites': summaries,
        'reported_test_methods': sum(item['test_methods'] or 0 for item in summaries.values()),
        'problems': problems, 'tests_rerun': 0, 'game_panels': 0, 'seeds_consumed': [],
        'scope': 'One existing artifact: reported suite results and declared pre-execution source alignment. '
                 'Not independent execution attestation, whole-repository CI, a gameplay result, or policy promotion.',
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--expected-sha256')
    parser.add_argument('--expected-checkout')
    parser.add_argument('--expected-run-id')
    parser.add_argument('--expected-attempt')
    parser.add_argument('--market-report', default='market-results.json')
    parser.add_argument('--market-log', default='market-tests.log')
    parser.add_argument('--json-output', type=Path)
    args = parser.parse_args()
    try:
        report = inspect_archive(args.archive, expected_sha256=args.expected_sha256,
                                 expected_checkout=args.expected_checkout,
                                 expected_run_id=args.expected_run_id,
                                 expected_attempt=args.expected_attempt,
                                 market_report=args.market_report, market_log=args.market_log)
        rendered = json.dumps(report, indent=2, sort_keys=True) + '\n'
        if args.json_output:
            args.json_output.parent.mkdir(parents=True, exist_ok=True)
            args.json_output.write_text(rendered, encoding='utf-8')
        print(rendered, end='')
        return {'COMPLETE_PASS': 0, 'FAIL': 1, 'INCOMPLETE': 2}[report['status']]
    except (OSError, ValueError) as exc:
        print(json.dumps({'status': 'ERROR', 'detail': str(exc)}), file=sys.stderr)
        return 3


if __name__ == '__main__':
    raise SystemExit(main())
