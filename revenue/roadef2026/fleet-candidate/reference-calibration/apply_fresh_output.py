#!/usr/bin/env python3
"""Apply the exact reusable-calibration fresh-output contract."""
from __future__ import annotations

from pathlib import Path

HERE = Path(__file__).resolve().parent
PATH = HERE / "run_calibration.py"

OLD = '''    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
'''
NEW = '''    output = args.output.resolve()
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise FileExistsError(
            f"Choose a fresh --output directory; existing evidence is never reused: {output}"
        ) from error
'''


def main() -> int:
    text = PATH.read_text(encoding="utf-8")
    if NEW in text and OLD not in text:
        print("fresh-output contract already present")
        return 0
    if text.count(OLD) != 1:
        raise SystemExit(f"expected one output-creation block, found {text.count(OLD)}")
    PATH.write_text(text.replace(OLD, NEW, 1), encoding="utf-8", newline="\n")
    print("applied fresh-output contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
