#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from transport import dump_json, load_json, project_docx, project_pdf, read_csv, read_xlsx, write_csv, write_xlsx


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="UIOWA-096 typed interchange")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("json-to-csv")
    p.add_argument("src")
    p.add_argument("dst")

    p = sub.add_parser("csv-to-json")
    p.add_argument("src")
    p.add_argument("dst")

    p = sub.add_parser("json-to-xlsx")
    p.add_argument("src")
    p.add_argument("dst")

    p = sub.add_parser("xlsx-to-json")
    p.add_argument("src")
    p.add_argument("dst")

    p = sub.add_parser("project-docx")
    p.add_argument("src")

    p = sub.add_parser("project-pdf")
    p.add_argument("src")

    args = parser.parse_args(argv)
    if args.cmd == "json-to-csv":
        write_csv(load_json(args.src), args.dst)
    elif args.cmd == "csv-to-json":
        dump_json(read_csv(args.src), args.dst)
    elif args.cmd == "json-to-xlsx":
        write_xlsx(load_json(args.src), args.dst)
    elif args.cmd == "xlsx-to-json":
        dump_json(read_xlsx(args.src), args.dst)
    elif args.cmd == "project-docx":
        json.dump(project_docx(args.src), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    elif args.cmd == "project-pdf":
        json.dump(project_pdf(args.src), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
