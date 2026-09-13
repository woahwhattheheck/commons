from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pandas as pd

from .core import EpisodeReport, Finding, ReferenceProfile, analyze_episode, fit_reference, score_findings, write_reports


def _require_parquet_engine() -> None:
    try:
        import pyarrow  # noqa: F401
        return
    except ImportError:
        try:
            import fastparquet  # noqa: F401
            return
        except ImportError as exc:
            raise RuntimeError("Parquet support required: install pyarrow (preferred) or fastparquet") from exc


def _read_info(root: Path) -> dict[str, Any]:
    path = root / "meta" / "info.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    version = str(data.get("codebase_version", ""))
    if version not in {"v2.0", "v2.1"}: raise ValueError(f"expected LeRobot v2.x dataset, got codebase_version={version!r}")
    return data


def _episode_indices(root: Path, info: dict[str, Any]) -> list[int]:
    path=root/"meta"/"episodes.jsonl"
    if path.exists():
        out=[]
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip(): out.append(int(json.loads(line)["episode_index"]))
        return sorted(set(out))
    return list(range(int(info.get("total_episodes",0))))


def _format_path(template: str, episode: int, chunks_size: int, *, video_key: str | None = None) -> str:
    vals={"episode_index":episode,"episode_chunk":episode//max(chunks_size,1),"chunk_index":episode//max(chunks_size,1),"video_key":video_key or ""}
    return template.format(**vals)


def _contract(root: Path):
    info=_read_info(root); chunks=int(info.get("chunks_size",1000) or 1000); features=info.get("features",{}) or {}
    data_t=str(info.get("data_path","data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet"))
    video_t=str(info.get("video_path","videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4"))
    shapes={k:v.get("shape",[]) for k,v in features.items() if isinstance(v,dict) and v.get("dtype") not in {"video","image"}}
    numeric=[k for k in features if k in {"action","observation.state"} or k.startswith("action.") or k.startswith("observation.state.")]
    videos=[k for k,v in features.items() if isinstance(v,dict) and v.get("dtype")=="video"]
    return info,chunks,data_t,video_t,shapes,numeric,videos


def fit_dataset_reference(root: Path, *, episodes: list[int] | None = None) -> ReferenceProfile:
    _require_parquet_engine(); root=root.resolve(); info,chunks,data_t,_,_,numeric,_=_contract(root)
    selected=episodes if episodes is not None else _episode_indices(root,info); frames=[]
    for ep in selected:
        path=root/_format_path(data_t,ep,chunks)
        if not path.exists(): raise FileNotFoundError(path)
        frames.append(pd.read_parquet(path))
    return fit_reference(frames,numeric)


def scan_dataset(root: Path, out_dir: Path, *, episodes: list[int] | None = None, reference: ReferenceProfile | None = None) -> list[EpisodeReport]:
    _require_parquet_engine(); root=root.resolve(); info,chunks,data_t,video_t,shapes,numeric,videos=_contract(root)
    fps=float(info.get("fps",0) or 0)
    if fps<=0: raise ValueError("meta/info.json must declare positive fps")
    selected=episodes if episodes is not None else _episode_indices(root,info); reports=[]
    for ep in selected:
        path=root/_format_path(data_t,ep,chunks)
        if not path.exists():
            finding=Finding("structure","MISSING_PARQUET","high",ep,None,None,f"missing episode parquet {path}")
            q,v,c=score_findings([finding]); reports.append(EpisodeReport(ep,0,None,[finding],q,v,c)); continue
        df=pd.read_parquet(path); video_paths=[root/_format_path(video_t,ep,chunks,video_key=k) for k in videos]
        reports.append(analyze_episode(df,ep,fps,expected_shapes=shapes,numeric_keys=numeric,video_paths=video_paths,reference=reference))
    write_reports(reports,out_dir); return reports
