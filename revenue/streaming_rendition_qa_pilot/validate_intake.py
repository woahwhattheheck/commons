from __future__ import annotations

import argparse
import json
import pathlib
import sys

from .pilot import canonical_report_bytes, compile_receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile a streaming rendition QA pilot receipt")
    parser.add_argument("intake", type=pathlib.Path, help="JSON intake file")
    parser.add_argument("--output", type=pathlib.Path, help="write canonical report JSON")
    parser.add_argument("--expect-ready", type=int)
    parser.add_argument("--expect-hold", type=int)
    args = parser.parse_args(argv)

    intake = json.loads(args.intake.read_text(encoding="utf-8"))
    receipt = compile_receipt(intake)
    report = receipt["report"]
    summary = report["summary"]
    if args.expect_ready is not None and summary["release_ready"] != args.expect_ready:
        print(f"expected ready={args.expect_ready}, got {summary['release_ready']}", file=sys.stderr)
        return 2
    if args.expect_hold is not None and summary["hold"] != args.expect_hold:
        print(f"expected hold={args.expect_hold}, got {summary['hold']}", file=sys.stderr)
        return 2
    if args.output:
        args.output.write_bytes(canonical_report_bytes(report))
    print(
        f"pilot_id={report['pilot_id']} decision={report['decision']} total={summary['total']} "
        f"ready={summary['release_ready']} hold={summary['hold']} sha256={receipt['report_sha256']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
