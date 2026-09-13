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

from . import frame_analysis as _previous
from .frame_analysis import *

def analyze_videos(
    context: DatasetContext,
    probe: ProbeResult,
    frame_summaries: Mapping[int, FrameSummary],
    config: Config,
    sink: IssueSink,
) -> dict[tuple[int, str], VideoSummary]:
    declared_fps = _finite_number(context.info.get("fps")) or 1.0
    for episode_index, episode in sorted(context.episodes.items()):
        starts: list[tuple[str, float]] = []
        ends: list[tuple[str, float]] = []
        summary = frame_summaries.get(episode_index)
        data_start = summary.first_timestamp if summary and summary.first_timestamp is not None else 0.0
        data_end = summary.last_timestamp if summary and summary.last_timestamp is not None else max(0.0, (episode.length - 1) / declared_fps)
        data_duration = max(0.0, data_end - data_start)
        for camera in context.camera_keys:
            key = (episode_index, camera)
            path = context.video_paths.get(key)
            rel = path.relative_to(context.root).as_posix() if path is not None else None
            video = probe.videos.get(key)
            if video is None:
                sink.add(
                    "SYNCHRONIZATION.VIDEO_RECORD_MISSING",
                    "critical",
                    "synchronization",
                    "no video timing/content probe record is available",
                    episode_index=episode_index,
                    modality=camera,
                    path=rel,
                )
                continue
            if not video.decode_ok:
                sink.add(
                    "CONTENT.VIDEO_CORRUPT",
                    "critical",
                    "content",
                    "video container could not be decoded",
                    episode_index=episode_index,
                    modality=camera,
                    path=video.path,
                )
            if video.frame_count is None:
                sink.add(
                    "TEMPORAL.VIDEO_FRAME_COUNT_UNKNOWN",
                    "warning",
                    "temporal",
                    "video frame count is unavailable",
                    episode_index=episode_index,
                    modality=camera,
                    path=video.path,
                )
            elif abs(video.frame_count - episode.length) > 1:
                sink.add(
                    "TEMPORAL.VIDEO_FRAME_COUNT_MISMATCH",
                    "error",
                    "temporal",
                    "camera frame count differs from the episode length",
                    episode_index=episode_index,
                    modality=camera,
                    path=video.path,
                    evidence={"expected": episode.length, "observed": video.frame_count},
                )
            if video.fps is None or video.fps <= 0:
                sink.add(
                    "TEMPORAL.VIDEO_FPS_UNKNOWN",
                    "warning",
                    "temporal",
                    "camera FPS is unavailable",
                    episode_index=episode_index,
                    modality=camera,
                    path=video.path,
                )
            elif abs(video.fps - declared_fps) / declared_fps > config.fps_relative_tolerance:
                sink.add(
                    "TEMPORAL.VIDEO_FPS_MISMATCH",
                    "error",
                    "temporal",
                    "camera FPS differs from info.fps",
                    episode_index=episode_index,
                    modality=camera,
                    path=video.path,
                    evidence={"declared": declared_fps, "observed": video.fps},
                )
            start = video.start_timestamp if video.start_timestamp is not None else 0.0
            end = video.end_timestamp
            if end is None and video.duration is not None:
                end = start + video.duration
            if end is not None:
                starts.append((camera, start))
                ends.append((camera, end))
                start_offset = start - data_start
                end_offset = end - data_end
                drift = abs((end - start) - data_duration)
                if abs(start_offset) > config.sync_offset_seconds:
                    sink.add(
                        "SYNCHRONIZATION.LATE_OR_EARLY_START",
                        "error",
                        "synchronization",
                        "camera starts too early or too late relative to state/action data",
                        episode_index=episode_index,
                        modality=camera,
                        path=video.path,
                        evidence={"offset_seconds": start_offset, "threshold": config.sync_offset_seconds},
                    )
                if abs(end_offset) > config.sync_offset_seconds:
                    sink.add(
                        "SYNCHRONIZATION.EARLY_OR_LATE_STOP",
                        "error",
                        "synchronization",
                        "camera stops too early or too late relative to state/action data",
                        episode_index=episode_index,
                        modality=camera,
                        path=video.path,
                        evidence={"offset_seconds": end_offset, "threshold": config.sync_offset_seconds},
                    )
                if drift > config.sync_drift_seconds:
                    sink.add(
                        "SYNCHRONIZATION.CLOCK_DRIFT",
                        "error",
                        "synchronization",
                        "camera duration diverges from state/action duration",
                        episode_index=episode_index,
                        modality=camera,
                        path=video.path,
                        evidence={"drift_seconds": drift, "threshold": config.sync_drift_seconds},
                    )
            else:
                sink.add(
                    "SYNCHRONIZATION.VIDEO_DURATION_UNKNOWN",
                    "warning",
                    "synchronization",
                    "camera timing coverage cannot be measured",
                    episode_index=episode_index,
                    modality=camera,
                    path=video.path,
                )
            if video.sample_count <= 0:
                sink.add(
                    "CONTENT.VISUAL_SAMPLES_UNAVAILABLE",
                    "critical",
                    "content",
                    "no decoded visual samples were available for black/flat-frame checks",
                    episode_index=episode_index,
                    modality=camera,
                    path=video.path,
                )
            else:
                if video.black_ratio is not None and video.black_ratio > config.black_ratio_threshold:
                    sink.add(
                        "CONTENT.BLACK_OR_WHITE_FRAMES",
                        "error",
                        "content",
                        "camera has excessive black/white sampled frames",
                        episode_index=episode_index,
                        modality=camera,
                        path=video.path,
                        evidence={"ratio": video.black_ratio, "threshold": config.black_ratio_threshold},
                    )
                if video.flat_ratio is not None and video.flat_ratio > config.flat_ratio_threshold:
                    sink.add(
                        "CONTENT.FLAT_OR_OCCLUDED_FRAMES",
                        "error",
                        "content",
                        "camera has excessive low-texture samples, consistent with occlusion or frozen imagery",
                        episode_index=episode_index,
                        modality=camera,
                        path=video.path,
                        evidence={"ratio": video.flat_ratio, "threshold": config.flat_ratio_threshold},
                    )
        if len(starts) >= 2:
            spread = max(value for _, value in starts) - min(value for _, value in starts)
            if spread > config.sync_offset_seconds:
                sink.add(
                    "SYNCHRONIZATION.CAMERA_START_SPREAD",
                    "error",
                    "synchronization",
                    "camera streams do not start together",
                    episode_index=episode_index,
                    evidence={"spread_seconds": spread, "starts": dict(starts)},
                )
        if len(ends) >= 2:
            spread = max(value for _, value in ends) - min(value for _, value in ends)
            if spread > config.sync_offset_seconds:
                sink.add(
                    "SYNCHRONIZATION.CAMERA_END_SPREAD",
                    "error",
                    "synchronization",
                    "camera streams do not stop together",
                    episode_index=episode_index,
                    evidence={"spread_seconds": spread, "ends": dict(ends)},
                )
    return probe.videos

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
    'analyze_videos'
]
