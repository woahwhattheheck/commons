#!/usr/bin/env python3
"""Archive-layout correction for the exact-current final-pressure panel.

The first published runner used a development-tree ``checks/reference`` prefix.
The immutable release archive stores those bound files at root ``reference``.
This narrow entrypoint replaces only the loader resolver and delegates every
other custody, gameplay, receipt, and analysis path to the original runner.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import evidence
import game_runner
import run_final_pressure_panel as panel


def load_release_evaluator(runtime: Path):
    """Load the evaluator and engine from the immutable archive root."""
    runtime = Path(runtime).resolve()
    evaluator_path = runtime / "reference/evaluator/evaluate.py"
    loader = runtime / "reference/evaluator/loader.py"
    engine_dir = runtime / "reference/engine"
    required = [
        evaluator_path,
        loader,
        *(engine_dir / name for name in (
            "kaggriculture.py",
            "kaggriculture.json",
            "utils.py",
        )),
    ]
    for path in required:
        if not path.is_file():
            raise evidence.EvidenceError(
                f"Missing evaluator input: {path.relative_to(runtime)}"
            )

    evaluator = game_runner.import_file(
        evaluator_path,
        "titan_final_pressure_evaluator_release_layout",
    )
    if evaluator.ENGINE_REF != game_runner.ENGINE_REF:
        raise evidence.EvidenceError(
            f"Engine ref drift: {evaluator.ENGINE_REF}"
        )
    engine, engine_hashes = evaluator.get_engine(engine_dir, loader)
    return evaluator, engine, engine_dir, loader, {
        "ref": game_runner.ENGINE_REF,
        "sha256": engine_hashes,
        "evaluator_sha256": evidence.snapshot(evaluator_path).sha256,
        "loader_sha256": evidence.snapshot(loader).sha256,
        "archive_layout": "reference/**",
    }


def main() -> int:
    panel._load_evaluator = load_release_evaluator
    return panel.main()


if __name__ == "__main__":
    raise SystemExit(main())
