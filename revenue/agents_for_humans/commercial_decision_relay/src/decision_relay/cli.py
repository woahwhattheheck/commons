from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .core import reconcile, verify_receipt


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dump(value: object, path: str | None = None) -> None:
    text = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if path:
        Path(path).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="decision-relay")
    sub = parser.add_subparsers(dest="command", required=True)

    p_reconcile = sub.add_parser("reconcile", help="build deterministic decision receipt")
    p_reconcile.add_argument("--batch", required=True)
    p_reconcile.add_argument("--evaluated-at")
    p_reconcile.add_argument("--output")

    p_verify = sub.add_parser("verify", help="verify receipt against source and out-of-band digest")
    p_verify.add_argument("--receipt", required=True)
    p_verify.add_argument("--batch", required=True)
    p_verify.add_argument("--expected-receipt-sha256", required=True)
    p_verify.add_argument("--evaluated-at")

    p_agent = sub.add_parser("agent", help="run the Strands orchestration agent")
    p_agent.add_argument("prompt", nargs="?", default="Process the evidence and show me only decisions that need a human.")
    p_agent.add_argument("--provider", choices=["bedrock", "openai"], default="bedrock")
    p_agent.add_argument("--audit-path", default=".relay/audit.jsonl")

    args = parser.parse_args(argv)
    if args.command == "reconcile":
        receipt = reconcile(_load(args.batch), evaluated_at=args.evaluated_at)
        _dump(receipt, args.output)
        return 0
    if args.command == "verify":
        valid = verify_receipt(
            _load(args.receipt),
            args.expected_receipt_sha256,
            _load(args.batch),
            evaluated_at=args.evaluated_at,
        )
        _dump({"valid": valid})
        return 0 if valid else 2

    from .strands_app import build_agent

    agent = build_agent(provider=args.provider, audit_path=args.audit_path)
    result = agent(args.prompt)
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
