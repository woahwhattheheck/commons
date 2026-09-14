from __future__ import annotations
import argparse, ast, json, stat, zipfile
from hashlib import sha256
from pathlib import Path
from core import TRACKS, canonical_json

REQUIRED = ("main.py", "core.py", "profiles.json", "runtime_contract.json", "model_config.json")
FORBIDDEN_IMPORTS = {"requests", "urllib", "httpx", "aiohttp", "socket", "ftplib", "paramiko"}
FORBIDDEN_TEXT = ("http://", "https://", "AKIA", "BEGIN PRIVATE KEY", "xoxb-")
FIXED_DT = (2026, 1, 1, 0, 0, 0)


def _scan_python(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    failures=[]
    for token in FORBIDDEN_TEXT:
        if token in text: failures.append(f"{path.name}: forbidden literal {token}")
    tree=ast.parse(text, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import): names=[a.name.split('.')[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom): names=[(node.module or '').split('.')[0]]
        else: continue
        for name in names:
            if name in FORBIDDEN_IMPORTS: failures.append(f"{path.name}: forbidden import {name}")
    return failures


def build(source: Path, track: str, output_zip: Path, receipt_path: Path, *, max_bytes: int = 14_000_000_000) -> dict:
    if track not in TRACKS: raise ValueError("unsupported track")
    missing=[x for x in REQUIRED if not (source/x).is_file()]
    if missing: raise ValueError(f"missing required files: {missing}")
    failures=[]; files=[]
    for p in sorted(source.rglob('*')):
        if not p.is_file(): continue
        rel=p.relative_to(source).as_posix()
        if p.is_symlink(): failures.append(f"symlink forbidden: {rel}"); continue
        if p.suffix=='.py': failures.extend(_scan_python(p))
        if p.stat().st_mode & (stat.S_ISUID|stat.S_ISGID): failures.append(f"privileged mode: {rel}")
        files.append((rel,p,sha256(p.read_bytes()).hexdigest(),p.stat().st_size))
    if failures: raise ValueError("; ".join(failures))
    runtime=json.loads((source/'runtime_contract.json').read_text())
    if runtime.get('internet_at_execution') is not False: raise ValueError('runtime must be offline')
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_zip,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for rel,p,_,_ in files:
            info=zipfile.ZipInfo(rel,FIXED_DT); info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o644<<16
            z.writestr(info,p.read_bytes())
    size=output_zip.stat().st_size
    if size>max_bytes: raise ValueError(f"bundle exceeds max_bytes: {size}>{max_bytes}")
    receipt={"schema_version":1,"track":track,"accepted":True,"runtime_commit":runtime['upstream_commit'],"internet_at_execution":False,
             "bundle_sha256":sha256(output_zip.read_bytes()).hexdigest(),"bundle_bytes":size,
             "files":[{"path":r,"sha256":h,"bytes":n} for r,_,h,n in files]}
    receipt_path.write_text(canonical_json(receipt),encoding='utf-8')
    return receipt


def verify(zip_path: Path, receipt_path: Path) -> bool:
    receipt=json.loads(receipt_path.read_text())
    if receipt.get('accepted') is not True or receipt.get('track') not in TRACKS: return False
    if sha256(zip_path.read_bytes()).hexdigest()!=receipt.get('bundle_sha256'): return False
    with zipfile.ZipFile(zip_path) as z:
        names=set(z.namelist())
        if not set(REQUIRED).issubset(names): return False
        for item in receipt['files']:
            if item['path'] not in names or sha256(z.read(item['path'])).hexdigest()!=item['sha256']: return False
    return True


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('source',type=Path); ap.add_argument('track',choices=sorted(TRACKS)); ap.add_argument('output_zip',type=Path); ap.add_argument('receipt',type=Path); ap.add_argument('--max-bytes',type=int,default=14_000_000_000)
    a=ap.parse_args(); build(a.source,a.track,a.output_zip,a.receipt,max_bytes=a.max_bytes)
if __name__=='__main__': main()
