from __future__ import annotations
import argparse, json, shutil
from pathlib import Path
from submission_src.datpark.bundle import sha256_file
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--bundle', required=True); ap.add_argument('--out', required=True); a=ap.parse_args(); src=Path(a.bundle); out=Path(a.out)
    if out.exists(): shutil.rmtree(out)
    out.mkdir(parents=True); manifest=json.loads((src/'manifest.json').read_text()); allowed={'manifest.json','training_receipt.json',*(m['path'] for m in manifest['members'])}
    extras={p.name for p in src.iterdir() if p.is_file()}-allowed
    if extras: raise SystemExit(f'unexpected bundle files: {sorted(extras)}')
    for name in sorted(allowed):
        p=src/name
        if p.exists(): shutil.copy2(p,out/name)
    receipt={p.name:sha256_file(p) for p in sorted(out.iterdir()) if p.is_file()}; (out/'PUBLICATION_RECEIPT.json').write_text(json.dumps(receipt, sort_keys=True, indent=2)+'\n')
if __name__=='__main__': main()
