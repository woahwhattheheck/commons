from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .gate import GateError, compile_packet, load_strict_json, render_markdown, verify_packet


def _write_new(path: Path, data: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
    finally:
        os.close(fd)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile/verify multi-framework evidence freshness packets")
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile")
    c.add_argument("input")
    c.add_argument("packet")
    c.add_argument("markdown")
    v = sub.add_parser("verify")
    v.add_argument("packet")
    ns = parser.parse_args(argv)
    try:
        if ns.cmd == "compile":
            raw = load_strict_json(ns.input)
            packet = compile_packet(raw)
            packet_bytes = json.dumps(packet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
            md_bytes = render_markdown(packet).encode("utf-8")
            packet_path = Path(ns.packet)
            md_path = Path(ns.markdown)
            if packet_path.exists() or md_path.exists() or packet_path.is_symlink() or md_path.is_symlink():
                raise GateError("output_exists")
            _write_new(packet_path, packet_bytes)
            try:
                _write_new(md_path, md_bytes)
            except Exception:
                # Do not delete the first visible publication by pathname: preserve partial publication for reconciliation.
                raise
            print(packet["receipt_sha256"])
            return 0
        packet = load_strict_json(ns.packet)
        verify_packet(packet)
        print(packet["receipt_sha256"])
        return 0
    except (GateError, OSError) as exc:
        print(f"ERROR:{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
