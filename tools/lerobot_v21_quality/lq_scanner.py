#!/usr/bin/env python3
"""Dataset-level orchestration and aggregate scoring."""
from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

try:
    from .lq_analysis import analyze_episode
    from .lq_io import (
        _camera_keys,
        _inventory_fingerprint,
        _merge_camera_samples,
        _native_parquet_frames,
        _probe_video,
        _resolve_template,
        inspect_episode_inventory,
        inspect_layout,
        load_manifest,
    )
    from .lq_model import (
        VERSION,
        DatasetReport,
        Diagnostic,
        EpisodeResult,
        FrameRecord,
        ModalitySample,
        Thresholds,
        _coerce_float,
        _median,
        _percentile,
        _round,
    )
except ImportError:  # direct script/test execution
    from lq_analysis import analyze_episode
    from lq_io import (
        _camera_keys,
        _inventory_fingerprint,
        _merge_camera_samples,
        _native_parquet_frames,
        _probe_video,
        _resolve_template,
        inspect_episode_inventory,
        inspect_layout,
        load_manifest,
    )
    from lq_model import (
        VERSION,
        DatasetReport,
        Diagnostic,
        EpisodeResult,
        FrameRecord,
        ModalitySample,
        Thresholds,
        _coerce_float,
        _median,
        _percentile,
        _round,
    )

def inspect_dataset(
    root: Path,
    *,
    manifest: Path | None = None,
    thresholds: Thresholds | None = None,
    sample_stride: int = 1,
) -> DatasetReport:
    """Inspect a dataset without modifying any input path."""
    if sample_stride <= 0:
        raise ValueError("sample_stride must be positive")
    root = root.resolve()
    thresholds = thresholds or Thresholds()
    metadata, dataset_diagnostics, episode_meta, fingerprint_paths = inspect_layout(root, thresholds)
    fps = _coerce_float(metadata.get("fps")) or 0.0
    expected_cameras = _camera_keys(metadata)
    frames_by_episode: dict[int, list[FrameRecord]] = defaultdict(list)
    complete = True

    if manifest is not None:
        manifest = manifest.resolve()
        fingerprint_paths.append(manifest)
        try:
            frames = load_manifest(manifest)
        except (OSError, ValueError) as exc:
            dataset_diagnostics.append(Diagnostic("invalid_manifest", "error", str(exc)))
            frames = []
            complete = False
        for frame in frames:
            frames_by_episode[frame.episode_index].append(frame)
        inventory_diagnostics, inventory_complete = inspect_episode_inventory(
            root, metadata, set(episode_meta) | set(frames_by_episode), fingerprint_paths
        )
        dataset_diagnostics.extend(inventory_diagnostics)
        complete = complete and inventory_complete
    else:
        data_template = metadata.get("data_path")
        video_template = metadata.get("video_path")
        chunks_size = metadata.get("chunks_size", 1000)
        if not isinstance(chunks_size, int) or chunks_size <= 0:
            chunks_size = 1000
            dataset_diagnostics.append(Diagnostic("invalid_chunks_size", "error", "chunks_size must be a positive integer"))
        episode_indices = sorted(episode_meta)
        if not episode_indices and isinstance(metadata.get("total_episodes"), int):
            episode_indices = list(range(max(0, metadata["total_episodes"])))
        pyarrow_missing_reported = False
        opencv_missing_reported = False
        for episode_index in episode_indices:
            if not isinstance(data_template, str):
                dataset_diagnostics.append(Diagnostic("invalid_data_path_template", "error", "data_path must be a string"))
                complete = False
                break
            try:
                data_path = root / _resolve_template(data_template, episode_index, chunks_size)
            except ValueError as exc:
                dataset_diagnostics.append(Diagnostic("invalid_data_path_template", "error", str(exc)))
                complete = False
                break
            if not data_path.is_file():
                dataset_diagnostics.append(
                    Diagnostic("missing_data_file", "error", "episode Parquet file is missing", episode_index, value=str(data_path.relative_to(root)))
                )
                complete = False
                continue
            fingerprint_paths.append(data_path)
            try:
                frames = _native_parquet_frames(data_path, episode_index)
            except RuntimeError as exc:
                if not pyarrow_missing_reported:
                    dataset_diagnostics.append(Diagnostic("dependency_missing_pyarrow", "error", str(exc), modality="parquet"))
                    pyarrow_missing_reported = True
                complete = False
                continue
            except Exception as exc:  # pyarrow exposes multiple format-specific exception classes
                dataset_diagnostics.append(
                    Diagnostic("parquet_decode_error", "error", f"cannot decode {data_path.relative_to(root)}: {exc}", episode_index, modality="parquet")
                )
                complete = False
                continue
            camera_samples: dict[str, dict[int, ModalitySample]] = {}
            if not isinstance(video_template, str):
                dataset_diagnostics.append(Diagnostic("invalid_video_path_template", "error", "video_path must be a string"))
                complete = False
            else:
                for camera in expected_cameras:
                    try:
                        video_path = root / _resolve_template(video_template, episode_index, chunks_size, camera)
                    except ValueError as exc:
                        dataset_diagnostics.append(Diagnostic("invalid_video_path_template", "error", str(exc), episode_index, modality=camera))
                        complete = False
                        continue
                    if not video_path.is_file():
                        dataset_diagnostics.append(
                            Diagnostic("missing_video_file", "error", "camera video is missing", episode_index, modality=camera, value=str(video_path.relative_to(root)))
                        )
                        complete = False
                        continue
                    fingerprint_paths.append(video_path)
                    try:
                        camera_samples[camera] = _probe_video(video_path, fps, sample_stride)
                    except RuntimeError as exc:
                        if not opencv_missing_reported:
                            dataset_diagnostics.append(Diagnostic("dependency_missing_opencv", "error", str(exc), modality="video"))
                            opencv_missing_reported = True
                        complete = False
                    except Exception as exc:
                        dataset_diagnostics.append(
                            Diagnostic("video_decode_error", "error", f"cannot decode {video_path.relative_to(root)}: {exc}", episode_index, modality=camera)
                        )
                        complete = False
            frames_by_episode[episode_index].extend(_merge_camera_samples(frames, camera_samples))

    all_episode_indices = sorted(set(episode_meta) | set(frames_by_episode))
    if isinstance(metadata.get("total_episodes"), int):
        all_episode_indices = sorted(set(all_episode_indices) | set(range(max(0, metadata["total_episodes"]))))
    episodes: list[EpisodeResult] = []
    for episode_index in all_episode_indices:
        rows = frames_by_episode.get(episode_index, [])
        expected_length: int | None = None
        episode_row = episode_meta.get(episode_index)
        if episode_row:
            for key in ("length", "episode_length", "num_frames"):
                value = episode_row.get(key)
                if isinstance(value, int) and value >= 0:
                    expected_length = value
                    break
        episodes.append(analyze_episode(episode_index, rows, fps, thresholds, expected_length, expected_cameras))

    declared_frames = metadata.get("total_frames")
    observed_frames = sum(item.frame_count for item in episodes)
    if isinstance(declared_frames, int) and declared_frames != observed_frames:
        dataset_diagnostics.append(
            Diagnostic(
                "total_frames_mismatch",
                "error",
                "sum of observed episode frames differs from meta/info.json total_frames",
                value=observed_frames,
                threshold=declared_frames,
            )
        )
    quality_values = [item.quality_score for item in episodes]
    value_values = [item.value_score for item in episodes]
    quality_score = statistics.mean(quality_values) if quality_values else 0.0
    value_score = statistics.mean(value_values) if value_values else 0.0
    task_counter: Counter[int] = Counter(
        frame.task_index
        for rows in frames_by_episode.values()
        for frame in rows
        if frame.task_index is not None
    )
    total_task_frames = sum(task_counter.values())
    task_entropy_bits = 0.0
    if total_task_frames:
        for count in task_counter.values():
            probability = count / total_task_frames
            task_entropy_bits -= probability * math.log2(probability)
    task_balance_score = (
        100.0
        if len(task_counter) <= 1
        else 100.0 * task_entropy_bits / math.log2(len(task_counter))
    )
    diagnostic_counter = Counter(item.severity for item in dataset_diagnostics)
    for episode in episodes:
        diagnostic_counter.update(item.severity for item in episode.diagnostics)
    summary = {
        "episode_count": len(episodes),
        "frame_count": observed_frames,
        "quality_score": _round(quality_score),
        "value_score": _round(value_score),
        "quality_distribution": {
            "p10": _round(_percentile(quality_values, 0.10)),
            "median": _round(_median(quality_values)),
            "p90": _round(_percentile(quality_values, 0.90)),
        },
        "value_distribution": {
            "p10": _round(_percentile(value_values, 0.10)),
            "median": _round(_median(value_values)),
            "p90": _round(_percentile(value_values, 0.90)),
            "low_value_episode_ratio_below_60": _round(
                sum(value < 60.0 for value in value_values) / max(1, len(value_values))
            ),
            "high_value_episode_ratio_at_least_80": _round(
                sum(value >= 80.0 for value in value_values) / max(1, len(value_values))
            ),
        },
        "task_distribution": {str(key): task_counter[key] for key in sorted(task_counter)},
        "task_entropy_bits": _round(task_entropy_bits),
        "task_balance_score": _round(task_balance_score),
        "diagnostic_counts": {key: diagnostic_counter.get(key, 0) for key in ("error", "warning", "info")},
        "complete": complete,
    }
    fingerprint = _inventory_fingerprint(fingerprint_paths, root)
    return DatasetReport(
        version=VERSION,
        root=str(root),
        input_fingerprint=fingerprint,
        complete=complete,
        metadata=metadata,
        thresholds=thresholds,
        diagnostics=dataset_diagnostics,
        episodes=episodes,
        summary=summary,
    )
