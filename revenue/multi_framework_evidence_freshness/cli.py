from __future__ import annotations
import argparse, json, os, stat
from pathlib import Path
from .gate import GateError, compile_packet, load_strict_json, render_markdown, verify_packet

def _write_new(path: Path, data: bytes) -> None:
    parent = path.parent if str(path.parent) else Path(".")
    dflags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"): dflags |= os.O_DIRECTORY
    if hasattr(os, "O_CLOEXEC"): dflags |= os.O_CLOEXEC
    if hasattr(os, "O_NOFOLLOW"): dflags |= os.O_NOFOLLOW
    dfd = os.open(parent, dflags)
    try:
        before = os.fstat(dfd)
        if not stat.S_ISDIR(before.st_mode): raise GateError("output_parent_not_directory")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_CLOEXEC"): flags |= os.O_CLOEXEC
        if hasattr(os, "O_NOFOLLOW"): flags |= os.O_NOFOLLOW
        fd = os.open(path.name, flags, 0o600, dir_fd=dfd)
        try:
            view = memoryview(data)
            sent = 0
            while sent < len(view):
                n = os.write(fd, view[sent:])
                if n <= 0: raise OSError("short_write")
                sent += n
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(dfd)
        try:
            current = os.stat(parent, follow_symlinks=False)
        except FileNotFoundError as exc:
            raise GateError("output_parent_changed") from exc
        if (before.st_dev, before.st_ino) != (current.st_dev, current.st_ino):
            raise GateError("output_parent_changed")
    finally:
        os.close(dfd)

def _target_exists(path: Path) -> bool:
    try:
        os.lstat(path)
        return True
    except FileNotFoundError:
        return False

def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(description="Compile/verify multi-framework evidence freshness packets")
    sub=parser.add_subparsers(dest="cmd",required=True)
    c=sub.add_parser("compile"); c.add_argument("input"); c.add_argument("packet"); c.add_argument("markdown")
    v=sub.add_parser("verify"); v.add_argument("packet")
    ns=parser.parse_args(argv)
    try:
        if ns.cmd=="compile":
            raw=load_strict_json(ns.input); packet=compile_packet(raw)
            packet_bytes=json.dumps(packet,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")+b"\n"; md_bytes=render_markdown(packet).encode("utf-8")
            packet_path=Path(ns.packet); md_path=Path(ns.markdown)
            if _target_exists(packet_path) or _target_exists(md_path):
                raise GateError("output_exists")
            _write_new(packet_path,packet_bytes); _write_new(md_path,md_bytes)
            print(packet["receipt_sha256"]); return 0
        packet=load_strict_json(ns.packet); verify_packet(packet); print(packet["receipt_sha256"]); return 0
    except (GateError,OSError) as exc:
        print(f"ERROR:{exc}"); return 2
if __name__=="__main__": raise SystemExit(main())
