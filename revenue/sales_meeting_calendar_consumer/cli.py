"""CLI for the read-only sales-meeting calendar consumer."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from .calendar_consumer import (
    CalendarConsumerError,
    build_google_availability_plan,
    compile_calendar_consumer,
    google_tool_args,
    render_markdown,
    strict_json_loads,
)


def _read_json(path: str):
    return strict_json_loads(Path(path).read_bytes())


def _emit(value):
    sys.stdout.write(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Plan/compile Google Calendar free-busy evidence for sales meeting owner review."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="emit exact read-only Google Calendar get_availability args")
    plan.add_argument("--trigger", required=True)
    plan.add_argument("--human-authority-sha256", required=True)
    plan.add_argument("--full-plan", action="store_true", help="emit retained plan instead of tool args")

    compile_p = sub.add_parser("compile", help="compile a retained capture through landed meeting readiness")
    compile_p.add_argument("--trigger", required=True)
    compile_p.add_argument("--capture", required=True)
    compile_p.add_argument("--human-authority-sha256", required=True)
    compile_p.add_argument("--calendar-capture-sha256", required=True)
    compile_p.add_argument("--markdown", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            retained = build_google_availability_plan(
                _read_json(args.trigger),
                expected_human_authority_sha256=args.human_authority_sha256,
            )
            _emit(retained if args.full_plan else google_tool_args(retained))
            return 0

        receipt = compile_calendar_consumer(
            _read_json(args.trigger),
            _read_json(args.capture),
            expected_human_authority_sha256=args.human_authority_sha256,
            expected_calendar_capture_sha256=args.calendar_capture_sha256,
            as_of=datetime.now(timezone.utc),
        )
        if args.markdown:
            sys.stdout.write(render_markdown(receipt))
            if not render_markdown(receipt).endswith("\n"):
                sys.stdout.write("\n")
        else:
            _emit(receipt)
        return 0
    except (CalendarConsumerError, OSError, ValueError) as exc:
        sys.stderr.write(f"sales-meeting-calendar-consumer: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
