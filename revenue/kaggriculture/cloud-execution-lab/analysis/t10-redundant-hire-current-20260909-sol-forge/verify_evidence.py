#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Verify the exact-current TITAN T10 redundant-hire evidence packet.

The verifier is independent of the panel runner. It binds the published bytes,
rejects duplicate JSON keys/cells, recomputes every paired outcome, and checks
that the development grid supports the narrow KEEP disposition. It grants no
hosted-score, holdout, release, or submission authority.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
import stat
from pathlib import Path
from typing import Any

ARCHIVE = "a055fd56ca5821208096f37787f77dbdddc2f65c14c24132d6e219a05e6f02ba"
SOURCE = "b96676977687ee8a92d7213380f96bf5774a5ec26925cb4f0d66bdd244eb44ba"
ENGINE = "28b6d8af3ce73926b3d0fda1410c1ddd8384ab8c"
SEEDS = (2609097001, 2609097002, 2609097003, 2609097004)
OPPONENTS = ("v1", "arlene", "apex", "kaito", "reyhan")
VARIANTS = ("redundant_hire_off", "redundant_hire_on")
SEATS = (0, 1)
GAME_COLUMNS = (
    "variant_index", "opponent_index", "seed", "seat", "own", "rival",
    "margin", "trace_sha256",
)
PAIR_COLUMNS = (
    "opponent_index", "seed", "seat", "own_delta", "rival_delta",
    "margin_delta", "trace_changed", "verdict_flip",
)


class EvidenceError(ValueError):
    """The packet is malformed, incomplete, or does not support its claim."""


def no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def load_json_bytes(data: bytes, label: str = "JSON") -> Any:
    try:
        return json.loads(data.decode("utf-8"),
                          object_pairs_hook=no_duplicate_object)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"cannot parse {label}: {exc}") from exc


def load_json(path: Path) -> Any:
    try:
        return load_json_bytes(path.read_bytes(), str(path))
    except OSError as exc:
        raise EvidenceError(f"cannot read JSON {path}: {exc}") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    try:
        return sha256_bytes(path.read_bytes())
    except OSError as exp:
        raise EvidenceError(f"cannot hash {path}: {exc}") from exc


def acquire_regular_file_bytes(path: Path) -> bytes:
    """Acquire immutable regular-file bytes once (no follow, no special files)."""
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(str(path), flags)
    except OSError as exc:
        raise EvidenceError(f"cannot open regular file {path}: {exc}") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise EvidenceError(f"not a regular file: {path}")
        data = os.read(fd, st.st_size)
        if len(data) != st.st_size:
            chunks = [data]
            while True:
                more = os.read(fd, 1 << 20)
                if not more:
                    break
                chunks.append(more)
            data = b"".join(chunks)
            if len(data) != st.st_size:
                raise EvidenceError(f"short read on {path}")
        return data
    finally:
        os.close(fd)
