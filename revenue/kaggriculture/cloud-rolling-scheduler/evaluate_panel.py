"""Paired official-engine games with per-game isolated actors and frozen sources."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module


def run(runtime,engine_dir,output,seeds,opponents,seats,arms):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((runtime/'runtime-manifest.json').read_text())
    for name,digest in manifest['runtime_sha256'].items():
        assert hashlib.sha256((runtime/name).read_bytes()).hexdigest()==digest,(name,'runtime changed')
    ev=load(ROOT/'cloud-eval/evaluate.py','t03_panel_evaluator')
    engine,engine_hashes=ev.get_engine(engine_dir)
    # Benchmark-only per-game event collection; actor working directories remain
    # private and are deleted by the unchanged existing close implementation.
    original_close=ev.Actor.close
    def close(actor):
        path=Path(actor.directory.name)/'t03-events.json'
        if path.exists():
            actor.stats['t03_events']=json.loads(path.read_text())
        return original_close(actor)
    ev.Actor.close=close
    games=[]
    for seed in seeds:
        for opponent in opponents:
            for seat in seats:
                for arm in arms:
                    name=f'{seed}-{opponent}-seat{seat}-{arm}'
                    destination=output/(name+'.json')
                    if destination.exists():
                        row=json.loads(destination.read_text())
                        matches = (row['source_sha256'].get('arlene.py')==manifest['source_sha256']['arlene.py'] and row['engine_sha256']==engine_hashes) if arm=='arlene' else row['source_sha256']==manifest['source_sha256']
                        if not matches:
                            raise ValueError('Existing game belongs to another source freeze; use another output directory')
                        games.append(row);continue
                    candidate=manifest['adapters'][arm]
                    rival=manifest['adapters'][opponent]
                    pair=[candidate,rival] if seat==0 else [rival,candidate]
                    row=ev.play(engine,pair,engine_dir,ev.LOADER,seed,seat,
                                action_timeout=1.0,startup_timeout=10,game_timeout=90)
                    row.update(arm=arm,opponent=opponent,source_sha256=manifest['source_sha256'],engine_sha256=engine_hashes)
                    destination.write_text(json.dumps(row,indent=2)+'\n')
                    games.append(row)
                    print(json.dumps({k:row[k] for k in ('seed','opponent','candidate_seat','arm','status','steps','scores','failure')}),flush=True)
    pairs=[]
    for seed in seeds:
        for opponent in opponents:
            for seat in seats:
                selected={r['arm']:r for r in games if r['seed']==seed and r['opponent']==opponent and r['candidate_seat']==seat}
                if 'arlene' not in selected or 'candidate' not in selected:continue
                a,b=selected['arlene'],selected['candidate']
                if a['status']!='complete' or b['status']!='complete':continue
                am=a['scores'][seat]-a['scores'][1-seat];bm=b['scores'][seat]-b['scores'][1-seat]
                outcome=lambda m:'W' if m>0 else 'L' if m<0 else 'T'
                pairs.append({'seed':seed,'opponent':opponent,'seat':seat,'control':outcome(am),'candidate':outcome(bm),
                              'own_cash_delta':b['scores'][seat]-a['scores'][seat],
                              'rival_cash_delta':b['scores'][1-seat]-a['scores'][1-seat],'margin_delta':bm-am})
    report={'games':games,'pairs':pairs,'seed_scope':'development unless accompanied by a prior immutable freeze receipt',
            'claim':'Offline simulations, not hosted leaderboard or cash earnings'}
    (output/'panel.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'pairs':pairs},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime',type=Path,required=True);p.add_argument('--engine-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seeds',required=True);p.add_argument('--opponents',default='arlene,apex');p.add_argument('--seats',default='0,1');p.add_argument('--arms',default='arlene,candidate')
    a=p.parse_args();run(a.runtime,a.engine_dir,a.output,[int(x) for x in a.seeds.split(',')],a.opponents.split(','),[int(x) for x in a.seats.split(',')],a.arms.split(','))
