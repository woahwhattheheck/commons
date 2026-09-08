# SPDX-License-Identifier: Apache-2.0
"""Run a source-bound existing frozen SELL actor over retained own observations.

Calls policies, not the engine. A comparison is correspondence/timing, not new
scored games. Use one fresh process per source/workload. Dependency roots must
be the unchanged source closure associated with the input trace.
"""
from __future__ import annotations
import argparse, copy, gzip, hashlib, importlib.util, json, random, sys, time
from pathlib import Path


def encoded(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scheduler',type=Path,required=True)
    parser.add_argument('--frames',type=Path,required=True)
    parser.add_argument('--seat',type=int,choices=(0,1),required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--capture-profiles',action='store_true')
    parser.add_argument('--canonical',action='store_true')
    parser.add_argument('--parent-count',action='store_true')
    args=parser.parse_args()
    raw=args.frames.read_bytes()
    rows=[json.loads(line) for line in gzip.decompress(raw).splitlines()]
    assert len(rows)==720 and [r['frame'] for r in rows]==list(range(720))
    scheduler=args.scheduler.resolve()
    before={str(p.relative_to(scheduler.parent)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in scheduler.parent.rglob('*.py')}
    sys.path.insert(0,str(scheduler.parent));random.seed(20260907)
    start=time.perf_counter()
    spec=importlib.util.spec_from_file_location('scheduler',scheduler)
    mod=importlib.util.module_from_spec(spec);sys.modules['scheduler']=mod
    exec(compile(scheduler.read_bytes(),str(scheduler),'exec'),mod.__dict__)
    if args.canonical:
        spec=importlib.util.spec_from_file_location('titan_runtime',scheduler.parent/'titan_runtime.py')
        canon=importlib.util.module_from_spec(spec);sys.modules['titan_runtime']=canon
        exec(compile((scheduler.parent/'titan_runtime.py').read_bytes(),str(scheduler.parent/'titan_runtime.py'),'exec'),canon.__dict__)
        actor=canon.TitanAgent()
    else:
        actor=mod.SellScheduler()
    parent_count=[0]
    def count_calls(frame,event,arg):
        if event=='call' and frame.f_code.co_name=='act' and frame.f_code.co_filename.endswith('/arlene.py'):
            parent_count[0]+=1
    if args.parent_count:sys.setprofile(count_calls)
    load_seconds=time.perf_counter()-start
    profiles=[]
    if args.capture_profiles:
        original=actor.receipt_profile
        def capture(*params,**kwargs):
            result=original(*params,**kwargs)
            env={n:c.cell_contents for n,c in zip(result.__code__.co_freevars,result.__closure__)}
            profiles.append({'step':params[0]['step'],'item':params[5],
                             'rows':env.get('profile',env.get('checks'))})
            return result
        actor.receipt_profile=capture
    outputs=[];times=[];errors=[];mismatches=[];states=[];changed_inputs=[]
    for step,frame in enumerate(rows[:-1]):
        obs=copy.deepcopy(frame['state'][args.seat]['observation'])
        cfg=copy.deepcopy(frame['configuration'])
        obs['step']=step;obs['remainingOverageTime']=0
        snapshot=encoded([obs,cfg])
        expected=rows[step+1]['state'][args.seat]['action']
        start=time.perf_counter()
        try:out=actor.act(obs,cfg)
        except BaseException as error:
            errors.append({'step':step,'kind':type(error).__name__,'message':str(error)})
            break
        times.append(time.perf_counter()-start)
        if encoded([obs,cfg])!=snapshot:changed_inputs.append(step)
        if out!=expected:mismatches.append({'step':step,'expected':expected,'actual':out})
        outputs.append(out)
        consumer=actor.consumer if args.canonical else actor
        state={'route':actor.controller.cur,'planned':consumer.planned,'pending':consumer.pending,
               'previous':consumer.previous,'observed_harvests':consumer.observed_harvests,
               'diagnostics':consumer.diagnostics}
        if args.canonical:
            state['events']=actor.seed_budget.events
            state['outer']={k:v for k,v in actor.diagnostics.items() if k not in
                ('elapsed_seconds','act_cpu_seconds','entrypoint_prelude_seconds')}
            state['selected']=actor.selected
            state['ready']=actor.ready
        states.append(hashlib.sha256(encoded(state)).hexdigest())
    if args.parent_count:sys.setprofile(None)
    after={str(p.relative_to(scheduler.parent)):hashlib.sha256(p.read_bytes()).hexdigest()
           for p in scheduler.parent.rglob('*.py')}
    report={'schema':'titan.receipt-capacity-prefix.v1','scheduler_sha256':before['scheduler.py'],
            'dependency_sha256':before,'sources_unchanged':before==after,
            'frames_sha256':hashlib.sha256(raw).hexdigest(),'seat':args.seat,
            'python':sys.version,'calls':len(outputs),'errors':errors,'expected_action_mismatches':mismatches,
            'input_mutations':changed_inputs,'action_digest':hashlib.sha256(encoded(outputs)).hexdigest(),
            'state_digests':states,'load_seconds':load_seconds,'call_seconds':times,
            'total_action_seconds':sum(times),'maximum_action_seconds':max(times,default=0),
            'profiles':profiles,'new_games':0,'seeds_consumed':[], 'canonical':args.canonical,
            'parent_calls':parent_count[0] if args.parent_count else None}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('calls','errors','action_digest','total_action_seconds','maximum_action_seconds','load_seconds')}))
    print('expected mismatches',len(mismatches),'input mutations',len(changed_inputs))
    return int(bool(errors or (mismatches and not args.canonical) or changed_inputs or before!=after))
if __name__=='__main__':raise SystemExit(main())
