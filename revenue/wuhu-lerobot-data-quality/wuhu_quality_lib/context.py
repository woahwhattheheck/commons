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

from . import model as _previous
from .model import *

def _add_metadata_failure(sink: IssueSink, code: str, reason: str, *, path: str | None = None, evidence: Mapping[str, Any] | None = None) -> None:
    sink.add(code, "critical", "structure", reason, path=path, evidence=evidence)


def load_context(root: Path, config: Config, sink: IssueSink) -> DatasetContext:
    try:
        root = root.expanduser().resolve(strict=True)
    except OSError as exc:
        raise QualityError(f"dataset root is unavailable: {root}: {exc}") from exc
    if not root.is_dir():
        raise QualityError(f"dataset root is not a directory: {root}")
    if root.is_symlink():
        raise QualityError(f"dataset root must not be a symbolic link: {root}")

    metadata_paths: list[Path] = []
    for rel in REQUIRED_METADATA:
        path = safe_dataset_path(root, rel, rel)
        metadata_paths.append(path)
        if not path.is_file():
            _add_metadata_failure(sink, "STRUCTURE.METADATA_MISSING", "required metadata file is missing", path=rel)

    info_path = safe_dataset_path(root, "meta/info.json", "info.json")
    info = load_json_strict(info_path) if info_path.is_file() else {}
    if not isinstance(info, dict):
        raise QualityError("meta/info.json must contain an object")

    if info.get("codebase_version") != EXPECTED_CODEBASE_VERSION:
        _add_metadata_failure(
            sink,
            "STRUCTURE.CODEBASE_VERSION",
            "dataset is not declared as LeRobot v2.1",
            path="meta/info.json",
            evidence={"observed": info.get("codebase_version"), "expected": EXPECTED_CODEBASE_VERSION},
        )

    fps = _finite_number(info.get("fps"))
    if fps is None or fps <= 0:
        _add_metadata_failure(sink, "STRUCTURE.FPS_INVALID", "info.fps must be finite and positive", path="meta/info.json")

    features = info.get("features")
    if not isinstance(features, dict):
        _add_metadata_failure(sink, "STRUCTURE.FEATURES_INVALID", "info.features must be an object", path="meta/info.json")
        features = {}

    for required in REQUIRED_FRAME_COLUMNS:
        if required not in features:
            _add_metadata_failure(
                sink,
                "STRUCTURE.FEATURE_MISSING",
                "required frame feature is absent from info.features",
                path="meta/info.json",
                evidence={"feature": required},
            )

    for vector_key in ("observation.state", "action"):
        feature = features.get(vector_key)
        if not isinstance(feature, dict):
            continue
        shape = feature.get("shape")
        if not isinstance(shape, list) or not shape or not all(_is_int(x) and x > 0 for x in shape):
            _add_metadata_failure(
                sink,
                "STRUCTURE.VECTOR_SHAPE_INVALID",
                "state/action feature shape must be a positive integer list",
                path="meta/info.json",
                evidence={"feature": vector_key, "shape": shape},
            )
        elif math.prod(shape) != config.expected_vector_dim:
            sink.add(
                "STRUCTURE.VECTOR_DIMENSION",
                "error",
                "structure",
                "declared state/action dimension differs from the competition contract",
                path="meta/info.json",
                evidence={"feature": vector_key, "declared": math.prod(shape), "expected": config.expected_vector_dim},
            )

    camera_keys = tuple(
        sorted(
            key
            for key, feature in features.items()
            if isinstance(feature, dict)
            and (feature.get("dtype") in {"video", "image"} or key.startswith("observation.images."))
        )
    )
    if len(camera_keys) != config.expected_cameras:
        sink.add(
            "STRUCTURE.CAMERA_COUNT",
            "error",
            "structure",
            "camera modality count differs from the competition contract",
            path="meta/info.json",
            evidence={"observed": len(camera_keys), "expected": config.expected_cameras, "cameras": list(camera_keys)},
        )

    episodes_path = safe_dataset_path(root, "meta/episodes.jsonl", "episodes.jsonl")
    episode_rows = load_jsonl_strict(episodes_path) if episodes_path.is_file() else []
    episodes: dict[int, EpisodeMeta] = {}
    for row_number, row in enumerate(episode_rows, 1):
        idx = row.get("episode_index")
        length = row.get("length")
        tasks = row.get("tasks")
        if not _is_int(idx) or idx < 0:
            _add_metadata_failure(
                sink,
                "STRUCTURE.EPISODE_INDEX_INVALID",
                "episode_index must be a non-negative integer",
                path="meta/episodes.jsonl",
                evidence={"row": row_number, "value": idx},
            )
            continue
        if idx in episodes:
            _add_metadata_failure(
                sink,
                "STRUCTURE.EPISODE_DUPLICATE",
                "duplicate episode_index in episodes metadata",
                path="meta/episodes.jsonl",
                evidence={"episode_index": idx},
            )
            continue
        if not _is_int(length) or length <= 0:
            _add_metadata_failure(
                sink,
                "STRUCTURE.EPISODE_LENGTH_INVALID",
                "episode length must be a positive integer",
                path="meta/episodes.jsonl",
                evidence={"episode_index": idx, "value": length},
            )
            length = 0
        if not isinstance(tasks, list) or not tasks or not all(isinstance(item, str) and item.strip() for item in tasks):
            _add_metadata_failure(
                sink,
                "STRUCTURE.EPISODE_TASKS_INVALID",
                "episode tasks must be a non-empty list of strings",
                path="meta/episodes.jsonl",
                evidence={"episode_index": idx},
            )
            tasks = []
        episodes[idx] = EpisodeMeta(idx, int(length), tuple(tasks), row)

    if episodes:
        observed = sorted(episodes)
        expected = list(range(len(episodes)))
        if observed != expected:
            sink.add(
                "STRUCTURE.EPISODE_INDEX_GAP",
                "error",
                "structure",
                "episode indices are not contiguous from zero",
                path="meta/episodes.jsonl",
                evidence={"observed": observed[:50], "expected_count": len(expected)},
            )

    tasks_path = safe_dataset_path(root, "meta/tasks.jsonl", "tasks.jsonl")
    task_rows = load_jsonl_strict(tasks_path) if tasks_path.is_file() else []
    tasks_map: dict[int, str] = {}
    task_texts: set[str] = set()
    for row_number, row in enumerate(task_rows, 1):
        idx = row.get("task_index")
        text = row.get("task")
        if not _is_int(idx) or idx < 0 or not isinstance(text, str) or not text.strip():
            _add_metadata_failure(
                sink,
                "STRUCTURE.TASK_INVALID",
                "task row requires non-negative task_index and non-empty task",
                path="meta/tasks.jsonl",
                evidence={"row": row_number},
            )
            continue
        if idx in tasks_map or text in task_texts:
            _add_metadata_failure(
                sink,
                "STRUCTURE.TASK_DUPLICATE",
                "task index or task text is duplicated",
                path="meta/tasks.jsonl",
                evidence={"task_index": idx, "task": text},
            )
            continue
        tasks_map[idx] = text
        task_texts.add(text)

    for episode in episodes.values():
        for task_text in episode.tasks:
            if task_text not in task_texts:
                sink.add(
                    "STRUCTURE.EPISODE_TASK_UNKNOWN",
                    "error",
                    "structure",
                    "episode references a task absent from tasks.jsonl",
                    episode_index=episode.episode_index,
                    path="meta/episodes.jsonl",
                    evidence={"task": task_text},
                )

    stats_path = safe_dataset_path(root, "meta/episodes_stats.jsonl", "episodes_stats.jsonl")
    stats_rows = load_jsonl_strict(stats_path) if stats_path.is_file() else []
    stats_map: dict[int, dict[str, Any]] = {}
    for row_number, row in enumerate(stats_rows, 1):
        idx = row.get("episode_index")
        stats = row.get("stats")
        if not _is_int(idx) or idx < 0 or not isinstance(stats, dict):
            _add_metadata_failure(
                sink,
                "STRUCTURE.STATS_INVALID",
                "episode stats row requires episode_index and stats object",
                path="meta/episodes_stats.jsonl",
                evidence={"row": row_number},
            )
            continue
        if idx in stats_map:
            _add_metadata_failure(
                sink,
                "STRUCTURE.STATS_DUPLICATE",
                "duplicate episode statistics",
                path="meta/episodes_stats.jsonl",
                evidence={"episode_index": idx},
            )
            continue
        stats_map[idx] = stats
    missing_stats = sorted(set(episodes) - set(stats_map))
    if missing_stats:
        sink.add(
            "STRUCTURE.STATS_MISSING",
            "error",
            "structure",
            "episodes are missing per-episode statistics",
            path="meta/episodes_stats.jsonl",
            evidence={"episode_indices": missing_stats[:100], "count": len(missing_stats)},
        )

    total_episodes = info.get("total_episodes")
    if not _is_int(total_episodes) or total_episodes != len(episodes):
        sink.add(
            "STRUCTURE.TOTAL_EPISODES_MISMATCH",
            "error",
            "structure",
            "info.total_episodes does not match episodes.jsonl",
            path="meta/info.json",
            evidence={"declared": total_episodes, "observed": len(episodes)},
        )
    total_frames = info.get("total_frames")
    observed_frames = sum(ep.length for ep in episodes.values())
    if not _is_int(total_frames) or total_frames != observed_frames:
        sink.add(
            "STRUCTURE.TOTAL_FRAMES_MISMATCH",
            "error",
            "structure",
            "info.total_frames does not match summed episode lengths",
            path="meta/info.json",
            evidence={"declared": total_frames, "observed": observed_frames},
        )
    total_tasks = info.get("total_tasks")
    if not _is_int(total_tasks) or total_tasks != len(tasks_map):
        sink.add(
            "STRUCTURE.TOTAL_TASKS_MISMATCH",
            "warning",
            "structure",
            "info.total_tasks does not match tasks.jsonl",
            path="meta/info.json",
            evidence={"declared": total_tasks, "observed": len(tasks_map)},
        )
    expected_videos = len(episodes) * len(camera_keys)
    total_videos = info.get("total_videos")
    if not _is_int(total_videos) or total_videos != expected_videos:
        sink.add(
            "STRUCTURE.TOTAL_VIDEOS_MISMATCH",
            "warning",
            "structure",
            "info.total_videos does not match episode-camera product",
            path="meta/info.json",
            evidence={"declared": total_videos, "observed": expected_videos},
        )

    chunk_size_value = info.get("chunks_size", info.get("chunk_size", 1000))
    if not _is_int(chunk_size_value) or chunk_size_value <= 0:
        sink.add(
            "STRUCTURE.CHUNK_SIZE_INVALID",
            "error",
            "structure",
            "chunk size must be a positive integer",
            path="meta/info.json",
            evidence={"value": chunk_size_value},
        )
        chunk_size_value = 1000

    data_template = info.get("data_path")
    video_template = info.get("video_path")
    if not isinstance(data_template, str):
        _add_metadata_failure(sink, "STRUCTURE.DATA_TEMPLATE_MISSING", "info.data_path is required", path="meta/info.json")
        data_template = "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet"
    if camera_keys and not isinstance(video_template, str):
        _add_metadata_failure(sink, "STRUCTURE.VIDEO_TEMPLATE_MISSING", "info.video_path is required for camera features", path="meta/info.json")
        video_template = "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4"

    data_paths: dict[int, Path] = {}
    video_paths: dict[tuple[int, str], Path] = {}
    for idx, episode in sorted(episodes.items()):
        chunk = idx // chunk_size_value
        try:
            data_rel = render_template(data_template, episode_index=idx, episode_chunk=chunk)
            data_path = safe_dataset_path(root, data_rel, "data_path")
            data_paths[idx] = data_path
            if not data_path.is_file():
                sink.add(
                    "STRUCTURE.DATA_FILE_MISSING",
                    "critical",
                    "structure",
                    "episode Parquet file is missing",
                    episode_index=idx,
                    path=data_rel,
                )
        except QualityError as exc:
            sink.add(
                "STRUCTURE.DATA_PATH_INVALID",
                "critical",
                "structure",
                str(exc),
                episode_index=idx,
                path="meta/info.json",
            )
        for camera in camera_keys:
            if not isinstance(video_template, str):
                continue
            try:
                video_rel = render_template(
                    video_template,
                    episode_index=idx,
                    episode_chunk=chunk,
                    video_key=camera,
                )
                video_path = safe_dataset_path(root, video_rel, "video_path")
                video_paths[(idx, camera)] = video_path
                if not video_path.is_file():
                    sink.add(
                        "STRUCTURE.VIDEO_FILE_MISSING",
                        "critical",
                        "structure",
                        "episode camera video is missing",
                        episode_index=idx,
                        modality=camera,
                        path=video_rel,
                    )
            except QualityError as exc:
                sink.add(
                    "STRUCTURE.VIDEO_PATH_INVALID",
                    "critical",
                    "structure",
                    str(exc),
                    episode_index=idx,
                    modality=camera,
                    path="meta/info.json",
                )

    context = DatasetContext(
        root=root,
        info=info,
        episodes=episodes,
        tasks=tasks_map,
        episode_stats=stats_map,
        camera_keys=camera_keys,
        data_paths=data_paths,
        video_paths=video_paths,
        metadata_paths=tuple(metadata_paths),
    )
    fingerprint, entries = dataset_fingerprint(context, config)
    context.fingerprint = fingerprint
    context.fingerprint_entries = entries
    return context


def _sampled_file_digest(path: Path, sample_bytes: int) -> dict[str, Any]:
    try:
        st = path.stat()
    except OSError as exc:
        return {"state": "unreadable", "error": type(exc).__name__}
    if not path.is_file():
        return {"state": "not-file", "mode": st.st_mode}
    hasher = hashlib.sha256()
    hasher.update(str(st.st_size).encode("ascii"))
    try:
        with path.open("rb") as handle:
            if st.st_size <= sample_bytes * 2:
                while chunk := handle.read(1 << 20):
                    hasher.update(chunk)
                mode = "full"
            else:
                hasher.update(handle.read(sample_bytes))
                handle.seek(max(0, st.st_size - sample_bytes))
                hasher.update(handle.read(sample_bytes))
                mode = "head-tail"
    except OSError as exc:
        return {"state": "unreadable", "error": type(exc).__name__, "size": st.st_size}
    return {"state": "file", "size": st.st_size, "digest": hasher.hexdigest(), "mode": mode}


def dataset_fingerprint(context: DatasetContext, config: Config) -> tuple[str, list[dict[str, Any]]]:
    entries: list[dict[str, Any]] = []
    all_paths: dict[str, Path] = {}
    for path in context.metadata_paths:
        try:
            rel = path.relative_to(context.root).as_posix()
        except ValueError:
            continue
        all_paths[rel] = path
    for path in context.data_paths.values():
        all_paths[path.relative_to(context.root).as_posix()] = path
    for path in context.video_paths.values():
        all_paths[path.relative_to(context.root).as_posix()] = path
    for rel, path in sorted(all_paths.items()):
        if rel.startswith("meta/"):
            digest = _sampled_file_digest(path, max(config.hash_sample_bytes, 1 << 30))
        else:
            digest = _sampled_file_digest(path, config.hash_sample_bytes)
        entries.append({"path": rel, **digest})
    payload = {
        "algorithm": "sha256(metadata-full, data/video-size+full-or-head-tail)",
        "entries": entries,
    }
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest(), entries

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
    'dataset_fingerprint'
]
