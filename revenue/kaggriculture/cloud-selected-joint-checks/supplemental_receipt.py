# SPDX-License-Identifier: Apache-2.0
"""Pure supplemental evidence helper for the existing joint receipt reader.

Consumes already-read bytes and declared source metadata. No filesystem access,
archive extraction, code import from inputs, test execution, or network calls.
"""
from __future__ import annotations

import json
import re
from typing import Any, Mapping

LAB = 'revenue/kaggriculture/cloud-execution-lab/'
MARKET = 'revenue/kaggriculture/cloud-selected-market-checks/'
ADAPTIVE = 'revenue/kaggriculture/cloud-market-game-theory/adaptive/'
COVER = 'revenue/kaggriculture/cloud-composition-cases/cover/'
WORKFLOW = '.github/workflows/titan-selected-projection.yml'
SUPPLEMENTS = {
    'loader': ('loader-tests.log', 'loader-results.json', 7,
               (MARKET + 'test_engine_binding.py',)),
    'empty_lot': ('empty-lot-tests.log', None, 15, (MARKET + 'test_empty_lot.py',)),
    'joined_wrapper': ('joined-wrapper-tests.log', None, 6,
                      (LAB + 'test_ordered_selected_sell.py', LAB + 'ordered_selected_sell.py')),
    'capture_binding': ('capture-binding-tests.log', 'capture-binding-results.json', 22,
                        (ADAPTIVE + 'test_capture_binding.py', ADAPTIVE + 'runtime.py',
                         LAB + 'selected_sell_core.py')),
    'score_schedule': ('score-schedule-tests.log', None, 10,
                       (LAB + 'test_score_schedule.py', LAB + 'selected_sell_core.py')),
    'workflow_bindings': ('workflow-bindings-tests.log', None, 8,
                          (COVER + 'test_regression_bindings.py', WORKFLOW)),
}
LOADER_SOURCES = {
    'checker': MARKET + 'check_market_contracts.py',
    'evaluator': LAB + 'reference/evaluator/evaluate.py',
    'loader': LAB + 'reference/evaluator/loader.py',
}


STRESS = 'revenue/kaggriculture/cloud-economic-stress/'
LATE_SUPPLEMENTS = {
    'deadline_cancellation': ('deadline-cancellation-tests.log', 'deadline-cancellation.json', 18,
                              (STRESS + 'cancellation/test_deadline_cancellation.py',)),
    'ledger_schedule': ('ledger-schedule-tests.log', 'ledger-schedule-results.json', 20,
                        (MARKET + 'test_ledger_schedule.py',)),
}
CANCELLATION_CLOSURE = (
    STRESS + 'test_runner.py', STRESS + 'cancellation/measure_cancellation.py',
    STRESS + 'cancellation/source/plan_overlay_commit_excerpt.py',
)
LEDGER_SOURCES = {name: LAB + name for name in (
    'selected_action_sell.py', 'selected_sell_core.py', 'mechanics.py',
    'reference/decision/decision.py')}
LEDGER_ENGINE = {name: LAB + 'reference/engine/' + name
                 for name in ('kaggriculture.py', 'kaggriculture.json', 'utils.py')}
LEDGER_REFERENCE = MARKET + 'fixtures/ledger_feasible_0364fa0a.py'
LEDGER_COUNTS = ('feasibility_comparisons', 'transform_comparisons',
                 'ordered_capacity_comparisons', 'official_market_calls')
SUPPLEMENTS.update(LATE_SUPPLEMENTS)


def integer(value: Any) -> bool:
    return type(value) is int and value >= 0


def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def finite_json(value: str) -> Any:
    raise ValueError(f'non-finite JSON value: {value}')


def inspect_supplemental(members: Mapping[str, bytes], snapshot: Mapping[str, Any],
                         core_receipt: Mapping[str, Any], *, require_all: bool = False) -> dict[str, Any]:
    """Check represented supplemental suites without altering caller-owned inputs.

    The existing reader remains responsible for archive digest, checkout/run,
    core suite validation and source/engine binding. Aggregate report schemas
    and further suites remain the caller's responsibility. A represented suite
    has its test-source snapshot row or a log/report member. Shared runtime
    dependencies alone do not declare that a newer suite ran. require_all also
    requests missing suites in older artifacts without relabeling old results.
    """
    problems: list[dict[str, str]] = []
    suites: dict[str, Any] = {}
    sources: dict[str, str] = {}
    def problem(level: str, detail: str) -> None:
        problems.append({'level': level, 'detail': detail})

    def obj(name: str) -> dict[str, Any] | None:
        if name not in members:
            problem('missing', f'missing {name}')
            return None
        try:
            if not isinstance(members[name], bytes):
                raise ValueError('member is not bytes')
            value = json.loads(members[name].decode('utf-8'), object_pairs_hook=unique_object,
                               parse_constant=finite_json)
            if not isinstance(value, dict):
                raise ValueError('expected a JSON object')
            return value
        except (ValueError, UnicodeError) as exc:
            problem('failure', f'invalid {name}: {exc}')
            return None

    files = snapshot.get('files', {})
    if not isinstance(files, dict):
        problem('failure', 'supplemental snapshot files is not an object')
        files = {}

    def source(name: str) -> str | None:
        row = files.get(name)
        if row is None:
            problem('missing', f'supplemental snapshot has no source: {name}')
            return None
        digest = row.get('sha256') if isinstance(row, dict) else None
        if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            problem('failure', f'invalid supplemental source hash: {name}')
            return None
        sources[name] = digest
        return digest

    def compare(actual: Any, expected: Any, label: str) -> None:
        if actual is None:
            problem('missing', f'{label}: missing value')
        elif expected is not None and (type(actual) is not type(expected) or actual != expected):
            problem('failure', f'{label}: differs from declared source/results')

    for label, (log_name, report_name, minimum, paths) in SUPPLEMENTS.items():
        represented = (log_name in members or report_name in members or paths[0] in files)
        if not represented and not require_all:
            continue
        for name in paths:
            source(name)
        summary: dict[str, Any] = {'test_methods': None, 'reported_pass': False,
                                   'minimum_methods': minimum, 'log': log_name,
                                   'binding': 'single artifact workflow checkout and source snapshot'}
        suites[label] = summary
        if log_name not in members:
            problem('missing', f'missing {log_name}')
        else:
            try:
                if not isinstance(members[log_name], bytes):
                    raise ValueError('log is not bytes')
                text = members[log_name].decode('utf-8').replace('\r\n', '\n')
            except (ValueError, UnicodeError):
                text = ''
                problem('failure', f'invalid UTF-8: {log_name}')
            counts = list(re.finditer(r'^Ran (\d+) tests? in [0-9.eE+-]+s[ \t]*$', text, re.MULTILINE))
            endings = list(re.finditer(r'^(OK(?: \([^\n]*\))?|FAILED(?: \([^\n]*\))?)[ \t]*$',
                                       text, re.MULTILINE))
            if re.search(r'^FAILED(?: |$)', text, re.MULTILINE):
                problem('failure', f'{label}: unittest failure footer')
            if len(counts) != 1 or len(endings) != 1 or endings[0].start() < counts[0].end():
                problem('missing', f'{label}: incomplete or ambiguous unittest completion')
            else:
                count, ending = int(counts[0].group(1)), endings[0].group(1).strip()
                summary.update(test_methods=count, reported_pass=ending == 'OK')
                if count < minimum:
                    problem('failure', f'{label}: below required {minimum} methods')
                if ending.startswith('FAILED'):
                    problem('failure', f'{label}: unittest reports failure')
                elif ending != 'OK':
                    problem('missing', f'{label}: qualified completion is not full coverage')
        if report_name is None:
            continue
        report = obj(report_name)
        if report is None:
            continue
        if label == 'deadline_cancellation':
            count = report.get('tests_run')
            if not integer(count) or count < minimum:
                problem('failure', 'deadline_cancellation: invalid/below-coverage tests_run')
            else:
                compare(count, summary['test_methods'], 'deadline_cancellation count')
            for key in ('failures', 'errors', 'skipped'):
                value = report.get(key)
                if not isinstance(value, list):
                    problem('failure', f'deadline_cancellation: {key} must be a list')
                elif value:
                    problem('missing' if key == 'skipped' else 'failure',
                            f'deadline_cancellation: nonempty {key}')
            new, inherited = (report.get('new_regression_methods'),
                              report.get('unchanged_upstream_guard_methods'))
            if (not integer(new) or new < 15 or not integer(inherited)
                    or inherited != 3 or not integer(count) or new + inherited != count):
                problem('failure', 'deadline_cancellation: inconsistent new/inherited partition')
            summary.update(new_regression_methods=new,
                           unchanged_upstream_guard_methods=inherited)
            compare(report.get('adapter_sha256'), source(STRESS + 'deadline_adapter.py'),
                    'deadline_cancellation adapter')
            for name in CANCELLATION_CLOSURE:
                source(name)
            continue
        if label == 'ledger_schedule':
            count = report.get('test_methods')
            if not integer(count) or count < minimum:
                problem('failure', 'ledger_schedule: invalid/below-coverage test_methods')
            else:
                compare(count, summary['test_methods'], 'ledger_schedule count')
            for key in ('failures', 'errors', 'skipped'):
                value = report.get(key)
                if not integer(value):
                    problem('failure', f'ledger_schedule: invalid {key}')
                elif value:
                    problem('missing' if key == 'skipped' else 'failure',
                            f'ledger_schedule: nonzero {key}')
            if report.get('successful') is not True:
                problem('failure', 'ledger_schedule: successful is not true')
            if (not integer(report.get('full_games')) or report['full_games'] != 0
                    or report.get('game_seeds') != []):
                problem('failure', 'ledger_schedule: unexpected gameplay/seed scope')
            for field, paths in (('sources_sha256', LEDGER_SOURCES),
                                 ('engine_sha256', LEDGER_ENGINE)):
                hashes = report.get(field)
                if not isinstance(hashes, dict):
                    problem('failure', f'ledger_schedule: {field} is not an object')
                    hashes = {}
                for key, name in paths.items():
                    compare(hashes.get(key), source(name), f'ledger_schedule {field} {key}')
            compare(report.get('reference_method_sha256'), source(LEDGER_REFERENCE),
                    'ledger_schedule reference method')
            counts = report.get('counts')
            if not isinstance(counts, dict):
                problem('failure', 'ledger_schedule: counts is not an object')
                counts = {}
            for key in LEDGER_COUNTS:
                if not integer(counts.get(key)) or counts[key] <= 0:
                    problem('failure', f'ledger_schedule: missing positive {key}')
            summary['comparisons'] = {key: counts.get(key) for key in LEDGER_COUNTS}
            continue
        if label == 'capture_binding':
            # The actual producer uses a nested tests object and has no schema
            # field. Do not invent the loader's schema/count shape for it.
            tests = report.get('tests')
            if not isinstance(tests, dict):
                problem('failure', 'capture_binding: tests is not an object')
                tests = {}
            count = tests.get('run')
            if not integer(count) or count < minimum:
                problem('failure', 'capture_binding: invalid/below-coverage tests.run')
            else:
                compare(count, summary['test_methods'], 'capture_binding count')
            for key in ('failures', 'errors'):
                if not integer(tests.get(key)) or tests[key] != 0:
                    problem('failure', f'capture_binding: invalid/nonzero tests.{key}')
            if tests.get('success') is not True:
                problem('failure', 'capture_binding: tests.success is not true')
            if (not integer(report.get('games')) or report['games'] != 0 or
                    report.get('seeds_consumed', []) != []):
                problem('failure', 'capture_binding: unexpected gameplay/seed scope')
            compare(report.get('runtime_sha256'), source(ADAPTIVE + 'runtime.py'),
                    'capture_binding runtime')
            compare(report.get('optimizer_sha256'), source(LAB + 'selected_sell_core.py'),
                    'capture_binding optimizer')
            continue
        compare(report.get('schema'), 'titan.selected-market-loader-tests.v1', 'loader schema')
        count = report.get('test_methods')
        if not integer(count) or count < minimum:
            problem('failure', 'loader: invalid/below-coverage test_methods')
        else:
            compare(count, summary['test_methods'], 'loader count')
        for key in ('failures', 'errors'):
            if not integer(report.get(key)) or report[key] != 0:
                problem('failure', f'loader: invalid/nonzero {key}')
        if report.get('successful') is not True:
            problem('failure', 'loader: successful is not true')
        if not integer(report.get('game_panels')) or report['game_panels'] != 0 or report.get('seeds_consumed') != []:
            problem('failure', 'loader: unexpected gameplay/seed scope')
        hashes = report.get('source_sha256', {})
        if not isinstance(hashes, dict):
            problem('failure', 'loader: source_sha256 is not an object')
            hashes = {}
        for key, name in LOADER_SOURCES.items():
            compare(hashes.get(key), source(name), 'loader ' + key)

    problems = [dict(pair) for pair in dict.fromkeys(tuple(p.items()) for p in problems)]
    status = ('FAIL' if any(p['level'] == 'failure' for p in problems) else
              'INCOMPLETE' if problems else 'COMPLETE_PASS')
    total = sum(s['test_methods'] or 0 for s in suites.values())
    core_count = core_receipt.get('reported_test_methods')
    return {
        'schema': 'titan.selected-joint-supplemental.v1', 'status': status,
        'suites': suites, 'sources': sources, 'problems': problems,
        'represented_suite_count': len(suites), 'reported_test_methods': total,
        'core_reported_test_methods': core_count,
        'core_plus_supplemental_methods': core_count + total if integer(core_count) else None,
        'core_status': core_receipt.get('status'),
        'checkout': core_receipt.get('checkout'),
        'tests_rerun': 0, 'game_panels': 0, 'seeds_consumed': [],
        'scope': 'Only represented suites named by SUPPLEMENTS. '
                 'Core status, aggregate summaries and further suites remain separate. '
                 'Not whole-repository CI, gameplay strength or execution attestation.',
    }
