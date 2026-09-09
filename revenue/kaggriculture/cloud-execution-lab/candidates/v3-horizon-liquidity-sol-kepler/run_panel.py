# SPDX-License-Identifier: Apache-2.0
"""Run the horizon-liquidity ablation through the existing official paired panel."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "v3-l02-ledger-tranche"
RUNNER = SOURCE / "run_panel.py"


def _load_runner():
    spec = importlib.util.spec_from_file_location("_sol_kepler_paired_panel", RUNNER)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {RUNNER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv=None) -> int:
    runner = _load_runner()
    original_dependency_receipt = runner.dependency_receipt
    original_markdown = runner.markdown

    def agent_spec(variant: str) -> str:
        path = runner.LAB / "main.py" if variant == "baseline" else HERE / "candidate.py"
        return str(path.resolve()) + "::agent"

    def dependency_receipt(head: str, *, evaluator=None):
        saved_here = runner.HERE
        runner.HERE = SOURCE
        try:
            receipt = original_dependency_receipt(head, evaluator=evaluator)
        finally:
            runner.HERE = saved_here
        receipt["sha256"]["candidate"] = runner.sha256_file(HERE / "candidate.py")
        receipt["sha256"].pop("overlay", None)
        receipt["sha256"]["liquidity_haircut"] = runner.sha256_file(
            HERE / "liquidity_haircut.py"
        )
        receipt["sha256"]["source_audit"] = runner.sha256_file(HERE / "audit_change.py")
        receipt["candidate_bundle"] = runner.tree_sha256(HERE)
        receipt["ablation"] = {
            "operation": "titan-v3-horizon-liquidity-20260909-sol-kepler-01",
            "factor": 0.95,
            "only_runtime_change": "MarketPath artificial-horizon carry factor 1.0 -> 0.95",
            "canonical_files_modified": False,
        }
        return receipt

    def markdown(report):
        text = original_markdown(report)
        return text.replace(
            "# TITAN L02 ledger-coherent tranche — development panel",
            "# TITAN V3 horizon-liquidity ablation — development panel",
            1,
        )

    runner._agent_spec = agent_spec
    runner.dependency_receipt = dependency_receipt
    runner.markdown = markdown
    return int(runner.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
