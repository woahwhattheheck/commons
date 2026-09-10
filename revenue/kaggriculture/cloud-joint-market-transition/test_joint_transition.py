# SPDX-License-Identifier: Apache-2.0
"""Run and seal all exact joint market/town transition contracts."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import unittest

import joint_transition as oracle
import test_support

SOURCE_FILES = (
    "engine_binding.py",
    "joint_transition.py",
    "protection.py",
    "state_contracts.py",
    "transition_core.py",
)
TEST_FILES = (
    "test_cases_cli.py",
    "test_cases_engine.py",
    "test_cases_fail_closed.py",
    "test_cases_market_blockers.py",
    "test_cases_market_core.py",
    "test_cases_market_effects.py",
    "test_joint_transition.py",
    "test_support.py",
)


def _hashes(root: Path, names: tuple[str, ...]) -> dict[str, str]:
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in names}


def _tree_hash(mapping: dict[str, str]) -> str:
    body = json.dumps(mapping, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine-source", required=True, type=Path)
    parser.add_argument("--result", type=Path)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    test_support.ENGINE_SOURCE = args.engine_source
    test_support.ENGINE = oracle.load_transition_engine(args.engine_source)
    started = time.perf_counter()
    suite = unittest.defaultTestLoader.discover(str(root), pattern="test_cases_*.py")
    outcome = unittest.TextTestRunner(verbosity=2).run(suite)
    elapsed = time.perf_counter() - started

    if args.result is not None:
        source_files = _hashes(root, SOURCE_FILES)
        test_files = _hashes(root, TEST_FILES)
        receipt = {
            "schema": "titan-joint-market-transition-validation-v1",
            "tests": outcome.testsRun,
            "failures": len(outcome.failures),
            "errors": len(outcome.errors),
            "skipped": len(outcome.skipped),
            "complete_comparison_cases": test_support.CASE_COUNT,
            "full_official_module_differential_cases": 4,
            "game_panels": 0,
            "game_seeds": 0,
            "elapsed_seconds": elapsed,
            "engine_repository": oracle.ENGINE_REPOSITORY,
            "engine_commit": oracle.ENGINE_COMMIT,
            "engine_path": oracle.ENGINE_PATH,
            "engine_git_blob": test_support.ENGINE.git_blob_sha1,
            "engine_sha256": test_support.ENGINE.source_sha256,
            "source_files": source_files,
            "source_tree_sha256": _tree_hash(source_files),
            "test_files": test_files,
            "test_tree_sha256": _tree_hash(test_files),
            "python": os.sys.version.split()[0],
        }
        args.result.parent.mkdir(parents=True, exist_ok=True)
        args.result.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if outcome.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
