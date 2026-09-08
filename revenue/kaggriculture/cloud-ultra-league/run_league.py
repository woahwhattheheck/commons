"""Additive full-trajectory league consumer of the pinned official evaluator."""
from __future__ import annotations
import argparse
import concurrent.futures
import datetime
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

from selected_action_audit import duplicate_harvest_targets

def load_evaluator(path):
    spec = importlib.util.spec_from_file_location("ultra_existing_evaluator", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

def detailed_actor(base):
    class DetailedActor(base):
        def report(self):
            result = super().report()
            result["call_seconds"] = list(self.stats["call_seconds"])
            result["rpc_seconds"] = list(self.stats["rpc_seconds"])
            return result
    return DetailedActor

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def write_json(path, value):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    tmp.replace(path)

class RecordingEngine:
    """Record official transition outputs; do not change agent observations."""
    def __init__(self, engine, stream):
        self.engine, self.stream = engine, stream
        self.specification = engine.specification
        self.index = 0

    def interpreter(self, state, env):
        conflicts = [duplicate_harvest_targets(s.observation, s.action) for s in state]
        result = self.engine.interpreter(state, env)
        record = {'transition': self.index, 'state': state, 'selected_action_conflicts': conflicts}
        self.stream.write(json.dumps(record, separators=(',', ':'), allow_nan=False) + '\n')
        self.index += 1
        return result

def cell(args):
    cfg = json.loads(Path(args.config).read_text())
    ev = load_evaluator(cfg.get("evaluator", str(HERE.parent / "cloud-eval/evaluate.py")))
    ev.Actor = detailed_actor(ev.Actor)
    item = next(x for x in cfg['cells'] if x['id'] == args.cell)
    out = Path(cfg['output']) / item['id']
    out.mkdir(parents=True, exist_ok=False)
    write_json(out / 'STARTED.json', {'started': now(), 'pid': os.getpid(), 'cell': item,
                                     'command': sys.argv, 'freeze_sha256': hashlib.sha256(Path(args.config).read_bytes()).hexdigest()})
    engine, engine_hashes = ev.get_engine(cfg['engine'], cfg['loader'])
    candidate, opponent = cfg['candidate'], cfg['opponents'][item['opponent']]
    specs = [candidate, opponent] if item['seat'] == 0 else [opponent, candidate]
    with gzip.open(out / 'trajectory.jsonl.gz', 'wt', encoding='utf-8', compresslevel=1) as stream:
        recorder = RecordingEngine(engine, stream)
        result = ev.play(recorder, specs, cfg['engine'], cfg['loader'], item['seed'], item['seat'],
                         cfg['rng_seed'], cfg['action_timeout'], cfg['startup_timeout'], cfg['game_timeout'], None)
    result.update(opponent=item['opponent'], cell_id=item['id'], finished=now(),
                  engine_sha256=engine_hashes, recorded_transitions=recorder.index)
    result['trajectory_sha256'] = hashlib.sha256((out / 'trajectory.jsonl.gz').read_bytes()).hexdigest()
    write_json(out / 'result.json', result)
    print(json.dumps({k: result[k] for k in ['cell_id', 'seed', 'candidate_seat', 'opponent', 'status', 'scores', 'failure', 'wall_seconds']}), flush=True)
    return int(result['status'] != 'complete')

def launch(args):
    cfg_path = Path(args.config).resolve()
    cfg = json.loads(cfg_path.read_text())
    out = Path(cfg['output'])
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    state = {'started': now(), 'pid': os.getpid(), 'command': sys.argv, 'config': str(cfg_path),
             'freeze_sha256': hashlib.sha256(cfg_path.read_bytes()).hexdigest(), 'scheduled': len(cfg['cells']), 'finished_cells': rows}
    write_json(out / 'BATCH-STATE.json', state)
    def run(item):
        command = [sys.executable, '-B', str(Path(__file__).resolve()), '--config', str(cfg_path), '--cell', item['id']]
        log = out / (item['id'] + '.log')
        started = now()
        with log.open('w') as f:
            proc = subprocess.Popen(command, stdout=f, stderr=subprocess.STDOUT)
            code = proc.wait()
        path = out / item['id'] / 'result.json'
        result = json.loads(path.read_text()) if path.exists() else {'status': 'driver_failed', 'failure': {'returncode': code}}
        return {'id': item['id'], 'seed': item['seed'], 'seat': item['seat'], 'opponent': item['opponent'],
                'started': started, 'finished': now(), 'pid': proc.pid, 'returncode': code,
                'status': result['status'], 'scores': result.get('scores'), 'failure': result.get('failure'),
                'wall_seconds': result.get('wall_seconds')}
    # Complete the operational eight before launching the rest; no game is repeated.
    for phase, cells in [('operational8', cfg['cells'][:8]), ('remaining', cfg['cells'][8:])]:
        state['phase'] = phase
        write_json(out / 'BATCH-STATE.json', state)
        with concurrent.futures.ThreadPoolExecutor(max_workers=cfg['jobs']) as pool:
            for row in pool.map(run, cells):
                rows.append(row)
                write_json(out / 'BATCH-STATE.json', state)
                print(json.dumps(row), flush=True)
        if phase == 'operational8':
            if any(x['status'] != 'complete' for x in rows):
                state['stopped'] = 'operational_failure'; write_json(out / 'BATCH-STATE.json', state); return 1
            print('OPERATIONAL8_COMPLETE', flush=True)
    state.update(phase='complete', finished=now())
    write_json(out / 'BATCH-STATE.json', state)
    return int(any(x['status'] != 'complete' for x in rows))

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True)
    p.add_argument('--cell')
    args = p.parse_args()
    raise SystemExit(cell(args) if args.cell else launch(args))
