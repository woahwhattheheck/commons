"""Measured synchronized multiprocess experiment. Entirely synthetic, no Slack."""
from __future__ import annotations
import argparse
import json
import multiprocessing
import platform
import tempfile
import time
from pathlib import Path
from coordination.read_coalescer.core import Broker
from coordination.read_coalescer.tests.test_core import parallel_worker


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workers', type=int, default=32)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if not 2 <= args.workers <= 64:
        parser.error('workers must be between 2 and 64')
    with tempfile.TemporaryDirectory() as tmp:
        path = str(Path(tmp)/'race.db')
        Broker(path)
        ctx = multiprocessing.get_context('spawn')
        barrier, counter, queue = ctx.Barrier(args.workers), ctx.Value('i', 0), ctx.Queue()
        processes = [ctx.Process(target=parallel_worker, args=(path, barrier, counter, queue)) for _ in range(args.workers)]
        start = time.monotonic()
        try:
            for p in processes:
                p.start()
            results = [queue.get(timeout=40) for _ in processes]
            for p in processes:
                p.join(timeout=5)
            measured = {
                'scenario': 'SYNTHETIC_SAME_QUERY_SAME_ACCESS_SCOPE_SAME_HOST',
                'python': platform.python_version(), 'platform': platform.platform(),
                'process_start_method': 'spawn', 'workers': args.workers,
                'provider_callbacks': counter.value,
                'fetched_results': sum(r.get('status') == 'FETCHED' for r in results),
                'cached_results': sum(r.get('status') == 'CACHE' for r in results),
                'distinct_result_digests': len({r.get('sha') for r in results}),
                'worker_errors': [r for r in results if 'error' in r],
                'worker_exit_codes': [p.exitcode for p in processes],
                'elapsed_ms': round((time.monotonic() - start)*1000),
                'poll_waits': sum(r.get('waits', 0) for r in results),
                'broker': Broker(path).stats(),
                'live_provider_tested': False, 'native_connector_adopted': False,
                'dollars_saved_measured': None,
            }
            measured['pass'] = counter.value == 1 and measured['fetched_results'] == 1 and \
                measured['cached_results'] == args.workers-1 and measured['distinct_result_digests'] == 1 and \
                not measured['worker_errors'] and all(p.exitcode == 0 for p in processes)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(measured, sort_keys=True, indent=2)+'\n')
            print(json.dumps(measured, sort_keys=True, indent=2))
            return 0 if measured['pass'] else 1
        finally:
            for p in processes:
                if p.is_alive():
                    p.terminate()
                p.join(timeout=5)
            queue.close()


if __name__ == '__main__':
    raise SystemExit(main())
