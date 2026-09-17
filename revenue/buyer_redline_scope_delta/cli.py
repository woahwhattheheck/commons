from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import tempfile

from .engine import RedlineError, compile_redline, render_owner_markdown, strict_json_loads, verify_packet


def _write_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError as exc:
            raise RedlineError(f"refusing to overwrite output: {path}") from exc
    finally:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile or verify buyer-redline scope-delta packets")
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile")
    c.add_argument("baseline", type=Path)
    c.add_argument("counter", type=Path)
    c.add_argument("output_json", type=Path)
    c.add_argument("--markdown", type=Path)
    v = sub.add_parser("verify")
    v.add_argument("packet", type=Path)
    ns = parser.parse_args(argv)
    try:
        if ns.cmd == "compile":
            packet = compile_redline(ns.baseline.read_bytes(), ns.counter.read_bytes())
            encoded = (json.dumps(packet, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
            _write_exclusive(ns.output_json, encoded)
            if ns.markdown:
                _write_exclusive(ns.markdown, render_owner_markdown(packet).encode("utf-8"))
            print(json.dumps({"status": packet["status"], "receipt_sha256": packet["receipt_sha256"]}, sort_keys=True))
            return 0
        packet = strict_json_loads(ns.packet.read_bytes())
        ok = isinstance(packet, dict) and verify_packet(packet)
        print(json.dumps({"verified": bool(ok)}, sort_keys=True))
        return 0 if ok else 2
    except (OSError, RedlineError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
