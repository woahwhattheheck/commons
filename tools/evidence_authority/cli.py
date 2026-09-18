"""CLI for the source-bound authority kernel. No external side effects."""
from __future__ import annotations
import argparse, os, stat, sys
from pathlib import Path
from .codec import AuthorityError, MAX_DOCUMENT_BYTES, canonical_bytes, loads_strict_json_bytes
from .core import compile_current, compile_integrity, verify_receipt


def _generation(st):
    return (st.st_dev, st.st_ino, st.st_size, getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000)))


def _read(path:str,label:str)->bytes:
    """Read one regular file from a stable descriptor generation.

    Refuse symlinks, non-regular files, oversized files, and visible path or
    descriptor generation changes across the bounded read. O_NOFOLLOW is used
    when the platform exposes it; the lstat/fstat identity fence remains in
    place on platforms that do not.
    """
    p=Path(path)
    fd=None
    flags=os.O_RDONLY | getattr(os,"O_BINARY",0) | getattr(os,"O_CLOEXEC",0)
    nofollow=getattr(os,"O_NOFOLLOW",0)
    if nofollow: flags|=nofollow
    try:
        visible_before=p.lstat()
        if stat.S_ISLNK(visible_before.st_mode) or not stat.S_ISREG(visible_before.st_mode):
            raise AuthorityError(f"{label} must be a real regular file")
        fd=os.open(p,flags)
        opened_before=os.fstat(fd)
        if not stat.S_ISREG(opened_before.st_mode):
            raise AuthorityError(f"{label} must be a regular file")
        if _generation(visible_before)!=_generation(opened_before):
            raise AuthorityError(f"{label} visible generation changed before read")
        if opened_before.st_size>MAX_DOCUMENT_BYTES:
            raise AuthorityError(f"{label} exceeds document byte bound")
        remaining=MAX_DOCUMENT_BYTES+1
        chunks=[]
        while remaining:
            chunk=os.read(fd,min(65_536,remaining))
            if not chunk: break
            chunks.append(chunk);remaining-=len(chunk)
        raw=b"".join(chunks)
        if len(raw)>MAX_DOCUMENT_BYTES:
            raise AuthorityError(f"{label} exceeds document byte bound")
        opened_after=os.fstat(fd)
        if _generation(opened_before)!=_generation(opened_after) or len(raw)!=opened_after.st_size:
            raise AuthorityError(f"{label} changed during read")
        visible_after=p.lstat()
        if stat.S_ISLNK(visible_after.st_mode) or _generation(visible_after)!=_generation(opened_after):
            raise AuthorityError(f"{label} visible generation changed during read")
        return raw
    except AuthorityError:
        raise
    except OSError as exc:
        raise AuthorityError(f"cannot read {label}") from exc
    finally:
        if fd is not None:
            try: os.close(fd)
            except OSError: pass


def _sources(directory:str)->dict[str,bytes]:
    root=Path(directory)
    try:
        root_before=root.lstat()
        if stat.S_ISLNK(root_before.st_mode) or not stat.S_ISDIR(root_before.st_mode):
            raise AuthorityError("sources directory must be a real directory")
        out={}
        for current,dirnames,filenames in os.walk(root,topdown=True,followlinks=False):
            current_path=Path(current)
            for name in list(dirnames):
                child=current_path/name
                st=child.lstat()
                if stat.S_ISLNK(st.st_mode):
                    raise AuthorityError("retained source tree must not contain symlink directories")
                if not stat.S_ISDIR(st.st_mode):
                    raise AuthorityError("retained source tree contains a non-directory traversal entry")
            for name in sorted(filenames):
                p=current_path/name
                rel=p.relative_to(root).as_posix()
                out[rel]=_read(str(p),f"source {rel}")
        root_after=root.lstat()
        if stat.S_ISLNK(root_after.st_mode) or _generation(root_before)!=_generation(root_after):
            raise AuthorityError("sources directory generation changed during read")
        return dict(sorted(out.items()))
    except AuthorityError:
        raise
    except OSError as exc:
        raise AuthorityError("cannot read retained source tree") from exc


def _candidate(path:str): return loads_strict_json_bytes(_read(path,"candidate"),label="candidate")
def _emit(value): sys.stdout.buffer.write(canonical_bytes(value)+b"\n")

def build_parser():
    p=argparse.ArgumentParser(prog="evidence-authority")
    sub=p.add_subparsers(dest="command",required=True)
    for name in ("compile-current","compile-integrity"):
        q=sub.add_parser(name);q.add_argument("candidate");q.add_argument("manifest");q.add_argument("sources_dir");q.add_argument("pinned_root")
    q=sub.add_parser("verify");q.add_argument("candidate");q.add_argument("manifest");q.add_argument("sources_dir");q.add_argument("pinned_root");q.add_argument("receipt")
    return p

def main(argv=None)->int:
    args=build_parser().parse_args(argv)
    try:
        c=_candidate(args.candidate);m=_read(args.manifest,"manifest");s=_sources(args.sources_dir)
        if args.command=="compile-current": result=compile_current(c,m,s,args.pinned_root)
        elif args.command=="compile-integrity": result=compile_integrity(c,m,s,args.pinned_root)
        else:
            receipt=loads_strict_json_bytes(_read(args.receipt,"receipt"),label="receipt")
            result=verify_receipt(c,m,s,args.pinned_root,receipt)
        _emit(result);return 0
    except AuthorityError as exc:
        _emit({"ok":False,"error":str(exc),"current_authority":False,"external_side_effects_authorized":False});return 2

if __name__=="__main__": raise SystemExit(main())
