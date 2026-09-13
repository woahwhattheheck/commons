#!/usr/bin/env python3
"""Shared data model and deterministic report rendering."""
from __future__ import annotations

import html
import json
import math
import statistics
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

VERSION = "0.1.0"
SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2}

@dataclass(frozen=True)
class Thresholds:
    """Transparent analyzer thresholds.

    Bounds are deliberately conservative defaults. Challenge-specific physical
    limits should be supplied explicitly once the organizer's authoritative
    ranges are available.
    """

    expected_state_dim: int = 20
    expected_action_dim: int = 20
    state_abs_max: float = 1_000_000.0
    action_abs_max: float = 1_000_000.0
    fps_jitter_fraction: float = 0.20
    sync_offset_ms: float = 25.0
    sync_drift_ms: float = 50.0
    minimum_modality_coverage: float = 0.98
    black_luma_max: float = 8.0
    low_texture_stddev_max: float = 4.0
    occlusion_ratio_min: float = 0.85

    def __post_init__(self) -> None:
        positive = {
            "expected_state_dim": self.expected_state_dim,
            "expected_action_dim": self.expected_action_dim,
            "state_abs_max": self.state_abs_max,
            "action_abs_max": self.action_abs_max,
            "fps_jitter_fraction": self.fps_jitter_fraction,
            "sync_offset_ms": self.sync_offset_ms,
            "sync_drift_ms": self.sync_drift_ms,
        }
        for name, value in positive.items():
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        for name in ("minimum_modality_coverage", "occlusion_ratio_min"):
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")


@dataclass(frozen=True)
class Diagnostic:
    code: str
    severity: str
    message: str
    episode_index: int | None = None
    frame_index: int | None = None
    modality: str | None = None
    value: Any = None
    threshold: Any = None

    def __post_init__(self) -> None:
        if self.severity not in SEVERITY_ORDER:
            raise ValueError(f"invalid severity: {self.severity}")

    def sort_key(self) -> tuple[Any, ...]:
        return (
            -SEVERITY_ORDER[self.severity],
            self.episode_index if self.episode_index is not None else -1,
            self.frame_index if self.frame_index is not None else -1,
            self.modality or "",
            self.code,
            self.message,
            json.dumps(self.value, sort_keys=True, default=str),
        )


@dataclass(frozen=True)
class ModalitySample:
    timestamp: float | None
    present: bool = True
    decode_ok: bool = True
    mean_luma: float | None = None
    luma_stddev: float | None = None
    occlusion_ratio: float | None = None


@dataclass(frozen=True)
class FrameRecord:
    episode_index: int
    frame_index: int
    timestamp: float
    task_index: int | None
    state: tuple[Any, ...] | None
    action: tuple[Any, ...] | None
    state_timestamp: float | None
    action_timestamp: float | None
    cameras: Mapping[str, ModalitySample]


@dataclass
class EpisodeResult:
    episode_index: int
    frame_count: int
    diagnostics: list[Diagnostic]
    metrics: dict[str, Any]
    subscores: dict[str, float]
    quality_score: float
    value_score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_index": self.episode_index,
            "frame_count": self.frame_count,
            "diagnostics": [_canonicalize(asdict(item)) for item in sorted(self.diagnostics, key=Diagnostic.sort_key)],
            "metrics": _canonicalize(self.metrics),
            "subscores": {key: _round(value) for key, value in sorted(self.subscores.items())},
            "quality_score": _round(self.quality_score),
            "value_score": _round(self.value_score),
        }


@dataclass
class DatasetReport:
    version: str
    root: str
    input_fingerprint: str
    complete: bool
    metadata: dict[str, Any]
    thresholds: Thresholds
    diagnostics: list[Diagnostic]
    episodes: list[EpisodeResult]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "lerobot-v21-quality-report/v1",
            "tool_version": self.version,
            "root": self.root,
            "input_fingerprint": self.input_fingerprint,
            "complete": self.complete,
            "metadata": _canonicalize(self.metadata),
            "thresholds": _canonicalize(asdict(self.thresholds)),
            "diagnostics": [_canonicalize(asdict(item)) for item in sorted(self.diagnostics, key=Diagnostic.sort_key)],
            "episodes": [episode.to_dict() for episode in sorted(self.episodes, key=lambda item: item.episode_index)],
            "summary": _canonicalize(self.summary),
        }

    def json_text(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"

    def markdown_text(self) -> str:
        data = self.to_dict()
        summary = data["summary"]
        lines = [
            "# LeRobot v2.1 Data Quality Report",
            "",
            f"- Complete scan: **{'yes' if data['complete'] else 'no'}**",
            f"- Episodes: **{summary['episode_count']}**",
            f"- Frames: **{summary['frame_count']}**",
            f"- Overall quality: **{summary['quality_score']:.2f}/100**",
            f"- Overall training value: **{summary['value_score']:.2f}/100**",
            f"- Input fingerprint: `{data['input_fingerprint']}`",
            "",
            "## Dataset diagnostics",
            "",
        ]
        diagnostics = data["diagnostics"]
        if diagnostics:
            lines.extend(_diagnostic_markdown(diagnostics))
        else:
            lines.append("No dataset-level diagnostics.")
        lines.extend(["", "## Episodes", ""])
        for episode in data["episodes"]:
            lines.extend(
                [
                    f"### Episode {episode['episode_index']}",
                    "",
                    f"Frames: **{episode['frame_count']}** · Quality: **{episode['quality_score']:.2f}** · Value: **{episode['value_score']:.2f}**",
                    "",
                    "| Subscore | Score |",
                    "|---|---:|",
                ]
            )
            for key, value in episode["subscores"].items():
                lines.append(f"| {key} | {value:.2f} |")
            lines.extend(["", "Diagnostics:", ""])
            if episode["diagnostics"]:
                lines.extend(_diagnostic_markdown(episode["diagnostics"]))
            else:
                lines.append("- None")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def html_text(self) -> str:
        markdown = self.markdown_text()
        # Deliberately simple, dependency-free HTML. Preserve every report line
        # and escape user-controlled metadata/diagnostic text.
        body = "\n".join(f"<div>{html.escape(line)}</div>" for line in markdown.splitlines())
        return (
            "<!doctype html>\n"
            '<html lang="en"><head><meta charset="utf-8">'
            "<title>LeRobot v2.1 Data Quality Report</title>"
            "<style>body{font-family:system-ui,sans-serif;max-width:1100px;margin:2rem auto;padding:0 1rem;}"
            "div{white-space:pre-wrap;margin:.15rem 0;}code{font-family:ui-monospace,monospace;}</style>"
            f"</head><body>{body}</body></html>\n"
        )


def _diagnostic_markdown(items: Sequence[Mapping[str, Any]]) -> list[str]:
    result: list[str] = []
    for item in items:
        location: list[str] = []
        if item.get("episode_index") is not None:
            location.append(f"episode={item['episode_index']}")
        if item.get("frame_index") is not None:
            location.append(f"frame={item['frame_index']}")
        if item.get("modality"):
            location.append(f"modality={item['modality']}")
        where = f" ({', '.join(location)})" if location else ""
        result.append(f"- **{item['severity'].upper()} `{item['code']}`**{where}: {item['message']}")
    return result


def _round(value: float) -> float:
    return round(float(value) + 0.0, 4)


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _canonicalize(value[key]) for key in sorted(value, key=lambda item: str(item))}
    if isinstance(value, (list, tuple)):
        return [_canonicalize(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            return str(value)
        return _round(value)
    return value


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


def _coerce_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if math.isfinite(value) and value.is_integer() else None
    if isinstance(value, str):
        text = value.strip()
        if text and (text.isdigit() or (text[0] in "+-" and text[1:].isdigit())):
            return int(text)
    return None


def _finite(value: Any) -> bool:
    number = _coerce_float(value)
    return number is not None and math.isfinite(number)


def _clamp_score(value: float) -> float:
    return max(0.0, min(100.0, value))


def _median(values: Sequence[float]) -> float:
    return statistics.median(values) if values else 0.0


def _percentile(values: Sequence[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, math.ceil(fraction * len(ordered)) - 1))
    return ordered[index]
