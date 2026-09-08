#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Run exact original/candidate solvers with matched deterministic search work.

Generated instances exercise the native implementation. This is not the official
checker, a public-instance screen, or a competition performance comparison.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import time


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def inputs(seed):
    rng=random.Random(seed)
    n=6+seed%7;h=1+seed%5
    nodes=[101+11*i for i in range(n)]
    edges=[]
    for u in range(n):
        for v in range(n):
            if u!=v and (v in ((u+1)%n,(u-1)%n) or rng.random()<0.33):
                edges.append({'id':len(edges),'from':nodes[u],'to':nodes[v],
                              'metric':rng.randint(1,5),'capacity':rng.randint(3,15)})
    demands=[]
    for _ in range(4+seed%5):
        s,t=rng.sample(nodes,2)
        demands.append({'s':s,'t':t,'v':[rng.randint(1,45) for _ in range(h)]})
    # Keep the directed ring intact; only optional chords can be removed.
    protected={(nodes[u],nodes[(u+1)%n]) for u in range(n)}
    protected|={(nodes[u],nodes[(u-1)%n]) for u in range(n)}
    extra=[e['id'] for e in edges if (e['from'],e['to']) not in protected]
    scenario={'max_segments':[1,2,4,8][seed%4],
              'budget':[{'t':t,'value':[0,3,6,12,100][(seed+t)%5]} for t in range(1,h)],
              'interventions':[{'t':t,'links':rng.sample(extra,min(len(extra),seed%3))} for t in range(h)]}
    return {'nodes':[{'id':x} for x in nodes],'links':edges}, {'num_time_slots':h,'demands':demands},scenario


def run(binary,paths,out,rounds,environment):
    out.parent.mkdir(parents=True,exist_ok=True)
    stats=out.with_suffix('.stats.json')
    env={k:v for k,v in os.environ.items() if not k.startswith(('SEDGE_','FLEET_','CLOUD_INITIAL_'))}
    env.update(SEDGE_SECONDS='120',SEDGE_MAX_ROUNDS=str(rounds),SEDGE_STATS=str(stats),**environment)
    started=time.perf_counter()
    result=subprocess.run([str(binary),*map(str,paths),str(out)],env=env,capture_output=True,timeout=125)
    duration=time.perf_counter()-started
    out.with_suffix('.stdout').write_bytes(result.stdout)
    out.with_suffix('.stderr').write_bytes(result.stderr)
    if result.returncode:raise RuntimeError(f'{binary.name}: {result.returncode}: {result.stderr.decode(errors="replace")}')
    record=json.loads(stats.read_text())
    # The time-dependent adaptive threshold must not have controlled the run.
    if record['seconds']>=70:
        raise RuntimeError('Fixed-round comparison reached time-dependent search regime')
    comparable={k:v for k,v in record.items() if k!='seconds'}
    return {'solution_sha256':digest(out),'statistics_sha256':digest(stats),
            'stderr_sha256':digest(out.with_suffix('.stderr')),'wall_seconds_diagnostic':duration,
            'solver_seconds_diagnostic':record['seconds'],'comparable':comparable}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original',type=Path,required=True)
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cases',type=int,default=24)
    p.add_argument('--rounds',type=int,default=24)
    a=p.parse_args()
    a.original=a.original.resolve();a.candidate=a.candidate.resolve();a.output=a.output.resolve()
    if not 1<=a.cases<=100 or not 0<=a.rounds<=1000:p.error('bounded cases/rounds required')
    if a.output.exists():p.error('output must be a new directory to preserve prior evidence')
    a.output.mkdir(parents=True)
    records=[]
    for i in range(a.cases):
        seed=2026090800+i
        folder=a.output/f'case-{i:02d}';folder.mkdir()
        paths=[folder/name for name in ('net.json','tm.json','scenario.json')]
        for path,data in zip(paths,inputs(seed)):
            path.write_text(json.dumps(data,separators=(',',':'))+'\n')
        settings=[{}, {'FLEET_DIRECTED':'0','FLEET_JOINT':'0'}][i%2]
        old=run(a.original,paths,folder/'original.json',a.rounds,settings)
        new=run(a.candidate,paths,folder/'candidate.json',a.rounds,settings)
        if old['solution_sha256']!=new['solution_sha256'] or old['comparable']!=new['comparable']:
            raise RuntimeError(f'Native cold correspondence failed at case{i}')
        records.append({'case':i,'kind':'cold','settings':settings,'inputs':{p.name:digest(p) for p in paths},'original':old,'candidate':new})
        if i%3==0:
            # Same already-validated original checkpoint in both processes.
            resume={**settings,'CLOUD_INITIAL_SOLUTION':str(folder/'original.json')}
            old=run(a.original,paths,folder/'resume-original.json',a.rounds,resume)
            new=run(a.candidate,paths,folder/'resume-candidate.json',a.rounds,resume)
            if old['solution_sha256']!=new['solution_sha256'] or old['comparable']!=new['comparable']:
                raise RuntimeError(f'Native resume correspondence failed at case{i}')
            records.append({'case':i,'kind':'resume','settings':resume,'original':old,'candidate':new})
    report={'scope':'generated native fixed-round correspondence; no official checker or public benchmark',
            'original_binary_sha256':digest(a.original),'candidate_binary_sha256':digest(a.candidate),
            'round_limit':a.rounds,'seconds_allowance':120,'pairs':len(records),'records':records,
            'solutions_equal':True,'all_loads_budgets_counters_equal':True,
            'paired_search_attempts':sum(r['original']['comparable']['attempted'] for r in records)}
    (a.output/'RESULTS.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))

if __name__=='__main__':main()
