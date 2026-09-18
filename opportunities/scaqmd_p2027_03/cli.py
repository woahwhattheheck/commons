from __future__ import annotations
import argparse, json, os, sys
from datetime import datetime, timezone
from pathlib import Path
from .engine import build_source_authority, compile_assessment, verify_assessment, ValidationError

def _pairs(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise ValueError(f"duplicate JSON key: {k}")
        out[k]=v
    return out

def load_json(path):
    p=Path(path)
    if not p.is_file() or p.is_symlink() or p.stat().st_size>10_000_000: raise ValueError("input must be bounded regular non-symlink file")
    return json.loads(p.read_text("utf-8"),object_pairs_hook=_pairs,parse_constant=lambda x: (_ for _ in ()).throw(ValueError(f"nonfinite {x}")))
def key_env():
    try: k=bytes.fromhex(os.environ.get("SCAQMD_SOURCE_AUTHORITY_KEY_HEX",""))
    except ValueError as exc: raise ValueError("SCAQMD_SOURCE_AUTHORITY_KEY_HEX must be hex") from exc
    if len(k)<32: raise ValueError("SCAQMD_SOURCE_AUTHORITY_KEY_HEX must decode to >=32 bytes")
    return k
def write_exclusive(path,value):
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL
    if hasattr(os,"O_NOFOLLOW"): flags|=os.O_NOFOLLOW
    fd=os.open(path,flags,0o600)
    try:
        data=(json.dumps(value,sort_keys=True,indent=2,ensure_ascii=False,allow_nan=False)+"\n").encode()
        os.write(fd,data); os.fsync(fd)
    finally: os.close(fd)
def main(argv=None):
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("sign-source"); p.add_argument("source"); p.add_argument("output"); p.add_argument("--key-id",required=True); p.add_argument("--issued-at")
    p=sub.add_parser("compile"); p.add_argument("packet"); p.add_argument("authority"); p.add_argument("output"); p.add_argument("--key-id",required=True); p.add_argument("--as-of")
    p=sub.add_parser("verify"); p.add_argument("packet"); p.add_argument("authority"); p.add_argument("assessment"); p.add_argument("--key-id",required=True)
    a=ap.parse_args(argv); key=key_env()
    try:
        if a.cmd=="sign-source":
            issued=a.issued_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
            write_exclusive(a.output,build_source_authority(load_json(a.source),key_id=a.key_id,key=key,issued_at=issued))
        elif a.cmd=="compile":
            as_of=a.as_of or datetime.now(timezone.utc).isoformat(timespec="seconds")
            write_exclusive(a.output,compile_assessment(load_json(a.packet),load_json(a.authority),key=key,expected_key_id=a.key_id,as_of=as_of))
        else:
            print("VERIFIED" if verify_assessment(load_json(a.packet),load_json(a.authority),load_json(a.assessment),key=key,expected_key_id=a.key_id) else "FAILED")
    except (ValidationError,ValueError,OSError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr); return 2
    return 0
if __name__=="__main__": raise SystemExit(main())
