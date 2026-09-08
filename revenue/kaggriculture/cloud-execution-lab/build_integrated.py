# SPDX-License-Identifier: Apache-2.0
"""Build and verify the single current TITAN release."""
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

ARCHIVE='exports/titan-current.tar.gz'
RECORD='runtime/integrated-selected/'


def source_files():
    """Archive member -> actual current repository source; no version selector."""
    mapping={p:p for p in RUNTIME if p not in ('integrated_main.py','integrated_parent.py')}
    for p in ['main.py','titan_runtime.py','frozen_selected.py','scheduler.py',
              'terminal_history_join.py','TITAN-CONFIG.json','LICENSE','NOTICE','TITAN-RELEASE.md']:
        mapping[p]=p
    for directory in ('reference/titan-current','reference/titan-history'):
        for p in (ROOT/directory).rglob('*'):
            if p.is_file() and '__pycache__' not in p.parts:
                name=str(p.relative_to(ROOT));mapping[name]=name
    for name in ('integrated_selected.py','selected_action_sell.py','selected_sell_core.py','ordered_selected_sell.py'):
        mapping[name]='reference/titan-current/latest/'+name
    for name in ('scheduler.py','mechanics.py','reference/next-panel/vendor/arlene.py','reference/decision/decision.py'):
        mapping['reference/titan-current/vendor/sell/'+name]=name
    mapping['reference/titan-current/vendor/terminal.py']='reference/titan-current/terminal.py'
    # Controls and experimental configuration are reproduction inputs only.
    for name in ('TITAN-HISTORY-CONFIG.json','test_terminal_history_join.py',
                 'test_entrypoint_clock.py','test_module_recovery.py','test_seed_derived.py','test_ordered_selected_sell.py','test_engine_semantics.py'):
        mapping['checks/'+name]=name
    for name in ('reference/historical/seed_budget-before-derived-cache.py','reference/engine/kaggriculture.py','reference/engine/kaggriculture.json',
                 'reference/engine/utils.py','reference/evaluator/evaluate.py','reference/evaluator/loader.py'):
        mapping['checks/'+name]=name
    return mapping


def render():
    mapping=source_files()
    blobs={p:(ROOT/source).read_bytes() for p,source in mapping.items()}
    manifest=json.loads((ROOT/(RECORD+'RELEASE.json')).read_text())
    manifest.update(entrypoint='main.py::agent',config='TITAN-CONFIG.json',
        default=json.loads(blobs['TITAN-CONFIG.json']),
        runtime={p:{'source_path':mapping[p],'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
                 for p,b in blobs.items()})
    encoded=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    blobs['SOURCE.json']=encoded
    output=io.BytesIO()
    with gzip.GzipFile(fileobj=output,mode='wb',mtime=0,filename='') as gz:
        with tarfile.open(fileobj=gz,mode='w') as archive:
            for path,data in sorted(blobs.items()):
                info=tarfile.TarInfo(path);info.size=len(data);info.mode=0o644;info.mtime=0
                archive.addfile(info,io.BytesIO(data))
    data=output.getvalue()
    receipt={'path':ARCHIVE,'entrypoint':'main.py::agent','config':'TITAN-CONFIG.json',
             'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),
             'runtime_files':len(mapping),'source_manifest':RECORD+'CURRENT-SOURCE.json',
             'source_manifest_sha256':hashlib.sha256(encoded).hexdigest()}
    return data,encoded,receipt


def build_release():
    data,manifest,receipt=render()
    # Preserve every superseded current archive before advancing the one stream.
    current=ROOT/ARCHIVE
    if current.exists() and current.read_bytes()!=data:
        old=current.read_bytes();digest=hashlib.sha256(old).hexdigest()
        historical=ROOT/'exports/historical'/('titan-'+digest+'.tar.gz')
        historical.parent.mkdir(parents=True,exist_ok=True)
        if historical.exists() and historical.read_bytes()!=old:
            raise ValueError('Historical archive identity collision')
        historical.write_bytes(old)
    current.write_bytes(data)
    (ROOT/(RECORD+'CURRENT-SOURCE.json')).write_bytes(manifest)
    (ROOT/(RECORD+'CURRENT-ARCHIVE.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    verify_current()
    return receipt


def verify_current():
    """Fail on stale source, stale pointer, changed config or archive contents."""
    data,manifest,receipt=render()
    actual=json.loads((ROOT/(RECORD+'CURRENT-ARCHIVE.json')).read_text())
    if actual!=receipt:raise ValueError('Current release pointer differs from current source')
    if (ROOT/ARCHIVE).read_bytes()!=data:raise ValueError('Canonical archive differs from current source')
    if (ROOT/(RECORD+'CURRENT-SOURCE.json')).read_bytes()!=manifest:
        raise ValueError('Current manifest differs from current source')
    return receipt


build=build_release

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--release',action='store_true',help=argparse.SUPPRESS)
    args=parser.parse_args()
    print(json.dumps(verify_current() if args.check else build_release()))
