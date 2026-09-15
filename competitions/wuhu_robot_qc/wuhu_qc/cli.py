from __future__ import annotations

import argparse
import json
from pathlib import Path

from .lerobot_v21 import DatasetReference, fit_dataset_reference, scan_dataset


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="LeRobot v2.1 trajectory quality detector for the Wuhu embodied-data challenge")
    sub = parser.add_subparsers(dest="cmd", required=True)

    prof = sub.add_parser("profile", help="fit a provenance-bound profile from organizer clean-reference trajectories only")
    prof.add_argument("dataset", type=Path)
    prof.add_argument("--out", type=Path, default=Path("reference.json"))
    prof.add_argument("--episodes", type=int, nargs="*")

    scan = sub.add_parser("scan")
    scan.add_argument("dataset", type=Path)
    scan.add_argument("--out", type=Path, default=Path("wuhu-qc-report"))
    scan.add_argument("--episodes", type=int, nargs="*")
    scan.add_argument("--reference", type=Path)

    args = parser.parse_args(argv)
    if args.cmd == "profile":
        ref = fit_dataset_reference(args.dataset, episodes=args.episodes)
        args.out.write_text(json.dumps(ref.as_dict(), indent=2) + "\n", encoding="utf-8")
        print(f"reference_features={len(ref.profile.features)} episodes={len(ref.selected_episodes)} manifest={ref.source_manifest_sha256} output={args.out}")
        return 0

    ref = None
    if args.reference:
        ref = DatasetReference.from_dict(json.loads(args.reference.read_text(encoding="utf-8")))
    reports = scan_dataset(args.dataset, args.out, episodes=args.episodes, reference=ref)
    holds = sum(report.quality_score < 70 for report in reports)
    print(f"episodes={len(reports)} quality_lt_70={holds} report={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
