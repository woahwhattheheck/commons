# SPDX-License-Identifier: Apache-2.0
"""Materialize the measured finite-horizon v3 policy as a runnable package."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from snapshot_build import materialize
from snapshot_evidence import (
    EXPECTED_BENCHMARK_SHA256,
    EXPECTED_ENGINE_REFERENCE,
    EXPECTED_ENGINE_SHA256,
    EXPECTED_EVALUATOR_SHA256,
    validate_evidence,
)
from snapshot_model import (
    FREEZE_PATHS,
    MAIN_BYTES,
    MAX_MEMBER_COUNT,
    OUTPUT_ENTRYPOINT,
    PRODUCTION_PIN,
    SCHEMA,
    SOURCE_ENTRYPOINT,
    SOURCE_MEMBERS,
    EvidenceLedgerPin,
    Pin,
    SnapshotError,
    read_archive,
    sha256,
)

# Stable private aliases retained for focused fixture tests and callers.
_read_archive = read_archive
_sha256 = sha256


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--lab-root", type=Path, default=Path(__file__).resolve().parents[2])
    result.add_argument("--output", type=Path, help="write the runnable deterministic tar.gz")
    result.add_argument("--receipt", type=Path, help="write JSON receipt; requires --output")
    result.add_argument("--overwrite", action="store_true")
    result.add_argument("--no-smoke-import", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        receipt = materialize(
            args.lab_root,
            output=args.output,
            receipt_path=args.receipt,
            overwrite=args.overwrite,
            run_smoke=not args.no_smoke_import,
        )
    except SnapshotError as exc:
        print(json.dumps({"schema": SCHEMA, "status": "INVALID", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2
    except OSError as exc:
        print(json.dumps({"schema": SCHEMA, "status": "ERROR", "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 3
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
