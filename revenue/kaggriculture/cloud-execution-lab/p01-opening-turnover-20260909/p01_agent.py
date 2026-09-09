# SPDX-License-Identifier: Apache-2.0
"""Executable P01 wrapper around the unchanged exact-current TITAN entrypoint."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import main as _canonical
import mechanics as _mechanics
from opening_turnover import MODES, prioritize_opening_seeds

MODE = os.environ.get("P01_MODE", "annual").strip().lower()
MAX_DAY = int(os.environ.get("P01_MAX_DAY", "10"))
if MODE not in MODES:
    raise ValueError(f"unsupported P01_MODE={MODE!r}")


def _digest(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _emit(observation, before, after, report) -> None:
    if not report.get("changed"):
        return
    directory = Path(os.environ.get("P01_TRACE_DIR", "/tmp/p01-traces"))
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"p01-{MODE}-{os.getpid()}.jsonl"
    row = {
        "schema": 1,
        "mode": MODE,
        "pid": os.getpid(),
        "step": int(observation.get("step", report.get("step", -1))),
        "player": int(observation.get("player", -1)),
        "before_action_sha256": _digest(before),
        "after_action_sha256": _digest(after),
        "before_market": before.get("market", []),
        "after_market": after.get("market", []),
        "report": report,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def agent(observation, configuration=None):
    cfg = dict(configuration or {})
    selected = _canonical.agent(observation, cfg)
    result, report = prioritize_opening_seeds(
        _mechanics, observation, cfg, selected, mode=MODE, max_day=MAX_DAY
    )
    _emit(observation, selected, result, report)
    return result
