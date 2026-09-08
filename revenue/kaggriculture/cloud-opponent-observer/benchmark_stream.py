"""Compare existing and streaming observation consumers in fresh processes.

This only replays supplied observations; it does not run an interpreter or game.
Tracemalloc timings include instrumentation and are not policy latency claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
import tracemalloc


def file_hash(path: Path) -> str:
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def worker(args):
    if args.worker == 'baseline':
        from observe import run_jsonl
    else:
        from stream_observations import run_jsonl
    root = args.output_dir
    output, summary = root/f'{args.worker}.jsonl', root/f'{args.worker}-summary.json'
    tracemalloc.start()
    started = time.perf_counter()
    result = run_jsonl(args.source, args.pack, args.input, output, summary)
    seconds = time.perf_counter() - started
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {'runner': args.worker, 'python_peak_bytes': peak,
            'instrumented_seconds': seconds,
            'telemetry_sha256': file_hash(output), 'summary_sha256': file_hash(summary),
            'calls': sum(a['calls'] for a in result['actors']),
            'actors': len(result['actors']),
            'telemetry_errors': sum(a['telemetry_errors'] for a in result['actors'])}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True,
                        help='New directory for this measurement; existing directories are untouched')
    parser.add_argument('--worker', choices=['baseline', 'stream'])
    args = parser.parse_args(argv)
    if args.worker:
        print(json.dumps(worker(args), sort_keys=True))
        return 0
    # A new directory ensures benchmark artifacts cannot collide with inputs.
    args.output_dir.mkdir(parents=True, exist_ok=False)
    original_digest = file_hash(args.input)
    results = []
    for mode in ('baseline', 'stream'):
        process = subprocess.run([sys.executable, str(Path(__file__).resolve()),
            '--source', str(args.source.resolve()), '--pack', str(args.pack.resolve()),
            '--input', str(args.input.resolve()), '--output-dir', str(args.output_dir.resolve()),
            '--worker', mode], text=True, capture_output=True, check=True)
        results.append(json.loads(process.stdout))
    old, new = results
    report = {'schema': 'cok-stream-benchmark-v1', 'python': sys.version.split()[0],
        'input_sha256': original_digest, 'input_unchanged': file_hash(args.input) == original_digest,
        'results': results,
        'telemetry_bytes_equal': old['telemetry_sha256'] == new['telemetry_sha256'],
        'summary_bytes_equal': old['summary_sha256'] == new['summary_sha256'],
        'peak_python_memory_reduction_fraction': 1 - new['python_peak_bytes']/old['python_peak_bytes'],
        'scope': 'Supplied observation processing in fresh Python processes, with tracemalloc enabled; not scored games or policy action latency.'}
    (args.output_dir/'benchmark.json').write_text(json.dumps(report, indent=2, sort_keys=True)+'\n')
    print(json.dumps(report, sort_keys=True))
    return int(not all(report[k] for k in ('input_unchanged','telemetry_bytes_equal','summary_bytes_equal')))


if __name__ == '__main__':
    raise SystemExit(main())
