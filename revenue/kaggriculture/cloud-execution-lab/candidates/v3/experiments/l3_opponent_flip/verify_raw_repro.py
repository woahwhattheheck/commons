#!/usr/bin/env python3
import json,statistics
from pathlib import Path
H=Path(__file__).resolve().parent
raw=json.loads((H/'RAW-REPRO-20260911.json').read_text()); pub=json.loads((H/'L3-OPPONENT-FLIP-20260911.json').read_text())
def km(n): return {(r[0],r[1]):r for r in raw['panels'][n]}
def margin(r): return r[2+r[1]]-r[2+(1-r[1])]
def sm(v): return {'max':max(v),'mean':sum(v)/len(v),'median':statistics.median(v),'min':min(v),'n':len(v),'negative':sum(x<0 for x in v),'positive':sum(x>0 for x in v),'zero':sum(x==0 for x in v)}
def cells(d): return [{'candidate_seat':k[1],'seed':k[0],'value':v} for k,v in sorted(d.items())]
lo,lc=km('low_l3_vs_arlene'),km('low_v31_vs_arlene_control'); assert lo.keys()==lc.keys(); low={k:margin(lo[k])-margin(lc[k]) for k in lo}
direct={k:margin(r) for k,r in km('low_l3_vs_v31').items()}
fo,fc=km('frozen_l3_vs_arlene'),km('frozen_v31_vs_arlene_control'); assert fo.keys()==fc.keys(); frozen={k:margin(fo[k])-margin(fc[k]) for k in fo}
assert cells(low)==pub['opponent_flip']['arlene']['cells']; assert sm(list(low.values()))==pub['opponent_flip']['arlene']['summary']
assert cells(direct)==pub['opponent_flip']['exact_v31']['cells']; assert sm(list(direct.values()))==pub['opponent_flip']['exact_v31']['summary']
assert cells(frozen)==pub['validation_frozen_arlene']['cells']; assert sm(list(frozen.values()))==pub['validation_frozen_arlene']['summary']
assert all(margin(r)==0 for r in raw['panels']['v31_self_seed101'])
t=raw['seed102_telemetry_by_seat']; assert t==[[102,0,97380.0,97695.0,70,30,240,240],[102,1,97695.0,97380.0,70,30,240,240]]
print(json.dumps({'ok':True,'low_arlene':sm(list(low.values())),'direct_v31':sm(list(direct.values())),'frozen_arlene':sm(list(frozen.values())),'seed102_telemetry_by_seat':t},sort_keys=True))
