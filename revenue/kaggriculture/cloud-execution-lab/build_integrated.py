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

if __name__=='__main__': print(json.dumps(build()))
