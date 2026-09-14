from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from engine import PacketError, compile_concept_markdown, evaluate


def _exclusive_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def main() -> int:
    parser = argparse.ArgumentParser(description="DCSA Innovation Call #01 readiness compiler")
    parser.add_argument("packet", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        packet = json.loads(args.packet.read_text(encoding="utf-8"))
        receipt = evaluate(packet)
        md = compile_concept_markdown(packet, receipt)
        _exclusive_write(args.out / "readiness_receipt.json", json.dumps(receipt, sort_keys=True, indent=2).encode() + b"\n")
        _exclusive_write(args.out / "concept_scaffold.md", md.encode("utf-8"))
    except (PacketError, OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    print(receipt["state"])
    return 0 if receipt["state"] in {"DIRECT_READY", "TEAMING_REQUIRED"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
