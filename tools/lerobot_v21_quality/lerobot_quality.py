#!/usr/bin/env python3
"""Read-only LeRobot v2.1 multimodal dataset quality inspector.

Native mode reads the v2.1 metadata, Parquet, and video inventory. A canonical
JSONL manifest mode gives deterministic synthetic fault injection and permits a
trusted decoder to feed the same analyzer path. Reports omit wall-clock time so
repeated scans of unchanged input are byte-identical.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Sequence

try:
    from .lq_analysis import analyze_episode
    from .lq_io import inspect_episode_inventory, inspect_layout, load_jsonl, load_manifest
    from .lq_model import (
        VERSION,
        DatasetReport,
        Diagnostic,
        EpisodeResult,
        FrameRecord,
        ModalitySample,
        Thresholds,
    )
    from .lq_scanner import inspect_dataset
except ImportError:  # direct script/test execution
    from lq_analysis import analyze_episode
    from lq_io import inspect_episode_inventory, inspect_layout, load_jsonl, load_manifest
    from lq_model import (
        VERSION,
        DatasetReport,
        Diagnostic,
        EpisodeResult,
        FrameRecord,
        ModalitySample,
        Thresholds,
    )
    from lq_scanner import inspect_dataset

def write_reports(report: DatasetReport, output_dir: Path, formats: Sequence[str]) -> dict[str, Path]:
    dataset_root = Path(report.root).resolve()
    output_dir = output_dir.resolve()
    if output_dir == dataset_root or dataset_root in output_dir.parents:
        raise ValueError("report output must be outside the read-only dataset root")
    output_dir.mkdir(parents=True, exist_ok=True)
    writers = {
        "json": ("report.json", report.json_text),
        "markdown": ("report.md", report.markdown_text),
        "html": ("report.html", report.html_text),
    }
    written: dict[str, Path] = {}
    for name in sorted(set(formats)):
        if name not in writers:
            raise ValueError(f"unsupported report format: {name}")
        filename, producer = writers[name]
        path = output_dir / filename
        temporary = output_dir / f".{filename}.tmp-{os.getpid()}"
        try:
            temporary.write_text(producer(), encoding="utf-8", newline="\n")
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
        written[name] = path
    return written


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path, help="LeRobot v2.1 dataset root")
    parser.add_argument("--manifest", type=Path, help="canonical decoded-observation JSONL manifest")
    parser.add_argument("--output", type=Path, default=Path("quality-report"), help="report output directory")
    parser.add_argument(
        "--format",
        action="append",
        choices=("json", "markdown", "html"),
        dest="formats",
        help="report format (repeatable; defaults to all)",
    )
    parser.add_argument("--sample-stride", type=int, default=1, help="native video sample stride (default: every frame)")
    parser.add_argument("--state-abs-max", type=float, default=Thresholds.state_abs_max)
    parser.add_argument("--action-abs-max", type=float, default=Thresholds.action_abs_max)
    parser.add_argument("--fps-jitter-fraction", type=float, default=Thresholds.fps_jitter_fraction)
    parser.add_argument("--sync-offset-ms", type=float, default=Thresholds.sync_offset_ms)
    parser.add_argument("--sync-drift-ms", type=float, default=Thresholds.sync_drift_ms)
    parser.add_argument("--minimum-modality-coverage", type=float, default=Thresholds.minimum_modality_coverage)
    parser.add_argument("--black-luma-max", type=float, default=Thresholds.black_luma_max)
    parser.add_argument("--low-texture-stddev-max", type=float, default=Thresholds.low_texture_stddev_max)
    parser.add_argument("--occlusion-ratio-min", type=float, default=Thresholds.occlusion_ratio_min)
    parser.add_argument("--version", action="version", version=VERSION)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        thresholds = Thresholds(
            state_abs_max=args.state_abs_max,
            action_abs_max=args.action_abs_max,
            fps_jitter_fraction=args.fps_jitter_fraction,
            sync_offset_ms=args.sync_offset_ms,
            sync_drift_ms=args.sync_drift_ms,
            minimum_modality_coverage=args.minimum_modality_coverage,
            black_luma_max=args.black_luma_max,
            low_texture_stddev_max=args.low_texture_stddev_max,
            occlusion_ratio_min=args.occlusion_ratio_min,
        )
        report = inspect_dataset(
            args.root,
            manifest=args.manifest,
            thresholds=thresholds,
            sample_stride=args.sample_stride,
        )
        formats = args.formats or ["json", "markdown", "html"]
        written = write_reports(report, args.output, formats)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    print(json.dumps({"complete": report.complete, "summary": report.summary, "reports": {k: str(v) for k, v in written.items()}}, sort_keys=True))
    if not report.complete:
        return 2
    if report.summary["diagnostic_counts"]["error"]:
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
