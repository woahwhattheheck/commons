"""Internal module for the LeRobot v2.1 quality inspector."""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import html
import json
import math
import os
import shutil
import statistics
import string
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from . import report as _previous
from .report import *

def _severity_at_least(report: Mapping[str, Any], threshold: str) -> bool:
    level = SEVERITY_ORDER[threshold]
    return any(SEVERITY_ORDER[issue["severity"]] >= level for issue in report["issues"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {TOOL_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect = sub.add_parser("inspect", help="inspect one local LeRobot v2.1 dataset")
    inspect.add_argument("dataset", type=Path)
    inspect.add_argument("--out-dir", type=Path, required=True)
    inspect.add_argument("--probe-jsonl", type=Path, help="fingerprint-bound normalized probe bundle")
    inspect.add_argument("--strict-capabilities", action="store_true", help="exit 3 unless every modality probe is complete")
    inspect.add_argument("--fail-on", choices=tuple(SEVERITY_ORDER), help="exit 4 when a finding meets this severity")
    inspect.add_argument("--expected-cameras", type=int, default=3)
    inspect.add_argument("--expected-vector-dim", type=int, default=20)
    inspect.add_argument("--state-abs-limit", type=float, default=1_000_000.0)
    inspect.add_argument("--action-abs-limit", type=float, default=1_000_000.0)
    inspect.add_argument("--fps-relative-tolerance", type=float, default=0.10)
    inspect.add_argument("--timestamp-jitter-relative", type=float, default=0.25)
    inspect.add_argument("--timestamp-gap-factor", type=float, default=1.80)
    inspect.add_argument("--sync-offset-seconds", type=float, default=0.10)
    inspect.add_argument("--sync-drift-seconds", type=float, default=0.20)
    inspect.add_argument("--black-ratio-threshold", type=float, default=0.05)
    inspect.add_argument("--flat-ratio-threshold", type=float, default=0.20)
    inspect.add_argument("--visual-samples", type=int, default=12)
    inspect.add_argument("--subprocess-timeout-seconds", type=int, default=45)

    capture = sub.add_parser("capture", help="capture normalized read-only probe evidence for deterministic replay")
    capture.add_argument("dataset", type=Path)
    capture.add_argument("--out", type=Path, required=True)
    capture.add_argument("--require-complete", action="store_true", help="exit 3 unless every modality probe is complete")
    capture.add_argument("--expected-cameras", type=int, default=3)
    capture.add_argument("--expected-vector-dim", type=int, default=20)
    capture.add_argument("--state-abs-limit", type=float, default=1_000_000.0)
    capture.add_argument("--action-abs-limit", type=float, default=1_000_000.0)
    capture.add_argument("--fps-relative-tolerance", type=float, default=0.10)
    capture.add_argument("--timestamp-jitter-relative", type=float, default=0.25)
    capture.add_argument("--timestamp-gap-factor", type=float, default=1.80)
    capture.add_argument("--sync-offset-seconds", type=float, default=0.10)
    capture.add_argument("--sync-drift-seconds", type=float, default=0.20)
    capture.add_argument("--black-ratio-threshold", type=float, default=0.05)
    capture.add_argument("--flat-ratio-threshold", type=float, default=0.20)
    capture.add_argument("--visual-samples", type=int, default=12)
    capture.add_argument("--subprocess-timeout-seconds", type=int, default=45)

    fingerprint = sub.add_parser("fingerprint", help="print the sampled immutable dataset fingerprint")
    fingerprint.add_argument("dataset", type=Path)
    fingerprint.add_argument("--expected-cameras", type=int, default=3)
    fingerprint.add_argument("--expected-vector-dim", type=int, default=20)
    return parser


def _validate_cli_config(config: Config) -> None:
    if config.expected_cameras <= 0 or config.expected_vector_dim <= 0:
        raise QualityError("expected camera count and vector dimension must be positive")
    for label, value in (
        ("state_abs_limit", config.state_abs_limit),
        ("action_abs_limit", config.action_abs_limit),
        ("fps_relative_tolerance", config.fps_relative_tolerance),
        ("timestamp_jitter_relative", config.timestamp_jitter_relative),
        ("timestamp_gap_factor", config.timestamp_gap_factor),
        ("sync_offset_seconds", config.sync_offset_seconds),
        ("sync_drift_seconds", config.sync_drift_seconds),
        ("black_ratio_threshold", config.black_ratio_threshold),
        ("flat_ratio_threshold", config.flat_ratio_threshold),
    ):
        if not math.isfinite(value) or value < 0:
            raise QualityError(f"{label} must be finite and non-negative")
    if config.timestamp_gap_factor <= 1:
        raise QualityError("timestamp_gap_factor must be greater than 1")
    if not 0 <= config.black_ratio_threshold <= 1 or not 0 <= config.flat_ratio_threshold <= 1:
        raise QualityError("visual ratio thresholds must be in [0, 1]")
    if config.visual_samples < 0 or config.subprocess_timeout_seconds <= 0:
        raise QualityError("visual samples must be non-negative and timeout must be positive")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "fingerprint":
            config = Config(expected_cameras=args.expected_cameras, expected_vector_dim=args.expected_vector_dim)
            _validate_cli_config(config)
            sink = IssueSink()
            context = load_context(args.dataset, config, sink)
            print(context.fingerprint)
            return 0
        if args.command == "capture":
            config = _config_from_args(args)
            _validate_cli_config(config)
            sink = IssueSink()
            context = load_context(args.dataset, config, sink)
            probe = auto_probe(context, config, sink)
            destination = write_probe_bundle(args.dataset, args.out, context, probe)
            complete = all(capability.state == "complete" for capability in probe.capabilities.values())
            print(
                json.dumps(
                    {
                        "dataset_fingerprint": context.fingerprint,
                        "coverage_complete": complete,
                        "capabilities": {name: capability.to_dict() for name, capability in sorted(probe.capabilities.items())},
                        "output": str(destination),
                    },
                    sort_keys=True,
                )
            )
            if args.require_complete and not complete:
                return 3
            return 0
        config = _config_from_args(args)
        _validate_cli_config(config)
        report = inspect_dataset(args.dataset, config=config, probe_jsonl=args.probe_jsonl)
        paths = write_report_bundle(args.dataset, args.out_dir, report)
        print(
            json.dumps(
                {
                    "report_digest": report["report_digest"],
                    "coverage_complete": report["coverage_complete"],
                    "quality_score": report["overall"]["quality_score"],
                    "training_value_score": report["overall"]["training_value_score"],
                    "outputs": {name: str(path) for name, path in paths.items()},
                },
                sort_keys=True,
            )
        )
        if args.strict_capabilities and not report["coverage_complete"]:
            return 3
        if args.fail_on and _severity_at_least(report, args.fail_on):
            return 4
        return 0
    except QualityError as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"IO_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

__all__ = [
    'TOOL_VERSION',
    'REPORT_SCHEMA',
    'PROBE_SCHEMA',
    'EXPECTED_CODEBASE_VERSION',
    'REQUIRED_METADATA',
    'REQUIRED_FRAME_COLUMNS',
    'SEVERITY_ORDER',
    'SEVERITY_PENALTY',
    'DIMENSIONS',
    'CAPABILITY_STATES',
    'NONFINITE_TOKENS',
    'QualityError',
    'DuplicateKeyError',
    'Config',
    'Issue',
    '_Span',
    'IssueSink',
    'Capability',
    'EpisodeMeta',
    'DatasetContext',
    'FrameSummary',
    'VideoSummary',
    'ProbeResult',
    '_ObjectPairs',
    '_strict_object',
    '_reject_constant',
    'load_json_strict',
    'load_jsonl_strict',
    'canonicalize',
    'canonical_json_bytes',
    '_is_int',
    '_finite_number',
    '_ensure_positive_int',
    '_ensure_nonnegative_int',
    '_relative_posix',
    'safe_dataset_path',
    'render_template',
    '_optional_nonnegative_int',
    '_optional_finite',
    '_optional_ratio',
    '_output_inside_dataset',
    'prepare_output_dir',
    '_atomic_write',
    '_add_metadata_failure',
    'load_context',
    '_sampled_file_digest',
    'dataset_fingerprint',
    '_probe_manifest',
    'load_probe',
    '_import_pyarrow',
    'probe_parquet',
    '_parse_fraction',
    '_run_readonly',
    '_probe_one_video',
    '_optional_stream_float',
    '_optional_stream_int',
    '_sample_video_luma',
    'probe_videos',
    'auto_probe',
    'probe_bundle_rows',
    'write_probe_bundle',
    '_numeric_vector',
    '_vector_delta',
    '_varying_dimensions',
    'analyze_frames',
    '_flag_vector_jitter',
    'analyze_videos',
    '_score_dimension',
    'compute_scores',
    'build_report',
    'inspect_dataset',
    'report_markdown',
    'report_html',
    'write_report_bundle',
    '_config_from_args',
    '_severity_at_least',
    'build_parser',
    '_validate_cli_config',
    'main'
]
