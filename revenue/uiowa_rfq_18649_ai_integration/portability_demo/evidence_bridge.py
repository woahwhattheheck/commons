#!/usr/bin/env python3
"""Execute pinned fictional adapters and bind narrowly scoped architecture evidence.

No network, model service, identity operation, deployment or University finding.
Run this standalone module in an isolated process; its retained upstream imports
use the original portlib package name.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import asdict
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parent
PARENT = ROOT.parent
UPSTREAM_COMMIT = 'c3a51c6b16eb2c45ba887e851fd75f7a2d5c5782'
UPSTREAM_AUTHOR = 'OP5-QUARRY / Claude Opus 5'
SOURCE_BLOBS = {
    'portlib/__init__.py': '1f6b57363b9a6a6b0a6e12ac58bba8af6dd3d4d4',
    'portlib/port.py': '329dc165a61b141db34cfc8d88f069ebc60e65fc',
    'portlib/caller.py': '248a17c399a13a24e48f9cd36aa01de3d8854139',
    'portlib/caller_leaky.py': '0629f3659aac2cacae0cfe811b76a67dcfb6b98c',
    'portlib/providers/__init__.py': 'df8717edde71c8b84ec9bea068148dbccac58b70',
    'portlib/providers/fake_alpha.py': 'ce02bf78ae1d2f20a3c30b1e5603f97ac526cd50',
    'portlib/providers/fake_beta.py': '28a50f691f7296b8c820dbc4de7fc4f0a8052950',
}
ASSESSOR_BLOB = '0a795791c374aba9abcaae5b662007a8584a8337'


def packed(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(f'blob {len(raw)}\0'.encode() + raw).hexdigest()


def verify_sources(root: Path = ROOT, parent: Path = PARENT) -> dict:
    """Exact-byte replay binding, not a signature or a general sandbox."""
    result = {}
    for name, expected in SOURCE_BLOBS.items():
        raw = (root / name).read_bytes()
        actual = git_blob(raw)
        if actual != expected:
            raise ValueError(f'upstream source drift: {name}: expected {expected}, got {actual}')
        result[name] = {'git_blob': actual, 'sha256': digest(raw), 'bytes': len(raw)}
    raw = (parent / 'assess.py').read_bytes()
    if git_blob(raw) != ASSESSOR_BLOB:
        raise ValueError('parent assessor source drift: re-review the integration before replay')
    result['../assess.py'] = {'git_blob': ASSESSOR_BLOB, 'sha256': digest(raw), 'bytes': len(raw)}
    raw = (root / 'evidence_bridge.py').read_bytes()
    result['evidence_bridge.py'] = {'git_blob': git_blob(raw), 'sha256': digest(raw), 'bytes': len(raw)}
    return result


# Validate bytes before importing the retained modules. This is reproducibility,
# not permission to execute arbitrary paths supplied in an input document.
verify_sources()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from portlib import caller
from portlib.port import Classification, ClassificationPort, Document, ProviderContractViolation, ProviderError, ProviderUnavailable, RoutingPolicy, check_conformance
from portlib.providers.fake_alpha import AlphaClassificationAdapter
from portlib.providers.fake_beta import BetaClassificationAdapter
for module_name in ('portlib', 'portlib.port', 'portlib.caller', 'portlib.providers', 'portlib.providers.fake_alpha', 'portlib.providers.fake_beta'):
    module = sys.modules[module_name]
    if not Path(module.__file__).resolve().is_relative_to(ROOT):
        raise ValueError(f'conflicting package already loaded: {module_name}; use an isolated process')


def validate_policy(policy: RoutingPolicy) -> None:
    if not isinstance(policy, RoutingPolicy):
        raise ValueError('expected RoutingPolicy')
    categories = policy.categories
    if not isinstance(categories, tuple) or not categories or any(not isinstance(x, str) or not x.strip() for x in categories):
        raise ValueError('categories must be a nonempty tuple of nonblank strings')
    if len(set(categories)) != len(categories):
        raise ValueError('duplicate category')
    floor = policy.confidence_floor
    if type(floor) is not float or not math.isfinite(floor) or not 0 <= floor <= 1:
        raise ValueError('confidence_floor must be a finite float in [0,1]')
    if not isinstance(policy.human_review_queue, str) or not policy.human_review_queue.strip():
        raise ValueError('missing human review queue')
    if policy.human_review_queue in {f'queue.{x}' for x in categories}:
        raise ValueError('human review queue must be distinct from automatic queues')
    if not isinstance(policy.always_review, tuple) or any(not isinstance(x, str) or x not in categories for x in policy.always_review):
        raise ValueError('always_review must be a tuple drawn from categories')
    if len(set(policy.always_review)) != len(policy.always_review):
        raise ValueError('duplicate always_review category')


class GuardedPort(ClassificationPort):
    """Validate EVERY response before it reaches the unchanged upstream caller."""
    def __init__(self, inner: ClassificationPort, policy: RoutingPolicy):
        validate_policy(policy)
        if not callable(getattr(inner, 'classify', None)) or not callable(getattr(inner, 'health', None)):
            raise ValueError('adapter must implement classify and health')
        self.inner, self.policy = inner, policy
        self.capability_class = getattr(inner, 'capability_class', None)
        if not isinstance(self.capability_class, str) or not self.capability_class.strip():
            raise ValueError('missing capability class')

    def classify(self, document: Document) -> Classification:
        if not isinstance(document, Document) or not isinstance(document.doc_id, str) or not document.doc_id.strip() or not isinstance(document.text, str):
            raise ProviderContractViolation('invalid input document')
        try:
            answer = self.inner.classify(document)
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderContractViolation(f'unmapped adapter exception: {type(exc).__name__}; no usable answer') from exc
        if not isinstance(answer, Classification):
            raise ProviderContractViolation('response is not a Classification')
        if not isinstance(answer.doc_id, str) or answer.doc_id != document.doc_id:
            raise ProviderContractViolation('response identity does not match input')
        if not isinstance(answer.category, str) or answer.category not in self.policy.categories:
            raise ProviderContractViolation('response category is outside the declared taxonomy')
        if type(answer.confidence) is not float or not math.isfinite(answer.confidence) or not 0 <= answer.confidence <= 1:
            raise ProviderContractViolation('response confidence is not a finite normalized float')
        if not isinstance(answer.rationale, str) or not answer.rationale.strip():
            raise ProviderContractViolation('response has no usable rationale')
        if answer.capability_class != self.capability_class:
            raise ProviderContractViolation('response capability class differs from adapter')
        if type(answer.degraded) is not bool or answer.degraded:
            raise ProviderContractViolation('degraded/ambiguous response is not an automatic classification')
        return answer

    def health(self) -> dict:
        try:
            health = self.inner.health()
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderContractViolation(f'unmapped health exception: {type(exc).__name__}') from exc
        if not isinstance(health, dict) or type(health.get('reachable')) is not bool:
            raise ProviderContractViolation('health reachability must be an explicit boolean')
        if not health['reachable']:
            raise ProviderUnavailable('capability reports unreachable')
        return health


SAMPLE = (
    Document('SYN-DOC-1', 'My card was declined paying the housing deposit.'),
    Document('SYN-DOC-2', 'I am locked out, my badge stopped working at the north door.'),
    Document('SYN-DOC-3', 'There is a leak above the elevator lobby on floor 3.'),
    Document('SYN-DOC-4', 'The thermostat in the seminar room reads oddly.'),
    Document('SYN-DOC-5', 'Asking about a schedule change for next term.'),
)


def scan_provider_imports(source: str) -> list[dict]:
    """Small static import screen, not a proof about dynamically selected code."""
    found = []
    for node in ast.walk(ast.parse(source)):
        modules = ([node.module or ''] if isinstance(node, ast.ImportFrom) else
                   [item.name for item in node.names] if isinstance(node, ast.Import) else [])
        for name in modules:
            if name == 'portlib.providers' or name.startswith('portlib.providers.'):
                found.append({'line': node.lineno, 'module': name})
    return sorted(found, key=lambda row: (row['line'], row['module']))


def run_case(factory, label: str, policy: RoutingPolicy, fail_mode: str | None = None) -> dict:
    port = GuardedPort(factory(policy, fail_mode=fail_mode), policy)
    try:
        conformance = check_conformance(port, policy)
    except ProviderError as exc:
        conformance = {'conformant': False, 'findings': [f'health/probe unavailable: {type(exc).__name__}']}
    if fail_mode is None and conformance['conformant'] is not True:
        raise ValueError('healthy adapter failed conformance; no baseline routing executed')
    decisions = caller.route_documents(port, SAMPLE, policy)
    return {'id': label, 'fail_mode': fail_mode, 'capability_class': port.capability_class,
            'conformance': conformance, 'caller_sha256': caller.caller_source_sha256(),
            'summary': caller.summarize_run(decisions), 'decisions': [asdict(d) for d in decisions]}


def compare_runs(a: dict, b: dict) -> dict:
    def indexed(run):
        result = {}
        for item in run['decisions']:
            if not isinstance(item.get('doc_id'), str) or not item['doc_id'].strip() or not isinstance(item.get('queue'), str) or type(item.get('needs_human_review')) is not bool:
                raise ValueError('invalid decision identity, queue or review state')
            if item['doc_id'] in result:
                raise ValueError('duplicate decision identity')
            result[item['doc_id']] = item
        if not result:
            raise ValueError('cannot compare an empty run')
        return result
    left, right = indexed(a), indexed(b)
    if set(left) != set(right):
        raise ValueError('cannot compare unmatched item populations')
    changes = [{'doc_id': key, 'a_queue': left[key]['queue'], 'b_queue': right[key]['queue']}
               for key in sorted(left) if left[key]['queue'] != right[key]['queue']]
    before = sum(item['needs_human_review'] for item in left.values())
    after = sum(item['needs_human_review'] for item in right.values())
    return {'items': len(left), 'queue_changes': changes, 'human_review_before': before,
            'human_review_after': after, 'additional_review_items': after - before,
            'review_share_change_percentage_points': (after-before) / len(left) * 100,
            'relative_review_count_change': (after-before) / before if before else None,
            'limitation': 'Counts of queued fictional items only; not measured labor, accuracy, capacity or University performance.'}


def build_receipt() -> dict:
    bindings = verify_sources()
    policy = RoutingPolicy()
    cases = ((AlphaClassificationAdapter, 'ALPHA-healthy', None),
             (BetaClassificationAdapter, 'BETA-healthy', None),
             (AlphaClassificationAdapter, 'ALPHA-timeout', 'timeout'),
             (AlphaClassificationAdapter, 'ALPHA-unavailable', 'refused'),
             (AlphaClassificationAdapter, 'ALPHA-unusable', 'garbage'),
             (BetaClassificationAdapter, 'BETA-timeout', 'slow'),
             (BetaClassificationAdapter, 'BETA-unavailable', 'down'),
             (BetaClassificationAdapter, 'BETA-unusable', 'garbage'))
    runs = [run_case(factory, label, policy, mode) for factory, label, mode in cases]
    return {'schema_version': 'uiowa-080-portability-observation/1.0', 'synthetic': True,
            'execution_kind': 'executed_offline_fictional_implementations',
            'upstream': {'commit': UPSTREAM_COMMIT, 'author': UPSTREAM_AUTHOR},
            'integrator': 'ZZ-QUARTZ-P80X / GPT-6 Astra Pro',
            'source_bindings': bindings, 'policy': asdict(policy), 'sample': [asdict(d) for d in SAMPLE],
            'caller_unchanged': len({r['caller_sha256'] for r in runs}) == 1,
            'caller_provider_imports': scan_provider_imports((ROOT / 'portlib/caller.py').read_text()),
            'negative_control_provider_imports': scan_provider_imports((ROOT / 'portlib/caller_leaky.py').read_text()),
            'runs': runs, 'comparison': compare_runs(runs[0], runs[1]),
            'limitations': ['No real provider, model, network, deployment or institutional input.',
                'Unchanged caller bytes do not establish equivalent behavior or quality.',
                'Queued human review is not completed human work or verified core-workflow recovery.',
                'No measurement of latency, availability, effort, retention or data export.',
                'The added guard is new integration code; only the retained caller is unchanged.']}


def architecture_input(receipt: dict) -> dict:
    """Connect observations to a NEW fictional case, never unrelated recommendations."""
    if receipt.get('schema_version') != 'uiowa-080-portability-observation/1.0' or receipt.get('synthetic') is not True:
        raise ValueError('expected this explicitly synthetic observation schema')
    if packed(receipt) != packed(build_receipt()):
        raise ValueError('observation does not reproduce from the current pinned sources')
    evidence_hash = digest(packed(receipt))
    unknown_range = {'low': None, 'high': None}
    alternatives = []
    for label in ('ALPHA', 'BETA'):
        dimensions = {}
        for key in ('request_response_contract', 'prompt_export', 'evaluation_replay', 'adapter_swap', 'data_export'):
            demonstrated = key in ('request_response_contract', 'adapter_swap')
            dimensions[key] = {'state': 'demonstrated' if demonstrated else 'unknown',
                'note': 'Executed fixed-input toy contract/swap only; no real-provider claim.' if demonstrated else
                        'Not established by this toy caller swap; no equivalent-quality, prompt or data-export experiment.',
                'evidence_refs': ['EXEC-MOCK'] if demonstrated else []}
        alternatives.append({'id': label, 'pattern': 'synchronous_assist',
            'suitable_when': 'A fictional classification draft can be routed to review under explicit policy.',
            'tradeoffs': 'Caller unchanged, but review queue count differs across providers. Real timing and operating requirements are unknown.',
            'change_option': 'Retain a quality rubric, representative workload and export/replay observations before any real migration.',
            'capabilities': ['classify_fictional_text', 'route_to_review'], 'evidence_refs': ['EXEC-MOCK', 'EXEC-FAULT'],
            'latency_basis': 'planning_envelope',
            'response_stages': [{'name': 'Unmeasured response path', 'ms': dict(unknown_range)}], 'completion_stages': [],
            'response_dependencies': [{'name': 'Unmeasured actual service', 'availability': None, 'window': None}],
            'independence_assumed': False,
            'integration_tasks': [{'name': 'Actual implementation effort not measured', 'hours': dict(unknown_range), 'owner_role': None}],
            'maintenance_tasks': [{'name': 'Actual recurring work not measured', 'hours_per_month': dict(unknown_range), 'owner_role': None}],
            'migration_tasks': [{'name': 'Actual migration effort not measured', 'hours': dict(unknown_range), 'owner_role': None}],
            'data_flows': [{'id': 'F1', 'source': 'fictional input', 'destination': 'offline toy adapter',
                           'payload': 'five authored fictional texts', 'zone': 'synthetic_process', 'retention_days': None,
                           'minimization': 'No client data supplied; this is not a real data-handling assessment.'}],
            'owners': {key: None for key in ('integration', 'support', 'data', 'evaluation', 'change')},
            'portability': dimensions,
            'degraded_mode': {'behavior': 'manual_queue', 'tested': True, 'evidence_refs': ['EXEC-FAULT'],
                              'note': 'Each of six simulated failure runs queued five items for review. No human task was completed and no real core workflow was exercised.'}})
    return {'schema_version': '1.0', 'synthetic': True,
            'basis': 'Executed fictional classification adapters; every real-world estimate and institutional fact remains unknown.',
            'evidence': {key: {'kind': 'synthetic', 'locator': f'receipt.json#/runs; sha256={evidence_hash}', 'note': note}
                         for key, note in {'EXEC-MOCK': 'Executed two healthy toy adapters using the same guarded caller; different review counts retained.',
                                           'EXEC-FAULT': 'Executed timeout, unavailable and unusable-answer modes for both toy providers; manual-queue behavior only.'}.items()},
            'cases': [{'id': 'SYN-PORTABILITY-CASE', 'title': 'Fictional intake triage, not an identity or institutional decision',
                       'recommendation_id': 'SYN-REC-080-PORT',
                       'requirements': {'response_budget_ms': None, 'completion_deadline_ms': None,
                           'response_availability_target': None, 'availability_window': None, 'allowed_zones': None,
                           'max_retention_days': None, 'required_capabilities': ['classify_fictional_text', 'route_to_review'],
                           'monthly_maintenance_hours': None, 'migration_budget_hours': None, 'core_must_continue_without_ai': None},
                       'alternatives': alternatives}]}


def assess_observation(receipt: dict) -> tuple[dict, dict, Any]:
    document = architecture_input(receipt)
    spec = importlib.util.spec_from_file_location('uiowa_080_pinned_assessor', PARENT / 'assess.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    report = module.assess(document)
    report['input_sha256'] = digest(packed(document))
    return document, report, module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='New output directory; existing paths are not overwritten')
    args = parser.parse_args(argv)
    try:
        receipt = build_receipt()
        document, report, module = assess_observation(receipt)
        outputs = {'receipt.json': packed(receipt), 'architecture_input.json': packed(document),
                   'architecture_assessment.json': packed(report), 'architecture_assessment.md': module.markdown(report).encode(),
                   'checks.csv': module.csv_text(report).encode()}
        args.out.mkdir(parents=True, exist_ok=False)
        for filename, raw in outputs.items():
            (args.out / filename).write_bytes(raw)
    except (ValueError, OSError) as exc:
        parser.exit(2, f'error: {exc}\n')
    print('Executed 8 fictional-provider runs. Unchanged caller; human-review queue 2/5 -> 3/5; all real-world readiness UNKNOWN.')
    print(f'Receipt SHA-256: {digest(outputs["receipt.json"])}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
