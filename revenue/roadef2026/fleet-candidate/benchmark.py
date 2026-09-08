"""Matched-budget candidate experiments, using the pinned official checker."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import time

ROOT = Path(__file__).resolve().parent

def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def execute(cmd, folder, label, env=None, timeout=660):
    start = time.monotonic()
    result = subprocess.run(list(map(str, cmd)), capture_output=True, env=env, timeout=timeout)
    (folder / (label + '.stdout')).write_bytes(result.stdout)
    (folder / (label + '.stderr')).write_bytes(result.stderr)
    if result.returncode:
        raise RuntimeError(f'{label} exited {result.returncode}: {result.stderr[-2000:]!r}')
    return result, time.monotonic() - start

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--solver', action='append', required=True, help='label=path')
    ap.add_argument('--seconds', type=float, default=30)
    ap.add_argument('--rounds', type=int)
    ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--instances', nargs='+', default=[f'setB-{i:02}' for i in range(1,13)])
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--checker', type=Path, default=ROOT/'bin'/('checker.exe' if os.name == 'nt' else 'checker'))
    ap.add_argument('--data', type=Path, help='Extracted pinned official challenge root')
    ap.add_argument('--resume-dir', type=Path)
    args = ap.parse_args()
    if args.data:
        data = args.data.resolve()
    else:
        paths = json.loads((ROOT/'paths.json').read_text(encoding='utf-8-sig'))
        data = Path(paths['challenge'])
    solvers = [(label, Path(path).resolve()) for label, path in (s.split('=', 1) for s in args.solver)]
    args.output = args.output.resolve()
    args.checker = args.checker.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    metadata = {'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        'platform':platform.platform(), 'benchmark_sha256':digest(__file__), 'seconds_per_solver':args.seconds,
        'rounds':args.rounds,'workers':args.workers,'checker_sha256':digest(args.checker),
        'challenge_commit':'d84d319a7fdb8de3b1866830d2eaa2937871e5ae',
        'networktools_commit':'aebafc9ee91891e5d721bb86725e8cf1533877d1',
        'solvers':{label:{'path':str(path),'sha256':digest(path)} for label,path in solvers}}
    (args.output/'experiment.json').write_text(json.dumps(metadata,indent=2))
    def trial(name):
        prefix = data / name[:4] / name
        inputs = [Path(str(prefix)+suffix) for suffix in ('-net.json','-tm.json','-scenario.json')]
        rows = []
        scores = []
        for label, solver in solvers:
            folder = args.output/name/label
            folder.mkdir(parents=True, exist_ok=True)
            solution, stats = folder/'solution.json', folder/'stats.json'
            env = dict(os.environ,SEDGE_SECONDS=str(args.seconds), SEDGE_STATS=str(stats))
            env.pop('CLOUD_INITIAL_SOLUTION', None)
            env.pop('SEDGE_MAX_ROUNDS', None)
            if args.rounds is not None: env['SEDGE_MAX_ROUNDS'] = str(args.rounds)
            if args.resume_dir: env['CLOUD_INITIAL_SOLUTION'] = str((args.resume_dir/name/'solution.json').resolve())
            _, wall = execute([solver,*inputs,solution],folder,'solver',env,timeout=max(90,args.seconds+90))
            check_times = {}
            checks = {}
            for decimals in (6,12):
                command = [args.checker,'--net',inputs[0],'--tm',inputs[1],'--scenario',inputs[2],
                           '--srpaths',solution,'--max-decimal-places',decimals]
                result, duration = execute(command,folder,f'checker-{decimals}',timeout=180)
                check = json.loads(result.stdout)
                if check.get('valid') is not True: raise RuntimeError(f'{name}/{label}: checker rejected')
                checks[decimals],check_times[decimals] = check,duration
            score = sorted((x['sat'] for x in checks[6]['saturations']), reverse=True)
            diagnostic = json.loads(stats.read_text())
            actual = {(x['t'],str(x['from']),str(x['to'])):x['sat'] for x in checks[12]['saturations']}
            predicted = {(x['t'],str(x['from']),str(x['to'])):x['sat'] for x in diagnostic['loads']}
            if actual.keys() != predicted.keys(): raise RuntimeError('Load key mismatch')
            error = max(abs(actual[k]-v) for k,v in predicted.items())
            if error >= 2e-9: raise RuntimeError(f'Load disagreement: {error}')
            if sum(diagnostic['budget_used']) != checks[12]['total_cost']: raise RuntimeError('Cost disagreement')
            row = {'instance':name,'solver':label,'valid':True,'mlu_6':score[0],
                   'total_cost':checks[6]['total_cost'],'wall_seconds':wall,'checker_seconds':check_times,
                   'accepted_moves':diagnostic['accepted'],'attempted_moves':diagnostic['attempted'],
                   'max_load_error':error,'load_count':len(score),'solution_sha256':digest(solution),
                   'input_sha256':{p.name:digest(p) for p in inputs}}
            if scores:
                baseline = scores[0]
                row['vs_first'] = 'win' if score < baseline else 'loss' if score > baseline else 'tie'
                row['first_difference_rank'] = next((i+1 for i,(a,b) in enumerate(zip(baseline,score)) if a!=b),None)
            scores.append(score)
            rows.append(row)
            (folder/'result.json').write_text(json.dumps(row,indent=2))
            print(json.dumps(row),flush=True)
        return rows
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(trial,args.instances))
    metadata['results'] = results
    (args.output/'summary.json').write_text(json.dumps(metadata,indent=2))

if __name__ == '__main__': main()
