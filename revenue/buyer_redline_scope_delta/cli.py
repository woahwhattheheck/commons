from __future__ import annotations
import argparse, json, os, stat, tempfile
from pathlib import Path
from .engine import RedlineError, compile_redline, render_owner_markdown, strict_json_loads, verify_packet

MAX_INPUT_BYTES = 2 * 1024 * 1024

def _read(path: Path) -> bytes:
    try:
        st = path.lstat()
    except OSError as exc:
        raise RedlineError(f"cannot stat input: {path}") from exc
    if not stat.S_ISREG(st.st_mode):
        raise RedlineError(f"input must be a regular file: {path}")
    if st.st_size > MAX_INPUT_BYTES:
        raise RedlineError(f"input exceeds {MAX_INPUT_BYTES} bytes: {path}")
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise RedlineError(f"cannot read input: {path}") from exc
    if len(data) != st.st_size:
        raise RedlineError(f"input changed while reading: {path}")
    return data

def _write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data); fh.flush(); os.fsync(fh.fileno())
        try:
            os.link(tmp, path)
        except FileExistsError as exc:
            raise RedlineError(f"refusing to overwrite output: {path}") from exc
    finally:
        try: os.unlink(tmp)
        except FileNotFoundError: pass

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Compile or semantically verify buyer-redline scope-delta packets")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile")
    for name in ("baseline", "counter", "output_json"): c.add_argument(name, type=Path)
    c.add_argument("--markdown", type=Path)
    v = sub.add_parser("verify")
    for name in ("baseline", "counter", "packet"): v.add_argument(name, type=Path)
    ns = p.parse_args(argv)
    try:
        if ns.cmd == "compile":
            b, cbytes = _read(ns.baseline), _read(ns.counter)
            packet = compile_redline(b, cbytes)
            encoded = (json.dumps(packet, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()
            markdown = render_owner_markdown(packet, b, cbytes).encode() if ns.markdown else None
            _write(ns.output_json, encoded)
            if ns.markdown and markdown is not None: _write(ns.markdown, markdown)
            print(json.dumps({"status": packet["status"], "receipt_sha256": packet["receipt_sha256"]}, sort_keys=True))
            return 0
        b, cbytes = _read(ns.baseline), _read(ns.counter)
        packet = strict_json_loads(_read(ns.packet))
        ok = isinstance(packet, dict) and verify_packet(packet, b, cbytes)
        print(json.dumps({"verified": bool(ok)}, sort_keys=True))
        return 0 if ok else 2
    except (OSError, RedlineError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
