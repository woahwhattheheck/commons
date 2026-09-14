from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import compile_manifest, verify_local_evidence
from .providers import FakeProvider, RunwayProvider
from .demo import build_demo_html
from .render import execute_generated_shots


def _load(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def _dump(value):
    print(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False))

def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="proofcut")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile")
    c.add_argument("packet")
    c.add_argument("--base-dir")
    r = sub.add_parser("render-plan")
    r.add_argument("packet")
    r.add_argument("--base-dir")
    r.add_argument("--provider", choices=("fake", "runway"), default="fake")
    r.add_argument("--execute", action="store_true")
    r.add_argument("--max-credits", type=int, default=0)
    d = sub.add_parser("demo")
    d.add_argument("packet")
    d.add_argument("--base-dir")
    d.add_argument("--output", required=True)
    args = p.parse_args(argv)
    packet = _load(args.packet)
    base_dir = Path(args.base_dir) if args.base_dir else Path(args.packet).resolve().parent
    verify_local_evidence(packet, base_dir)
    manifest = compile_manifest(packet)
    if args.cmd == "compile":
        _dump(manifest)
        return 0
    if args.cmd == "demo":
        Path(args.output).write_text(build_demo_html(packet, base_dir=base_dir), encoding="utf-8")
        return 0
    provider = FakeProvider() if args.provider == "fake" else RunwayProvider(execute=args.execute, max_credits=args.max_credits)
    _dump(execute_generated_shots(manifest, provider))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
