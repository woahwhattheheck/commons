#!/usr/bin/env python3
"""Pinned Parcel/ASTER package recovery acceptance; synthetic loopback traffic only.

Run from any location with Python 3.11+:
  python ferry_package_recovery_probe.py --root /path/to/commons --output receipt.json

This executes the existing bundle builder and extracted run.py, not a replacement
workflow. Expected source blobs pin the implementation under test. All databases,
archives, receiver state and server processes are temporary and cleaned on exit.
No browser, provider service, customer installation, or full-repository CI claim.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import selectors
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import ProxyHandler, Request, build_opener
import zipfile

PIN = '6785a43546108403470e58fe1cfa35031d010a8a'
EXPECTED = {
    'revenue/hive/fulfillment-desk/bundle.py': 'd1802a62d246687cc20abee64e718c06bfc586aa',
    'revenue/hive/fulfillment-desk/run_bundle.py': '2d89364219840eac1b10711d52887c11cd6c27b3',
    'revenue/hive/intake-crm-workflow/workflow.py': 'da339d714fd610689dafaca5a2e47c57d772edce',
    'revenue/hive/intake-crm-workflow/index.html': '62f98f0bfd798d8b5abe74094337fea3af7c991a',
}
PRESETS = ('client-intake', 'quote-request', 'service-request')
FIELDS = ('name', 'email', 'phone', 'address', 'service', 'preferred_date', 'notes')
CORE_TABLES = ('customers', 'intakes', 'jobs', 'tasks')


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'Cannot load {path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_identity(root):
    identities = {}
    for path, expected in EXPECTED.items():
        data = (root / path).read_bytes()
        require(blob(data) == expected, f'Source changed: {path}; deliberately update/review pins before testing another implementation')
        identities[path] = {'git_blob': expected, 'bytes': len(data), 'sha256': sha256(data)}
    return identities


def request(address, path, payload=None):
    data = None if payload is None else json.dumps(payload, allow_nan=False).encode()
    req = Request(address + path, data=data, headers={'Content-Type': 'application/json'})
    with build_opener(ProxyHandler({})).open(req, timeout=12) as response:
        return json.loads(response.read())


@contextmanager
def launcher(package, database):
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', NO_PROXY='127.0.0.1,localhost', no_proxy='127.0.0.1,localhost')
    for key in tuple(env):
        if key.lower() in ('http_proxy', 'https_proxy', 'all_proxy'):
            env.pop(key)
    process = subprocess.Popen(
        [sys.executable, '-B', 'run.py', '--db', str(database), 'serve', '--host', '127.0.0.1', '--port', '0'],
        cwd=package, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            if not selector.select(timeout=10):
                raise RuntimeError('Packaged launcher did not announce startup')
        line = process.stdout.readline().strip()
        require(line.startswith('Cleaning workflow at http://127.0.0.1:'), f'Unexpected startup: {line}')
        address = line.split(' at ', 1)[1]
        require(request(address, '/health') == {'ok': True}, 'Packaged service health failed')
        yield address
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
        try:
            _, errors = process.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            _, errors = process.communicate(timeout=5)
            raise RuntimeError('Packaged service required forced cleanup')
        require(process.returncode == 0, f'Packaged service exit {process.returncode}: {errors}')
        require(not errors.strip(), f'Unexpected packaged service stderr: {errors}')


@contextmanager
def receiver(workflow, database, failed_event, mode):
    """Real HTTP receiver using the original Store.receive durable inbox.

The failure injection is the receiver fixture's transport behavior. A fresh Store
is opened for each request, so deduplication cannot rely on an in-memory set.
"""
    history = []
    workflow.Store(database)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            raw = self.rfile.read(int(self.headers['Content-Length']))
            value = json.loads(raw)
            key = self.headers.get('Idempotency-Key')
            require(key == value['event_id'], 'Wire header does not match event ID')
            first_failure = key == failed_event and not any(row['id'] == key for row in history)
            entry = {'id': key, 'payload_sha256': sha256(raw)}
            history.append(entry)
            if first_failure and mode == 'reject-before-commit':
                entry.update(status=503, accepted=False, duplicate=None)
                self.send_response(503)
                self.send_header('Content-Length', '0')
                self.end_headers()
                return
            result = workflow.Store(database).receive(key, value)
            entry.update(accepted=True, duplicate=result['duplicate'])
            if first_failure and mode == 'commit-then-lose-ack':
                entry['status'] = 'connection-closed-before-ack'
                self.close_connection = True
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            entry['status'] = 200
            data = json.dumps(result).encode()
            self.send_response(200)
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f'http://127.0.0.1:{server.server_port}/api/receive', history
        finally:
            server.shutdown()
            thread.join(timeout=5)
            require(not thread.is_alive(), 'Receiver did not terminate')


def run_case(root, bundle, workflow, preset, mode):
    with tempfile.TemporaryDirectory(prefix='ferry-parcel-') as directory:
        work = Path(directory)
        mapping = {field: 'source_' + field for field in FIELDS}
        payload = {
            mapping['name']: 'Synthetic Fixture', mapping['email']: 'fixture@example.invalid',
            mapping['phone']: '', mapping['address']: 'Synthetic fixture location',
            mapping['service']: 'Fixture service', mapping['preferred_date']: '',
            mapping['notes']: 'Generated acceptance fixture; not a real customer.',
        }
        intake_a = {'id': 'ferry-' + preset + '-A', 'payload': payload}
        intake_b = {'id': 'ferry-' + preset + '-B', 'payload': payload}
        event_a, event_b = 'intake:' + intake_a['id'], 'intake:' + intake_b['id']
        tasks = [preset + ': review', preset + ': prepare', preset + ': follow up']
        deployment = {
            'format': 'parcel.intake-handoff', 'version': 1, 'preset': preset,
            'agency': 'Synthetic Agency', 'client': 'Synthetic Client', 'title': 'Recovery acceptance',
            'support': 'Synthetic fixture only', 'scope': 'Local acceptance; no external delivery',
            'brand': '#123456', 'fieldMapping': mapping, 'tasks': tasks, 'exampleIntake': intake_a,
        }
        deployment_path = work / 'deployment.json'
        deployment_path.write_text(json.dumps(deployment), encoding='utf-8')
        archive_path = work / 'package.zip'
        build_receipt = bundle.build(deployment_path, root / 'revenue/hive/intake-crm-workflow', archive_path, PIN)
        second = work / 'same-package.zip'
        bundle.build(deployment_path, root / 'revenue/hive/intake-crm-workflow', second, PIN)
        require(archive_path.read_bytes() == second.read_bytes(), 'Identical source/deployment produced different ZIP bytes')
        package = work / 'extracted'
        package.mkdir()
        with zipfile.ZipFile(archive_path) as archive:
            manifest = json.loads(archive.read('MANIFEST.json'))
            require(set(archive.namelist()) == set(manifest['files']) | {'MANIFEST.json'}, 'Manifest/file set mismatch')
            for info in archive.infolist():
                name = PurePosixPath(info.filename)
                require(len(name.parts) == 1 and name.name not in ('.', '..'), 'Unexpected package member')
                data = archive.read(info)
                if info.filename != 'MANIFEST.json':
                    claimed = manifest['files'][info.filename]
                    require(claimed == {'sha256': sha256(data), 'bytes': len(data)}, 'Package manifest mismatch')
                (package / name.name).write_bytes(data)
        for name, source in [('workflow.py', 'intake-crm-workflow/workflow.py'), ('index.html', 'intake-crm-workflow/index.html'), ('run.py', 'fulfillment-desk/run_bundle.py')]:
            require((package / name).read_bytes() == (root / 'revenue/hive' / source).read_bytes(), 'Packaged runtime changed: ' + name)
        database, receiver_database = work / 'sender.sqlite3', work / 'receiver.sqlite3'
        with receiver(workflow, receiver_database, event_a, mode) as (endpoint, history):
            with launcher(package, database) as address:
                request(address, '/api/config', {'mapping': mapping, 'endpoint': endpoint})
                # B is deliberately older: an implementation ignoring the selected ID fails.
                created_b = request(address, '/api/intakes', intake_b)
                created_a = request(address, '/api/intakes', intake_a)
                replay_a = request(address, '/api/intakes', intake_a)
                require(created_a['created'] and created_b['created'] and not replay_a['created'], 'Intake replay semantics failed')
                require(replay_a['job_id'] == created_a['job_id'], 'Replay changed job identity')
                initial = request(address, '/api/state')
                require({table: len(initial[table]) for table in CORE_TABLES} == {'customers': 1, 'intakes': 2, 'jobs': 2, 'tasks': 6}, 'Unexpected initial record counts')
                for job in initial['jobs']:
                    actual = [row['title'] for row in sorted(initial['tasks'], key=lambda row: row['position']) if row['job_id'] == job['id']]
                    require(actual == tasks, 'Branded task preset was not applied')
                failed = request(address, '/api/process', {'id': event_a})
                require(failed.get('id') == event_a and failed.get('state') == 'retry', 'Selected failing event did not enter retry')
                delivered = request(address, '/api/process', {'id': event_b})
                require(delivered.get('id') == event_b and delivered.get('state') == 'delivered', 'Unrelated event did not deliver')
                before_restart = request(address, '/api/state')
            inbox_before = workflow.Store(receiver_database).snapshot()['inbox']
            require(len(inbox_before) == (1 if mode == 'reject-before-commit' else 2), 'Unexpected receiver commit before retry')
            with launcher(package, database) as address:
                require(request(address, '/api/state') == before_restart, 'Restart altered persisted state')
                require(request(address, '/api/config')['endpoint'] == endpoint, 'Restart lost configured receiver')
                require(request(address, '/api/retry', {'id': event_a})['state'] == 'pending', 'Explicit retry failed')
                recovered = request(address, '/api/process', {'id': event_a})
                require(recovered.get('id') == event_a and recovered.get('state') == 'delivered', 'Selected recovery failed')
                require(request(address, '/api/retry', {'id': event_b})['state'] == 'delivered', 'Retry reopened a delivered unrelated event')
                require(request(address, '/api/process', {'id': event_b}) == {'processed': False}, 'Unrelated delivery was resent')
                require(request(address, '/api/process', {'id': event_a}) == {'processed': False}, 'Recovered delivery was resent')
                final = request(address, '/api/export')
                for table in CORE_TABLES:
                    require(final[table] == initial[table], 'Recovery changed core records: ' + table)
                require(not final['notifications'], 'HTTP delivery unexpectedly generated local notifications')
                outbox = {row['id']: row for row in final['outbox']}
                require(len(outbox) == 2, 'Recovery changed outbox cardinality')
                require(all(row['state'] == 'delivered' for row in outbox.values()), 'Delivery remained incomplete')
                require(outbox[event_a]['attempts'] == 2 and outbox[event_b]['attempts'] == 1, 'Attempt counts do not match selected retries')
            # Reopen again after both sender processes have terminated.
            require(workflow.Store(database).snapshot() == final, 'Final persisted state differs after shutdown')
            inbox_after = workflow.Store(receiver_database).snapshot()['inbox']
            require({row['id'] for row in inbox_after} == {event_a, event_b}, 'Receiver did not retain exactly two unique events')
            require([row['id'] for row in history] == [event_a, event_b, event_a], 'Unexpected receiver request sequence')
            require(history[0]['payload_sha256'] == history[2]['payload_sha256'], 'Retry changed wire payload bytes')
            require(history[2]['duplicate'] is (mode == 'commit-then-lose-ack'), 'Receiver did not report the correct durable deduplication outcome')
        return {
            'preset': preset, 'failure_mode': mode, 'result': 'PASS',
            'package_sha256': build_receipt['sha256'], 'package_files': build_receipt['files'],
            'sender_counts': {table: len(final[table]) for table in CORE_TABLES},
            'event_attempts': {'selected': 2, 'unrelated': 1},
            'receiver_inbox_before_retry': len(inbox_before), 'receiver_inbox_after_retry': len(inbox_after),
            'receiver_requests': history, 'sender_process_starts': 2,
            'source_ids_preserved': True, 'original_runtime_bytes_preserved': True,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    before = source_identity(root)
    bundle = load('_ferry_parcel_bundle', root / 'revenue/hive/fulfillment-desk/bundle.py')
    workflow = load('_ferry_aster_workflow', root / 'revenue/hive/intake-crm-workflow/workflow.py')
    started = time.monotonic()
    cases = []
    for preset in PRESETS:
        for mode in ('reject-before-commit', 'commit-then-lose-ack'):
            cases.append(run_case(root, bundle, workflow, preset, mode))
            print(f'PASS {preset} / {mode}', flush=True)
    require(source_identity(root) == before, 'Source bytes changed during probe')
    receipt = {
        'schema': 'ferry-parcel-recovery-probe-v1', 'source_commit': PIN,
        'sources': before, 'scenario_count': len(cases), 'passed_scenarios': len(cases),
        'elapsed_seconds': round(time.monotonic() - started, 3),
        'python': sys.version.split()[0], 'cases': cases,
        'boundaries': ['synthetic loopback HTTP and temporary SQLite only',
                       'six scenarios, not six unittest methods or full-repository CI',
                       'optional upstream README absent in this reconstructed minimal runtime when not on disk',
                       'no native browser E2E or customer/provider/deployment claim',
                       'dedupe tested for this receiver; no generic exactly-once external-effects claim'],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': len(cases), 'seconds': receipt['elapsed_seconds'], 'receipt': str(args.output)}, sort_keys=True))


if __name__ == '__main__':
    main()
