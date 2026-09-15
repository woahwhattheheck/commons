from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from .core import EpisodeReport, Finding, ReferenceProfile, analyze_episode, fit_reference, score_findings, write_reports

REFERENCE_ROLE = "ORGANIZER_CLEAN_REFERENCE"
SCAN_ROLE = "ORGANIZER_TEST"
REFERENCE_VERSION = "wuhu-dataset-reference/v2"


@dataclass(frozen=True)
class SourceFile:
    episode_index: int
    relative_path: str
    sha256: str
    bytes: int

    def as_dict(self) -> dict[str, Any]:
        return {"episode_index": self.episode_index, "relative_path": self.relative_path, "sha256": self.sha256, "bytes": self.bytes}

    @staticmethod
    def from_dict(value: Mapping[str, Any]) -> "SourceFile":
        row = SourceFile(int(value["episode_index"]), str(value["relative_path"]), str(value["sha256"]), int(value["bytes"]))
        if row.episode_index < 0 or not row.relative_path or row.bytes < 0:
            raise ValueError("invalid source-file manifest entry")
        if not _valid_sha256(row.sha256):
            raise ValueError("invalid source-file sha256")
        return row


@dataclass(frozen=True)
class DatasetReference:
    version: str
    source_role: str
    dataset_contract_sha256: str
    dataset_manifest_sha256: str
    source_manifest_sha256: str
    selected_episodes: tuple[int, ...]
    required_features: tuple[str, ...]
    source_files: tuple[SourceFile, ...]
    profile: ReferenceProfile

    def _manifest_payload(self) -> dict[str, Any]:
        return {
            "source_role": self.source_role,
            "dataset_contract_sha256": self.dataset_contract_sha256,
            "dataset_manifest_sha256": self.dataset_manifest_sha256,
            "selected_episodes": list(self.selected_episodes),
            "required_features": list(self.required_features),
            "source_files": [row.as_dict() for row in self.source_files],
        }

    def as_dict(self) -> dict[str, Any]:
        return {"version": self.version, **self._manifest_payload(), "source_manifest_sha256": self.source_manifest_sha256, "profile": self.profile.as_dict()}

    def provenance_dict(self) -> dict[str, Any]:
        return {"version": self.version, **self._manifest_payload(), "source_manifest_sha256": self.source_manifest_sha256}

    @staticmethod
    def from_dict(value: Mapping[str, Any]) -> "DatasetReference":
        if value.get("version") != REFERENCE_VERSION:
            raise ValueError("unbound/unsupported reference profile; regenerate with the profile command")
        role = str(value.get("source_role", ""))
        if role != REFERENCE_ROLE:
            raise ValueError(f"reference source_role must be {REFERENCE_ROLE}")
        episodes = tuple(int(v) for v in value.get("selected_episodes", []))
        if not episodes or episodes != tuple(sorted(set(episodes))) or any(v < 0 for v in episodes):
            raise ValueError("reference selected_episodes must be a non-empty sorted unique list")
        required = tuple(str(v) for v in value.get("required_features", []))
        if not required or required != tuple(sorted(set(required))):
            raise ValueError("reference required_features must be a non-empty sorted unique list")
        files = tuple(SourceFile.from_dict(row) for row in value.get("source_files", []))
        if len(files) != len(episodes) or tuple(row.episode_index for row in files) != episodes:
            raise ValueError("reference source-file episode manifest mismatch")
        contract = str(value.get("dataset_contract_sha256", ""))
        dataset_manifest = str(value.get("dataset_manifest_sha256", ""))
        manifest = str(value.get("source_manifest_sha256", ""))
        if not _valid_sha256(contract) or not _valid_sha256(dataset_manifest) or not _valid_sha256(manifest):
            raise ValueError("invalid reference provenance digest")
        profile = ReferenceProfile.from_dict(value["profile"])
        ref = DatasetReference(REFERENCE_VERSION, role, contract, dataset_manifest, manifest, episodes, required, files, profile)
        expected = _digest_json(ref._manifest_payload())
        if not hmac.compare_digest(expected, manifest):
            raise ValueError("reference source manifest digest mismatch")
        if tuple(sorted(profile.features)) != required:
            raise ValueError("reference profile features do not match provenance")
        return ref


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _digest_json(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
    if version not in {"v2.0", "v2.1"}:
        raise ValueError(f"expected LeRobot v2.x dataset, got codebase_version={version!r}")
    return data


def _episode_indices(root: Path, info: dict[str, Any]) -> list[int]:
    path = root / "meta" / "episodes.jsonl"
    if path.exists():
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(int(json.loads(line)["episode_index"]))
        return sorted(set(out))
    return list(range(int(info.get("total_episodes", 0))))


def _format_path(template: str, episode: int, chunks_size: int, *, video_key: str | None = None) -> str:
    vals = {"episode_index": episode, "episode_chunk": episode // max(chunks_size, 1), "chunk_index": episode // max(chunks_size, 1), "video_key": video_key or ""}
    return template.format(**vals)


def _contract(root: Path):
    info = _read_info(root)
    chunks = int(info.get("chunks_size", 1000) or 1000)
    features = info.get("features", {}) or {}
    data_t = str(info.get("data_path", "data/chunk-{episode_chunk:03d}/episode_{episode_index:06d}.parquet"))
    video_t = str(info.get("video_path", "videos/chunk-{episode_chunk:03d}/{video_key}/episode_{episode_index:06d}.mp4"))
    shapes = {k: v.get("shape", []) for k, v in features.items() if isinstance(v, dict) and v.get("dtype") not in {"video", "image"}}
    numeric = [k for k in features if k in {"action", "observation.state"} or k.startswith("action.") or k.startswith("observation.state.")]
    videos = [k for k, v in features.items() if isinstance(v, dict) and v.get("dtype") == "video"]
    return info, chunks, data_t, video_t, shapes, numeric, videos


def _select_episodes(root: Path, info: dict[str, Any], episodes: Sequence[int] | None) -> list[int]:
    available = _episode_indices(root, info)
    selected = available if episodes is None else [int(v) for v in episodes]
    if not selected:
        raise ValueError("no episodes selected")
    if len(selected) != len(set(selected)):
        raise ValueError("duplicate episode ids are not allowed")
    selected = sorted(selected)
    unknown = sorted(set(selected) - set(available))
    if unknown:
        raise ValueError(f"selected episodes not declared by dataset metadata: {unknown}")
    return selected


def _dataset_contract_digest(root: Path) -> str:
    rows = []
    for rel in ("meta/info.json", "meta/episodes.jsonl"):
        path = root / rel
        if path.exists():
            rows.append({"path": rel, "bytes": path.stat().st_size, "sha256": _sha256_file(path)})
    if not rows:
        raise ValueError("dataset metadata manifest is empty")
    return _digest_json(rows)


def _dataset_manifest_digest(root: Path, info: dict[str, Any], chunks: int, data_t: str) -> str:
    episode_files = []
    for ep in _episode_indices(root, info):
        rel = _format_path(data_t, ep, chunks)
        path = root / rel
        row: dict[str, Any] = {"episode_index": ep, "relative_path": rel}
        if path.exists():
            row.update({"bytes": path.stat().st_size, "sha256": _sha256_file(path)})
        else:
            row["missing"] = True
        episode_files.append(row)
    if not episode_files:
        raise ValueError("dataset episode manifest is empty")
    return _digest_json({"metadata_contract_sha256": _dataset_contract_digest(root), "episode_files": episode_files})


def _source_file(root: Path, path: Path, episode_index: int) -> SourceFile:
    resolved = path.resolve()
    try:
        rel = resolved.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"episode source escapes dataset root: {resolved}") from exc
    return SourceFile(episode_index, rel, _sha256_file(resolved), resolved.stat().st_size)


def _strict_numeric_matrix(series: pd.Series, *, feature: str, episode_index: int) -> np.ndarray:
    rows = []
    width = None
    for value in series.tolist():
        try:
            arr = np.asarray(value, dtype=np.float64).reshape(-1)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"clean-reference episode {episode_index} feature {feature} is non-numeric") from exc
        if width is None:
            width = arr.size
        if arr.size != width:
            raise ValueError(f"clean-reference episode {episode_index} feature {feature} has inconsistent width")
        rows.append(arr)
    if not rows:
        raise ValueError(f"clean-reference episode {episode_index} feature {feature} is empty")
    matrix = np.vstack(rows)
    if not np.all(np.isfinite(matrix)):
        raise ValueError(f"clean-reference episode {episode_index} feature {feature} contains non-finite values")
    return matrix


def _validate_reference_frame(df: pd.DataFrame, *, episode_index: int, required_features: Sequence[str], shapes: Mapping[str, Sequence[int]]) -> None:
    if df.empty:
        raise ValueError(f"clean-reference episode {episode_index} is empty")
    for key in required_features:
        if key not in df.columns:
            raise ValueError(f"clean-reference episode {episode_index} missing required modeled feature {key}")
        matrix = _strict_numeric_matrix(df[key], feature=key, episode_index=episode_index)
        shape = shapes.get(key) or []
        if shape:
            expected = int(np.prod(shape))
            if matrix.shape[1] != expected:
                raise ValueError(f"clean-reference episode {episode_index} feature {key} width={matrix.shape[1]} expected={expected}")


def fit_dataset_reference(root: Path, *, episodes: list[int] | None = None, source_role: str = REFERENCE_ROLE) -> DatasetReference:
    if source_role != REFERENCE_ROLE:
        raise ValueError(f"reference source_role must be exactly {REFERENCE_ROLE}")
    _require_parquet_engine()
    root = root.resolve()
    info, chunks, data_t, _, shapes, numeric, _ = _contract(root)
    required = tuple(sorted(numeric))
    if not required:
        raise ValueError("dataset declares no modeled state/action features")
    selected = _select_episodes(root, info, episodes)
    frames = []
    source_files = []
    for ep in selected:
        path = root / _format_path(data_t, ep, chunks)
        if not path.exists():
            raise FileNotFoundError(path)
        df = pd.read_parquet(path)
        _validate_reference_frame(df, episode_index=ep, required_features=required, shapes=shapes)
        frames.append(df)
        source_files.append(_source_file(root, path, ep))
    profile = fit_reference(frames, required)
    if tuple(sorted(profile.features)) != required:
        raise ValueError("reference profile omitted one or more required modeled features")
    source_rows = tuple(source_files)
    contract_digest = _dataset_contract_digest(root)
    dataset_manifest_digest = _dataset_manifest_digest(root, info, chunks, data_t)
    skeleton = {
        "source_role": REFERENCE_ROLE,
        "dataset_contract_sha256": contract_digest,
        "dataset_manifest_sha256": dataset_manifest_digest,
        "selected_episodes": selected,
        "required_features": list(required),
        "source_files": [row.as_dict() for row in source_rows],
    }
    manifest_digest = _digest_json(skeleton)
    return DatasetReference(REFERENCE_VERSION, REFERENCE_ROLE, contract_digest, dataset_manifest_digest, manifest_digest, tuple(selected), required, source_rows, profile)


def _scan_source_files(root: Path, selected: Sequence[int], data_t: str, chunks: int) -> tuple[SourceFile, ...]:
    rows = []
    for ep in selected:
        path = root / _format_path(data_t, ep, chunks)
        if path.exists():
            rows.append(_source_file(root, path, ep))
    return tuple(rows)


def _assert_no_reference_overlap(reference: DatasetReference, scan_dataset_manifest_sha256: str, scan_files: Sequence[SourceFile]) -> None:
    if hmac.compare_digest(reference.dataset_manifest_sha256, scan_dataset_manifest_sha256):
        raise ValueError("reference/test dataset identity overlap detected; refusing competition score for the same declared corpus")
    overlap = sorted({row.sha256 for row in reference.source_files} & {row.sha256 for row in scan_files})
    if overlap:
        raise ValueError(f"reference/test source overlap detected; refusing competition score for {len(overlap)} shared episode file digest(s)")


def scan_dataset(root: Path, out_dir: Path, *, episodes: list[int] | None = None, reference: DatasetReference | None = None) -> list[EpisodeReport]:
    _require_parquet_engine()
    root = root.resolve()
    info, chunks, data_t, video_t, shapes, numeric, videos = _contract(root)
    fps = float(info.get("fps", 0) or 0)
    if fps <= 0:
        raise ValueError("meta/info.json must declare positive fps")
    selected = _select_episodes(root, info, episodes)
    scan_files = _scan_source_files(root, selected, data_t, chunks)
    scan_dataset_manifest_sha256 = _dataset_manifest_digest(root, info, chunks, data_t)
    if reference is not None:
        if reference.source_role != REFERENCE_ROLE:
            raise ValueError("reference provenance has invalid source role")
        _assert_no_reference_overlap(reference, scan_dataset_manifest_sha256, scan_files)

    reports = []
    for ep in selected:
        path = root / _format_path(data_t, ep, chunks)
        if not path.exists():
            finding = Finding("structure", "MISSING_PARQUET", "high", ep, None, None, f"missing episode parquet {path}")
            q, v, c = score_findings([finding])
            reports.append(EpisodeReport(ep, 0, None, [finding], q, v, c))
            continue
        df = pd.read_parquet(path)
        video_paths = [root / _format_path(video_t, ep, chunks, video_key=k) for k in videos]
        if reference is not None:
            missing = [key for key in reference.required_features if key not in df.columns]
            if missing:
                finding = Finding("structure", "REFERENCE_FEATURE_MISSING", "high", ep, None, None, f"test episode missing reference-modeled feature(s): {', '.join(missing)}")
                q, v, c = score_findings([finding])
                reports.append(EpisodeReport(ep, len(df), None, [finding], q, v, c))
                continue
        reports.append(analyze_episode(df, ep, fps, expected_shapes=shapes, numeric_keys=numeric, video_paths=video_paths, reference=reference.profile if reference is not None else None))

    write_reports(reports, out_dir)
    report_path = out_dir / "report.json"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["scan_provenance"] = {
        "role": SCAN_ROLE,
        "dataset_contract_sha256": _dataset_contract_digest(root),
        "dataset_manifest_sha256": scan_dataset_manifest_sha256,
        "selected_episodes": selected,
        "source_files": [row.as_dict() for row in scan_files],
        "reference": reference.provenance_dict() if reference is not None else None,
    }
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return reports
