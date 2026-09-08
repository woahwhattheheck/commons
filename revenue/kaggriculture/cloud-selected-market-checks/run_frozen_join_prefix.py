# SPDX-License-Identifier: Apache-2.0
"""Replay retained own observations through one actual TitanAgent; no engine runs."""
from __future__ import annotations
import argparse, copy, gzip, hashlib, importlib.util, json, os, random, sys, time
from pathlib import Path

def sha(data): return hashlib.sha256(data).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--frames',type=Path,required=True)
    p.add_argument('--seat',type=int,choices=(0,1),required=True)
    p.add_argument('--seed-disabled',action='store_true')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args(); root=a.root.resolve()
    raw=a.frames.read_bytes()
    with gzip.open(a.frames,'rt') as stream: frames=[json.loads(line) for line in stream]
    if len(frames)!=720:raise ValueError('expected complete 720-frame retained episode')
    sources={str(q.relative_to(root)):sha(q.read_bytes()) for q in root.rglob('*.py')}
    random.seed(20260907);sys.path.insert(0,str(root))
    before_load=time.perf_counter()
    import titan_runtime
    actor=titan_runtime.TitanAgent(titan_runtime.Features(seed=not a.seed_disabled))
    parent_calls=[0]; original_initialize=actor._initialize
    def initialize_once():
        original_initialize()
        original_act=actor.production.act
        def counted(obs):
            parent_calls[0]+=1
            return original_act(obs)
        actor.production.act=counted
    actor._initialize=initialize_once
    load=time.perf_counter()-before_load
    rows=[];mismatches=[];errors=[];fallbacks=[]
    for step,frame in enumerate(frames[:-1]):
        obs=copy.deepcopy(frame['state'][a.seat]['observation']);obs['step']=step;obs['remainingOverageTime']=0
        cfg=copy.deepcopy(frame['configuration']);before=copy.deepcopy((obs,cfg));calls_before=parent_calls[0]
        t=time.perf_counter();cpu=time.process_time()
        try:output=actor.act(obs,cfg)
        except BaseException as exc:
            errors.append({'step':step,'type':type(exc).__name__,'detail':str(exc)})
            raise
        wall=time.perf_counter()-t;cpu=time.process_time()-cpu
        if (obs,cfg)!=before:raise AssertionError('caller input mutated')
        if parent_calls[0]-calls_before!=1:raise AssertionError('expected exactly one actual parent call')
        expected=frames[step+1]['state'][a.seat]['action']
        if output!=expected:mismatches.append(step)
        if actor.diagnostics['status']!='completed':fallbacks.append({'step':step,'diagnostics':actor.diagnostics})
        state={'route':actor.controller.cur,'planned':actor.consumer.planned,'pending':actor.consumer.pending,
               'previous':actor.consumer.previous,'observed_harvests':actor.consumer.observed_harvests,
               'seller_diagnostics':actor.consumer.diagnostics,'seed_funding':actor.diagnostics.get('seed_funding'),
               'seed_events':getattr(actor.seed_budget,'events',None), 'selected':actor.selected}
        state_hash=sha(json.dumps(state,sort_keys=True,separators=(',',':')).encode())
        rows.append({'step':step,'action':output,'state_sha256':state_hash,'wall_seconds':wall,'cpu_seconds':cpu})
    values=sorted(row['wall_seconds'] for row in rows)
    result={'schema':'titan.frozen-scorer.join-prefix.v1','seed_enabled':not a.seed_disabled,
            'input_sha256':sha(raw),'seat':a.seat,'calls':len(rows),'actual_parent_calls':parent_calls[0],
            'recorded_action_mismatch_steps':mismatches,'errors':errors,'fallbacks':fallbacks,'root_sources':sources,
            'sources_unchanged':sources=={str(q.relative_to(root)):sha(q.read_bytes()) for q in root.rglob('*.py')},
            'timings':{'load_seconds':load,'load_through_first_call_seconds':load+rows[0]['wall_seconds'],
                       'sum_action_seconds':sum(values),'p99_seconds':values[int(.99*(len(values)-1))],'max_seconds':max(values)},
            'rows':rows,'new_games':0,'engine_calls':0,'python':sys.version,'pythonhashseed':os.environ.get('PYTHONHASHSEED'),
            'scope':'Actual TitanAgent on retained own observation/configuration frames. Source-specific action/state parity, not responsive games or hosted timing. Module preload and nominal parent-count observer included in loading.'}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','root_sources','scope','python')}))
if __name__=='__main__':main()
