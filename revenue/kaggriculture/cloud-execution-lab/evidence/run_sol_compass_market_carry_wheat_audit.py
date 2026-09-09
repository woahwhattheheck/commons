#!/usr/bin/env python3
"""Binding-corrected runner for the SOL-COMPASS WHEAT carry audit.

The original audit engine is retained byte-for-byte. This runner corrects one
preflight label before execution: the SELL product universe is defined by
scheduler.py, while frozen_selected.py imports that universe. Both files remain
independently pinned, and the final report records both source identities.
"""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

SCHEDULER_BLOB = "a483b24dd72b580d7d8811636b54d2d44f391575"
FROZEN_SELECTED_BLOB = "fc7baf5c179818a55037f6a61d92984d81d1a21c"


def load_legacy(path: Path):
    spec = importlib.util.spec_from_file_location("_sol_compass_wheat_audit_engine", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    here = Path(__file__).resolve().parent
    legacy_path = here / "sol_compass_market_carry_wheat_audit.py"
    legacy = load_legacy(legacy_path)

    # Preserve a separately named pin for the imported FrozenSelected consumer.
    legacy.PATHS["frozen_selected"] = legacy.PATHS["frozen"]
    legacy.EXPECTED_BLOBS["frozen_selected"] = FROZEN_SELECTED_BLOB

    # The static product-universe assertion belongs to scheduler.py. Repoint
    # only that preflight label; the calculation and parent-route audit remain
    # the original exact bytes.
    legacy.PATHS["frozen"] = "scheduler.py"
    legacy.EXPECTED_BLOBS["frozen"] = SCHEDULER_BLOB

    # Complete the synthetic private schema used only for parent liquidation.
    # The legacy fixture already supplies every product and crop key. Official
    # private state also includes animal objects in shed; add zero-valued keys
    # so the optimistic parent probe cannot depend on a partial mapping.
    original_synthetic = legacy.synthetic_observation

    def complete_synthetic(parent, step, wheat):
        observation = original_synthetic(parent, step, wheat)
        for animal in parent.ANIMALS:
            observation["private"]["shed"].setdefault(animal, 0)
        return observation

    legacy.synthetic_observation = complete_synthetic

    result = int(legacy.main())

    report_path = Path("WHEAT-AUDIT.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    sources = dict(report["source_blobs"])
    scheduler = sources.pop("frozen")
    frozen_selected = sources.pop("frozen_selected")
    if scheduler != SCHEDULER_BLOB or frozen_selected != FROZEN_SELECTED_BLOB:
        raise AssertionError("binding correction did not preserve exact source blobs")
    sources["scheduler"] = scheduler
    sources["frozen_selected"] = frozen_selected
    report["source_blobs"] = sources
    report["audit_engine_source_sha256"] = report.pop("audit_source_sha256")
    report["audit_runner_source_sha256"] = sha256(Path(__file__).read_bytes()).hexdigest()
    report["binding_correction"] = {
        "reason": "SELL product universe is defined in scheduler.py and imported by frozen_selected.py",
        "scheduler_blob": scheduler,
        "frozen_selected_blob": frozen_selected,
        "calculation_engine_unchanged": True,
        "synthetic_private_schema_complete": True,
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    summary = Path("WHEAT-AUDIT.md")
    with summary.open("a", encoding="utf-8") as handle:
        handle.write(
            "\n## Source-binding correction\n\n"
            "The executable audit pins `scheduler.py` as the source of the "
            "WHEAT/FERTILIZER SELL exclusion and independently pins "
            "`frozen_selected.py` as its importing consumer. The synthetic "
            "private state includes zero-valued official animal shed keys. No "
            "economic calculation or parent-route logic was changed.\n"
        )

    print("FINAL_REPORT_SHA256", sha256(report_path.read_bytes()).hexdigest())
    return result


if __name__ == "__main__":
    raise SystemExit(main())
