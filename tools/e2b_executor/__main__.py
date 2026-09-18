from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .executor import (
    MAX_JOB_PACKET_BYTES,
    JobValidationError,
    execute_job,
    parse_job_packet_text,
)


def _read_bounded(stream) -> str:
    raw = stream.read(MAX_JOB_PACKET_BYTES + 1)
    if isinstance(raw, str):
        try:
            encoded = raw.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise JobValidationError("job JSON must be valid UTF-8") from exc
        if len(encoded) > MAX_JOB_PACKET_BYTES:
            raise JobValidationError("job JSON exceeds byte limit")
        return raw
    if len(raw) > MAX_JOB_PACKET_BYTES:
        raise JobValidationError("job JSON exceeds byte limit")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise JobValidationError("job JSON must be valid UTF-8") from exc


def _load_packet(path: str | None) -> dict:
    if path:
        with Path(path).open("rb") as handle:
            return dict(parse_job_packet_text(_read_bounded(handle)))
    stream = getattr(sys.stdin, "buffer", sys.stdin)
    return dict(parse_job_packet_text(_read_bounded(stream)))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run a caller-supplied source archive in one E2B sandbox and emit "
            "a canonical byte-custody execution receipt. Git commit binding is separate."
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
    except (JobValidationError, OSError) as exc:
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
