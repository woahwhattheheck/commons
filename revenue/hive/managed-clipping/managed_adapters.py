from __future__ import annotations
import math
from typing import Any
from managed_common import DEFAULT_FPS, ManagedClippingError

def normalize_kestrel_segments(document: Any) -> list[dict[str, Any]]:
    if isinstance(document, dict) and "document" in document and isinstance(document["document"], dict):
        document = document["document"]
    if isinstance(document, dict):
        segments = document.get("segments", [])
    elif isinstance(document, list):
        segments = document
    else:
        raise ManagedClippingError("transcript input must be a KESTREL document or segment list")
    out: list[dict[str, Any]] = []
    last_end = -1.0
    seen: set[str] = set()
    for idx, row in enumerate(segments):
        if not isinstance(row, dict):
            raise ManagedClippingError(f"segment {idx} is not an object")
        sid = str(row.get("id", f"s{idx+1}"))
        if sid in seen:
            raise ManagedClippingError(f"duplicate segment id: {sid}")
        seen.add(sid)
        start = float(row["start"])
        end = float(row["end"])
        if not (math.isfinite(start) and math.isfinite(end) and 0 <= start < end):
            raise ManagedClippingError(f"invalid segment range: {sid}")
        if start < last_end - 1e-9:
            raise ManagedClippingError("transcript segments overlap or are not chronological")
        last_end = end
        out.append({
            "id": sid,
            "start_ms": int(round(start * 1000)),
            "end_ms": int(round(end * 1000)),
            "speaker": row.get("speaker"),
            "text": str(row.get("text", "")),
            "verified": bool(row.get("verified", False)),
        })
    return out


def normalize_cedar_keeps(raw: Any, fps: float = DEFAULT_FPS) -> list[tuple[int, int]]:
    if isinstance(raw, dict):
        if "kept" in raw:
            rows = raw["kept"]
            intervals = [
                (int(round(float(r["source_start"]) / fps * 1000)),
                 int(round(float(r["source_end"]) / fps * 1000)))
                for r in rows
            ]
        elif "timeline" in raw and isinstance(raw["timeline"], dict) and "kept" in raw["timeline"]:
            return normalize_cedar_keeps(raw["timeline"], fps=fps)
        elif "keep" in raw:
            return normalize_cedar_keeps(raw["keep"], fps=fps)
        else:
            raise ManagedClippingError("CEDAR keep input missing kept/keep rows")
    elif isinstance(raw, list):
        intervals = []
        for pair in raw:
            if not (isinstance(pair, (list, tuple)) and len(pair) == 2):
                raise ManagedClippingError("CEDAR keep ranges must be [start_seconds,end_seconds]")
            intervals.append((int(round(float(pair[0]) * 1000)), int(round(float(pair[1]) * 1000))))
    else:
        raise ManagedClippingError("CEDAR keep input must be a list or timeline object")
    clean: list[tuple[int, int]] = []
    prev_end = -1
    for start, end in intervals:
        if start < 0 or end <= start:
            raise ManagedClippingError("invalid CEDAR keep range")
        if start < prev_end:
            raise ManagedClippingError("CEDAR keep ranges must be chronological and nonoverlapping")
        clean.append((start, end))
        prev_end = end
    return clean


def _point_allowed(mid_ms: int, keeps: list[tuple[int, int]]) -> bool:
    return not keeps or any(start <= mid_ms <= end for start, end in keeps)


def _choose_transcript_moments(
    segments: list[dict[str, Any]], keeps: list[tuple[int, int]], count: int, duration_ms: int
) -> list[dict[str, Any]]:
    eligible = [s for s in segments if _point_allowed((s["start_ms"] + s["end_ms"]) // 2, keeps)]
    if not eligible:
        return []
    if len(eligible) >= count:
        if count == 1:
            picks = [eligible[len(eligible) // 2]]
        else:
            indexes = [round(i * (len(eligible) - 1) / (count - 1)) for i in range(count)]
            picks = [eligible[i] for i in indexes]
    else:
        picks = list(eligible)
        while len(picks) < count:
            picks.extend(eligible[: count - len(picks)])
    moments: list[dict[str, Any]] = []
    for idx, seg in enumerate(picks[:count], 1):
        start = max(0, seg["start_ms"] - 150)
        end = min(duration_ms, seg["end_ms"] + 150)
        if end - start < 350:
            end = min(duration_ms, start + 350)
        moments.append({
            "id": f"clip-{idx:03d}",
            "source_filename": None,
            "start_ms": start,
            "end_ms": end,
            "caption": seg["text"],
            "hook": seg["text"][:100],
            "crop": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
            "transcript_refs": [seg["id"]],
            "enabled": True,
            "renders": [],
        })
    return moments


def _choose_even_moments(keeps: list[tuple[int, int]], count: int, duration_ms: int) -> list[dict[str, Any]]:
    available = keeps or [(0, duration_ms)]
    total = sum(end - start for start, end in available)
    if total < count * 250:
        raise ManagedClippingError("source/keep ranges are too short to create distinct clips")
    window = max(350, min(2200, total // max(count * 2, 1)))
    moments = []
    for i in range(count):
        target = int((i + 0.5) * total / count)
        remaining = target
        chosen = available[-1]
        for span in available:
            span_len = span[1] - span[0]
            if remaining <= span_len:
                chosen = span
                break
            remaining -= span_len
        center = min(chosen[1] - 1, chosen[0] + max(1, remaining))
        start = max(chosen[0], center - window // 2)
        end = min(chosen[1], start + window)
        start = max(chosen[0], end - window)
        moments.append({
            "id": f"clip-{i+1:03d}",
            "source_filename": None,
            "start_ms": start,
            "end_ms": end,
            "caption": f"Clip {i+1}",
            "hook": f"Moment {i+1}",
            "crop": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0},
            "transcript_refs": [],
            "enabled": True,
            "renders": [],
        })
    return moments

