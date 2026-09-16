from __future__ import annotations
import argparse, json, os, stat, sys
from .engine import MapError, canonical_bytes, compile_receipt, strict_loads, verify_receipt

MAX_BYTES=2_000_000

def read_regular(path: str) -> bytes:
    flags=os.O_RDONLY|getattr(os,"O_CLOEXEC",0)|getattr(os,"O_NONBLOCK",0)
    if hasattr(os,"O_NOFOLLOW"): flags |= os.O_NOFOLLOW
    try:
        fd=os.open(path,flags)
    except OSError as exc:
        raise MapError(f"cannot open regular no-follow input: {path}") from exc
    try:
        st=os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise MapError(f"not regular file: {path}")
        if st.st_size > MAX_BYTES:
            raise MapError(f"input too large: {path}")
        chunks=[]; total=0
        while True:
            chunk=os.read(fd,min(65536,MAX_BYTES+1-total))
            if not chunk: break
            total += len(chunk)
            if total > MAX_BYTES: raise MapError(f"input too large: {path}")
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)

def write_exclusive(path: str, data: bytes) -> None:
    flags=os.O_WRONLY|os.O_CREAT|os.O_EXCL|getattr(os,"O_CLOEXEC",0)
    if hasattr(os,"O_NOFOLLOW"): flags |= os.O_NOFOLLOW
    fd=os.open(path,flags,0o600)
    try:
        view=memoryview(data)
        while view:
            n=os.write(fd,view)
            if n<=0: raise MapError("short write")
            view=view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)

def main(argv=None):
    p=argparse.ArgumentParser()
    s=p.add_subparsers(dest="cmd",required=True)
    v=s.add_parser("compile")
    v.add_argument("--map",required=True); v.add_argument("--receipt",required=True)
    q=s.add_parser("verify")
    q.add_argument("--map",required=True); q.add_argument("--receipt",required=True)
    args=p.parse_args(argv)
    try:
        raw=strict_loads(read_regular(args.map))
        if args.cmd=="compile":
            receipt=compile_receipt(raw)
            write_exclusive(args.receipt,canonical_bytes(receipt))
            print(json.dumps({"target_count":receipt["target_count"],"route_status_counts":receipt["route_status_counts"],"receipt_sha256":receipt["receipt_sha256"]},sort_keys=True))
            return 0
        receipt=strict_loads(read_regular(args.receipt))
        ok=verify_receipt(raw,receipt)
        print("EXACT_BUYER_MAP_MATCH" if ok else "BUYER_MAP_MISMATCH")
        return 0 if ok else 3
    except (MapError,OSError,UnicodeError) as exc:
        print(json.dumps({"error":str(exc)},sort_keys=True),file=sys.stderr)
        return 2

if __name__=="__main__":
    raise SystemExit(main())
