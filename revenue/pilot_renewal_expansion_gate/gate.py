#!/usr/bin/env python3
"""Evidence-bound pilot delivery -> renewal/expansion review gate CLI."""
from __future__ import annotations

import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .common import AUTHORITY, GateError, TRUTH_CEILING, canonical_json, sha256, strict_loads, _read_regular
from .schema import normalize
from .engine import compile_current, evaluate, verify_current

def render_markdown(packet: dict[str, Any]) -> str:
    lines = [
        "# Renewal / Expansion Owner Review Packet",
        "",
        f"- Engagement: `{packet['engagement_id']}`",
        f"- Organization: `{packet['organization_id']}`",
        f"- Decision: **{packet['decision']}**",
        f"- Verified at: `{packet['verified_at']}`",
        f"- Truth ceiling: `{packet['truth_ceiling']}`",
        "",
        "## Expansion hypotheses",
    ]
    if packet["expansion_hypotheses"]:
        for item in packet["expansion_hypotheses"]:
            lines.append(f"- `{item['id']}` — {item['statement']} — **{item['state']}**")
    else:
        lines.append("- None recorded.")
    lines += ["", "## Holds / reasons"]
    if packet["reasons"]:
        for reason in packet["reasons"]:
            lines.append(f"- `{reason['code']}` / `{reason['ref']}` — {reason['detail']}")
    else:
        lines.append("- None.")
    lines += [
        "",
        "## Authority ceiling",
        "This packet is owner-review evidence only. It does not authorize external send, signature/contract, buyer acceptance, renewal/expansion approval, invoicing/payment, cash/revenue recognition, deployment, scheduling, or CRM mutation.",
        "",
    ]
    return "\n".join(lines)


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile")
    c.add_argument("input")
    c.add_argument("output_dir")
    v = sub.add_parser("verify")
    v.add_argument("input")
    v.add_argument("packet")
    v.add_argument("receipt")
    args = parser.parse_args(argv)
    try:
        raw = strict_loads(_read_regular(Path(args.input)))
        if args.cmd == "compile":
            _, packet, receipt = compile_current(raw)
            out = Path(args.output_dir)
            if out.exists():
                raise GateError("output_dir must not already exist")
            out.mkdir(parents=True, exist_ok=False)
            _atomic_write(out / "packet.json", canonical_json(packet))
            _atomic_write(out / "packet.md", render_markdown(packet).encode("utf-8"))
            _atomic_write(out / "receipt.json", canonical_json(receipt))
            print(packet["decision"])
            return 0
        packet = strict_loads(_read_regular(Path(args.packet)))
        receipt = strict_loads(_read_regular(Path(args.receipt)))
        result = verify_current(raw, packet, receipt)
        print(canonical_json(result).decode("utf-8"), end="")
        return 0 if result["integrity_valid"] else 2
    except (GateError, OSError) as exc:
        print(f"ERROR: {exc}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
