from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import canonical_json, compile_json_text, load_strict_json, verify_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile or verify an internal partner workshare data-room packet.")
    parser.add_argument("input", help="strict JSON input")
    parser.add_argument("--markdown", help="write generated Markdown packet")
    parser.add_argument("--receipt", help="write generated machine receipt JSON")
    parser.add_argument("--verify-markdown", help="existing Markdown packet to verify")
    parser.add_argument("--verify-receipt", help="existing receipt JSON to verify")
    args = parser.parse_args()

    input_path = Path(args.input)
    raw = input_path.read_text(encoding="utf-8")
    packet = load_strict_json(raw)

    if args.verify_markdown or args.verify_receipt:
        if not (args.verify_markdown and args.verify_receipt):
            parser.error("--verify-markdown and --verify-receipt must be provided together")
        markdown = Path(args.verify_markdown).read_text(encoding="utf-8")
        receipt = load_strict_json(Path(args.verify_receipt).read_text(encoding="utf-8"))
        ok, reason = verify_bundle(packet, markdown, receipt)
        print(canonical_json({"verified": ok, "reason": reason}))
        return 0 if ok else 2

    markdown, receipt = compile_json_text(raw)
    if args.markdown:
        Path(args.markdown).write_text(markdown, encoding="utf-8")
    else:
        print(markdown)
    if args.receipt:
        Path(args.receipt).write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
