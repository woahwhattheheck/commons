from __future__ import annotations
import argparse
import json
from pathlib import Path
from .core import process_offline, strict_json_loads, verify_receipt, decide


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="QuietOps deterministic demo / verifier")
    p.add_argument("input", type=Path)
    p.add_argument("--out", type=Path)
    p.add_argument("--verify", type=Path, help="verify a prior receipt against this input")
    args = p.parse_args(argv)
    item = strict_json_loads(args.input.read_text(encoding="utf-8"))
    if args.verify:
        receipt_doc = strict_json_loads(args.verify.read_text(encoding="utf-8"))
        receipt = receipt_doc
        if isinstance(receipt_doc, dict) and "receipt" in receipt_doc:
            receipt = receipt_doc["receipt"]
        ok = verify_receipt(item, receipt)
        print(json.dumps({"valid": ok}, sort_keys=True))
        return 0 if ok else 2
    output = process_offline(item)
    text = json.dumps(output, sort_keys=True, indent=2)
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
