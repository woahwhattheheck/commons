from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .engine import ContractError, canonical_bytes, compile_result, loads_strict, render_markdown, verify_result
    from .io_secure import _read_regular, _write_exclusive
except ImportError:
    from engine import ContractError, canonical_bytes, compile_result, loads_strict, render_markdown, verify_result
    from io_secure import _read_regular, _write_exclusive

def command_compile(args: argparse.Namespace) -> int:
    scenario = loads_strict(_read_regular(Path(args.scenario)))
    result = compile_result(scenario)
    json_raw = canonical_bytes(result) + b"\n"
    md_raw = render_markdown(result).encode("utf-8")
    # Stage complete bytes before either publication. JSON is authoritative; Markdown is a projection.
    _write_exclusive(Path(args.json_out), json_raw)
    try:
        _write_exclusive(Path(args.markdown_out), md_raw)
    except Exception as exc:
        raise ContractError(f"authoritative JSON committed; Markdown projection failed: {exc}") from exc
    print(result["status"])
    print(result["receipt"]["result_sha256"])
    return 0


def command_verify(args: argparse.Namespace) -> int:
    scenario = loads_strict(_read_regular(Path(args.scenario)))
    result = loads_strict(_read_regular(Path(args.result)))
    valid = verify_result(scenario, result)
    print(json.dumps({"valid": valid}, sort_keys=True, separators=(",", ":")))
    return 0 if valid else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DARPA DV026 deterministic market technical proof")
    sub = parser.add_subparsers(dest="command", required=True)
    compile_p = sub.add_parser("compile")
    compile_p.add_argument("--scenario", required=True)
    compile_p.add_argument("--json-out", required=True)
    compile_p.add_argument("--markdown-out", required=True)
    compile_p.set_defaults(func=command_compile)
    verify_p = sub.add_parser("verify")
    verify_p.add_argument("--scenario", required=True)
    verify_p.add_argument("--result", required=True)
    verify_p.set_defaults(func=command_verify)
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ContractError, OSError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
