from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

try:  # package import
    from .profile_receipt import *
except ImportError:  # direct script / cwd import
    from profile_receipt import *


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Strict OWL-Time/PROV-O/Biolink interoperability profile")
    sub = parser.add_subparsers(dest="command", required=True)

    export = sub.add_parser("export", help="export temporal JSONL to canonical N-Triples")
    export.add_argument("jsonl")
    export.add_argument("ntriples")
    export.add_argument("--receipt")

    import_cmd = sub.add_parser("import", help="import the exact profile back to canonical temporal JSONL")
    import_cmd.add_argument("ntriples")
    import_cmd.add_argument("jsonl")

    verify = sub.add_parser("verify", help="verify JSONL, N-Triples, and conformance receipt")
    verify.add_argument("jsonl")
    verify.add_argument("ntriples")
    verify.add_argument("receipt")

    args = parser.parse_args(argv)
    try:
        if args.command == "export":
            jsonl_text = _read_text(args.jsonl)
            nt_text = export_ntriples(jsonl_text)
            _write_text(args.ntriples, nt_text)
            if args.receipt:
                receipt = build_receipt(jsonl_text, nt_text)
                _write_text(args.receipt, json.dumps(receipt, sort_keys=True, indent=2) + "\n")
            return 0
        if args.command == "import":
            graph = import_ntriples(_read_text(args.ntriples))
            _write_text(args.jsonl, graph.to_jsonl())
            return 0
        raw_receipt = strict_json_loads(_read_text(args.receipt))
        valid = isinstance(raw_receipt, Mapping) and verify_receipt(
            raw_receipt, _read_text(args.jsonl), _read_text(args.ntriples)
        )
        print("VALID" if valid else "INVALID")
        return 0 if valid else 2
    except (OntologyProfileError, TemporalEvidenceError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
