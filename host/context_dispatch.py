#!/usr/bin/env python3
"""CLI for Commons context packet compilation, verification and rendering."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

try:
    from host.context_packet import PacketError, compile_packet, markdown, verify_packet
except ModuleNotFoundError:
    from context_packet import PacketError, compile_packet, markdown, verify_packet

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> tuple[Any, bytes]:
    raw = path.read_bytes()
    return json.loads(raw.decode()), raw


def _source(label: str, path: Path, raw: bytes) -> dict[str, Any]:
    return {"source": label, "path": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)}


def _claims(path: Path | None) -> tuple[list[dict[str, Any]], list[tuple[str, bytes]]]:
    if path is None:
        return [], []
    if path.is_dir():
        rows, raws = [], []
        for item in sorted(path.glob("*.json")):
            value, raw = _load(item); raws.append((str(item), raw))
            if isinstance(value, Mapping):
                rows.append(dict(value))
        return rows, raws
    value, raw = _load(path)
    if isinstance(value, list):
        rows = [dict(x) for x in value if isinstance(x, Mapping)]
    elif isinstance(value, Mapping) and isinstance(value.get("holdings"), list):
        rows = [dict(x) for x in value["holdings"] if isinstance(x, Mapping)]
    elif isinstance(value, Mapping):
        rows = [dict(value)]
    else:
        raise PacketError("claims input must be object, list, or directory")
    return rows, [(str(path), raw)]


def _compile(args: argparse.Namespace) -> dict[str, Any]:
    pulse, pulse_raw = _load(args.pulse)
    recent, recent_raw = _load(args.recent)
    ledger, ledger_raw = _load(args.ledger)
    if not isinstance(pulse, Mapping) or not isinstance(recent, list) or not isinstance(ledger, Mapping):
        raise PacketError("pulse/ledger must be objects and recent must be an array")
    coordination, coordination_raw = None, None
    if args.coordination:
        coordination, coordination_raw = _load(args.coordination)
        if not isinstance(coordination, Mapping):
            raise PacketError("coordination must be an object")
    claims, claim_raws = _claims(args.claims)
    provenance = [
        _source("pulse", args.pulse, pulse_raw),
        _source("recent", args.recent, recent_raw),
        _source("resource-ledger", args.ledger, ledger_raw),
    ]
    if args.coordination:
        provenance.append(_source("coordination", args.coordination, coordination_raw))
    if len(claim_raws) == 1:
        path, raw = claim_raws[0]
        provenance.append({"source":"claims","path":path,"sha256":hashlib.sha256(raw).hexdigest(),"bytes":len(raw)})
    elif claim_raws:
        manifest = "\n".join(f"{path}\t{hashlib.sha256(raw).hexdigest()}\t{len(raw)}" for path,raw in claim_raws).encode()
        provenance.append({"source":"claims","path":str(args.claims),"sha256":hashlib.sha256(manifest).hexdigest(),"files":len(claim_raws),"bytes":sum(len(raw) for _,raw in claim_raws)})
    return compile_packet(
        operation=args.operation, objective=args.objective, pulse=pulse,
        recent=[x for x in recent if isinstance(x, Mapping)], ledger=ledger,
        claims=claims, coordination=coordination, explicit_terms=args.term,
        paths=args.path, requested_main_head=args.main_head, provenance=provenance,
        max_chars=args.max_chars, max_events=args.max_events,
        max_resources=args.max_resources, max_claims=args.max_claims,
        max_coordination=args.max_coordination,
    )


def _write(text: str, out: Path | None) -> None:
    if out is None:
        sys.stdout.write(text); return
    if out.exists():
        raise PacketError(f"refusing to overwrite {out}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    packet = sub.add_parser("packet")
    packet.add_argument("--operation", required=True); packet.add_argument("--objective", required=True)
    packet.add_argument("--term", action="append", default=[]); packet.add_argument("--path", action="append", default=[])
    packet.add_argument("--pulse", type=Path, default=ROOT/"pulse.json")
    packet.add_argument("--recent", type=Path, default=ROOT/"recent.json")
    packet.add_argument("--ledger", type=Path, default=ROOT/"ground"/"RESOURCE_LEDGER.json")
    packet.add_argument("--coordination", type=Path); packet.add_argument("--claims", type=Path); packet.add_argument("--main-head")
    packet.add_argument("--max-chars", type=int, default=12000); packet.add_argument("--max-events", type=int, default=12)
    packet.add_argument("--max-resources", type=int, default=12); packet.add_argument("--max-claims", type=int, default=6)
    packet.add_argument("--max-coordination", type=int, default=8)
    packet.add_argument("--format", choices=("json","markdown"), default="json"); packet.add_argument("--out", type=Path)
    verify = sub.add_parser("verify"); verify.add_argument("packet", type=Path)
    render = sub.add_parser("render"); render.add_argument("packet", type=Path); render.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "packet":
            result = _compile(args)
            _write(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n" if args.format == "json" else markdown(result), args.out)
            return 0
        value, _ = _load(args.packet)
        if not isinstance(value, Mapping):
            raise PacketError("packet must be an object")
        ok, reason = verify_packet(value)
        if not ok:
            sys.stderr.write(f"INVALID {reason}\n"); return 2
        if args.command == "render":
            _write(markdown(value), args.out); return 0
        sys.stdout.write(f"VALID {value['schema']} {value['semantic_sha256']}\n"); return 0
    except (OSError, json.JSONDecodeError, PacketError) as exc:
        sys.stderr.write(f"ERROR {exc}\n"); return 2


if __name__ == "__main__":
    raise SystemExit(main())
