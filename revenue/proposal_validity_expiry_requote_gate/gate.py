from __future__ import annotations

import argparse
import datetime as _dt
from pathlib import Path
from typing import Any

from boundary import GateError, MAX_SAFE_INT, canonical as _canonical, strict_json_loads
from engine import (
    EVENT_KINDS,
    SOURCE_STATUS_CURRENT,
    STATUSES,
    _TRUSTED_UTC_NOW,
    _evaluate_at,
    _utc_now,
    _verify_packet_at,
    evaluate_offer,
    verify_packet,
)


def _load(path: str) -> Any:
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise GateError(f"cannot read {path}: {exc}") from None
    return strict_json_loads(raw)


def _write_new(path: str, value: Any) -> None:
    try:
        with Path(path).open("xb") as fh:
            fh.write(_canonical(value))
    except FileExistsError:
        raise GateError(f"refusing to overwrite existing output: {path}") from None
    except OSError as exc:
        raise GateError(f"cannot write {path}: {exc}") from None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Proposal validity / requote owner-review gate")
    sub = parser.add_subparsers(dest="command", required=True)
    compile_p = sub.add_parser("compile")
    compile_p.add_argument("--issued", required=True); compile_p.add_argument("--current", required=True); compile_p.add_argument("--out", required=True)
    verify_p = sub.add_parser("verify")
    verify_p.add_argument("--issued", required=True); verify_p.add_argument("--current", required=True); verify_p.add_argument("--packet", required=True)
    ns = parser.parse_args(argv)
    try:
        issued, current = _load(ns.issued), _load(ns.current)
        if ns.command == "compile":
            _write_new(ns.out, evaluate_offer(issued, current)); return 0
        if not verify_packet(issued, current, _load(ns.packet)):
            raise GateError("verification failed")
        print("VERIFIED"); return 0
    except (GateError, OSError, UnicodeError, ValueError, RecursionError, OverflowError) as exc:
        message = str(exc) if isinstance(exc, GateError) else "runtime boundary failure"
        try: print(f"ERROR: {message}")
        except UnicodeError: print("ERROR: runtime boundary failure")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
