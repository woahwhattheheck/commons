"""One-command deterministic SAGE ablation sweep (mock evidence only)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from harness import DEFAULT_VARIANTS, ExperimentPlan, compile_report, verify_report
from sage_runner import LevelSwitchDoorEnv, run_plan


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=24)
    parser.add_argument("--levels", type=int, default=3)
    parser.add_argument("--max-actions", type=int, default=80)
    parser.add_argument("--source-revision", default="local")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 1 <= args.seeds <= 1000:
        parser.error("--seeds must be 1..1000")
    if not 1 <= args.levels <= len(LevelSwitchDoorEnv._LAYOUTS):
        parser.error(f"--levels must be 1..{len(LevelSwitchDoorEnv._LAYOUTS)}")
    plan = ExperimentPlan(
        experiment_id="arc3-sage-ablation-mock-v1",
        variants=DEFAULT_VARIANTS,
        seeds=tuple(range(args.seeds)),
        levels=tuple(range(args.levels)),
        max_actions=args.max_actions,
        evidence_kind="mock",
        source_revision=args.source_revision,
    )
    report = compile_report(plan, run_plan(plan))
    if not verify_report(report):
        raise RuntimeError("self-produced report failed receipt verification")
    text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
