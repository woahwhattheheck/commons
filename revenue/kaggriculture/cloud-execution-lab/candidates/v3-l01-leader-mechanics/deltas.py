#!/usr/bin/env python3
"""Paired own-cash deltas vs canonical for L01 candidates."""
import json, sys
from pathlib import Path
from collections import defaultdict
from statistics import mean

def games(path):
    out=[]
    for line in Path(path).read_text().splitlines():
        if line.strip():
            g=json.loads(line)
            if g.get('status')=='complete':
                out.append(g)
    return out

def index(rows):
    d={}
    for g in rows:
        cs=int(g['candidate_seat'])
        own=g['scores'][cs]; rival=g['scores'][1-cs]
        d[(g['opponent'], int(g['seed']), cs)] = {'own': own, 'rival': rival, 'margin': own-rival}
    return d

def summarize(name, cand, base):
    deltas=[]
    plus=minus=zero=0
    flips=[]
    missing=0
    per_opp=defaultdict(list)
    for k, b in base.items():
        if k not in cand:
            missing += 1
            continue
        d = cand[k]['own'] - b['own']
        deltas.append(d)
        per_opp[k[0]].append(d)
        if d>0: plus += 1
        elif d<0: minus += 1
        else: zero += 1
        bwin = b['margin']>0; cwin = cand[k]['margin']>0
        if bwin != cwin:
            flips.append({'key': list(k), 'canonical_margin': b['margin'], 'candidate_margin': cand[k]['margin']})
    def pack(xs):
        if not xs: return None
        return {'n': len(xs), 'mean': round(mean(xs), 3), 'min': min(xs), 'max': max(xs),
                'plus': sum(1 for x in xs if x>0), 'minus': sum(1 for x in xs if x<0), 'zero': sum(1 for x in xs if x==0)}
    return {
        'candidate': name,
        'paired': pack(deltas),
        'per_opponent': {o: pack(xs) for o,xs in sorted(per_opp.items())},
        'result_flips': flips,
        'missing': missing,
    }

def main(panel_dir):
    panel=Path(panel_dir)
    base=index(games(panel/'canonical.GAMES.jsonl'))
    names=['land','sheep','day0buy','tranche','leanplant']
    reports=[]
    keep=[]
    for name in names:
        p=panel/f'{name}.GAMES.jsonl'
        if not p.is_file():
            continue
        r=summarize(name, index(games(p)), base)
        reports.append(r)
        mean_d=(r['paired'] or {}).get('mean')
        if mean_d is not None and mean_d >= 0:
            keep.append(name)
    out={'reports': reports, 'combine': keep}
    print(json.dumps(out, indent=2))
    (panel/'DELTAS.json').write_text(json.dumps(out, indent=2)+'\n')
    print('COMBINE', ','.join(keep) if keep else '(none)')

if __name__=='__main__':
    main(sys.argv[1] if len(sys.argv)>1 else '/tmp/v25/land/v3-l01-leader-mechanics/panels')
