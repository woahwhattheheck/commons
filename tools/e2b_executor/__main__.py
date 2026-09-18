from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .executor import JobValidationError, execute_job


def _load_packet(path: str | None) -> dict:
    if path:
        return json.loads(Path(path).read_text("utf-8"))
    return json.load(sys.stdin)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run an exact-head source archive in one E2B sandbox and emit "
            "a canonical receipt."
        )
    )
    parser.add_argument(
        "job",
        nargs="?",
        help="JSON job packet path; omit to read stdin",
    )
    args = parser.parse_args(argv)
    try:
        receipt = execute_job(_load_packet(args.job))
    except (JobValidationError, OSError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {"error": type(exc).__name__, "message": str(exc)},
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(receipt, sort_keys=True, separators=(",", ":")))
    return 0 if receipt.get("green") else 1


if __name__ == "__main__":
    raise SystemExit(main())
