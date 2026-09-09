# SPDX-License-Identifier: Apache-2.0
"""Shared strict evidence constants, hashing, and executable-root custody."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Mapping

OPERATION = "titan-v3-v1v2-seller-factorial-20260909-01"
ARMS = ("control", "carry_095", "force_end", "both")
NONCONTROL = ARMS[1:]
EXPECTED_SEEDS = (2611092201, 2611092203, 2611092205, 2611092207)
EXPECTED_OPPONENTS = ("arlene", "apex", "public_bt12", "v1")
EXPECTED_CELLS_PER_ARM = len(EXPECTED_SEEDS) * len(EXPECTED_OPPONENTS) * 2
EXPECTED_STEPS = 719
EXPECTED_EPISODE_STEPS = 720
EXPECTED_ACTION_COUNT = 719
EXPECTED_AGENT_RNG_SEED = 20260909
EXPECTED_EVALUATOR_SOURCE_BLOB = "077feb2208b6e0c1727835eb4f8089709bf67f3b"
EXPECTED_EVALUATOR_REPAIR_OPERATION = "titan-v2-target-domain-ablation-20260909-sol-bulwark-01"
EXPECTED_EVALUATOR_RAW_OLD_AFTER = (0, 1, 0)
EXPECTED_EVALUATOR_EMBEDDED_OLD = (0, 1, 0)
EXPECTED_ENGINE_REF = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
EXPECTED_ENGINE_FILES = ("kaggriculture.py", "kaggriculture.json", "utils.py")
EXPECTED_METHOD = (
    "Official interpreter with explicit driver; not hosted Kaggle scoring. "
    "Decision timings are child-reported; RPC deadlines are parent-enforced. "
    "Resource samples combine child rusage, available Linux procfs, and final "
    "wait4 usage when supported; actor provenance records the actual sources. "
    "Entry-file hashes do not cover arbitrary agent dependencies."
)
EXPECTED_LIMITS = {
    "action_rpc_seconds": 1.0,
    "startup_seconds": 15.0,
    "game_seconds_between_steps": 180.0,
    "remaining_overage_time": 0,
}
EXPECTED_INTERVENTIONS: Mapping[str, tuple[float, bool]] = {
    "control": (1.0, False),
    "carry_095": (0.95, False),
    "force_end": (1.0, True),
    "both": (0.95, True),
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX32 = re.compile(r"^[0-9a-f]{32}$")


class AdmissionError(ValueError):
    """The retained evidence cannot support a factorial screen verdict."""


def _reject_constant(value: str) -> None:
    raise AdmissionError(f"non-finite JSON token: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AdmissionError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    try:
        return json.loads(
            Path(path).read_text(encoding="utf-8"),
            parse_constant=_reject_constant,
            object_pairs_hook=_unique_object,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AdmissionError(f"cannot read strict JSON {path}: {type(exc).__name__}: {exc}") from exc


def atomic_json(path: Path, value: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
    ).hexdigest()


def _is_int(value: Any) -> bool:
    return type(value) is int


def _is_number(value: Any) -> bool:
    return type(value) in (int, float) and math.isfinite(float(value))


def _require_hex(value: Any, pattern: re.Pattern[str], label: str) -> str:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise AdmissionError(f"{label} must be lowercase hexadecimal")
    return value


def _ignored(relative: Path) -> bool:
    return (
        any(part in {"__pycache__", ".pytest_cache"} for part in relative.parts)
        or relative.suffix in {".pyc", ".pyo"}
    )


def tree_receipt(root: Path, *, exclude: frozenset[str] = frozenset()) -> dict[str, Any]:
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise AdmissionError(f"closure root is not a directory: {root}")
    entries: list[dict[str, Any]] = []
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*"), key=lambda p: p.relative_to(root).as_posix()):
        relative_path = path.relative_to(root)
        relative = relative_path.as_posix()
        if path.is_symlink():
            raise AdmissionError(f"symlink forbidden in closure: {relative}")
        if path.is_dir() or relative in exclude or _ignored(relative_path):
            continue
        if not path.is_file():
            raise AdmissionError(f"non-regular closure member: {relative}")
        content_sha = sha256_file(path)
        size = path.stat().st_size
        digest.update(relative.encode("utf-8") + b"\0" + bytes.fromhex(content_sha))
        entries.append({"path": relative, "bytes": size, "sha256": content_sha})
    return {
        "schema_version": 1,
        "files": len(entries),
        "bytes": sum(int(row["bytes"]) for row in entries),
        "sha256": digest.hexdigest(),
        "entries": entries,
    }


def expected_keys() -> set[tuple[str, int, int]]:
    return {
        (opponent, seed, seat)
        for opponent in EXPECTED_OPPONENTS
        for seed in EXPECTED_SEEDS
        for seat in (0, 1)
    }

