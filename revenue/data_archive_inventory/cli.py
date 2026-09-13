from __future__ import annotations
import argparse,json,os,stat,tempfile
from pathlib import Path
from .inventory import HOLD, InventoryError, canonical_json, compile_inventory, verify_inventory
MAX=2_000_000

def read_plain(p:Path)->bytes:
    flags=os.O_RDONLY | (getattr(os,"O_NOFOLLOW",0))
    fd=os.open(p,flags)
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode): raise InventoryError("input must be ordinary file")
        if st.st_size>MAX: raise InventoryError("input too large")
        b=b""
        while len(b)<st.st_size:
            c=os.read(fd,min(65536,st.st_size-len(b)))
            if not c: break
            b+=c
        if len(b)!=st.st_size: raise InventoryError("short read")
        return b
    finally: os.close(fd)

def write_atomic(p:Path,b:bytes)->None:
    p.parent.mkdir(parents=True,exist_ok=True)
    if p.is_symlink(): raise InventoryError("refuse symlink output")
    fd,tmp=tempfile.mkstemp(prefix=f".{p.name}.",dir=p.parent)
    tp=Path(tmp)
    try:
        with os.fdopen(fd,"wb") as f: f.write(b); f.flush(); os.fsync(f.fileno())
        os.replace(tp,p)
    finally:
        try: tp.unlink()
        except FileNotFoundError: pass

def main(argv=None)->int:
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    b=sub.add_parser("build"); b.add_argument("input"); b.add_argument("--receipt",required=True); b.add_argument("--csv",required=True); b.add_argument("--at",required=True)
    v=sub.add_parser("verify"); v.add_argument("input"); v.add_argument("--receipt",required=True); v.add_argument("--csv",required=True); v.add_argument("--at",required=True)
    a=ap.parse_args(argv)
    try:
        doc=json.loads(read_plain(Path(a.input)).decode())
        if a.cmd=="build":
            r,c=compile_inventory(doc,a.at); write_atomic(Path(a.receipt),canonical_json(r)); write_atomic(Path(a.csv),c); print(f"decision={r['decision']} eligible={r['counts']['eligible']} hold={r['counts']['hold']} receipt_sha256={r['receipt_sha256']}"); return 3 if r["decision"]==HOLD else 0
        r=json.loads(read_plain(Path(a.receipt)).decode()); c=read_plain(Path(a.csv)); ok=verify_inventory(doc,r,c,a.at); print("VERIFIED" if ok else "INVALID"); return 0 if ok else 2
    except (InventoryError,OSError,UnicodeDecodeError,json.JSONDecodeError) as e:
        print(f"HOLD: {e}"); return 2
if __name__=="__main__": raise SystemExit(main())
