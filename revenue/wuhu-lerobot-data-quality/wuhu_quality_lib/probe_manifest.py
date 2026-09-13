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

from . import context as _previous
from .context import *

def _probe_manifest(path: Path, expected_fingerprint: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows = load_jsonl_strict(path)
    if not rows or rows[0].get("kind") != "manifest":
        raise QualityError("probe JSONL must begin with a manifest row")
    manifest = rows[0]
    if manifest.get("schema_version") != PROBE_SCHEMA:
        raise QualityError(f"unsupported probe schema: {manifest.get('schema_version')!r}")
    if manifest.get("dataset_fingerprint") != expected_fingerprint:
        raise QualityError("probe dataset_fingerprint does not match the current dataset bytes")
    capabilities = manifest.get("capabilities")
    if not isinstance(capabilities, dict):
        raise QualityError("probe manifest capabilities must be an object")
    for name in ("parquet", "video_container", "visual_content"):
        state = capabilities.get(name)
        if state not in {"complete", "partial"}:
            raise QualityError(f"probe capability {name} must be complete or partial")
    return manifest, rows[1:]


def load_probe(path: Path, context: DatasetContext, sink: IssueSink) -> ProbeResult:
    manifest, rows = _probe_manifest(path, context.fingerprint)
    frames: dict[int, list[dict[str, Any]]] = defaultdict(list)
    videos: dict[tuple[int, str], VideoSummary] = {}
    frame_keys: set[tuple[int, int]] = set()
    for row_number, row in enumerate(rows, 2):
        kind = row.get("kind")
        if kind == "frame":
            episode_index = row.get("episode_index")
            frame_index = row.get("frame_index")
            if not _is_int(episode_index) or episode_index not in context.episodes:
                raise QualityError(f"probe row {row_number}: unknown episode_index")
            if not _is_int(frame_index) or frame_index < 0:
                raise QualityError(f"probe row {row_number}: frame_index must be non-negative integer")
            key = (episode_index, frame_index)
            if key in frame_keys:
                raise QualityError(f"probe row {row_number}: duplicate frame key {key}")
            frame_keys.add(key)
            frames[episode_index].append(row)
        elif kind == "video":
            episode_index = row.get("episode_index")
            camera = row.get("camera")
            if not _is_int(episode_index) or episode_index not in context.episodes:
                raise QualityError(f"probe row {row_number}: unknown video episode_index")
            if camera not in context.camera_keys:
                raise QualityError(f"probe row {row_number}: unknown camera {camera!r}")
            key = (episode_index, camera)
            if key in videos:
                raise QualityError(f"probe row {row_number}: duplicate video key {key}")
            path_value = row.get("path")
            if not isinstance(path_value, str):
                expected_path = context.video_paths.get(key)
                path_value = expected_path.relative_to(context.root).as_posix() if expected_path is not None else camera
            videos[key] = VideoSummary(
                episode_index=episode_index,
                camera=camera,
                path=path_value,
                frame_count=_optional_nonnegative_int(row.get("frame_count"), f"probe row {row_number} frame_count"),
                fps=_optional_finite(row.get("fps"), f"probe row {row_number} fps"),
                start_timestamp=_optional_finite(row.get("start_timestamp"), f"probe row {row_number} start_timestamp"),
                end_timestamp=_optional_finite(row.get("end_timestamp"), f"probe row {row_number} end_timestamp"),
                duration=_optional_finite(row.get("duration"), f"probe row {row_number} duration"),
                width=_optional_nonnegative_int(row.get("width"), f"probe row {row_number} width"),
                height=_optional_nonnegative_int(row.get("height"), f"probe row {row_number} height"),
                decode_ok=bool(row.get("decode_ok")) if isinstance(row.get("decode_ok"), bool) else False,
                sample_count=_optional_nonnegative_int(row.get("sample_count", 0), f"probe row {row_number} sample_count") or 0,
                black_ratio=_optional_ratio(row.get("black_ratio"), f"probe row {row_number} black_ratio"),
                flat_ratio=_optional_ratio(row.get("flat_ratio"), f"probe row {row_number} flat_ratio"),
                mean_luma=_optional_finite(row.get("mean_luma"), f"probe row {row_number} mean_luma"),
                mean_luma_std=_optional_finite(row.get("mean_luma_std"), f"probe row {row_number} mean_luma_std"),
            )
        else:
            raise QualityError(f"probe row {row_number}: unsupported kind {kind!r}")

    caps: dict[str, Capability] = {}
    declared = manifest["capabilities"]
    expected_frames = sum(ep.length for ep in context.episodes.values())
    frame_count = sum(len(items) for items in frames.values())
    expected_videos = len(context.episodes) * len(context.camera_keys)
    if declared["parquet"] == "complete" and frame_count != expected_frames:
        sink.add(
            "CAPABILITY.PROBE_FRAME_COVERAGE",
            "critical",
            "structure",
            "probe declares complete Parquet coverage but frame records are incomplete",
            evidence={"expected": expected_frames, "observed": frame_count},
        )
        parquet_state = "partial"
    else:
        parquet_state = declared["parquet"]
    if declared["video_container"] == "complete" and len(videos) != expected_videos:
        sink.add(
            "CAPABILITY.PROBE_VIDEO_COVERAGE",
            "critical",
            "structure",
            "probe declares complete video coverage but video records are incomplete",
            evidence={"expected": expected_videos, "observed": len(videos)},
        )
        video_state = "partial"
    else:
        video_state = declared["video_container"]
    visual_records = sum(1 for item in videos.values() if item.sample_count > 0)
    if declared["visual_content"] == "complete" and visual_records != expected_videos:
        sink.add(
            "CAPABILITY.PROBE_VISUAL_COVERAGE",
            "critical",
            "content",
            "probe declares complete visual coverage but sampled-video records are incomplete",
            evidence={"expected": expected_videos, "observed": visual_records},
        )
        visual_state = "partial"
    else:
        visual_state = declared["visual_content"]
    caps["parquet"] = Capability("parquet", parquet_state, "probe-jsonl", "normalized frame records", frame_count)
    caps["video_container"] = Capability("video_container", video_state, "probe-jsonl", "container timing records", len(videos))
    caps["visual_content"] = Capability("visual_content", visual_state, "probe-jsonl", "decoded visual samples", visual_records)
    return ProbeResult(dict(frames), videos, caps, "probe-jsonl")

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
    'load_probe'
]
