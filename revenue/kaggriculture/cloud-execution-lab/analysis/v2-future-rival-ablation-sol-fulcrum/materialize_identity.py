# SPDX-License-Identifier: Apache-2.0
"""Frozen-V2 identities, strict JSON, and digest helpers."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

OPERATION = "titan-v2-future-rival-ablation-20260909-sol-fulcrum-01"
FREEZE_GIT_BLOB = "8a1bcae694e5a3dd84acefa553f29bb36011a338"
SCHEDULER_GIT_BLOB = "7c068b7078c3d7c09bb3836590ad42b0af934cdf"
SCHEDULER_SHA256 = "72865b83e66d0c1ed27ddc35e5ab428f8212872e8e8e918f2826eb7665fbe7f8"
ENTRYPOINT_SHA256 = "2e4897fb3aa8b0bee3e97709808c3aa25fa5055bcf5ce7d433b493eb334870f2"
V2_SCENARIOS = (
    "no_rival",
    "observed_paired",
    "observed_later_order",
    "observed_next_turn",
    "observed_before_delayed_batch",
)
ABLATION_SCENARIOS = V2_SCENARIOS[:3]
FUTURE_SCENARIO_BLOCK = """    if end>now:
        scenarios.append(('observed_next_turn',((now+1,rival_quantity),),'paired'))
    if end>now+2:
        scenarios.append(('observed_before_delayed_batch',((end-1,rival_quantity),),'paired'))
"""
HEX40 = re.compile(r"^[0-9a-f]{40}$")

class MaterializeError(ValueError):
    """The frozen source or requested materialization violated its contract."""

def _reject_pairs(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise MaterializeError(f"duplicate JSON key: {key!r}")
        output[key] = value
    return output

def strict_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                MaterializeError(f"non-finite JSON token: {token}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MaterializeError(f"cannot read strict JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise MaterializeError(f"expected JSON object in {path}")
    return value

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def git_blob_bytes(data: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(data)).encode("ascii") + b"\0" + data,
        usedforsecurity=False,
    ).hexdigest()
