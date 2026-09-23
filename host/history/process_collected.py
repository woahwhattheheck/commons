"""Process all saved full-body batches, resuming through JEV receipts.

Independent source files run concurrently. ``--follow`` rescans for batches
atomically added by a live collector; it never marks a source complete until
``read_history.py`` has written its full-body completion receipt.
"""
import argparse
import concurrent.futures
import json
from pathlib import Path
import subprocess
import sys
import time

parser=argparse.ArgumentParser()
parser.add_argument('directory')
parser.add_argument('--pattern',default='mail-*.json')
parser.add_argument('--workers',type=int,default=4)
parser.add_argument('--follow',action='store_true')
parser.add_argument('--poll-seconds',type=int,default=15)
args=parser.parse_args()
if args.workers < 1 or args.poll_seconds < 1:
    parser.error('workers and poll-seconds must be positive')
root=Path(args.directory)

def process(source):
    receipt=source.parent/'jev-results'/(source.stem+'-complete.json')
    if receipt.exists():
        return None
    result=subprocess.run([sys.executable,str(Path(__file__).with_name('read_history.py')),str(source)],capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError(json.dumps({'source_file':source.name,'status':'failed','code':result.returncode,
                                       'stderr_tail':result.stderr[-500:]}))
    if not receipt.exists():
        raise RuntimeError(f'missing completion receipt: {source.name}')
    return result.stdout.strip()

with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
    while True:
        pending=[source for source in sorted(root.glob(args.pattern))
                 if not (source.parent/'jev-results'/(source.stem+'-complete.json')).exists()]
        if pending:
            print(json.dumps({'status':'processing','pending_files':len(pending),'workers':args.workers}),flush=True)
            futures={pool.submit(process,source):source for source in pending}
            for future in concurrent.futures.as_completed(futures):
                try:
                    report=future.result()
                except Exception as error:
                    print(str(error),flush=True)
                    raise SystemExit(1)
                if report:
                    print(report,flush=True)
        else:
            print(json.dumps({'status':'all_current_files_processed'}),flush=True)
        if not args.follow:
            break
        time.sleep(args.poll_seconds)
