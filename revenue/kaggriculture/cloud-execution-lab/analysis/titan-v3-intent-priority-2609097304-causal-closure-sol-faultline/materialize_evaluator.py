#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Instrument the pinned evaluator with action/debug timelines, fail closed."""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
from typing import Any

EXPECTED_GIT_BLOB = "077feb2208b6e0c1727835eb4f8089709bf67f3b"
OPERATION = "titan-v3-intent-priority-first-divergence-evaluator-20260910-01"


class EvaluatorError(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def replace_once(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise EvaluatorError(f"{label} anchor count is {count}, expected 1")
    return source.replace(old, new, 1)


def patch_source(original: bytes) -> tuple[bytes, dict[str, Any]]:
    blob = git_blob_sha1(original)
    if blob != EXPECTED_GIT_BLOB:
        raise EvaluatorError(f"evaluator source drift: expected {EXPECTED_GIT_BLOB}, got {blob}")
    try:
        source = original.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise EvaluatorError("evaluator is not UTF-8") from exc

    source = replace_once(
        source,
        '''                action = function(obs, cfg) if takes_config else function(obs)\n                seconds, cpu_seconds = time.perf_counter() - start, time.process_time() - cpu\n''',
        '''                action = function(obs, cfg) if takes_config else function(obs)\n                seconds, cpu_seconds = time.perf_counter() - start, time.process_time() - cpu\n                debug_provider = getattr(\n                    sys.modules.get(getattr(function, "__module__", "")),\n                    "debug_snapshot",\n                    None,\n                )\n                debug = debug_provider() if callable(debug_provider) else None\n''',
        "worker debug capture",
    )
    source = replace_once(
        source,
        '''                send({"kind": "action", "action": action, "call_seconds": seconds,\n                      "call_cpu_seconds": cpu_seconds, **usage()})\n''',
        '''                send({"kind": "action", "action": action, "debug": debug,\n                      "call_seconds": seconds, "call_cpu_seconds": cpu_seconds, **usage()})\n''',
        "worker action packet",
    )
    source = replace_once(
        source,
        '''    result = {"seed": seed, "candidate_seat": candidate_seat, "status": "failed", "scores": None,\n              "failure": None, "steps": 0, "episode_steps": cfg.episodeSteps, "daily_bank": []}\n''',
        '''    result = {"seed": seed, "candidate_seat": candidate_seat, "status": "failed", "scores": None,\n              "failure": None, "steps": 0, "episode_steps": cfg.episodeSteps, "daily_bank": [],\n              "candidate_timeline": []}\n''',
        "game result timeline",
    )
    source = replace_once(
        source,
        '''        for step in range(cfg.episodeSteps):\n            actions = []\n            for seat, actor in enumerate(actors):\n''',
        '''        for step in range(cfg.episodeSteps):\n            actions, responses = [], []\n            for seat, actor in enumerate(actors):\n''',
        "response retention",
    )
    source = replace_once(
        source,
        '''                actions.append(response["action"])\n            for seat in range(2):\n                state[seat].action = actions[seat]\n            engine.interpreter(state, env)\n            result["steps"] += 1\n            bank = [float(state[0].observation.farms[i]["money"]) for i in range(2)]\n''',
        '''                actions.append(response["action"])\n                responses.append(response)\n            pre_world = encoded([s.observation for s in state])\n            timeline = {\n                "step": step,\n                "pre_world_sha256": hashlib.sha256(pre_world).hexdigest(),\n                "tested_action": json.loads(encoded(actions[candidate_seat])),\n                "tested_action_sha256": hashlib.sha256(encoded(actions[candidate_seat])).hexdigest(),\n                "rival_action": json.loads(encoded(actions[1 - candidate_seat])),\n                "rival_action_sha256": hashlib.sha256(encoded(actions[1 - candidate_seat])).hexdigest(),\n                "debug": json.loads(encoded(responses[candidate_seat].get("debug"))),\n            }\n            for seat in range(2):\n                state[seat].action = actions[seat]\n            engine.interpreter(state, env)\n            result["steps"] += 1\n            bank = [float(state[0].observation.farms[i]["money"]) for i in range(2)]\n            timeline["post_world_sha256"] = hashlib.sha256(\n                encoded([s.observation for s in state])\n            ).hexdigest()\n            timeline["bank"] = bank\n            result["candidate_timeline"].append(timeline)\n''',
        "timeline append",
    )

    try:
        compile(source, "instrumented_evaluate.py", "exec")
    except SyntaxError as exc:
        raise EvaluatorError(f"instrumented evaluator does not compile: {exc}") from exc
    patched = source.encode("utf-8")
    return patched, {
        "source_git_blob_sha1": blob,
        "source_sha256": sha256(original),
        "source_bytes": len(original),
        "patched_git_blob_sha1": git_blob_sha1(patched),
        "patched_sha256": sha256(patched),
        "patched_bytes": len(patched),
        "capture_phase": "after both returned actions, before official interpreter",
        "pre_world_field": "candidate_timeline[].pre_world_sha256",
        "tested_action_field": "candidate_timeline[].tested_action",
        "rival_action_field": "candidate_timeline[].rival_action",
        "debug_field": "candidate_timeline[].debug",
        "post_world_field": "candidate_timeline[].post_world_sha256",
    }


def atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def materialize(source: Path, output: Path, receipt_path: Path) -> dict[str, Any]:
    source = source.resolve(strict=True)
    output = output.resolve()
    receipt_path = receipt_path.resolve()
    if output == source or receipt_path in (source, output):
        raise EvaluatorError("source, output, and receipt must be distinct")
    original = source.read_bytes()
    patched, identity = patch_source(original)
    if source.read_bytes() != original:
        raise EvaluatorError("source evaluator changed during materialization")
    atomic_write(output, patched)
    if output.read_bytes() != patched:
        raise EvaluatorError("instrumented evaluator readback mismatch")
    diff = "".join(difflib.unified_diff(
        original.decode().splitlines(keepends=True),
        patched.decode().splitlines(keepends=True),
        fromfile="evaluate.py",
        tofile="instrumented_evaluate.py",
        n=3,
    ))
    receipt = {
        "schema_version": 1,
        "operation": OPERATION,
        "source": {
            "path": str(source),
            "git_blob_sha1": identity["source_git_blob_sha1"],
            "sha256": identity["source_sha256"],
            "bytes": identity["source_bytes"],
        },
        "patched": {
            "path": str(output),
            "git_blob_sha1": identity["patched_git_blob_sha1"],
            "sha256": identity["patched_sha256"],
            "bytes": identity["patched_bytes"],
            "capture_phase": identity["capture_phase"],
            "fields": {
                key: value for key, value in identity.items()
                if key.endswith("_field")
            },
        },
        "semantic_boundary": "observability only; actions and interpreter inputs are unchanged",
        "unified_diff": diff,
    }
    atomic_write(
        receipt_path,
        (json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(),
    )
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    result = materialize(args.source, args.output, args.receipt)
    print(json.dumps(result["patched"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
