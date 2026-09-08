#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Count native distance calls on the saved cold/resumed benchmark, untimed.

Only diagnostic counters and a final stderr line are inserted into a temporary
copy. The original production file is not modified. Not a throughput measurement.
"""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,tempfile
from fixed_round import run
from probe import SIGNATURE


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True);p.add_argument('--vendor',type=Path,required=True)
    p.add_argument('--workload',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();a.workload=a.workload.resolve();a.output=a.output.resolve()
    if a.output.exists():p.error('new output directory required')
    a.output.mkdir(parents=True)
    original=a.source.read_bytes();text=original.decode()
    before='static volatile std::sig_atomic_t interrupted = 0;'
    counters='''static unsigned long long wrenDistanceCalls=0, wrenDifferentCalls=0;
struct WrenDistanceProfile { ~WrenDistanceProfile() {
    std::cerr << "WREN_DISTANCE_CALLS " << wrenDistanceCalls << " " << wrenDifferentCalls << "\\n";
} } wrenDistanceProfile;
'''
    assert text.count(before)==1 and text.count(SIGNATURE)==1
    text=text.replace(before,counters+before,1)
    text=text.replace(SIGNATURE,SIGNATURE+'\n        ++wrenDistanceCalls;\n        if (a != b) ++wrenDifferentCalls;',1)
    src=a.output/'instrumented.cpp';src.write_text(text)
    binary=a.output/'instrumented'
    command=['g++','-std=c++20','-O3','-DNDEBUG','-I',str(a.vendor.resolve()),str(src),'-o',str(binary)]
    built=subprocess.run(command,capture_output=True,timeout=60)
    (a.output/'build.log').write_bytes(built.stdout+built.stderr)
    if built.returncode:raise RuntimeError('diagnostic build failed')
    paths=[a.workload/n for n in ('net.json','tm.json','scenario.json')]
    reference=json.loads((a.workload/'RESULTS.json').read_text())['records'][0]['original']
    rows=[]
    for name,env in [('cold',{}),('resume',{'CLOUD_INITIAL_SOLUTION':str(a.workload/'00'/'original.json')})]:
        item=run(binary,paths,a.output/(name+'.json'),48,env)
        match=re.search(rb'WREN_DISTANCE_CALLS (\d+) (\d+)',(a.output/(name+'.stderr')).read_bytes())
        if match is None:raise RuntimeError('Missing native counter')
        if name=='cold' and (item['comparable']!=reference['comparable'] or item['solution_sha256']!=reference['solution_sha256']):
            raise RuntimeError('Instrumented cold work differs from saved original')
        rows.append({'kind':name,'distance_calls':int(match[1]),'nonidentical_calls':int(match[2]),
                     'equal_route_calls':int(match[1])-int(match[2]),'result':item})
    report={'scope':'untimed native call-count attribution on existing generated workload',
            'source_sha256':hashlib.sha256(original).hexdigest(),
            'instrumented_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),
            'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'rows':rows}
    (a.output/'RESULTS.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({**{k:v for k,v in report.items() if k!='rows'},'rows':[{k:v for k,v in r.items() if k!='result'} for r in rows]},indent=2))
if __name__=='__main__':main()
