from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable
import torch
from .model import DaTNet3d
from .preprocess import PreprocessConfig

BUNDLE_SCHEMA = "dat-parkinsons-public-carrier/v1"


def sha256_file(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""): h.update(block)
    return h.hexdigest()


def canonical_json(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def save_bundle(out_dir: str | Path, state_dicts: Iterable[dict], *, temperatures: Iterable[float], preprocess: PreprocessConfig, metadata: dict) -> dict:
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True); members = []; temperatures = [float(v) for v in temperatures]
    for index, state in enumerate(state_dicts):
        path = out / f"fold_{index}.pt"; torch.save(state, path); members.append({"path": path.name, "sha256": sha256_file(path)})
    manifest = {"schema": BUNDLE_SCHEMA, "architecture": "DaTNet3d(width=16,dropout=0.20)", "preprocess": asdict(preprocess), "temperatures": temperatures, "members": members, "metadata": metadata}
    (out / "manifest.json").write_bytes(canonical_json(manifest)); return manifest


def load_bundle(bundle_dir: str | Path, device: str):
    root = Path(bundle_dir); raw = json.loads((root / "manifest.json").read_text())
    if raw.get("schema") != BUNDLE_SCHEMA: raise ValueError("unsupported model bundle schema")
    members = raw.get("members"); temps = raw.get("temperatures")
    if not isinstance(members, list) or not members or not isinstance(temps, list) or len(temps) != len(members): raise ValueError("malformed ensemble manifest")
    allowed = {"shape", "lower_q", "upper_q", "foreground_fraction", "margin"}; cfg_raw = raw.get("preprocess")
    if not isinstance(cfg_raw, dict) or set(cfg_raw) != allowed: raise ValueError("malformed preprocessing contract")
    cfg_raw["shape"] = tuple(cfg_raw["shape"]); config = PreprocessConfig(**cfg_raw); models = []
    for member in members:
        name = member.get("path"); expected = member.get("sha256")
        if not isinstance(name, str) or Path(name).name != name: raise ValueError("unsafe model member path")
        path = root / name
        if sha256_file(path) != expected: raise ValueError(f"model member digest mismatch: {name}")
        model = DaTNet3d().to(device); state = torch.load(path, map_location=device, weights_only=True); model.load_state_dict(state, strict=True); model.eval(); models.append(model)
    return models, [float(t) for t in temps], config, raw
