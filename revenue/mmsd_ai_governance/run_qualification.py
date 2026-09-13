#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

from qualification import QualificationError, compile_readiness, load_json, verify_package


def usage() -> int:
    print("usage: run_qualification.py <compile|verify> <json-path>", file=sys.stderr)
    return 2


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        return usage()
    command, path = argv[1:]
    try:
        value = load_json(Path(path))
        if command == "compile":
            out = compile_readiness(value)
        elif command == "verify":
            out = verify_package(value)
        else:
            return usage()
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0
    except (QualificationError, json.JSONDecodeError, OSError) as exc:
        print(f"mmsd-ai-governance: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
