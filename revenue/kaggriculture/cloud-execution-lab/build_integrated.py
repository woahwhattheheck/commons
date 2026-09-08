# SPDX-License-Identifier: Apache-2.0
"""Build only the new integrated candidate and its parent control."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

ROOT=Path(__file__).resolve().parent
RUNTIME=['integrated_selected.py','integrated_main.py','integrated_parent.py',
 'ordered_selected_sell.py','selected_action_sell.py','selected_sell_core.py','mechanics.py',
 'reference/decision/decision.py','reference/decision/README.md',
 'reference/ordered-feasibility/atlas/projection.py',
 'reference/selected-action/t08/arrival_contract.py','reference/selected-action/t08/LICENSE-ROOT',
 'reference/next-panel/vendor/arlene.py','reference/next-panel/LICENSE',
 'reference/next-panel/NEXT-DISTRIBUTION-NOTICE.txt','reference/next-panel/UPSTREAM.json',
 'reference/engine/LICENSE','reference/integrated-selected/alder/seed_budget.py',
 'reference/integrated-selected/UPSTREAM.json',
 *['reference/integrated-selected/claude/'+f for f in
   ['arlene_plan.py','native_motifs.py','run_cards.py','arrival_facts.py','engine_pin.py',
    'LICENSE-MIT.txt','LICENSE-APACHE-2.0.txt']]]

def build():
    blobs={p:(ROOT/p).read_bytes() for p in RUNTIME}
    rows={p:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)} for p,b in blobs.items()}
    manifest={'runtime':rows,'candidate':'integrated_main.py','parent':'integrated_parent.py',
              'module':'integrated_selected.py','factory':'make_agent',
              'default_switches':{'seed':True,'committed':True,'sell':True}}
    encoded=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    (ROOT/'runtime/integrated-selected/SOURCE.json').write_bytes(encoded)
    blobs['SOURCE.json']=encoded
    output=io.BytesIO()
    with gzip.GzipFile(fileobj=output,mode='wb',mtime=0,filename='') as gz:
        with tarfile.open(fileobj=gz,mode='w') as archive:
            for path,data in sorted(blobs.items()):
                info=tarfile.TarInfo(path);info.size=len(data);info.mode=0o644;info.mtime=0
                archive.addfile(info,io.BytesIO(data))
    path=ROOT/'exports/integrated-selected-v1.tar.gz';path.write_bytes(output.getvalue())
    receipt={'path':str(path.relative_to(ROOT)), 'sha256':hashlib.sha256(output.getvalue()).hexdigest(),
             'bytes':len(output.getvalue()),'runtime_files':len(rows)}
    (ROOT/'runtime/integrated-selected/ARCHIVE.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def build_release(version=None):
    """Evolve this packaging boundary; retain the PR9997 archive unchanged."""
    blobs={p:(ROOT/p).read_bytes() for p in RUNTIME}
    for p in ['main.py','titan_runtime.py','frozen_selected.py','TITAN-CONFIG.json',
              'scheduler.py','LICENSE','NOTICE','TITAN-RELEASE.md']:
        blobs[p]=(ROOT/p).read_bytes()
    for p in (ROOT/'reference/titan-current').rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts:
            blobs[str(p.relative_to(ROOT))]=p.read_bytes()
    for name in ['integrated_selected.py','selected_action_sell.py',
                 'selected_sell_core.py','ordered_selected_sell.py']:
        blobs[name]=blobs['reference/titan-current/latest/'+name]
    # OSPREY's exact shipped relative paths, with no original-repository imports.
    for name in ['scheduler.py','mechanics.py','reference/next-panel/vendor/arlene.py',
                 'reference/decision/decision.py']:
        blobs['reference/titan-current/vendor/sell/'+name]=(ROOT/name).read_bytes()
    blobs['reference/titan-current/vendor/terminal.py']=blobs['reference/titan-current/terminal.py']
    if version == 'history-v2':
        for name in ['terminal_history_join.py','TITAN-HISTORY-CONFIG.json']:
            blobs[name]=(ROOT/name).read_bytes()
        for name in ['test_terminal_history_join.py','test_ordered_selected_sell.py','test_engine_semantics.py']:
            blobs['checks/'+name]=(ROOT/name).read_bytes()
        for name in ['reference/engine/kaggriculture.py','reference/engine/kaggriculture.json',
                     'reference/engine/utils.py','reference/evaluator/evaluate.py','reference/evaluator/loader.py']:
            blobs['checks/'+name]=(ROOT/name).read_bytes()
        for p in (ROOT/'reference/titan-history').rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                blobs[str(p.relative_to(ROOT))]=p.read_bytes()
    rows={p:{'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)} for p,b in blobs.items()}
    manifest=json.loads((ROOT/'runtime/integrated-selected/RELEASE.json').read_text())
    manifest.update(runtime=rows,entrypoint='main.py',default=json.loads(blobs['TITAN-CONFIG.json']))
    if version == 'history-v2':
        manifest.update(release='titan-history-v2',history=json.loads((ROOT/'runtime/integrated-selected/HISTORY-RELEASE.json').read_text()))
    encoded=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    blobs['SOURCE.json']=encoded
    prefix='HISTORY' if version == 'history-v2' else 'CURRENT'
    (ROOT/f'runtime/integrated-selected/{prefix}-SOURCE.json').write_bytes(encoded)
    output=io.BytesIO()
    with gzip.GzipFile(fileobj=output,mode='wb',mtime=0,filename='') as gz:
        with tarfile.open(fileobj=gz,mode='w') as archive:
            for path,data in sorted(blobs.items()):
                info=tarfile.TarInfo(path);info.size=len(data);info.mode=0o644;info.mtime=0
                archive.addfile(info,io.BytesIO(data))
    path=ROOT/('exports/titan-history-v2.tar.gz' if version == 'history-v2' else 'exports/titan-current.tar.gz')
    path.write_bytes(output.getvalue())
    receipt={'path':str(path.relative_to(ROOT)), 'sha256':hashlib.sha256(output.getvalue()).hexdigest(),
             'bytes':len(output.getvalue()),'runtime_files':len(rows),
             'source_manifest_sha256':hashlib.sha256(encoded).hexdigest()}
    (ROOT/f'runtime/integrated-selected/{prefix}-ARCHIVE.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

if __name__=='__main__':
    import sys
    print(json.dumps(build_release('history-v2' if '--history-v2' in sys.argv else None)
                     if '--release' in sys.argv or '--history-v2' in sys.argv else build()))
