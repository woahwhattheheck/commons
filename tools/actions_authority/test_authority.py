from __future__ import annotations
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from .authority import classify
from .cli import main
from .common import EvidenceError, parse_json_bytes
HEAD = 'a' * 40
BASE = 'b' * 40
NOW = datetime(2026, 9, 13, 8, 30, tzinfo=timezone.utc)

def workflow(workflow_id=101, path='.github/workflows/ci.yml', name='CI'):
    return {'workflow_id': workflow_id, 'workflow_path': path, 'workflow_name': name}

def policy(*required):
    return {'schema_version': 'commons-actions-policy/v1', 'source': {'kind': 'repository_manifest', 'locator': f'{BASE}:.github/actions-authority-policy.json', 'source_sha256': 'sha256:' + 'c' * 64}, 'base_ref': 'refs/heads/main', 'base_sha': BASE, 'captured_at': '2026-09-13T08:24:00Z', 'required_workflows': list(required) or [workflow()]}

def inventory(total_count):
    return {'source': 'github-actions-runs', 'complete': True, 'total_count': total_count, 'pages': 1, 'next_url': None}

def job_inventory(total_count):
    return {'source': 'github-actions-jobs', 'complete': True, 'total_count': total_count, 'pages': 1, 'next_url': None}

def job(status='completed', conclusion='success', runner='GitHub Actions 1', runner_id=701, started='2026-09-13T08:20:02Z', steps=None, job_id=11):
    if steps is None and status == 'completed' and (conclusion == 'success'):
        steps = [{'name': 'test', 'status': 'completed', 'conclusion': 'success'}]
    return {'job_id': job_id, 'name': 'test', 'status': status, 'conclusion': conclusion, 'runner_id': runner_id, 'runner_name': runner, 'started_at': started, 'completed_at': '2026-09-13T08:21:00Z' if status == 'completed' else None, 'steps': steps}

def run(*, workflow_id=101, workflow_path='.github/workflows/ci.yml', workflow_name='CI', run_id=1, run_number=1, run_attempt=1, status='completed', conclusion='success', jobs=None):
    job_rows = [job()] if jobs is None else jobs
    return {'run_id': run_id, 'run_number': run_number, 'run_attempt': run_attempt, 'workflow_id': workflow_id, 'workflow_path': workflow_path, 'workflow_name': workflow_name, 'head_sha': HEAD, 'status': status, 'conclusion': conclusion, 'created_at': '2026-09-13T08:20:00Z', 'started_at': '2026-09-13T08:20:01Z' if status in {'in_progress', 'completed'} else None, 'completed_at': '2026-09-13T08:21:01Z' if status == 'completed' else None, 'jobs_inventory': job_inventory(len(job_rows)), 'jobs': job_rows}

def payload(*runs, required=None):
    rows = list(runs)
    return {'schema_version': 'commons-actions-evidence/v2', 'repository': 'acme/widget', 'head_sha': HEAD, 'captured_at': '2026-09-13T08:25:00Z', 'policy': policy(*(required or [workflow()])), 'inventory': inventory(len(rows)), 'runs': rows}

class AuthorityTests(unittest.TestCase):

    def test_01(self):
        receipt = classify(payload(run()), now=NOW)
        self.assertEqual(receipt['decision'], 'TERMINAL_GREEN')
        self.assertTrue(receipt['declared_policy_green'])
        self.assertFalse(receipt['merge_authorized'])
        self.assertEqual(receipt['authorization_scope'], 'CLASSIFICATION_ONLY')
        self.assertFalse(receipt['runner_exception_candidate'])

    def test_02(self):
        evidence = payload(run())
        evidence['schema_version'] = 'commons-actions-evidence/v1'
        with self.assertRaisesRegex(EvidenceError, 'v1 caller-curated authority is rejected'):
            classify(evidence, now=NOW)

    def test_03(self):
        old_green = run(run_id=10, run_number=40)
        new_red = run(run_id=11, run_number=41, run_attempt=2, conclusion='failure', jobs=[job(conclusion='failure')])
        receipt = classify(payload(old_green, new_red), now=NOW)
        self.assertEqual(receipt['decision'], 'TERMINAL_RED')
        row = receipt['required_workflows'][0]
        self.assertEqual(row['selected_run_id'], 11)
        self.assertEqual(row['selected_run_number'], 41)
        self.assertEqual(row['selected_run_attempt'], 2)
        self.assertEqual(row['older_exact_head_run_ids'], [10])

    def test_04(self):
        with self.assertRaisesRegex(EvidenceError, 'duplicate run_number'):
            classify(payload(run(run_id=1, run_number=7), run(run_id=2, run_number=7)), now=NOW)

    def test_05(self):
        cases = []
        cases.append(payload(run(run_id=1), run(run_id=2, workflow_path='.github/workflows/other.yml', run_number=2)))
        cases.append(payload(run(run_id=1), run(run_id=2, workflow_id=202, run_number=2)))
        cases.append(payload(run(run_id=1), run(run_id=2, run_number=2, workflow_id=202, workflow_path='.github/workflows/other.yml', workflow_name='CI')))
        for evidence in cases:
            with self.subTest(case=evidence['runs'][1]):
                with self.assertRaisesRegex(EvidenceError, 'maps to multiple'):
                    classify(evidence, now=NOW)

    def test_06(self):
        required = [workflow(101, '.github/workflows/ci.yml', 'CI')]
        impostor = run(workflow_id=202, workflow_path='.github/workflows/impostor.yml', workflow_name='CI')
        receipt = classify(payload(impostor, required=required), now=NOW)
        self.assertEqual(receipt['decision'], 'WAIT_MISSING')
        self.assertFalse(receipt['merge_authorized'])
        self.assertIsNone(receipt['required_workflows'][0]['selected_run_id'])
        self.assertEqual(receipt['ignored_extra_workflows'][0]['workflow_id'], 202)

    def test_07(self):
        evidence = payload(run())
        evidence['inventory']['complete'] = False
        with self.assertRaisesRegex(EvidenceError, 'complete must be true'):
            classify(evidence, now=NOW)
        evidence = payload(run())
        evidence['inventory']['total_count'] = 2
        with self.assertRaisesRegex(EvidenceError, 'total_count'):
            classify(evidence, now=NOW)
        evidence = payload(run())
        evidence['inventory']['next_url'] = 'https://api.github.com/next'
        with self.assertRaisesRegex(EvidenceError, 'next_url must be null'):
            classify(evidence, now=NOW)

    def test_08(self):
        evidence = payload(run())
        evidence['runs'][0]['jobs_inventory']['complete'] = False
        with self.assertRaisesRegex(EvidenceError, 'jobs_inventory.complete must be true'):
            classify(evidence, now=NOW)
        evidence = payload(run())
        evidence['runs'][0]['jobs_inventory']['total_count'] = 2
        with self.assertRaisesRegex(EvidenceError, 'does not match supplied complete job inventory'):
            classify(evidence, now=NOW)
        evidence = payload(run())
        evidence['runs'][0]['jobs_inventory']['next_url'] = 'https://api.github.com/next'
        with self.assertRaisesRegex(EvidenceError, 'jobs_inventory.next_url must be null'):
            classify(evidence, now=NOW)
        zero = job(status='completed', conclusion='cancelled', runner='', runner_id=0, started='2026-09-13T08:20:00Z', steps=[])
        evidence = payload(run(conclusion='cancelled', jobs=[zero]))
        evidence['runs'][0]['jobs_inventory']['total_count'] = 2
        with self.assertRaisesRegex(EvidenceError, 'does not match supplied complete job inventory'):
            classify(evidence, now=NOW)

    def test_09(self):
        first = classify(payload(run()), now=NOW)
        changed = payload(run())
        changed['policy']['source']['source_sha256'] = 'sha256:' + 'd' * 64
        second = classify(changed, now=NOW)
        self.assertNotEqual(first['policy_digest'], second['policy_digest'])
        self.assertNotEqual(first['receipt_digest'], second['receipt_digest'])
        self.assertEqual(first['policy_source']['base_ref'], 'refs/heads/main')

    def test_10(self):
        delivery = workflow(202, '.github/workflows/delivery.yml', 'Delivery')
        failed = run(workflow_id=202, workflow_path=delivery['workflow_path'], workflow_name=delivery['workflow_name'], run_id=2, conclusion='failure', jobs=[job(conclusion='failure', job_id=22)])
        receipt = classify(payload(run(), failed, required=[workflow(), delivery]), now=NOW)
        self.assertEqual(receipt['decision'], 'TERMINAL_RED')
        self.assertFalse(receipt['merge_authorized'])

    def test_11(self):
        for status, conclusion in [('queued', None), ('completed', 'cancelled')]:
            with self.subTest(status=status):
                z = job(status=status, conclusion=conclusion, runner='', runner_id=0, started='2026-09-13T08:20:00Z', steps=[])
                evidence = payload(run(status=status, conclusion=conclusion, jobs=[z]))
                receipt = classify(evidence, now=NOW)
                self.assertEqual(receipt['decision'], 'WAIT_RUNNER_BACKLOG')
                self.assertTrue(receipt['runner_exception_candidate'])
                self.assertFalse(receipt['merge_authorized'])

    def test_12(self):
        z = job(status='completed', conclusion='cancelled', runner='runner-1', runner_id=42, started='2026-09-13T08:20:05Z', steps=[])
        receipt = classify(payload(run(conclusion='cancelled', jobs=[z])), now=NOW)
        self.assertEqual(receipt['decision'], 'HOLD')

    def test_13(self):
        delivery = workflow(202, '.github/workflows/delivery.yml', 'Delivery')
        missing = classify(payload(run(), required=[workflow(), delivery]), now=NOW)
        self.assertEqual(missing['decision'], 'WAIT_MISSING')
        active = job(status='in_progress', conclusion=None, runner='runner-1', runner_id=42, started='2026-09-13T08:20:05Z', steps=[])
        waiting = classify(payload(run(status='in_progress', conclusion=None, jobs=[active])), now=NOW)
        self.assertEqual(waiting['decision'], 'WAIT_EXECUTION')

    def test_14(self):
        failed = job(conclusion='failure', steps=[{'name': 'test', 'status': 'completed', 'conclusion': 'failure'}])
        self.assertEqual(classify(payload(run(jobs=[failed])), now=NOW)['decision'], 'HOLD')
        skipped = job(conclusion='skipped', runner=None, runner_id=None, started=None, steps=[])
        self.assertEqual(classify(payload(run(conclusion='skipped', jobs=[skipped])), now=NOW)['decision'], 'HOLD')

    def test_15(self):
        cases = []
        wrong = payload(run())
        wrong['runs'][0]['head_sha'] = 'b' * 40
        cases.append(wrong)
        stale = payload(run())
        stale['captured_at'] = '2026-09-13T07:00:00Z'
        cases.append(stale)
        stale_policy = payload(run())
        stale_policy['policy']['captured_at'] = '2026-09-13T07:00:00Z'
        cases.append(stale_policy)
        future = payload(run())
        future['captured_at'] = '2026-09-13T09:00:00Z'
        cases.append(future)
        future_policy = payload(run())
        future_policy['policy']['captured_at'] = '2026-09-13T09:00:00Z'
        cases.append(future_policy)
        for evidence in cases:
            with self.subTest(evidence=evidence.get('captured_at')):
                with self.assertRaises(EvidenceError):
                    classify(evidence, now=NOW)

    def test_16(self):
        late = run(status='queued', conclusion=None, jobs=[job(status='queued', conclusion=None, runner=None, runner_id=None, started=None, steps=None)])
        late['created_at'] = '2026-09-13T08:31:00Z'
        with self.assertRaisesRegex(EvidenceError, 'after the evidence capture'):
            classify(payload(late), now=NOW)
        late_job = run()
        late_job['jobs'][0]['completed_at'] = '2026-09-13T08:31:00Z'
        with self.assertRaisesRegex(EvidenceError, 'after the evidence capture'):
            classify(payload(late_job), now=NOW)

    def test_17(self):
        optional = run(workflow_id=303, workflow_path='.github/workflows/optional.yml', workflow_name='Optional', run_id=3)
        receipt = classify(payload(run(), optional), now=NOW)
        self.assertEqual(receipt['decision'], 'TERMINAL_GREEN')
        self.assertEqual(receipt['ignored_extra_workflows'][0]['workflow_id'], 303)

    def test_18(self):
        with self.assertRaises(EvidenceError):
            parse_json_bytes(b'{"schema_version":"x","schema_version":"y"}')
        evidence = payload(run())
        evidence['trust_me'] = True
        with self.assertRaises(EvidenceError):
            classify(evidence, now=NOW)
        evidence = payload(run())
        evidence['runs'][0]['workflow_path'] = '.github/workflows/../evil.yml'
        with self.assertRaises(EvidenceError):
            classify(evidence, now=NOW)
        evidence = payload(run())
        del evidence['runs'][0]['jobs'][0]['runner_id']
        with self.assertRaisesRegex(EvidenceError, 'missing fields: runner_id'):
            classify(evidence, now=NOW)

    def test_19(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / 'evidence.json'
            out = root / 'receipt.json'
            src.write_text(json.dumps(payload(run())), encoding='utf-8')
            self.assertEqual(main([str(src), '--out', str(out), '--now', '2026-09-13T08:30:00Z']), 3)
            receipt = json.loads(out.read_text(encoding='utf-8'))
            self.assertFalse(receipt['merge_authorized'])
            self.assertEqual(main([str(src), '--out', str(out), '--now', '2026-09-13T08:30:00Z']), 2)
            if hasattr(os, 'symlink'):
                link = root / 'link.json'
                try:
                    link.symlink_to(src.name)
                except (OSError, NotImplementedError):
                    return
                self.assertEqual(main([str(link), '--out', str(root / 'other.json'), '--now', '2026-09-13T08:30:00Z']), 2)

    def test_20(self):
        evidence = payload(run())
        reparsed = parse_json_bytes(json.dumps(evidence).encode())
        first = classify(evidence, now=NOW)
        later = classify(reparsed, now=datetime(2026, 9, 13, 8, 31, tzinfo=timezone.utc))
        self.assertNotEqual(first['evaluated_at'], later['evaluated_at'])
        self.assertEqual(first['receipt_digest'], later['receipt_digest'])
if __name__ == '__main__':
    unittest.main()
