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

from . import probe_manifest as _previous
from .probe_manifest import *

def _import_pyarrow() -> Any | None:
    try:
        import pyarrow.parquet as parquet  # type: ignore
    except (ImportError, OSError):
        return None
    return parquet


def probe_parquet(context: DatasetContext, config: Config, sink: IssueSink) -> tuple[dict[int, list[dict[str, Any]]], Capability]:
    parquet = _import_pyarrow()
    if parquet is None:
        sink.add(
            "CAPABILITY.PYARROW_UNAVAILABLE",
            "critical",
            "structure",
            "Parquet frame inspection was not performed because pyarrow is unavailable",
            evidence={"install": "python -m pip install pyarrow or supply --probe-jsonl"},
        )
        return {}, Capability("parquet", "unavailable", "auto", "pyarrow unavailable", 0)
    frames: dict[int, list[dict[str, Any]]] = {}
    complete = True
    record_count = 0
    for episode_index, episode in sorted(context.episodes.items()):
        path = context.data_paths.get(episode_index)
        if path is None or not path.is_file():
            complete = False
            continue
        rel = path.relative_to(context.root).as_posix()
        try:
            pf = parquet.ParquetFile(path)
            names = set(pf.schema_arrow.names)
            missing = [name for name in REQUIRED_FRAME_COLUMNS if name not in names]
            if missing:
                sink.add(
                    "STRUCTURE.PARQUET_COLUMNS_MISSING",
                    "critical",
                    "structure",
                    "Parquet episode is missing required columns",
                    episode_index=episode_index,
                    path=rel,
                    evidence={"missing": missing, "columns": sorted(names)},
                )
                complete = False
            available = [name for name in REQUIRED_FRAME_COLUMNS if name in names]
            if "index" in names:
                available.append("index")
            rows: list[dict[str, Any]] = []
            for batch in pf.iter_batches(batch_size=4096, columns=available):
                rows.extend(batch.to_pylist())
            frames[episode_index] = rows
            record_count += len(rows)
        except Exception as exc:  # pyarrow raises several implementation-specific exceptions
            sink.add(
                "CONTENT.PARQUET_CORRUPT",
                "critical",
                "content",
                "Parquet episode could not be decoded",
                episode_index=episode_index,
                path=rel,
                evidence={"error_type": type(exc).__name__, "message": str(exc)[:300]},
            )
            complete = False
    state = "complete" if complete and len(frames) == len(context.episodes) else "partial"
    return frames, Capability("parquet", state, "auto-pyarrow", "Parquet rows decoded with pyarrow", record_count)


def _parse_fraction(value: Any) -> float | None:
    if not isinstance(value, str) or not value or value in {"0/0", "N/A"}:
        return None
    try:
        if "/" in value:
            numerator, denominator = value.split("/", 1)
            denominator_value = float(denominator)
            if denominator_value == 0:
                return None
            result = float(numerator) / denominator_value
        else:
            result = float(value)
    except (ValueError, ZeroDivisionError):
        return None
    return result if math.isfinite(result) else None


def _run_readonly(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise QualityError(f"read-only probe timed out: {command[0]}") from exc
    except OSError as exc:
        raise QualityError(f"cannot execute read-only probe {command[0]}: {exc}") from exc


def _probe_one_video(path: Path, rel: str, episode_index: int, camera: str, config: Config) -> VideoSummary:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        raise QualityError("ffprobe is unavailable")
    proc = _run_readonly(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-count_frames",
            "-show_entries",
            "stream=nb_read_frames,nb_frames,avg_frame_rate,r_frame_rate,duration,start_time,width,height",
            "-of",
            "json",
            str(path),
        ],
        config.subprocess_timeout_seconds,
    )
    if proc.returncode != 0:
        return VideoSummary(
            episode_index,
            camera,
            rel,
            None,
            None,
            None,
            None,
            None,
            None,
            None,
            False,
            0,
            None,
            None,
            None,
            None,
        )
    try:
        payload = json.loads(proc.stdout.decode("utf-8"), parse_constant=_reject_constant)
        stream = payload["streams"][0]
    except (UnicodeError, json.JSONDecodeError, KeyError, IndexError, TypeError, QualityError):
        stream = {}
    frame_count: int | None = None
    for key in ("nb_read_frames", "nb_frames"):
        value = stream.get(key)
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            continue
        if parsed >= 0:
            frame_count = parsed
            break
    fps = _parse_fraction(stream.get("avg_frame_rate")) or _parse_fraction(stream.get("r_frame_rate"))
    start = _optional_stream_float(stream.get("start_time"))
    duration = _optional_stream_float(stream.get("duration"))
    if start is None:
        start = 0.0
    end = start + duration if duration is not None else None
    width = _optional_stream_int(stream.get("width"))
    height = _optional_stream_int(stream.get("height"))
    visual = _sample_video_luma(path, duration, config)
    return VideoSummary(
        episode_index=episode_index,
        camera=camera,
        path=rel,
        frame_count=frame_count,
        fps=fps,
        start_timestamp=start,
        end_timestamp=end,
        duration=duration,
        width=width,
        height=height,
        decode_ok=(shutil.which("ffmpeg") is None or visual[0] > 0),
        sample_count=visual[0],
        black_ratio=visual[1],
        flat_ratio=visual[2],
        mean_luma=visual[3],
        mean_luma_std=visual[4],
    )


def _optional_stream_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _optional_stream_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 else None


def _sample_video_luma(path: Path, duration: float | None, config: Config) -> tuple[int, float | None, float | None, float | None, float | None]:
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None or config.visual_samples <= 0:
        return (0, None, None, None, None)
    sample_rate = 1.0
    if duration is not None and duration > 0:
        sample_rate = max(0.05, min(5.0, config.visual_samples / duration))
    proc = _run_readonly(
        [
            ffmpeg,
            "-v",
            "error",
            "-i",
            str(path),
            "-vf",
            f"fps={sample_rate:.9f},scale=64:64:flags=area,format=gray",
            "-frames:v",
            str(config.visual_samples),
            "-f",
            "rawvideo",
            "-pix_fmt",
            "gray",
            "-",
        ],
        config.subprocess_timeout_seconds,
    )
    if proc.returncode != 0:
        return (0, None, None, None, None)
    frame_size = 64 * 64
    frame_count = len(proc.stdout) // frame_size
    if frame_count <= 0:
        return (0, None, None, None, None)
    means: list[float] = []
    stds: list[float] = []
    black = 0
    flat = 0
    for index in range(frame_count):
        frame = proc.stdout[index * frame_size : (index + 1) * frame_size]
        mean = sum(frame) / frame_size
        variance = sum((pixel - mean) ** 2 for pixel in frame) / frame_size
        std = math.sqrt(variance)
        means.append(mean)
        stds.append(std)
        if mean <= config.black_luma_threshold or mean >= config.white_luma_threshold:
            black += 1
        if std <= config.flat_luma_std_threshold:
            flat += 1
    return (
        frame_count,
        black / frame_count,
        flat / frame_count,
        statistics.fmean(means),
        statistics.fmean(stds),
    )


def probe_videos(context: DatasetContext, config: Config, sink: IssueSink) -> tuple[dict[tuple[int, str], VideoSummary], dict[str, Capability]]:
    ffprobe = shutil.which("ffprobe")
    ffmpeg = shutil.which("ffmpeg")
    if ffprobe is None:
        sink.add(
            "CAPABILITY.FFPROBE_UNAVAILABLE",
            "critical",
            "content",
            "video container inspection was not performed because ffprobe is unavailable",
        )
        return {}, {
            "video_container": Capability("video_container", "unavailable", "auto", "ffprobe unavailable", 0),
            "visual_content": Capability("visual_content", "unavailable", "auto", "ffmpeg unavailable", 0),
        }
    videos: dict[tuple[int, str], VideoSummary] = {}
    container_complete = True
    visual_complete = ffmpeg is not None
    for key, path in sorted(context.video_paths.items()):
        if not path.is_file():
            container_complete = False
            visual_complete = False
            continue
        episode_index, camera = key
        rel = path.relative_to(context.root).as_posix()
        try:
            summary = _probe_one_video(path, rel, episode_index, camera, config)
        except QualityError as exc:
            sink.add(
                "CONTENT.VIDEO_PROBE_FAILED",
                "critical",
                "content",
                str(exc),
                episode_index=episode_index,
                modality=camera,
                path=rel,
            )
            container_complete = False
            visual_complete = False
            continue
        videos[key] = summary
        if not summary.decode_ok:
            container_complete = False
            visual_complete = False
        if summary.sample_count <= 0:
            visual_complete = False
    container_state = "complete" if container_complete and len(videos) == len(context.video_paths) else "partial"
    if ffmpeg is None:
        visual_state = "unavailable"
        sink.add(
            "CAPABILITY.FFMPEG_UNAVAILABLE",
            "critical",
            "content",
            "visual black/flat-frame inspection was not performed because ffmpeg is unavailable",
        )
    else:
        visual_state = "complete" if visual_complete and len(videos) == len(context.video_paths) else "partial"
    return videos, {
        "video_container": Capability("video_container", container_state, "auto-ffprobe", "video stream metadata", len(videos)),
        "visual_content": Capability(
            "visual_content",
            visual_state,
            "auto-ffmpeg",
            "64x64 grayscale samples; black/white and low-texture heuristics",
            sum(1 for item in videos.values() if item.sample_count > 0),
        ),
    }


def auto_probe(context: DatasetContext, config: Config, sink: IssueSink) -> ProbeResult:
    frames, parquet_cap = probe_parquet(context, config, sink)
    videos, video_caps = probe_videos(context, config, sink)
    capabilities = {"parquet": parquet_cap, **video_caps}
    return ProbeResult(frames, videos, capabilities, "auto")

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
    'auto_probe'
]
