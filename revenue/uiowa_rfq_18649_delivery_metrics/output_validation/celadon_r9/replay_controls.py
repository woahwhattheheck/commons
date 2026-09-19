#!/usr/bin/env python3
"""Run the two declared negative controls on disposable calculator copies."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

import staging_replay

CONTROLS = (
    ("without_source_recheck",
     "# Recheck after writing, before making the complete report visible.\n        check_destination()",
     "# Recheck after writing, before making the complete report visible.\n        pass",
     18),
    ("without_staging_cleanup", "            temporary.unlink(missing_ok=True)",
     "            pass", 63),
)


def run(calculator: Path, expected_blob: str) -> dict:
    original = calculator.read_bytes()
    if staging_replay.git_blob(original) != expected_blob:
        raise ValueError("calculator does not match the declared source blob")
    text = original.decode("utf-8")
    results = []
    with tempfile.TemporaryDirectory(prefix="uiowa64-r9-controls-") as folder:
        root = Path(folder)
        for name, old, new, expected_failures in CONTROLS:
            if text.count(old) != 1:
                raise ValueError(f"{name}: expected one exact mutation site")
            data = text.replace(old, new).encode("utf-8")
            path = root / (name + ".py")
            path.write_bytes(data)
            blob = staging_replay.git_blob(data)
            module = staging_replay.load_calculator(path, blob)
            result = staging_replay.replay(module)
            matched = (
                result["tests"] == 81 and result["failures"] == expected_failures
                and result["errors"] == 0 and result["skips"] == 0
                and not result["success"]
            )
            results.append({"name": name, "mutated_blob": blob,
                            "expected_failures": expected_failures,
                            "matched_expectation": matched, "execution": result})
    preserved = calculator.read_bytes() == original
    return {"schema": "uiowa64.staging-controls.v1", "synthetic": True,
            "source_blob": expected_blob, "source_preserved": preserved,
            "success": preserved and all(r["matched_expectation"] for r in results),
            "controls": results}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--calculator", type=Path, required=True)
    parser.add_argument("--expected-blob", required=True)
    parser.add_argument("--report", type=Path, help="optional NEW JSON report path")
    args = parser.parse_args(argv)
    try:
        result = run(args.calculator, args.expected_blob)
        payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.report:
            with args.report.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(payload)
        else:
            sys.stdout.write(payload)
        return 0 if result["success"] else 1
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
