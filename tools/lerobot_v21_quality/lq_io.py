#!/usr/bin/env python3
"""Read-only LeRobot v2.1 metadata, manifest, Parquet, and video ingestion."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

try:
    from .lq_model import Diagnostic, FrameRecord, ModalitySample, Thresholds, _coerce_float, _coerce_int
except ImportError:  # direct script/test execution
    from lq_model import Diagnostic, FrameRecord, ModalitySample, Thresholds, _coerce_float, _coerce_int

def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            text = raw.strip()
            if not text:
                continue
            try:
                value = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON: {exc.msg}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number}: each line must be a JSON object")
            records.append(value)
    return records


def _manifest_row_to_frame(row: Mapping[str, Any], line_number: int) -> FrameRecord:
    required = ("episode_index", "frame_index", "timestamp")
    for key in required:
        if key not in row:
            raise ValueError(f"manifest line {line_number}: missing {key}")
    episode_index = _coerce_int(row["episode_index"])
    frame_index = _coerce_int(row["frame_index"])
    timestamp = _coerce_float(row["timestamp"])
    if episode_index is None or frame_index is None or timestamp is None:
        raise ValueError(f"manifest line {line_number}: invalid index/timestamp")
    task_index = row.get("task_index")
    if task_index is not None:
        task_index = _coerce_int(task_index)
        if task_index is None:
            raise ValueError(f"manifest line {line_number}: invalid task_index")
    state = row.get("observation.state", row.get("state"))
    action = row.get("action")
    if state is not None and not isinstance(state, list):
        state = (state,)
    if action is not None and not isinstance(action, list):
        action = (action,)
    cameras_raw = row.get("cameras", {})
    if not isinstance(cameras_raw, dict):
        raise ValueError(f"manifest line {line_number}: cameras must be an object")
    cameras: dict[str, ModalitySample] = {}
    for name, sample_raw in sorted(cameras_raw.items()):
        if sample_raw is None:
            cameras[str(name)] = ModalitySample(timestamp=None, present=False, decode_ok=False)
            continue
        if not isinstance(sample_raw, dict):
            raise ValueError(f"manifest line {line_number}: camera {name!r} must be an object or null")
        cameras[str(name)] = ModalitySample(
            timestamp=_coerce_float(sample_raw.get("timestamp")),
            present=bool(sample_raw.get("present", True)),
            decode_ok=bool(sample_raw.get("decode_ok", True)),
            mean_luma=_coerce_float(sample_raw.get("mean_luma")),
            luma_stddev=_coerce_float(sample_raw.get("luma_stddev")),
            occlusion_ratio=_coerce_float(sample_raw.get("occlusion_ratio")),
        )
    return FrameRecord(
        episode_index=episode_index,
        frame_index=frame_index,
        timestamp=timestamp,
        task_index=task_index,
        state=tuple(state) if state is not None else None,
        action=tuple(action) if action is not None else None,
        state_timestamp=_coerce_float(row.get("state_timestamp", timestamp)),
        action_timestamp=_coerce_float(row.get("action_timestamp", timestamp)),
        cameras=cameras,
    )


def load_manifest(path: Path) -> list[FrameRecord]:
    return [_manifest_row_to_frame(row, index) for index, row in enumerate(load_jsonl(path), start=1)]


def _feature_shape(info: Mapping[str, Any], key: str) -> tuple[int, ...] | None:
    features = info.get("features")
    if not isinstance(features, dict):
        return None
    value = features.get(key)
    if not isinstance(value, dict):
        return None
    shape = value.get("shape")
    if not isinstance(shape, list) or not all(isinstance(item, int) for item in shape):
        return None
    return tuple(shape)


def _camera_keys(info: Mapping[str, Any]) -> list[str]:
    features = info.get("features")
    if not isinstance(features, dict):
        return []
    keys: list[str] = []
    for key, spec in features.items():
        if not isinstance(spec, dict):
            continue
        dtype = str(spec.get("dtype", "")).lower()
        if key.startswith("observation.images.") or dtype in {"video", "image"}:
            keys.append(str(key))
    return sorted(keys)


def _resolve_template(template: str, episode_index: int, chunks_size: int, video_key: str | None = None) -> str:
    chunk = episode_index // max(1, chunks_size)
    values = {
        "episode_index": episode_index,
        "episode_chunk": chunk,
        "chunk_index": chunk,
        "video_key": video_key or "",
    }
    try:
        return template.format(**values)
    except (KeyError, ValueError) as exc:
        raise ValueError(f"unsupported path template {template!r}: {exc}") from exc


def _inventory_fingerprint(paths: Iterable[Path], root: Path) -> str:
    digest = hashlib.sha256()
    unique = sorted({path.resolve() for path in paths if path.exists()}, key=lambda item: str(item))
    for path in unique:
        try:
            relative = path.relative_to(root.resolve()).as_posix()
        except ValueError:
            relative = path.name
        digest.update(relative.encode("utf-8", errors="surrogateescape"))
        if path.is_file():
            size = path.stat().st_size
            digest.update(str(size).encode("ascii"))
            with path.open("rb") as handle:
                first = handle.read(65_536)
                if size > 65_536:
                    handle.seek(max(0, size - 65_536))
                    last = handle.read(65_536)
                else:
                    last = b""
            digest.update(hashlib.sha256(first).digest())
            digest.update(hashlib.sha256(last).digest())
    return digest.hexdigest()


def inspect_layout(root: Path, thresholds: Thresholds) -> tuple[dict[str, Any], list[Diagnostic], dict[int, dict[str, Any]], list[Path]]:
    diagnostics: list[Diagnostic] = []
    fingerprint_paths: list[Path] = []
    info_path = root / "meta" / "info.json"
    if not info_path.is_file():
        diagnostics.append(Diagnostic("missing_info", "error", "meta/info.json is missing"))
        return {}, diagnostics, {}, fingerprint_paths
    fingerprint_paths.append(info_path)
    try:
        info = json.loads(info_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        diagnostics.append(Diagnostic("invalid_info", "error", f"cannot parse meta/info.json: {exc}"))
        return {}, diagnostics, {}, fingerprint_paths
    if not isinstance(info, dict):
        diagnostics.append(Diagnostic("invalid_info_shape", "error", "meta/info.json must contain a JSON object"))
        return {}, diagnostics, {}, fingerprint_paths
    if info.get("codebase_version") != "v2.1":
        diagnostics.append(
            Diagnostic(
                "version_mismatch",
                "error",
                "dataset codebase_version is not v2.1",
                value=info.get("codebase_version"),
                threshold="v2.1",
            )
        )
    for key in ("total_episodes", "total_frames", "fps", "data_path", "video_path", "features"):
        if key not in info:
            diagnostics.append(Diagnostic("missing_info_field", "error", f"meta/info.json is missing {key}", modality=key))
    fps = _coerce_float(info.get("fps"))
    if fps is None or not math.isfinite(fps) or fps <= 0:
        diagnostics.append(Diagnostic("invalid_fps", "error", "fps must be a positive finite number", value=info.get("fps")))
    state_shape = _feature_shape(info, "observation.state")
    action_shape = _feature_shape(info, "action")
    if state_shape != (thresholds.expected_state_dim,):
        diagnostics.append(
            Diagnostic(
                "state_schema_dimension",
                "error",
                "observation.state schema dimension does not match the expected challenge dimension",
                modality="observation.state",
                value=state_shape,
                threshold=[thresholds.expected_state_dim],
            )
        )
    if action_shape != (thresholds.expected_action_dim,):
        diagnostics.append(
            Diagnostic(
                "action_schema_dimension",
                "error",
                "action schema dimension does not match the expected challenge dimension",
                modality="action",
                value=action_shape,
                threshold=[thresholds.expected_action_dim],
            )
        )
    cameras = _camera_keys(info)
    if len(cameras) != 3:
        diagnostics.append(
            Diagnostic(
                "camera_schema_count",
                "error",
                "challenge schema expects exactly three camera modalities",
                value=cameras,
                threshold=3,
            )
        )
    episodes_path = root / "meta" / "episodes.jsonl"
    episode_meta: dict[int, dict[str, Any]] = {}
    if not episodes_path.is_file():
        diagnostics.append(Diagnostic("missing_episodes_metadata", "error", "meta/episodes.jsonl is missing"))
    else:
        fingerprint_paths.append(episodes_path)
        try:
            rows = load_jsonl(episodes_path)
        except (OSError, ValueError) as exc:
            diagnostics.append(Diagnostic("invalid_episodes_metadata", "error", str(exc)))
            rows = []
        for row_number, row in enumerate(rows, start=1):
            raw_index = row.get("episode_index")
            index = _coerce_int(raw_index)
            if index is None:
                diagnostics.append(
                    Diagnostic("invalid_episode_index", "error", f"episodes.jsonl row {row_number} has invalid episode_index", value=raw_index)
                )
                continue
            if index in episode_meta:
                diagnostics.append(Diagnostic("duplicate_episode_index", "error", "duplicate episode_index in metadata", episode_index=index))
            episode_meta[index] = row
    expected_total = info.get("total_episodes")
    if isinstance(expected_total, int) and expected_total >= 0:
        expected_indices = set(range(expected_total))
        actual_indices = set(episode_meta)
        for missing in sorted(expected_indices - actual_indices):
            diagnostics.append(Diagnostic("missing_episode_index", "error", "episode index absent from metadata", episode_index=missing))
        for extra in sorted(actual_indices - expected_indices):
            diagnostics.append(Diagnostic("unexpected_episode_index", "error", "episode index exceeds declared total", episode_index=extra))
    return info, diagnostics, episode_meta, fingerprint_paths



def inspect_episode_inventory(
    root: Path,
    metadata: Mapping[str, Any],
    episode_indices: Iterable[int],
    fingerprint_paths: list[Path],
) -> tuple[list[Diagnostic], bool]:
    """Validate the expected v2.1 Parquet/video inventory without decoding it."""
    diagnostics: list[Diagnostic] = []
    complete = True
    data_template = metadata.get("data_path")
    video_template = metadata.get("video_path")
    chunks_size = metadata.get("chunks_size", 1000)
    if not isinstance(chunks_size, int) or chunks_size <= 0:
        diagnostics.append(Diagnostic("invalid_chunks_size", "error", "chunks_size must be a positive integer"))
        chunks_size = 1000
        complete = False
    if not isinstance(data_template, str):
        diagnostics.append(Diagnostic("invalid_data_path_template", "error", "data_path must be a string"))
        return diagnostics, False
    if not isinstance(video_template, str):
        diagnostics.append(Diagnostic("invalid_video_path_template", "error", "video_path must be a string"))
        return diagnostics, False
    cameras = _camera_keys(metadata)
    for episode_index in sorted(set(episode_indices)):
        try:
            data_path = root / _resolve_template(data_template, episode_index, chunks_size)
        except ValueError as exc:
            diagnostics.append(Diagnostic("invalid_data_path_template", "error", str(exc), episode_index=episode_index))
            complete = False
            continue
        if not data_path.is_file():
            diagnostics.append(
                Diagnostic(
                    "missing_data_file",
                    "error",
                    "episode Parquet file is missing",
                    episode_index=episode_index,
                    modality="parquet",
                    value=str(data_path.relative_to(root)),
                )
            )
            complete = False
        elif data_path.stat().st_size == 0:
            diagnostics.append(
                Diagnostic(
                    "empty_data_file",
                    "error",
                    "episode Parquet file is empty",
                    episode_index=episode_index,
                    modality="parquet",
                    value=str(data_path.relative_to(root)),
                )
            )
            complete = False
            fingerprint_paths.append(data_path)
        else:
            fingerprint_paths.append(data_path)
        for camera in cameras:
            try:
                video_path = root / _resolve_template(video_template, episode_index, chunks_size, camera)
            except ValueError as exc:
                diagnostics.append(
                    Diagnostic("invalid_video_path_template", "error", str(exc), episode_index=episode_index, modality=camera)
                )
                complete = False
                continue
            if not video_path.is_file():
                diagnostics.append(
                    Diagnostic(
                        "missing_video_file",
                        "error",
                        "camera video is missing",
                        episode_index=episode_index,
                        modality=camera,
                        value=str(video_path.relative_to(root)),
                    )
                )
                complete = False
            elif video_path.stat().st_size == 0:
                diagnostics.append(
                    Diagnostic(
                        "empty_video_file",
                        "error",
                        "camera video is empty",
                        episode_index=episode_index,
                        modality=camera,
                        value=str(video_path.relative_to(root)),
                    )
                )
                complete = False
                fingerprint_paths.append(video_path)
            else:
                fingerprint_paths.append(video_path)
    return diagnostics, complete

def _native_parquet_frames(path: Path, episode_index: int) -> list[FrameRecord]:
    try:
        import pyarrow.parquet as pq  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("optional dependency pyarrow is required for native Parquet inspection") from exc
    table = pq.read_table(path)
    rows = table.to_pylist()
    frames: list[FrameRecord] = []
    for position, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: row {position} is not an object")
        manifest_row = {
            "episode_index": row.get("episode_index", episode_index),
            "frame_index": row.get("frame_index", position),
            "timestamp": row.get("timestamp", math.nan),
            "task_index": row.get("task_index"),
            "observation.state": row.get("observation.state"),
            "action": row.get("action"),
            "state_timestamp": row.get("state_timestamp", row.get("timestamp")),
            "action_timestamp": row.get("action_timestamp", row.get("timestamp")),
            "cameras": {},
        }
        frames.append(_manifest_row_to_frame(manifest_row, position + 1))
    return frames


def _probe_video(path: Path, fps: float, sample_stride: int) -> dict[int, ModalitySample]:
    try:
        import cv2  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("optional dependency opencv-python is required for native video inspection") from exc
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError(f"cannot open video {path}")
    result: dict[int, ModalitySample] = {}
    index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if index % sample_stride == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            mean_luma = float(gray.mean())
            luma_stddev = float(gray.std())
            # A transparent proxy for occlusion/corruption: nearly uniform or
            # overwhelmingly saturated pixels. It is not a learned detector and
            # is reported as such.
            saturated = float(((gray <= 2) | (gray >= 253)).mean())
            result[index] = ModalitySample(
                timestamp=index / fps,
                present=True,
                decode_ok=True,
                mean_luma=mean_luma,
                luma_stddev=luma_stddev,
                occlusion_ratio=saturated,
            )
        else:
            # Unsampled frames still contribute to file/frame and synchronization
            # coverage. Content ratios use only samples with decoded statistics.
            result[index] = ModalitySample(timestamp=index / fps, present=True, decode_ok=True)
        index += 1
    capture.release()
    if index == 0:
        raise ValueError(f"video contains no decodable frames: {path}")
    return result


def _merge_camera_samples(frames: Sequence[FrameRecord], camera_samples: Mapping[str, Mapping[int, ModalitySample]]) -> list[FrameRecord]:
    merged: list[FrameRecord] = []
    for frame in frames:
        cameras = dict(frame.cameras)
        for key, samples in camera_samples.items():
            cameras[key] = samples.get(frame.frame_index, ModalitySample(timestamp=None, present=False, decode_ok=False))
        merged.append(
            FrameRecord(
                episode_index=frame.episode_index,
                frame_index=frame.frame_index,
                timestamp=frame.timestamp,
                task_index=frame.task_index,
                state=frame.state,
                action=frame.action,
                state_timestamp=frame.state_timestamp,
                action_timestamp=frame.action_timestamp,
                cameras=cameras,
            )
        )
    return merged
