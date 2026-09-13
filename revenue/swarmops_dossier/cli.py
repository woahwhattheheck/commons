from __future__ import annotations

import argparse
import json
import os
import stat
from pathlib import Path

from .engine import DossierError, canonical_bytes, compile_dossier, render_markdown, strict_json_loads, verify_dossier

MAX_INPUT = 1_048_576


def read_regular(path: str) -> str:
    p = Path(path)
    st = os.lstat(p)
    if not stat.S_ISREG(st.st_mode):
        raise DossierError(f"not a regular input file: {path}")
    if st.st_size > MAX_INPUT:
        raise DossierError(f"input too large: {path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(p, flags)
    try:
        data = os.read(fd, MAX_INPUT + 1)
        if len(data) > MAX_INPUT:
            raise DossierError(f"input too large: {path}")
        if os.read(fd, 1):
            raise DossierError(f"input too large: {path}")
    finally:
        os.close(fd)
    return data.decode("utf-8")


def write_new(path: str, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    try:
        view = memoryview(data)
        while view:
            n = os.write(fd, view)
            view = view[n:]
    finally:
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Compile and verify prospect-safe Commons SwarmOps evidence dossiers")
    sub = ap.add_subparsers(dest="cmd", required=True)
    cp = sub.add_parser("compile")
    cp.add_argument("packet")
    cp.add_argument("policy")
    cp.add_argument("--as-of", required=True)
    cp.add_argument("--json-out", required=True)
    cp.add_argument("--markdown-out", required=True)
    vp = sub.add_parser("verify")
    vp.add_argument("packet")
    vp.add_argument("policy")
    vp.add_argument("candidate")
    vp.add_argument("--as-of", required=True)
    ns = ap.parse_args(argv)
    try:
        packet = strict_json_loads(read_regular(ns.packet))
        policy = strict_json_loads(read_regular(ns.policy))
        if ns.cmd == "compile":
            dossier = compile_dossier(packet, policy, ns.as_of)
            write_new(ns.json_out, canonical_bytes(dossier) + b"\n")
            write_new(ns.markdown_out, render_markdown(dossier).encode("utf-8"))
            return 0 if dossier["status"] == "READY_FOR_OWNER_REVIEW" else 2
        candidate = strict_json_loads(read_regular(ns.candidate))
        return 0 if verify_dossier(packet, policy, ns.as_of, candidate) else 3
    except (DossierError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
