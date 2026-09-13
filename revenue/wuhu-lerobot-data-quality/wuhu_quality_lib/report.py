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

from . import video_analysis as _previous
from .video_analysis import *

def _score_dimension(issues: Sequence[Issue], dimension: str, episode_index: int) -> float:
    by_code: dict[str, float] = defaultdict(float)
    for issue in issues:
        if issue.dimension != dimension:
            continue
        if issue.episode_index not in {None, episode_index}:
            continue
        occurrence_factor = 1.0 + min(2.0, math.log2(max(1, issue.occurrences))) * 0.25
        by_code[issue.code] += SEVERITY_PENALTY[issue.severity] * occurrence_factor
    # A single code can dominate a stream but should not obscure independent
    # defects. Cap each family before summing.
    penalty = sum(min(50.0, value) for value in by_code.values())
    return max(0.0, 100.0 - penalty)


def compute_scores(
    context: DatasetContext,
    issues: Sequence[Issue],
    frames: Mapping[int, FrameSummary],
    videos: Mapping[tuple[int, str], VideoSummary],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    episode_scores: list[dict[str, Any]] = []
    task_counter: Counter[str] = Counter()
    total_frames = sum(max(0, episode.length) for episode in context.episodes.values()) or 1
    weighted_quality = 0.0
    weighted_value = 0.0
    healthy_episodes = 0

    for episode_index, episode in sorted(context.episodes.items()):
        dimensions = {dimension: _score_dimension(issues, dimension, episode_index) for dimension in DIMENSIONS}
        quality = statistics.fmean(dimensions.values())
        frame_summary = frames.get(episode_index, FrameSummary(episode_index))
        motion = statistics.fmean([frame_summary.state_motion_score, frame_summary.action_motion_score])
        camera_records = sum(1 for camera in context.camera_keys if (episode_index, camera) in videos)
        camera_coverage = 100.0 if not context.camera_keys else 100.0 * camera_records / len(context.camera_keys)
        value = 0.65 * quality + 0.20 * motion + 0.15 * camera_coverage
        status = "clean" if quality >= 90 else "review" if quality >= 70 else "reject"
        if status == "clean":
            healthy_episodes += 1
        for task in episode.tasks:
            task_counter[task] += 1
        row = {
            "episode_index": episode_index,
            "length": episode.length,
            "tasks": list(episode.tasks),
            "dimension_scores": dimensions,
            "quality_score": quality,
            "training_value_score": value,
            "motion_signal_score": motion,
            "camera_coverage_score": camera_coverage,
            "status": status,
        }
        episode_scores.append(canonicalize(row))
        weight = episode.length / total_frames
        weighted_quality += quality * weight
        weighted_value += value * weight

    episode_count = len(context.episodes)
    unique_tasks = len(task_counter)
    # Diversity is a transparent descriptive signal, not a semantic success
    # judgment. Repeated trajectories of the same task can still score highly on
    # quality while receiving a lower coverage signal.
    task_diversity = 0.0
    if episode_count:
        task_diversity = min(100.0, 100.0 * unique_tasks / max(1, min(episode_count, 10)))
    healthy_ratio = 100.0 * healthy_episodes / episode_count if episode_count else 0.0
    overall_value = 0.70 * weighted_value + 0.15 * task_diversity + 0.15 * healthy_ratio
    overall = {
        "quality_score": weighted_quality,
        "training_value_score": overall_value,
        "episode_weighted_value_score": weighted_value,
        "task_diversity_score": task_diversity,
        "clean_episode_ratio": healthy_ratio,
        "episode_count": episode_count,
        "unique_task_count": unique_tasks,
        "task_distribution": dict(sorted(task_counter.items())),
        "scoring_contract": {
            "dimension_score": "100 minus capped severity penalties per independent issue code",
            "quality": "mean(structure, temporal, synchronization, content)",
            "episode_value": "0.65*quality + 0.20*motion_signal + 0.15*camera_coverage",
            "dataset_value": "0.70*episode_weighted_value + 0.15*task_diversity + 0.15*clean_episode_ratio",
            "severity_penalties": SEVERITY_PENALTY,
        },
    }
    return episode_scores, canonicalize(overall)


def build_report(
    context: DatasetContext,
    probe: ProbeResult,
    frame_summaries: Mapping[int, FrameSummary],
    video_summaries: Mapping[tuple[int, str], VideoSummary],
    issues: Sequence[Issue],
    config: Config,
) -> dict[str, Any]:
    episode_scores, overall = compute_scores(context, issues, frame_summaries, video_summaries)
    issue_counts = Counter(issue.severity for issue in issues)
    capability_payload = {name: cap.to_dict() for name, cap in sorted(probe.capabilities.items())}
    complete = all(cap.state == "complete" for cap in probe.capabilities.values())
    report: dict[str, Any] = {
        "schema_version": REPORT_SCHEMA,
        "tool": {"name": "wuhu-quality", "version": TOOL_VERSION},
        "dataset": {
            "root_name": context.root.name,
            "fingerprint": context.fingerprint,
            "fingerprint_algorithm": "metadata full hash; data/video size plus full-or-head-tail sample",
            "codebase_version": context.info.get("codebase_version"),
            "declared_fps": context.info.get("fps"),
            "episodes": len(context.episodes),
            "frames": sum(ep.length for ep in context.episodes.values()),
            "cameras": list(context.camera_keys),
            "probe_source": probe.source,
        },
        "capabilities": capability_payload,
        "coverage_complete": complete,
        "overall": overall,
        "episode_scores": episode_scores,
        "frame_summaries": [frame_summaries[index].to_dict() for index in sorted(frame_summaries)],
        "video_summaries": [video_summaries[key].to_dict() for key in sorted(video_summaries)],
        "issue_counts": {severity: issue_counts.get(severity, 0) for severity in ("critical", "error", "warning", "info")},
        "issues": [issue.to_dict() for issue in issues],
        "configuration": canonicalize(dataclasses.asdict(config)),
        "limitations": [
            "Visual black/white and occlusion checks are deterministic low-luma/high-luma/low-texture heuristics, not semantic scene understanding.",
            "Training-value scoring measures integrity, modality coverage, motion signal, and task coverage; it does not claim task success or policy performance.",
            "A non-complete capability receipt means the corresponding modality was not fully inspected and must not be interpreted as clean.",
        ],
    }
    digest_basis = dict(report)
    report_digest = hashlib.sha256(canonical_json_bytes(digest_basis)).hexdigest()
    report["report_digest"] = report_digest
    return canonicalize(report)


def inspect_dataset(
    root: Path,
    *,
    config: Config | None = None,
    probe_jsonl: Path | None = None,
) -> dict[str, Any]:
    config = config or Config()
    sink = IssueSink()
    context = load_context(root, config, sink)
    if probe_jsonl is not None:
        probe = load_probe(probe_jsonl.expanduser().resolve(strict=True), context, sink)
    else:
        probe = auto_probe(context, config, sink)
    frame_summaries = analyze_frames(context, probe, config, sink)
    video_summaries = analyze_videos(context, probe, frame_summaries, config, sink)
    issues = sink.finish()
    return build_report(context, probe, frame_summaries, video_summaries, issues, config)


def report_markdown(report: Mapping[str, Any]) -> str:
    overall = report["overall"]
    counts = report["issue_counts"]
    lines = [
        "# LeRobot v2.1 multimodal data-quality report",
        "",
        f"- Dataset fingerprint: `{report['dataset']['fingerprint']}`",
        f"- Report digest: `{report['report_digest']}`",
        f"- Coverage complete: **{str(report['coverage_complete']).lower()}**",
        f"- Quality score: **{overall['quality_score']:.2f}/100**",
        f"- Training-value score: **{overall['training_value_score']:.2f}/100**",
        f"- Issues: {counts['critical']} critical, {counts['error']} error, {counts['warning']} warning, {counts['info']} info",
        "",
        "## Capability receipts",
        "",
        "| Capability | State | Source | Records | Detail |",
        "|---|---:|---|---:|---|",
    ]
    for name, capability in sorted(report["capabilities"].items()):
        lines.append(
            f"| {name} | {capability['state']} | {capability['source']} | {capability['records']} | {capability['detail']} |"
        )
    lines += [
        "",
        "## Episode scorecard",
        "",
        "| Episode | Frames | Status | Quality | Value | Structure | Temporal | Sync | Content |",
        "|---:|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for episode in report["episode_scores"]:
        dims = episode["dimension_scores"]
        lines.append(
            f"| {episode['episode_index']} | {episode['length']} | {episode['status']} | "
            f"{episode['quality_score']:.2f} | {episode['training_value_score']:.2f} | "
            f"{dims['structure']:.2f} | {dims['temporal']:.2f} | {dims['synchronization']:.2f} | {dims['content']:.2f} |"
        )
    lines += ["", "## Located anomalies", ""]
    if not report["issues"]:
        lines.append("No anomalies were recorded under the configured checks.")
    for issue in report["issues"]:
        location: list[str] = []
        if "episode_index" in issue:
            location.append(f"episode {issue['episode_index']}")
        if "frame_start" in issue:
            frame_text = str(issue["frame_start"])
            if issue.get("frame_end") != issue["frame_start"]:
                frame_text += f"–{issue.get('frame_end')}"
            location.append(f"frame {frame_text}")
        if "modality" in issue:
            location.append(issue["modality"])
        if "path" in issue:
            location.append(f"`{issue['path']}`")
        suffix = f" ({', '.join(location)})" if location else ""
        lines.append(f"- **{issue['severity'].upper()} · {issue['code']}**{suffix}: {issue['reason']}")
    lines += ["", "## Interpretation boundary", ""]
    for item in report["limitations"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def report_html(report: Mapping[str, Any]) -> str:
    markdown = report_markdown(report)
    # A dependency-free HTML view keeps all report text escaped and exposes the
    # canonical JSON as a downloadable-in-browser script payload.
    json_text = canonical_json_bytes(report).decode("utf-8")
    escaped_markdown = html.escape(markdown)
    escaped_json = html.escape(json_text)
    return f"""<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\">
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">
<title>LeRobot v2.1 quality report</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#1b1b1b}}
pre{{white-space:pre-wrap;background:#f5f5f5;padding:1rem;border-radius:.5rem;overflow:auto}}
details{{margin-top:1rem}} code{{font-family:ui-monospace,monospace}}
</style>
</head>
<body>
<h1>LeRobot v2.1 multimodal data-quality report</h1>
<pre>{escaped_markdown}</pre>
<details><summary>Canonical JSON</summary><pre>{escaped_json}</pre></details>
</body>
</html>
"""


def write_report_bundle(dataset_root: Path, out_dir: Path, report: Mapping[str, Any]) -> dict[str, Path]:
    out = prepare_output_dir(dataset_root, out_dir)
    paths = {
        "json": out / "report.json",
        "markdown": out / "report.md",
        "html": out / "report.html",
        "issues": out / "issues.jsonl",
    }
    _atomic_write(paths["json"], json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False).encode("utf-8") + b"\n")
    _atomic_write(paths["markdown"], report_markdown(report).encode("utf-8"))
    _atomic_write(paths["html"], report_html(report).encode("utf-8"))
    issue_bytes = b"".join(canonical_json_bytes(issue) for issue in report["issues"])
    _atomic_write(paths["issues"], issue_bytes)
    return paths


def _config_from_args(args: argparse.Namespace) -> Config:
    return Config(
        expected_cameras=args.expected_cameras,
        expected_vector_dim=args.expected_vector_dim,
        state_abs_limit=args.state_abs_limit,
        action_abs_limit=args.action_abs_limit,
        fps_relative_tolerance=args.fps_relative_tolerance,
        timestamp_jitter_relative=args.timestamp_jitter_relative,
        timestamp_gap_factor=args.timestamp_gap_factor,
        sync_offset_seconds=args.sync_offset_seconds,
        sync_drift_seconds=args.sync_drift_seconds,
        black_ratio_threshold=args.black_ratio_threshold,
        flat_ratio_threshold=args.flat_ratio_threshold,
        visual_samples=args.visual_samples,
        subprocess_timeout_seconds=args.subprocess_timeout_seconds,
    )

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
    '_config_from_args'
]
