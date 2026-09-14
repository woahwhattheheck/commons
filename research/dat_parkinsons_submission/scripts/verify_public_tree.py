from __future__ import annotations
import argparse
from pathlib import Path
FORBIDDEN_SUFFIXES={'.nii','.nii.gz','.pt','.pth','.ckpt','.safetensors','.dcm','.dicom','.npz'}
FORBIDDEN_NAMES={'train_labels.csv','submission.csv','submission.zip','smoke_test_data.tar.gz','model_bundle'}
def suffix_for(path:Path):
    name=path.name.lower(); return '.nii.gz' if name.endswith('.nii.gz') else path.suffix.lower()
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('root', nargs='?', default='.'); a=ap.parse_args(); root=Path(a.root).resolve(); problems=[]
    for p in root.rglob('*'):
        if any(part in {'.git','__pycache__'} for part in p.parts): continue
        if p.name in FORBIDDEN_NAMES: problems.append(f'forbidden name: {p.relative_to(root)}')
        if p.is_file():
            if suffix_for(p) in FORBIDDEN_SUFFIXES: problems.append(f'forbidden binary/data suffix: {p.relative_to(root)}')
            if p.stat().st_size>2_000_000: problems.append(f'public file unexpectedly >2MB: {p.relative_to(root)}')
    if problems: raise SystemExit('\n'.join(problems))
    print('PUBLIC_TREE_DATA_GUARD_PASS')
if __name__=='__main__': main()
