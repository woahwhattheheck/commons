from __future__ import annotations

import argparse
import json
from pathlib import Path

from .gate import (
    GateError,
    compile_packet,
    load_strict_json,
    render_markdown,
    verify_current_packet,
    verify_packet,
    write_new_bytes,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile/verify multi-framework evidence freshness packets")
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile")
    c.add_argument("input")
    c.add_argument("packet")
    c.add_argument("markdown")
    v = sub.add_parser("verify")
    v.add_argument("packet")
    vh = sub.add_parser("verify-historical")
    vh.add_argument("packet")
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
            write_new_bytes(packet_path, packet_bytes)
            try:
                write_new_bytes(md_path, md_bytes)
            except Exception:
                raise
            print(packet["receipt_sha256"])
            return 0
        packet = load_strict_json(ns.packet)
        if ns.cmd == "verify-historical":
            verify_packet(packet)
        else:
            verify_current_packet(packet)
        print(packet["receipt_sha256"])
        return 0
    except (GateError, OSError) as exc:
        print(f"ERROR:{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
