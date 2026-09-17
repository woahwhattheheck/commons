from __future__ import annotations

import argparse
import json
import sys

from .acceptance import evaluate_scenario
from .core import CarrierError, load_json_file
from .engine import compile_packet, verify_packet
from .report import publish


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="inkomoko-ai-platform",
        description="Fail-closed Inkomoko AI platform pursuit readiness carrier.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    compile_p = sub.add_parser("compile")
    compile_p.add_argument("--reference", required=True)
    compile_p.add_argument("--candidate", required=True)
    compile_p.add_argument("--output-dir", required=True)

    verify_p = sub.add_parser("verify")
    verify_p.add_argument("--reference", required=True)
    verify_p.add_argument("--candidate", required=True)
    verify_p.add_argument("--packet", required=True)

    accept_p = sub.add_parser("accept")
    accept_p.add_argument("--scenario", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "accept":
            scenario = load_json_file(args.scenario)
            report = evaluate_scenario(scenario)
            sys.stdout.write(json.dumps(report, sort_keys=True, separators=(",", ":")) + "\n")
            return 0 if report["status"] == "PASS" else 3

        reference = load_json_file(args.reference)
        candidate = load_json_file(args.candidate)
        if args.command == "compile":
            packet = compile_packet(reference, candidate)
            json_path, md_path = publish(packet, args.output_dir)
            sys.stdout.write(
                json.dumps(
                    {
                        "status": packet["status"],
                        "packet": str(json_path),
                        "markdown": str(md_path),
                        "receipt_sha256": packet["receipt"]["receipt_sha256"],
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            return 0

        packet = load_json_file(args.packet)
        verify_packet(packet, reference, candidate)
        sys.stdout.write(
            json.dumps(
                {
                    "verified": True,
                    "receipt_sha256": packet["receipt"]["receipt_sha256"],
                },
                sort_keys=True,
            )
            + "\n"
        )
        return 0
    except CarrierError as exc:
        sys.stderr.write(f"ERROR: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
