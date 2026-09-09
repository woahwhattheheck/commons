#!/usr/bin/env python3
"""Bounded public entrypoint for the Kaggriculture replay differential.

The analysis implementation lives in ``replay_program_diff_core``. This facade
owns all file ingestion and replay-wire compatibility: it admits raw and gzip
evidence under hard byte limits, treats engine-valid empty action rows as inert,
and aligns Kaggle's result-row actions with the observation transition they
actually produced.
"""
from __future__ import annotations

import gzip
import hashlib
import io
import os
import stat
from pathlib import Path
from typing import Any, Mapping, Sequence

import replay_program_diff_core as _core
from replay_program_diff_core import *  # noqa: F401,F403 - public analysis API

MAX_COMPRESSED_BYTES = 512 * 1024 * 1024
MAX_DECOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024

_ORIGINAL_NORMALIZE_ORDER = _core._normalize_order
_ORIGINAL_ANALYZE_REPLAY = _core.analyze_replay


def _normalize_replay_order(row: Any, label: str) -> tuple[str, list[Any]]:
    """Admit an empty unit/market row as the engine's inert placeholder.

    Titan route tapes intentionally retain internal ``[]`` rows. Kaggriculture's
    permissive action object passes them to the interpreter, where they are
    silent no-ops.  Their exact bytes remain represented by ``action_sha256``;
    they simply do not become economic events.
    """
    if isinstance(row, list) and not row:
        return "BLANK", []
    return _ORIGINAL_NORMALIZE_ORDER(row, label)


# Core action walkers resolve this name dynamically in their defining module.
_core._normalize_order = _normalize_replay_order


def _has_framework_result_row_orientation(replay: Mapping[str, Any]) -> bool:
    """Recognize native kaggle-environments replay rows without guessing.

    ``Environment.step`` attaches an action to the current state, runs the
    interpreter, and appends that post-interpreter state.  Native rows therefore
    carry observation.step == row index and row ``k``'s action produced row
    ``k`` from observation ``k-1``.  Unversioned synthetic fixtures lacking the
    framework step counter retain the core's legacy source-row convention.
    """
    steps = replay.get("steps")
    if not isinstance(steps, list) or len(steps) < 2:
        return False
    for index, row in enumerate(steps):
        if not isinstance(row, list) or not row or not isinstance(row[0], dict):
            return False
        observation = row[0].get("observation")
        if not isinstance(observation, dict):
            return False
        step = observation.get("step")
        if isinstance(step, bool) or not isinstance(step, int) or step != index:
            return False
    return True


def _align_framework_result_row_actions(replay: Mapping[str, Any]) -> dict[str, Any]:
    """Project native result-row actions onto source rows for the core walker."""
    steps = replay["steps"]
    aligned_steps: list[list[Any]] = []
    for source_index, row in enumerate(steps):
        aligned_row: list[Any] = []
        for player, state in enumerate(row):
            if not isinstance(state, dict):
                aligned_row.append(state)
                continue
            aligned_state = dict(state)
            if source_index + 1 < len(steps):
                next_row = steps[source_index + 1]
                if isinstance(next_row, list) and player < len(next_row):
                    next_state = next_row[player]
                    if isinstance(next_state, dict):
                        aligned_state["action"] = next_state.get("action")
            aligned_row.append(aligned_state)
        aligned_steps.append(aligned_row)
    aligned = dict(replay)
    aligned["steps"] = aligned_steps
    return aligned


def analyze_replay(
    replay: Mapping[str, Any],
    provenance: Mapping[str, Any],
    envelope_path: Sequence[str],
    player_a: int,
    player_b: int,
) -> dict[str, Any]:
    """Analyze one replay with explicit wire-orientation custody."""
    native_orientation = _has_framework_result_row_orientation(replay)
    admitted = _align_framework_result_row_actions(replay) if native_orientation else replay
    report = _ORIGINAL_ANALYZE_REPLAY(
        admitted,
        provenance,
        envelope_path,
        player_a,
        player_b,
    )
    if native_orientation:
        # Source identity is over the evidence bytes/object, never the aligned
        # internal projection used only by the transition walker.
        report["source"]["canonical_replay_sha256"] = _core._sha256(
            _core._canonical_json_bytes(replay)
        )
        report["source"]["replay_action_orientation"] = (
            "result_row_action_k_maps_observation_k_minus_1_to_k"
        )
        report["comparison"]["action_row_offset"] = 1
    else:
        report["source"]["replay_action_orientation"] = (
            "legacy_source_row_unversioned_fixture"
        )
        report["comparison"]["action_row_offset"] = 0
    return report


# The core CLI resolves this name in its own module; bind the public adapter.
_core.analyze_replay = analyze_replay


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _bounded_source_read(path: Path) -> bytes:
    """Read one regular file without ever consuming more than the input cap.

    ``Path.read_bytes()`` would allocate an arbitrarily large local input before
    the size check. Opening first, checking the descriptor, and reading at most
    ``MAX_COMPRESSED_BYTES + 1`` makes the compressed/source ceiling an
    admission boundary rather than only a post-allocation assertion.
    """
    try:
        with path.open("rb") as stream:
            descriptor = os.fstat(stream.fileno())
            if not stat.S_ISREG(descriptor.st_mode):
                raise ReplayError("input must resolve to a regular file")
            if descriptor.st_size > MAX_COMPRESSED_BYTES:
                raise ReplayError(
                    "input exceeds compressed-size limit: "
                    f"{descriptor.st_size} > {MAX_COMPRESSED_BYTES}"
                )
            raw = stream.read(MAX_COMPRESSED_BYTES + 1)
    except ReplayError:
        raise
    except OSError as exc:
        raise ReplayError(f"could not read replay input: {exc}") from exc
    if len(raw) > MAX_COMPRESSED_BYTES:
        raise ReplayError(
            "input exceeds compressed-size limit: "
            f"> {MAX_COMPRESSED_BYTES}"
        )
    return raw


def _bounded_gzip_decompress(raw: bytes) -> bytes:
    chunks: list[bytes] = []
    total = 0
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw), mode="rb") as stream:
            while True:
                remaining = MAX_DECOMPRESSED_BYTES + 1 - total
                chunk = stream.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > MAX_DECOMPRESSED_BYTES:
                    raise ReplayError(
                        "input exceeds decompressed-size limit: "
                        f"> {MAX_DECOMPRESSED_BYTES}"
                    )
    except ReplayError:
        raise
    except (EOFError, OSError) as exc:
        raise ReplayError(f"invalid gzip stream: {exc}") from exc
    return b"".join(chunks)


def _read_input(path: Path) -> tuple[Any, dict[str, Any]]:
    raw = _bounded_source_read(path)
    is_gzip = raw.startswith(b"\x1f\x8b")
    decoded = _bounded_gzip_decompress(raw) if is_gzip else raw
    if len(decoded) > MAX_DECOMPRESSED_BYTES:
        raise ReplayError(
            f"input exceeds decompressed-size limit: {len(decoded)} > {MAX_DECOMPRESSED_BYTES}"
        )
    try:
        text = decoded.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ReplayError(f"input is not strict UTF-8: {exc}") from exc
    payload = strict_json_loads(text, str(path))
    return payload, {
        "path": str(path),
        "compressed": is_gzip,
        "input_bytes": len(raw),
        "decoded_bytes": len(decoded),
        "input_sha256": _sha256(raw),
        "decoded_sha256": _sha256(decoded),
    }


def main(argv: Sequence[str] | None = None) -> int:
    # The core's CLI resolves this symbol in its own module. Bind it only to
    # this bounded implementation; parser, analysis, and rendering stay exact.
    _core._read_input = _read_input
    return _core.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
