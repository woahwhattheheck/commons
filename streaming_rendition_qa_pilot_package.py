from __future__ import annotations
import hashlib, json, os, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FILES = [
    ".github/workflows/streaming-rendition-qa-pilot.yml",
    "revenue/streaming_rendition_qa_pilot/__init__.py",
    "revenue/streaming_rendition_qa_pilot/core.py",
    "revenue/streaming_rendition_qa_pilot/artifacts.py",
    "revenue/streaming_rendition_qa_pilot/README.md",
    "revenue/streaming_rendition_qa_pilot/manifest.json",
    "streaming_rendition_qa_pilot_standalone.py",
    "streaming_rendition_qa_pilot_package.py",
    "test_streaming_rendition_qa_pilot.py",
]
FIXED=(1980,1,1,0,0,0)
def sha(b): return hashlib.sha256(b).hexdigest()
def build(out_path):
    payloads={}
    for rel in FILES:
        p=ROOT/rel
        if not p.is_file() or p.is_symlink(): raise ValueError(f"bad source file {rel}")
        payloads[rel]=p.read_bytes()
    sums="".join(f"{sha(payloads[r])}  {r}\n" for r in sorted(payloads)).encode()
    sbom=(json.dumps({"schema":"streaming-rendition-qa-pilot.sbom/v1","files":[{"path":r,"sha256":sha(payloads[r]),"bytes":len(payloads[r])} for r in sorted(payloads)],"runtime_dependencies":[]},sort_keys=True,separators=(",",":"))+"\n").encode()
    entries={**payloads,"SHA256SUMS":sums,"SBOM.json":sbom}
    out=Path(out_path)
    if out.exists() or out.is_symlink(): raise FileExistsError(out)
    with zipfile.ZipFile(out,"x",compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for rel in sorted(entries):
            info=zipfile.ZipInfo(rel,date_time=FIXED); info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=(0o100644&0xffff)<<16; info.create_system=3
            z.writestr(info,entries[rel])
    d=sha(out.read_bytes()); print(d); return d

def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if len(argv)!=1: print("usage: streaming_rendition_qa_pilot_package.py OUT.zip"); return 2
    try: build(argv[0]); return 0
    except (OSError,ValueError) as e: print(f"ERROR: {e}"); return 2
if __name__=="__main__": raise SystemExit(main())
