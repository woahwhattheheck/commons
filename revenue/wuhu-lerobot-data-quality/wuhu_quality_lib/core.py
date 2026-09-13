"""Core types and deterministic parsing for the LeRobot v2.1 inspector."""

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

TOOL_VERSION = "1.0.0"
REPORT_SCHEMA = "wuhu.lerobot-quality/v1"
PROBE_SCHEMA = "wuhu.lerobot-probe/v1"
EXPECTED_CODEBASE_VERSION = "v2.1"
REQUIRED_METADATA = (
    "meta/info.json",
    "meta/episodes.jsonl",
    "meta/tasks.jsonl",
    "meta/episodes_stats.jsonl",
)
REQUIRED_FRAME_COLUMNS = (
    "timestamp",
    "frame_index",
    "episode_index",
    "task_index",
    "observation.state",
    "action",
)
SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2, "critical": 3}
SEVERITY_PENALTY = {"info": 0.0, "warning": 8.0, "error": 18.0, "critical": 35.0}
DIMENSIONS = ("structure", "temporal", "synchronization", "content")
CAPABILITY_STATES = {"complete", "partial", "unavailable", "failed"}
NONFINITE_TOKENS = {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}


class QualityError(ValueError):
    """Stable user-facing input or report error."""


class DuplicateKeyError(QualityError):
    pass


@dataclass(frozen=True)
class Config:
    expected_cameras: int = 3
    expected_vector_dim: int = 20
    state_abs_limit: float = 1_000_000.0
    action_abs_limit: float = 1_000_000.0
    fps_relative_tolerance: float = 0.10
    timestamp_jitter_relative: float = 0.25
    timestamp_gap_factor: float = 1.80
    sync_offset_seconds: float = 0.10
    sync_drift_seconds: float = 0.20
    black_luma_threshold: float = 8.0
    white_luma_threshold: float = 247.0
    flat_luma_std_threshold: float = 4.0
    black_ratio_threshold: float = 0.05
    flat_ratio_threshold: float = 0.20
    visual_samples: int = 12
    subprocess_timeout_seconds: int = 45
    hash_sample_bytes: int = 65_536


@dataclass(frozen=True)
class Issue:
    code: str
    severity: str
    dimension: str
    reason: str
    episode_index: int | None = None
    frame_start: int | None = None
    frame_end: int | None = None
    modality: str | None = None
    path: str | None = None
    occurrences: int = 1
    evidence: Mapping[str, Any] = dataclasses.field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.severity not in SEVERITY_ORDER:
            raise ValueError(f"invalid severity: {self.severity}")
        if self.dimension not in DIMENSIONS:
            raise ValueError(f"invalid dimension: {self.dimension}")

    def sort_key(self) -> tuple[Any, ...]:
        return (
            -SEVERITY_ORDER[self.severity],
            self.episode_index if self.episode_index is not None else -1,
            self.frame_start if self.frame_start is not None else -1,
            self.modality or "",
            self.code,
            self.path or "",
            self.reason,
        )

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "dimension": self.dimension,
            "reason": self.reason,
            "occurrences": self.occurrences,
        }
        if self.episode_index is not None:
            payload["episode_index"] = self.episode_index
        if self.frame_start is not None:
            payload["frame_start"] = self.frame_start
        if self.frame_end is not None:
            payload["frame_end"] = self.frame_end
        if self.modality is not None:
            payload["modality"] = self.modality
        if self.path is not None:
            payload["path"] = self.path
        if self.evidence:
            payload["evidence"] = canonicalize(dict(self.evidence))
        return payload


@dataclass
class _Span:
    code: str
    severity: str
    dimension: str
    reason: str
    episode_index: int
    modality: str | None
    path: str | None
    frame_start: int
    frame_end: int
    occurrences: int
    evidence: dict[str, Any]


class IssueSink:
    """Collect issues and compress repeated per-frame anomalies into spans."""

    def __init__(self) -> None:
        self._issues: list[Issue] = []
        self._spans: dict[tuple[Any, ...], _Span] = {}

    def add(
        self,
        code: str,
        severity: str,
        dimension: str,
        reason: str,
        *,
        episode_index: int | None = None,
        frame_start: int | None = None,
        frame_end: int | None = None,
        modality: str | None = None,
        path: str | None = None,
        occurrences: int = 1,
        evidence: Mapping[str, Any] | None = None,
    ) -> None:
        self._issues.append(
            Issue(
                code=code,
                severity=severity,
                dimension=dimension,
                reason=reason,
                episode_index=episode_index,
                frame_start=frame_start,
                frame_end=frame_end,
                modality=modality,
                path=path,
                occurrences=occurrences,
                evidence=canonicalize(dict(evidence or {})),
            )
        )

    def frame(
        self,
        code: str,
        severity: str,
        dimension: str,
        reason: str,
        *,
        episode_index: int,
        frame_index: int,
        modality: str | None = None,
        path: str | None = None,
        evidence: Mapping[str, Any] | None = None,
    ) -> None:
        key = (code, severity, dimension, reason, episode_index, modality, path)
        data = canonicalize(dict(evidence or {}))
        span = self._spans.get(key)
        if span is not None and frame_index == span.frame_end + 1:
            span.frame_end = frame_index
            span.occurrences += 1
            # Preserve the first sample and the latest sample without making the
            # report grow linearly with bad frames.
            if data:
                span.evidence["last"] = data
            return
        if span is not None:
            self._flush_span(key)
        self._spans[key] = _Span(
            code=code,
            severity=severity,
            dimension=dimension,
            reason=reason,
            episode_index=episode_index,
            modality=modality,
            path=path,
            frame_start=frame_index,
            frame_end=frame_index,
            occurrences=1,
            evidence={"first": data} if data else {},
        )

    def _flush_span(self, key: tuple[Any, ...]) -> None:
        span = self._spans.pop(key)
        self._issues.append(
            Issue(
                code=span.code,
                severity=span.severity,
                dimension=span.dimension,
                reason=span.reason,
                episode_index=span.episode_index,
                frame_start=span.frame_start,
                frame_end=span.frame_end,
                modality=span.modality,
                path=span.path,
                occurrences=span.occurrences,
                evidence=canonicalize(span.evidence),
            )
        )

    def finish(self) -> list[Issue]:
        for key in list(self._spans):
            self._flush_span(key)
        return sorted(self._issues, key=Issue.sort_key)


@dataclass(frozen=True)
class Capability:
    name: str
    state: str
    source: str
    detail: str
    records: int = 0

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class EpisodeMeta:
    episode_index: int
    length: int
    tasks: tuple[str, ...]
    raw: Mapping[str, Any]


@dataclass
class DatasetContext:
    root: Path
    info: dict[str, Any]
    episodes: dict[int, EpisodeMeta]
    tasks: dict[int, str]
    episode_stats: dict[int, dict[str, Any]]
    camera_keys: tuple[str, ...]
    data_paths: dict[int, Path]
    video_paths: dict[tuple[int, str], Path]
    metadata_paths: tuple[Path, ...]
    fingerprint: str = ""
    fingerprint_entries: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class FrameSummary:
    episode_index: int
    rows: int = 0
    first_timestamp: float | None = None
    last_timestamp: float | None = None
    median_dt: float | None = None
    jitter_ratio: float | None = None
    state_motion_score: float = 0.0
    action_motion_score: float = 0.0
    static_action_ratio: float = 1.0
    state_varying_dimensions: int = 0
    action_varying_dimensions: int = 0

    def to_dict(self) -> dict[str, Any]:
        return canonicalize(dataclasses.asdict(self))


@dataclass
class VideoSummary:
    episode_index: int
    camera: str
    path: str
    frame_count: int | None
    fps: float | None
    start_timestamp: float | None
    end_timestamp: float | None
    duration: float | None
    width: int | None
    height: int | None
    decode_ok: bool
    sample_count: int
    black_ratio: float | None
    flat_ratio: float | None
    mean_luma: float | None
    mean_luma_std: float | None

    def to_dict(self) -> dict[str, Any]:
        return canonicalize(dataclasses.asdict(self))


@dataclass
class ProbeResult:
    frames: dict[int, list[dict[str, Any]]]
    videos: dict[tuple[int, str], VideoSummary]
    capabilities: dict[str, Capability]
    source: str

def canonicalize(value: Any) -> Any:
    """Return a JSON-safe, deterministically rounded structure."""
    if dataclasses.is_dataclass(value):
        return canonicalize(dataclasses.asdict(value))
    if isinstance(value, Mapping):
        return {str(k): canonicalize(value[k]) for k in sorted(value, key=lambda item: str(item))}
    if isinstance(value, (list, tuple)):
        return [canonicalize(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            return str(value)
        rounded = round(value, 9)
        return 0.0 if rounded == 0 else rounded
    if isinstance(value, Path):
        return value.as_posix()
    return value


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(canonicalize(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    return None

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
    'canonicalize',
    'canonical_json_bytes',
    '_is_int',
    '_finite_number',
]
