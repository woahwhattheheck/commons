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

from . import probe_bundle as _previous
from .probe_bundle import *

def _numeric_vector(value: Any) -> tuple[list[float], str | None]:
    if not isinstance(value, (list, tuple)):
        return [], "not-a-list"
    numbers: list[float] = []
    for item in value:
        if isinstance(item, str) and item.strip().lower() in NONFINITE_TOKENS:
            return numbers, "non-finite"
        number = _finite_number(item)
        if number is None:
            return numbers, "non-numeric-or-non-finite"
        numbers.append(number)
    return numbers, None


def _vector_delta(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        return math.inf
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(left, right)))


def _varying_dimensions(vectors: Sequence[Sequence[float]], epsilon: float = 1e-9) -> int:
    if not vectors:
        return 0
    width = len(vectors[0])
    count = 0
    for column in range(width):
        values = [row[column] for row in vectors if len(row) == width]
        if values and max(values) - min(values) > epsilon:
            count += 1
    return count


def analyze_frames(context: DatasetContext, probe: ProbeResult, config: Config, sink: IssueSink) -> dict[int, FrameSummary]:
    summaries: dict[int, FrameSummary] = {}
    fps = _finite_number(context.info.get("fps")) or 1.0
    expected_dt = 1.0 / fps
    known_task_indices = set(context.tasks)
    global_expected_index = 0

    for episode_index, episode in sorted(context.episodes.items()):
        records = probe.frames.get(episode_index, [])
        path = context.data_paths.get(episode_index)
        rel = path.relative_to(context.root).as_posix() if path is not None else None
        summary = FrameSummary(episode_index=episode_index, rows=len(records))
        summaries[episode_index] = summary
        if not records:
            sink.add(
                "CONTENT.FRAME_RECORDS_UNAVAILABLE",
                "critical",
                "content",
                "no decoded frame records are available for this episode",
                episode_index=episode_index,
                path=rel,
            )
            global_expected_index += episode.length
            continue
        if len(records) != episode.length:
            sink.add(
                "TEMPORAL.FRAME_COUNT_MISMATCH",
                "error",
                "temporal",
                "decoded Parquet row count differs from episode length",
                episode_index=episode_index,
                path=rel,
                evidence={"expected": episode.length, "observed": len(records)},
            )

        timestamps: list[float] = []
        frame_indices: list[int] = []
        state_vectors: list[list[float]] = []
        action_vectors: list[list[float]] = []
        state_deltas: list[tuple[int, float]] = []
        action_deltas: list[tuple[int, float]] = []
        last_state: list[float] | None = None
        last_action: list[float] | None = None

        for row_position, row in enumerate(records):
            frame_index = row.get("frame_index")
            if not _is_int(frame_index) or frame_index < 0:
                sink.frame(
                    "STRUCTURE.FRAME_INDEX_INVALID",
                    "error",
                    "structure",
                    "frame_index must be a non-negative integer",
                    episode_index=episode_index,
                    frame_index=row_position,
                    path=rel,
                    evidence={"observed": frame_index},
                )
                frame_index = row_position
            frame_indices.append(frame_index)
            if frame_index != row_position:
                sink.frame(
                    "TEMPORAL.FRAME_ORDER_OR_GAP",
                    "error",
                    "temporal",
                    "frame_index is not the expected contiguous row position",
                    episode_index=episode_index,
                    frame_index=frame_index,
                    path=rel,
                    evidence={"expected": row_position, "observed": frame_index},
                )
            row_episode = row.get("episode_index")
            if row_episode != episode_index:
                sink.frame(
                    "STRUCTURE.FRAME_EPISODE_MISMATCH",
                    "error",
                    "structure",
                    "frame episode_index differs from containing episode",
                    episode_index=episode_index,
                    frame_index=frame_index,
                    path=rel,
                    evidence={"observed": row_episode},
                )
            global_index = row.get("index")
            if global_index is not None and global_index != global_expected_index + row_position:
                sink.frame(
                    "TEMPORAL.GLOBAL_INDEX_ORDER",
                    "warning",
                    "temporal",
                    "global frame index is not contiguous",
                    episode_index=episode_index,
                    frame_index=frame_index,
                    path=rel,
                    evidence={"expected": global_expected_index + row_position, "observed": global_index},
                )
            task_index = row.get("task_index")
            if not _is_int(task_index) or task_index not in known_task_indices:
                sink.frame(
                    "STRUCTURE.TASK_INDEX_UNKNOWN",
                    "error",
                    "structure",
                    "frame task_index is absent from tasks.jsonl",
                    episode_index=episode_index,
                    frame_index=frame_index,
                    path=rel,
                    evidence={"observed": task_index},
                )

            timestamp = _finite_number(row.get("timestamp"))
            if timestamp is None:
                sink.frame(
                    "TEMPORAL.TIMESTAMP_INVALID",
                    "error",
                    "temporal",
                    "timestamp is missing or non-finite",
                    episode_index=episode_index,
                    frame_index=frame_index,
                    path=rel,
                    evidence={"observed": row.get("timestamp")},
                )
            else:
                timestamps.append(timestamp)

            for key, limit, destination in (
                ("observation.state", config.state_abs_limit, state_vectors),
                ("action", config.action_abs_limit, action_vectors),
            ):
                vector, error = _numeric_vector(row.get(key))
                if error is not None:
                    code = "CONTENT.VECTOR_NONFINITE" if "finite" in error else "CONTENT.VECTOR_MALFORMED"
                    sink.frame(
                        code,
                        "error",
                        "content",
                        "state/action vector is malformed or contains non-finite values",
                        episode_index=episode_index,
                        frame_index=frame_index,
                        modality=key,
                        path=rel,
                        evidence={"problem": error},
                    )
                    continue
                if len(vector) != config.expected_vector_dim:
                    sink.frame(
                        "CONTENT.VECTOR_DIMENSION",
                        "error",
                        "content",
                        "state/action vector has the wrong dimension",
                        episode_index=episode_index,
                        frame_index=frame_index,
                        modality=key,
                        path=rel,
                        evidence={"expected": config.expected_vector_dim, "observed": len(vector)},
                    )
                    continue
                destination.append(vector)
                offending = [index for index, number in enumerate(vector) if abs(number) > limit]
                if offending:
                    sink.frame(
                        "CONTENT.VECTOR_OUT_OF_RANGE",
                        "error",
                        "content",
                        "state/action vector exceeds the configured absolute bound",
                        episode_index=episode_index,
                        frame_index=frame_index,
                        modality=key,
                        path=rel,
                        evidence={"limit": limit, "indices": offending[:20]},
                    )
                if key == "observation.state":
                    if last_state is not None:
                        state_deltas.append((frame_index, _vector_delta(last_state, vector)))
                    last_state = vector
                else:
                    if last_action is not None:
                        action_deltas.append((frame_index, _vector_delta(last_action, vector)))
                    last_action = vector

        global_expected_index += episode.length
        if timestamps:
            summary.first_timestamp = timestamps[0]
            summary.last_timestamp = timestamps[-1]
        deltas: list[float] = []
        for index in range(1, len(timestamps)):
            delta = timestamps[index] - timestamps[index - 1]
            deltas.append(delta)
            frame_index = frame_indices[index] if index < len(frame_indices) else index
            if delta < 0:
                sink.frame(
                    "TEMPORAL.TIMESTAMP_REVERSAL",
                    "critical",
                    "temporal",
                    "timestamp moved backward",
                    episode_index=episode_index,
                    frame_index=frame_index,
                    path=rel,
                    evidence={"delta": delta},
                )
            elif delta == 0:
                sink.frame(
                    "TEMPORAL.TIMESTAMP_DUPLICATE",
                    "error",
                    "temporal",
                    "consecutive frames share a timestamp",
                    episode_index=episode_index,
                    frame_index=frame_index,
                    path=rel,
                )
            elif delta > expected_dt * config.timestamp_gap_factor:
                sink.frame(
                    "TEMPORAL.FRAME_LOSS_GAP",
                    "error",
                    "temporal",
                    "timestamp gap indicates missing or dropped frames",
                    episode_index=episode_index,
                    frame_index=frame_index,
                    path=rel,
                    evidence={"delta": delta, "expected_dt": expected_dt},
                )
            elif abs(delta - expected_dt) / expected_dt > config.timestamp_jitter_relative:
                sink.frame(
                    "TEMPORAL.FPS_JITTER",
                    "warning",
                    "temporal",
                    "inter-frame interval exceeds the configured FPS jitter tolerance",
                    episode_index=episode_index,
                    frame_index=frame_index,
                    path=rel,
                    evidence={"delta": delta, "expected_dt": expected_dt},
                )
        positive_deltas = [delta for delta in deltas if delta > 0]
        if positive_deltas:
            median_dt = statistics.median(positive_deltas)
            summary.median_dt = median_dt
            summary.jitter_ratio = statistics.median(abs(delta - median_dt) for delta in positive_deltas) / median_dt
            observed_fps = 1.0 / median_dt
            if abs(observed_fps - fps) / fps > config.fps_relative_tolerance:
                sink.add(
                    "TEMPORAL.OBSERVED_FPS_MISMATCH",
                    "error",
                    "temporal",
                    "median timestamp FPS differs from info.fps",
                    episode_index=episode_index,
                    path=rel,
                    evidence={"declared_fps": fps, "observed_fps": observed_fps},
                )

        _flag_vector_jitter(state_deltas, "observation.state", episode_index, rel, sink)
        _flag_vector_jitter(action_deltas, "action", episode_index, rel, sink)
        summary.state_varying_dimensions = _varying_dimensions(state_vectors)
        summary.action_varying_dimensions = _varying_dimensions(action_vectors)
        if config.expected_vector_dim > 0:
            summary.state_motion_score = 100.0 * summary.state_varying_dimensions / config.expected_vector_dim
            summary.action_motion_score = 100.0 * summary.action_varying_dimensions / config.expected_vector_dim
        if action_deltas:
            static = sum(1 for _, delta in action_deltas if delta <= 1e-9)
            summary.static_action_ratio = static / len(action_deltas)
        if summary.static_action_ratio >= 0.95 and len(action_deltas) >= 3:
            sink.add(
                "VALUE.LOW_ACTION_SIGNAL",
                "warning",
                "content",
                "episode action stream is almost entirely static and may have low training value",
                episode_index=episode_index,
                modality="action",
                path=rel,
                evidence={"static_ratio": summary.static_action_ratio},
            )
    return summaries


def _flag_vector_jitter(
    deltas: Sequence[tuple[int, float]],
    modality: str,
    episode_index: int,
    path: str | None,
    sink: IssueSink,
) -> None:
    finite = [value for _, value in deltas if math.isfinite(value)]
    if len(finite) < 5:
        return
    median = statistics.median(finite)
    mad = statistics.median(abs(value - median) for value in finite)
    threshold = median + 8.0 * max(mad, 1e-9)
    # Avoid calling every small movement a spike when the stream is nearly static.
    threshold = max(threshold, median * 5.0, 1e-6)
    for frame_index, value in deltas:
        if math.isfinite(value) and value > threshold:
            sink.frame(
                "TEMPORAL.DATA_JITTER_SPIKE",
                "warning",
                "temporal",
                "state/action step is a robust outlier relative to the episode",
                episode_index=episode_index,
                frame_index=frame_index,
                modality=modality,
                path=path,
                evidence={"delta_norm": value, "median": median, "mad": mad, "threshold": threshold},
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
    '_flag_vector_jitter'
]
