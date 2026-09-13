#!/usr/bin/env python3
"""Per-episode temporal, synchronization, content, and value analysis."""
from __future__ import annotations

import math
import statistics
from collections import defaultdict
from typing import Any, Sequence

try:
    from .lq_model import (
        Diagnostic,
        EpisodeResult,
        FrameRecord,
        Thresholds,
        _clamp_score,
        _coerce_float,
        _finite,
        _median,
        _percentile,
        _round,
    )
except ImportError:  # direct script/test execution
    from lq_model import (
        Diagnostic,
        EpisodeResult,
        FrameRecord,
        Thresholds,
        _clamp_score,
        _coerce_float,
        _finite,
        _median,
        _percentile,
        _round,
    )

def _analyze_vector(
    vector: tuple[Any, ...] | None,
    expected_dim: int,
    abs_max: float,
    episode_index: int,
    frame_index: int,
    modality: str,
) -> tuple[list[Diagnostic], bool, bool]:
    diagnostics: list[Diagnostic] = []
    if vector is None:
        diagnostics.append(
            Diagnostic("missing_vector", "error", f"{modality} is missing", episode_index, frame_index, modality)
        )
        return diagnostics, False, False
    if len(vector) != expected_dim:
        diagnostics.append(
            Diagnostic(
                "vector_dimension",
                "error",
                f"{modality} has the wrong dimension",
                episode_index,
                frame_index,
                modality,
                value=len(vector),
                threshold=expected_dim,
            )
        )
        return diagnostics, False, False
    finite = True
    in_range = True
    for position, value in enumerate(vector):
        number = _coerce_float(value)
        if number is None or not math.isfinite(number):
            finite = False
            diagnostics.append(
                Diagnostic(
                    "nonfinite_value",
                    "error",
                    f"{modality}[{position}] is not finite",
                    episode_index,
                    frame_index,
                    modality,
                    value=value,
                    threshold="finite",
                )
            )
        elif abs(number) > abs_max:
            in_range = False
            diagnostics.append(
                Diagnostic(
                    "out_of_range_value",
                    "error",
                    f"{modality}[{position}] exceeds the configured absolute bound",
                    episode_index,
                    frame_index,
                    modality,
                    value=number,
                    threshold=abs_max,
                )
            )
    return diagnostics, finite, in_range


def analyze_episode(
    episode_index: int,
    frames: Sequence[FrameRecord],
    fps: float,
    thresholds: Thresholds,
    expected_length: int | None,
    expected_cameras: Sequence[str],
) -> EpisodeResult:
    diagnostics: list[Diagnostic] = []
    if not frames:
        diagnostics.append(Diagnostic("empty_episode", "error", "episode contains no frames", episode_index=episode_index))
        subscores = {"structure": 0.0, "temporal": 0.0, "synchronization": 0.0, "content": 0.0}
        return EpisodeResult(episode_index, 0, diagnostics, {}, subscores, 0.0, 0.0)

    frame_count = len(frames)
    if expected_length is not None and expected_length != frame_count:
        diagnostics.append(
            Diagnostic(
                "episode_length_mismatch",
                "error",
                "observed frame count differs from metadata",
                episode_index=episode_index,
                value=frame_count,
                threshold=expected_length,
            )
        )

    frame_steps_good = 0
    monotonic_timestamps = 0
    fps_intervals_good = 0
    interval_count = max(0, frame_count - 1)
    expected_dt = 1.0 / fps if fps > 0 else 0.0
    intervals: list[float] = []
    duplicate_indices = 0
    gap_frames = 0
    for position, frame in enumerate(frames):
        if frame.episode_index != episode_index:
            diagnostics.append(
                Diagnostic(
                    "row_episode_mismatch",
                    "error",
                    "row episode_index differs from the episode being analyzed",
                    episode_index=episode_index,
                    frame_index=frame.frame_index,
                    value=frame.episode_index,
                    threshold=episode_index,
                )
            )
        if not _finite(frame.timestamp):
            diagnostics.append(
                Diagnostic("invalid_timestamp", "error", "timestamp is not finite", episode_index, frame.frame_index, "timestamp", frame.timestamp)
            )
        if position == 0:
            continue
        previous = frames[position - 1]
        step = frame.frame_index - previous.frame_index
        if step == 1:
            frame_steps_good += 1
        elif step == 0:
            duplicate_indices += 1
            diagnostics.append(
                Diagnostic("duplicate_frame_index", "error", "frame_index is duplicated", episode_index, frame.frame_index, "frame_index")
            )
        elif step < 0:
            diagnostics.append(
                Diagnostic(
                    "frame_order_reversal",
                    "error",
                    "frame_index moved backwards",
                    episode_index,
                    frame.frame_index,
                    "frame_index",
                    value=step,
                    threshold=1,
                )
            )
        else:
            gap_frames += step - 1
            diagnostics.append(
                Diagnostic(
                    "frame_gap",
                    "error",
                    "one or more frame indices are missing",
                    episode_index,
                    frame.frame_index,
                    "frame_index",
                    value=step - 1,
                    threshold=0,
                )
            )
        dt = frame.timestamp - previous.timestamp
        intervals.append(dt)
        if dt > 0:
            monotonic_timestamps += 1
        else:
            diagnostics.append(
                Diagnostic(
                    "timestamp_reversal",
                    "error",
                    "timestamp did not increase",
                    episode_index,
                    frame.frame_index,
                    "timestamp",
                    value=dt,
                    threshold="> 0",
                )
            )
        if dt > 0 and expected_dt > 0:
            deviation_fraction = abs(dt - expected_dt) / expected_dt
            if deviation_fraction <= thresholds.fps_jitter_fraction:
                fps_intervals_good += 1
            else:
                diagnostics.append(
                    Diagnostic(
                        "fps_jitter",
                        "warning",
                        "frame interval exceeds configured FPS jitter tolerance",
                        episode_index,
                        frame.frame_index,
                        "timestamp",
                        value=_round(deviation_fraction),
                        threshold=thresholds.fps_jitter_fraction,
                    )
                )

    state_valid = 0
    action_valid = 0
    state_in_range = 0
    action_in_range = 0
    for frame in frames:
        state_diagnostics, state_finite, state_range = _analyze_vector(
            frame.state,
            thresholds.expected_state_dim,
            thresholds.state_abs_max,
            episode_index,
            frame.frame_index,
            "observation.state",
        )
        action_diagnostics, action_finite, action_range = _analyze_vector(
            frame.action,
            thresholds.expected_action_dim,
            thresholds.action_abs_max,
            episode_index,
            frame.frame_index,
            "action",
        )
        diagnostics.extend(state_diagnostics)
        diagnostics.extend(action_diagnostics)
        state_valid += int(state_finite and frame.state is not None and len(frame.state) == thresholds.expected_state_dim)
        action_valid += int(action_finite and frame.action is not None and len(frame.action) == thresholds.expected_action_dim)
        state_in_range += int(state_finite and state_range)
        action_in_range += int(action_finite and action_range)

    modality_timestamps: dict[str, list[tuple[float, float, int]]] = defaultdict(list)
    for frame in frames:
        if frame.state_timestamp is not None and _finite(frame.state_timestamp):
            modality_timestamps["observation.state"].append((frame.timestamp, float(frame.state_timestamp), frame.frame_index))
        if frame.action_timestamp is not None and _finite(frame.action_timestamp):
            modality_timestamps["action"].append((frame.timestamp, float(frame.action_timestamp), frame.frame_index))
        for camera, sample in frame.cameras.items():
            if sample.present and sample.timestamp is not None and _finite(sample.timestamp):
                modality_timestamps[camera].append((frame.timestamp, float(sample.timestamp), frame.frame_index))

    expected_modalities = ["observation.state", "action", *sorted(expected_cameras)]
    sync_metrics: dict[str, Any] = {}
    sync_components: list[float] = []
    for modality in expected_modalities:
        samples = modality_timestamps.get(modality, [])
        coverage = len(samples) / frame_count
        offsets_ms = [(observed - reference) * 1000.0 for reference, observed, _ in samples]
        median_offset = _median(offsets_ms)
        p95_offset = _percentile([abs(value) for value in offsets_ms], 0.95)
        drift = (max(offsets_ms) - min(offsets_ms)) if offsets_ms else math.inf
        sync_metrics[modality] = {
            "coverage": coverage,
            "median_offset_ms": median_offset if offsets_ms else None,
            "p95_absolute_offset_ms": p95_offset if offsets_ms else None,
            "drift_ms": drift if offsets_ms else None,
        }
        if coverage < thresholds.minimum_modality_coverage:
            diagnostics.append(
                Diagnostic(
                    "modality_coverage",
                    "error",
                    "modality coverage is below the configured minimum",
                    episode_index=episode_index,
                    modality=modality,
                    value=_round(coverage),
                    threshold=thresholds.minimum_modality_coverage,
                )
            )
        if offsets_ms and abs(median_offset) > thresholds.sync_offset_ms:
            diagnostics.append(
                Diagnostic(
                    "sync_offset",
                    "error",
                    "median modality timestamp offset exceeds the configured limit",
                    episode_index=episode_index,
                    modality=modality,
                    value=_round(median_offset),
                    threshold=thresholds.sync_offset_ms,
                )
            )
        if offsets_ms and drift > thresholds.sync_drift_ms:
            diagnostics.append(
                Diagnostic(
                    "sync_drift",
                    "error",
                    "modality clock drift exceeds the configured limit",
                    episode_index=episode_index,
                    modality=modality,
                    value=_round(drift),
                    threshold=thresholds.sync_drift_ms,
                )
            )
        coverage_component = min(1.0, coverage / thresholds.minimum_modality_coverage)
        offset_component = 0.0 if not offsets_ms else max(0.0, 1.0 - abs(median_offset) / max(1e-9, thresholds.sync_offset_ms * 2.0))
        drift_component = 0.0 if not offsets_ms else max(0.0, 1.0 - drift / max(1e-9, thresholds.sync_drift_ms * 2.0))
        sync_components.append(100.0 * (0.5 * coverage_component + 0.3 * offset_component + 0.2 * drift_component))

    camera_total = 0
    decode_good = 0
    luma_observed = 0
    texture_observed = 0
    occlusion_observed = 0
    nonblack = 0
    nonoccluded = 0
    texture_good = 0
    signal_values: list[float] = []
    for frame in frames:
        for camera in expected_cameras:
            camera_total += 1
            sample = frame.cameras.get(camera)
            if sample is None or not sample.present:
                diagnostics.append(
                    Diagnostic("missing_camera_frame", "error", "camera sample is absent", episode_index, frame.frame_index, camera)
                )
                continue
            if not sample.decode_ok:
                diagnostics.append(
                    Diagnostic("corrupt_camera_frame", "error", "camera sample did not decode", episode_index, frame.frame_index, camera)
                )
                continue
            decode_good += 1
            if sample.mean_luma is not None:
                luma_observed += 1
                is_black = sample.mean_luma <= thresholds.black_luma_max
                if is_black:
                    diagnostics.append(
                        Diagnostic(
                            "black_frame",
                            "error",
                            "camera frame mean luminance is below the black-frame threshold",
                            episode_index,
                            frame.frame_index,
                            camera,
                            value=sample.mean_luma,
                            threshold=thresholds.black_luma_max,
                        )
                    )
                else:
                    nonblack += 1
            if sample.luma_stddev is not None:
                texture_observed += 1
                is_low_texture = sample.luma_stddev <= thresholds.low_texture_stddev_max
                if is_low_texture:
                    diagnostics.append(
                        Diagnostic(
                            "low_texture_frame",
                            "warning",
                            "camera frame has very low luminance variation (occlusion/corruption proxy)",
                            episode_index,
                            frame.frame_index,
                            camera,
                            value=sample.luma_stddev,
                            threshold=thresholds.low_texture_stddev_max,
                        )
                    )
                else:
                    texture_good += 1
                if math.isfinite(sample.luma_stddev):
                    signal_values.append(sample.luma_stddev)
            if sample.occlusion_ratio is not None:
                occlusion_observed += 1
                is_occluded = sample.occlusion_ratio >= thresholds.occlusion_ratio_min
                if is_occluded:
                    diagnostics.append(
                        Diagnostic(
                            "occluded_frame",
                            "error",
                            "camera frame occlusion/saturation proxy exceeds the configured threshold",
                            episode_index,
                            frame.frame_index,
                            camera,
                            value=sample.occlusion_ratio,
                            threshold=thresholds.occlusion_ratio_min,
                        )
                    )
                else:
                    nonoccluded += 1

    continuity = frame_steps_good / interval_count if interval_count else 1.0
    monotonicity = monotonic_timestamps / interval_count if interval_count else 1.0
    fps_stability = fps_intervals_good / interval_count if interval_count else 1.0
    temporal_score = 100.0 * (0.40 * continuity + 0.30 * monotonicity + 0.30 * fps_stability)

    structure_penalty = 0.0
    structure_penalty += 20.0 if expected_length is not None and expected_length != frame_count else 0.0
    structure_penalty += min(25.0, gap_frames * 3.0 + duplicate_indices * 5.0)
    structure_penalty += min(25.0, sum(1 for item in diagnostics if item.code in {"row_episode_mismatch", "invalid_timestamp"}) * 5.0)
    structure_score = _clamp_score(100.0 - structure_penalty)

    vector_denominator = max(1, frame_count * 2)
    vector_valid_ratio = (state_valid + action_valid) / vector_denominator
    vector_range_ratio = (state_in_range + action_in_range) / vector_denominator
    if camera_total:
        decode_ratio = decode_good / camera_total
        # Unmeasured content is not assumed healthy. Sampling therefore lowers
        # confidence/score without generating false per-frame fault diagnoses.
        nonblack_ratio = nonblack / camera_total
        nonoccluded_ratio = nonoccluded / camera_total
        texture_ratio = texture_good / camera_total
        luma_coverage = luma_observed / camera_total
        texture_coverage = texture_observed / camera_total
        occlusion_coverage = occlusion_observed / camera_total
    else:
        decode_ratio = nonblack_ratio = nonoccluded_ratio = texture_ratio = 0.0
        luma_coverage = texture_coverage = occlusion_coverage = 0.0
    content_score = 100.0 * (
        0.30 * vector_valid_ratio
        + 0.20 * vector_range_ratio
        + 0.20 * decode_ratio
        + 0.10 * nonblack_ratio
        + 0.10 * nonoccluded_ratio
        + 0.10 * texture_ratio
    )
    sync_score = statistics.mean(sync_components) if sync_components else 0.0
    subscores = {
        "structure": _clamp_score(structure_score),
        "temporal": _clamp_score(temporal_score),
        "synchronization": _clamp_score(sync_score),
        "content": _clamp_score(content_score),
    }
    quality_score = (
        0.20 * subscores["structure"]
        + 0.25 * subscores["temporal"]
        + 0.25 * subscores["synchronization"]
        + 0.30 * subscores["content"]
    )
    coverage_score = 100.0 * statistics.mean(
        [metric["coverage"] for metric in sync_metrics.values()] or [0.0]
    )
    if signal_values:
        richness = min(100.0, 10.0 * math.log1p(statistics.mean(signal_values)))
    else:
        richness = 0.0
    task_indices = {frame.task_index for frame in frames if frame.task_index is not None}
    task_signal = 100.0 if task_indices else 0.0
    error_frames = {
        item.frame_index
        for item in diagnostics
        if item.severity == "error" and item.frame_index is not None
    }
    usable_frame_ratio = max(0.0, 1.0 - len(error_frames) / max(1, frame_count))
    value_score = _clamp_score(
        0.65 * quality_score
        + 0.15 * coverage_score
        + 0.10 * richness
        + 0.05 * task_signal
        + 0.05 * (100.0 * usable_frame_ratio)
    )

    metrics = {
        "expected_fps": fps,
        "expected_interval_s": expected_dt,
        "frame_continuity_ratio": continuity,
        "timestamp_monotonicity_ratio": monotonicity,
        "fps_stability_ratio": fps_stability,
        "interval_median_s": _median(intervals),
        "interval_p95_s": _percentile(intervals, 0.95),
        "missing_frame_count": gap_frames,
        "duplicate_frame_count": duplicate_indices,
        "state_valid_ratio": state_valid / frame_count,
        "action_valid_ratio": action_valid / frame_count,
        "state_in_range_ratio": state_in_range / frame_count,
        "action_in_range_ratio": action_in_range / frame_count,
        "camera_decode_ratio": decode_ratio,
        "camera_nonblack_ratio": nonblack_ratio,
        "camera_nonoccluded_ratio": nonoccluded_ratio,
        "camera_texture_ratio": texture_ratio,
        "camera_content_metric_coverage": {
            "mean_luma": luma_coverage,
            "luma_stddev": texture_coverage,
            "occlusion_ratio": occlusion_coverage,
        },
        "synchronization": sync_metrics,
        "task_indices": sorted(task_indices),
        "signal_richness": richness,
        "usable_frame_ratio": usable_frame_ratio,
    }
    return EpisodeResult(
        episode_index=episode_index,
        frame_count=frame_count,
        diagnostics=diagnostics,
        metrics=metrics,
        subscores=subscores,
        quality_score=_clamp_score(quality_score),
        value_score=value_score,
    )
