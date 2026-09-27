#!/usr/bin/env python3
"""Print SUMMARY.json plus per-game tokens seed:own_s0/rival_s0/own_s1/rival_s1."""
import json, sys
from pathlib import Path
from collections import defaultdict

def load_games(path):
    rows=[]
    for line in Path(path).read_text().splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows

def main(outdir):
    outdir=Path(outdir)
    summary=json.loads((outdir/'SUMMARY.json').read_text())
    print('SUMMARY', json.dumps(summary, sort_keys=True))
    games=load_games(outdir/'GAMES.jsonl')
    by=defaultdict(dict)
    for g in games:
        if g.get('status')!='complete':
            print('FAIL', g)
            continue
        cs=int(g['candidate_seat']); scores=g['scores']
        by[(g['opponent'], int(g['seed']))][cs]=scores
    opps=sorted({k[0] for k in by})
    for opp in opps:
        print(f'## {opp}')
        seeds=sorted({k[1] for k in by if k[0]==opp})
        for seed in seeds:
            seats=by[(opp,seed)]
            s0=seats.get(0); s1=seats.get(1)
            def tok(scores, cs):
                if not scores: return 'NA/NA'
                return f'{scores[cs]}/{scores[1-cs]}'
            print(f'{seed}:{tok(s0,0)}/{tok(s1,1)}')

if __name__=='__main__':
    main(sys.argv[1])
