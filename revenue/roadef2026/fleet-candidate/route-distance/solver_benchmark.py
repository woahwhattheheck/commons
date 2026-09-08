#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Alternating native fixed-round timings on one generated workload.

The unchanged official checker and public-instance benchmark are not invoked.
All solutions and non-time solver statistics must match; runtime boundaries stay
well clear of the time-triggered search regime.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import statistics
from fixed_round import run


def workload():
    rng=random.Random(2026090807);n=36;h=16
    nodes=[100+7*i for i in range(n)];links=[]
    for u in range(n):
        for v in range(n):
            if u!=v and (v in ((u+1)%n,(u-1)%n) or rng.random()<0.09):
                links.append({'id':len(links),'from':nodes[u],'to':nodes[v],
                              'metric':rng.randint(1,7),'capacity':rng.randint(4,35)})
    demands=[]
    for _ in range(48):
        s,t=rng.sample(nodes,2)
        demands.append({'s':s,'t':t,'v':[rng.randint(1,75) for _ in range(h)]})
    scenario={'max_segments':8,'budget':[{'t':t,'value':6+(t%4)*6} for t in range(1,h)],'interventions':[]}
    return {'nodes':[{'id':x} for x in nodes],'links':links},{'num_time_slots':h,'demands':demands},scenario


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--original',type=Path,required=True);p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--rounds',type=int,default=9)
    p.add_argument('--resume',type=Path,help='Same completed incumbent for both arms; activates interval search')
    a=p.parse_args();a.original=a.original.resolve();a.candidate=a.candidate.resolve();a.output=a.output.resolve()
    if a.output.exists() or not 1<=a.rounds<=20:p.error('new output directory and1..20 rounds required')
    a.output.mkdir(parents=True)
    paths=[a.output/name for name in ('net.json','tm.json','scenario.json')]
    for path,obj in zip(paths,workload()):path.write_text(json.dumps(obj,separators=(',',':'))+'\n')
    settings={}
    if a.resume:
        (a.output/'incumbent.json').write_bytes(a.resume.read_bytes())
        settings['CLOUD_INITIAL_SOLUTION']=str(a.output/'incumbent.json')
    records=[];expected=None
    for i in range(a.rounds):
        record={}
        order=('original','candidate') if i%2==0 else ('candidate','original')
        for label in order:
            item=run(getattr(a,label),paths,a.output/f'{i:02d}'/(label+'.json'),48,settings)
            comparable=(item['solution_sha256'],item['comparable'])
            if expected is None:expected=comparable
            if comparable!=expected:raise RuntimeError('Unequal fixed-round native work or solution')
            record[label]=item
        records.append(record)
        (a.output/'progress.json').write_text(json.dumps({'pairs':len(records)},indent=2)+'\n')
    medians={label:statistics.median(r[label]['solver_seconds_diagnostic'] for r in records) for label in ('original','candidate')}
    report={'scope':'one generated36-node/16-slot/48-demand fixed48-round workload; not public benchmarks',
            'pairs':len(records),'resumed':bool(a.resume),'incumbent_sha256':hashlib.sha256(a.resume.read_bytes()).hexdigest() if a.resume else None,'original_binary_sha256':hashlib.sha256(a.original.read_bytes()).hexdigest(),
            'candidate_binary_sha256':hashlib.sha256(a.candidate.read_bytes()).hexdigest(),
            'medians_solver_seconds':medians,'reduction_percent':100*(1-medians['candidate']/medians['original']),
            'all_solutions_loads_budgets_counters_equal':True,'records':records}
    (a.output/'RESULTS.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))
if __name__=='__main__':main()
