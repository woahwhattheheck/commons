#!/usr/bin/env python3
"""Managed clipping service workspace.

A small, file-backed project format for turning one source recording into a
rerunnable set of clips. The module intentionally owns only moment selection,
clip rendering, captions, and handoff files. It can consume external timeline
or transcript exports by normalizing their common millisecond fields, but does
not fork the upstream editor or podcast workspace.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

PROJECT_VERSION = 1
DEFAULT_WIDTH = 320
DEFAULT_HEIGHT = 180


class ClipError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(cmd, text=True, capture_output=True, check=True)
    except FileNotFoundError as exc:
        raise ClipError(f"required executable is unavailable: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise ClipError(f"command failed ({cmd[0]}): {detail}") from exc


def probe_duration_ms(path: Path) -> int:
    result = _run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ])
    try:
        return int(round(float(result.stdout.strip()) * 1000))
    except ValueError as exc:
        raise ClipError(f"ffprobe returned an invalid duration for {path}") from exc


def probe_playable(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size <= 0:
        return False
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
        text=True, capture_output=True,
    )
    return result.returncode == 0 and "video" in result.stdout


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def _dump_project(project_path: Path, project: dict[str, Any]) -> None:
    _atomic_write_text(project_path, json.dumps(project, indent=2, ensure_ascii=False) + "\n")


def _resolve_source(project_path: Path, project: dict[str, Any]) -> Path:
    raw = project["source"]["path"]
    path = Path(raw)
    if not path.is_absolute():
        path = project_path.parent / path
    return path.resolve()


def load_project(project_path: Path, *, verify_source: bool = True) -> dict[str, Any]:
    try:
        project = json.loads(project_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ClipError(f"cannot read project: {project_path}") from exc
    if project.get("version") != PROJECT_VERSION:
        raise ClipError("unsupported project version")
    clips = project.get("clips")
    if not isinstance(clips, list) or not clips:
        raise ClipError("project must contain clips")
    ids = [clip.get("id") for clip in clips if isinstance(clip, dict)]
    if len(ids) != len(clips) or len(set(ids)) != len(ids):
        raise ClipError("clip ids must be present and unique")
    source = _resolve_source(project_path, project)
    if not source.is_file():
        raise ClipError(f"source recording is missing: {source}")
    if verify_source:
        expected = project["source"].get("sha256")
        if expected and sha256_file(source) != expected:
            raise ClipError("source recording hash changed; refusing unsynchronized render")
    return project


def normalize_external_moments(payload: Any) -> list[dict[str, Any]]:
    """Normalize common timeline/transcript export shapes.

    Accepted list locations: payload itself, payload['clips'], payload['moments'],
    payload['segments']. Accepted time keys are start_ms/end_ms or
    start_millis/end_millis. Caption text may be caption/text/transcript.
    This is deliberately a compatibility seam rather than an upstream fork.
    """
    if isinstance(payload, dict):
        for key in ("clips", "moments", "segments"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        raise ClipError("external moments must be a list or contain clips/moments/segments")
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(payload, 1):
        if not isinstance(item, dict):
            raise ClipError(f"external moment {index} is not an object")
        start = item.get("start_ms", item.get("start_millis"))
        end = item.get("end_ms", item.get("end_millis"))
        try:
            start_i, end_i = int(start), int(end)
        except (TypeError, ValueError) as exc:
            raise ClipError(f"external moment {index} lacks integer millisecond bounds") from exc
        caption = item.get("caption", item.get("text", item.get("transcript", "")))
        normalized.append({
            "start_ms": start_i,
            "end_ms": end_i,
            "caption": str(caption),
        })
    return normalized


def _clip_filename(clip_id: str) -> str:
    return f"{clip_id}.mp4"


def _caption_filename(clip_id: str) -> str:
    return f"{clip_id}.srt"


def create_project(source: Path, project_path: Path, moments: list[dict[str, Any]]) -> dict[str, Any]:
    source = source.resolve()
    if not source.is_file():
        raise ClipError(f"source recording is missing: {source}")
    duration = probe_duration_ms(source)
    clips: list[dict[str, Any]] = []
    for index, moment in enumerate(moments, 1):
        start = int(moment["start_ms"])
        end = int(moment["end_ms"])
        if start < 0 or end <= start or end > duration:
            raise ClipError(f"clip {index} has invalid bounds {start}..{end} for {duration}ms source")
        clip_id = str(moment.get("id") or f"clip-{index:02d}")
        crop = moment.get("crop") or {"x": 0, "y": 0, "w": DEFAULT_WIDTH, "h": DEFAULT_HEIGHT}
        clips.append({
            "id": clip_id,
            "source_filename": source.name,
            "start_ms": start,
            "end_ms": end,
            "caption": str(moment.get("caption") or f"Moment {index}"),
            "hook_variant": str(moment.get("hook_variant") or f"Hook {index:02d}"),
            "crop": {k: int(crop[k]) for k in ("x", "y", "w", "h")},
            "output": _clip_filename(clip_id),
            "caption_file": _caption_filename(clip_id),
            "revision": 1,
        })
    try:
        rel = os.path.relpath(source, project_path.parent.resolve())
    except ValueError:
        rel = str(source)
    project = {
        "version": PROJECT_VERSION,
        "label": "SELF-AUTHORED SYNTHETIC DEMONSTRATION" if source.name.startswith("demo_source") else "SOURCE PROVIDED TO THIS WORKSPACE",
        "source": {
            "filename": source.name,
            "path": rel,
            "duration_ms": duration,
            "sha256": sha256_file(source),
        },
        "clips": clips,
    }
    _dump_project(project_path, project)
    return project


def edit_clip(project_path: Path, clip_id: str, *, start_ms: int | None = None,
              end_ms: int | None = None, caption: str | None = None,
              crop: dict[str, int] | None = None) -> dict[str, Any]:
    project = load_project(project_path)
    target = next((clip for clip in project["clips"] if clip["id"] == clip_id), None)
    if target is None:
        raise ClipError(f"unknown clip id: {clip_id}")
    new_start = int(start_ms if start_ms is not None else target["start_ms"])
    new_end = int(end_ms if end_ms is not None else target["end_ms"])
    duration = int(project["source"]["duration_ms"])
    if new_start < 0 or new_end <= new_start or new_end > duration:
        raise ClipError("edited clip bounds are outside the source")
    target["start_ms"] = new_start
    target["end_ms"] = new_end
    if caption is not None:
        target["caption"] = caption
    if crop is not None:
        target["crop"] = {k: int(crop[k]) for k in ("x", "y", "w", "h")}
    target["revision"] = int(target.get("revision", 1)) + 1
    _dump_project(project_path, project)
    return project


def _srt_timestamp(ms: int) -> str:
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def _write_caption(path: Path, clip: dict[str, Any]) -> None:
    duration = int(clip["end_ms"]) - int(clip["start_ms"])
    text = f"1\n00:00:00,000 --> {_srt_timestamp(duration)}\n{clip['caption']}\n"
    _atomic_write_text(path, text)


def render_clip(project_path: Path, clip_id: str, output_dir: Path) -> Path:
    project = load_project(project_path)
    source = _resolve_source(project_path, project)
    clip = next((c for c in project["clips"] if c["id"] == clip_id), None)
    if clip is None:
        raise ClipError(f"unknown clip id: {clip_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / clip["output"]
    caption = output_dir / clip["caption_file"]
    crop = clip["crop"]
    if crop["w"] <= 0 or crop["h"] <= 0 or crop["x"] < 0 or crop["y"] < 0:
        raise ClipError("crop values must be positive dimensions and non-negative offsets")
    duration_ms = int(clip["end_ms"]) - int(clip["start_ms"])
    fd, temp_name = tempfile.mkstemp(prefix=clip_id + ".", suffix=".mp4", dir=str(output_dir))
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        vf = f"crop={crop['w']}:{crop['h']}:{crop['x']}:{crop['y']},scale={DEFAULT_WIDTH}:{DEFAULT_HEIGHT}"
        _run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-ss", f"{int(clip['start_ms']) / 1000:.3f}",
            "-i", str(source), "-t", f"{duration_ms / 1000:.3f}",
            "-vf", vf, "-an", "-c:v", "libx264", "-preset", "ultrafast",
            "-crf", "38", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            str(temp_path),
        ])
        if not probe_playable(temp_path):
            raise ClipError(f"rendered output is not playable: {clip_id}")
        os.replace(temp_path, output)
        _write_caption(caption, clip)
    finally:
        temp_path.unlink(missing_ok=True)
    return output


def render_project(project_path: Path, output_dir: Path, clip_ids: Iterable[str] | None = None) -> list[Path]:
    project = load_project(project_path)
    wanted = set(clip_ids) if clip_ids is not None else {c["id"] for c in project["clips"]}
    unknown = wanted - {c["id"] for c in project["clips"]}
    if unknown:
        raise ClipError("unknown clip ids: " + ", ".join(sorted(unknown)))
    outputs: list[Path] = []
    for clip in project["clips"]:
        if clip["id"] in wanted:
            outputs.append(render_clip(project_path, clip["id"], output_dir))
    return outputs


def export_handoff(project_path: Path, output_dir: Path, handoff_dir: Path) -> Path:
    project = load_project(project_path)
    handoff_dir.mkdir(parents=True, exist_ok=True)
    csv_path = handoff_dir / "clips.csv"
    fieldnames = [
        "id", "source_filename", "start_ms", "end_ms", "caption", "hook_variant",
        "crop_x", "crop_y", "crop_w", "crop_h", "revision", "output", "caption_file",
    ]
    rows = []
    for clip in project["clips"]:
        video = output_dir / clip["output"]
        caption = output_dir / clip["caption_file"]
        if not probe_playable(video):
            raise ClipError(f"handoff is missing playable output: {clip['id']}")
        if not caption.is_file():
            raise ClipError(f"handoff is missing caption file: {clip['id']}")
        rows.append({
            "id": clip["id"], "source_filename": clip["source_filename"],
            "start_ms": clip["start_ms"], "end_ms": clip["end_ms"],
            "caption": clip["caption"], "hook_variant": clip["hook_variant"],
            "crop_x": clip["crop"]["x"], "crop_y": clip["crop"]["y"],
            "crop_w": clip["crop"]["w"], "crop_h": clip["crop"]["h"],
            "revision": clip["revision"], "output": clip["output"],
            "caption_file": clip["caption_file"],
        })
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    shutil.copy2(project_path, handoff_dir / "project.json")
    bundle = handoff_dir / "managed-clipping-demo-bundle.zip"
    temp_bundle = handoff_dir / (bundle.name + ".tmp")
    with zipfile.ZipFile(temp_bundle, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(handoff_dir / "project.json", "project.json")
        zf.write(csv_path, "clips.csv")
        source = _resolve_source(project_path, project)
        zf.write(source, project["source"]["filename"])
        for clip in project["clips"]:
            zf.write(output_dir / clip["output"], f"clips/{clip['output']}")
            zf.write(output_dir / clip["caption_file"], f"captions/{clip['caption_file']}")
    os.replace(temp_bundle, bundle)
    return bundle


def create_demo_source(path: Path, *, seconds: int = 30) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    _run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i", f"color=c=black:size={DEFAULT_WIDTH}x{DEFAULT_HEIGHT}:rate=2:duration={seconds}",
        "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "45",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(path),
    ])
    if not probe_playable(path):
        raise ClipError("failed to create playable self-authored demo source")
    return path


def demo_moments(count: int = 20) -> list[dict[str, Any]]:
    moments: list[dict[str, Any]] = []
    for i in range(count):
        start = 500 + i * 1200
        end = start + 950
        inset = (i % 4) * 4
        moments.append({
            "id": f"clip-{i + 1:02d}",
            "start_ms": start,
            "end_ms": end,
            "caption": f"Self-authored demo moment {i + 1}: source-synchronized clip.",
            "hook_variant": f"Hook variant {i + 1:02d}",
            "crop": {"x": inset, "y": inset, "w": DEFAULT_WIDTH - inset * 2, "h": DEFAULT_HEIGHT - inset * 2},
        })
    return moments


def build_demo(workspace: Path) -> dict[str, Path]:
    workspace.mkdir(parents=True, exist_ok=True)
    source = create_demo_source(workspace / "demo_source.mp4")
    project_path = workspace / "project.json"
    create_project(source, project_path, demo_moments())
    output_dir = workspace / "renders"
    render_project(project_path, output_dir)
    handoff_dir = workspace / "handoff"
    bundle = export_handoff(project_path, output_dir, handoff_dir)
    return {"source": source, "project": project_path, "outputs": output_dir, "handoff": handoff_dir, "bundle": bundle}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="build the labeled self-authored 20-clip demonstration")
    demo.add_argument("workspace", type=Path)

    init = sub.add_parser("init", help="create a project from source + external moments JSON")
    init.add_argument("--source", type=Path, required=True)
    init.add_argument("--moments", type=Path, required=True)
    init.add_argument("--project", type=Path, required=True)

    render = sub.add_parser("render", help="render all clips or selected clip ids")
    render.add_argument("--project", type=Path, required=True)
    render.add_argument("--output-dir", type=Path, required=True)
    render.add_argument("--clip-id", action="append")

    edit = sub.add_parser("edit", help="edit one clip in the project")
    edit.add_argument("--project", type=Path, required=True)
    edit.add_argument("--clip-id", required=True)
    edit.add_argument("--start-ms", type=int)
    edit.add_argument("--end-ms", type=int)
    edit.add_argument("--caption")

    handoff = sub.add_parser("handoff", help="export CSV/project/captions/videos into a ZIP handoff")
    handoff.add_argument("--project", type=Path, required=True)
    handoff.add_argument("--output-dir", type=Path, required=True)
    handoff.add_argument("--handoff-dir", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.command == "demo":
        paths = build_demo(args.workspace)
        print(json.dumps({k: str(v) for k, v in paths.items()}, indent=2))
        return 0
    if args.command == "init":
        payload = json.loads(args.moments.read_text(encoding="utf-8"))
        moments = normalize_external_moments(payload)
        create_project(args.source, args.project, moments)
        return 0
    if args.command == "render":
        render_project(args.project, args.output_dir, args.clip_id)
        return 0
    if args.command == "edit":
        edit_clip(args.project, args.clip_id, start_ms=args.start_ms, end_ms=args.end_ms, caption=args.caption)
        return 0
    if args.command == "handoff":
        print(export_handoff(args.project, args.output_dir, args.handoff_dir))
        return 0
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
