#!/usr/bin/env python3
"""Hash-bound cross-replay controller fingerprinting for TITAN Kaggriculture.

This module is intentionally evidence-only. It never imports or executes a
candidate/controller and never mutates Kaggle/provider/submission state.

Orientation:
- Kaggle replay action at steps[k] is treated as the action submitted after
  observing steps[k-1].observation (step 0 has no prior observation).
- Engine-reachable hand actions are the submitted hand prefix up to the prior
  public hand count. Any submitted suffix beyond that count is retained as
  unreachable evidence rather than discarded.
- Market projections preserve step boundaries. Non-SELL excludes empty rows;
  SELL contains only non-empty rows whose opcode is exactly "SELL";
  empty-row projection is the per-step count of empty rows.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

SCHEMA = "titan-controller-fingerprint-v1"
MOVE_OPS = frozenset({"NORTH", "SOUTH", "EAST", "WEST"})


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def digest(value: Any) -> str:
    return sha256_bytes(canonical_bytes(value))


def read_replay_gzip(path: Path, expected_sha256: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = path.read_bytes()
    got = sha256_bytes(raw)
    if expected_sha256 is not None and got != expected_sha256:
        raise ValueError(f"{path.name}: transport sha256 mismatch: {got} != {expected_sha256}")
    try:
        decoded = gzip.decompress(raw)
    except (OSError, EOFError) as exc:
        raise ValueError(f"{path.name}: invalid gzip") from exc
    try:
        replay = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path.name}: invalid JSON payload") from exc
    if not isinstance(replay, dict):
        raise ValueError(f"{path.name}: replay root must be object")
    transport = {
        "filename": path.name,
        "bytes": len(raw),
        "sha256": got,
        "json_bytes": len(decoded),
        "json_sha256": sha256_bytes(decoded),
    }
    return replay, transport


def _require_int(value: Any, label: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{label} must be an integer")
    return value


def find_agent_seat(replay: dict[str, Any], agent_name: str) -> int:
    info = replay.get("info")
    if not isinstance(info, dict):
        raise ValueError("missing info object")
    agents = info.get("Agents")
    if not isinstance(agents, list):
        raise ValueError("missing info.Agents")
    hits: list[int] = []
    for i, agent in enumerate(agents):
        if isinstance(agent, dict) and agent.get("Name") == agent_name:
            hits.append(i)
    if len(hits) != 1:
        raise ValueError(f"expected exactly one agent named {agent_name!r}, found {len(hits)}")
    return hits[0]


def _validate_action(action: Any, step: int) -> dict[str, Any]:
    if not isinstance(action, dict):
        raise ValueError(f"step {step}: action must be object")
    for key in ("farmer", "hands", "market"):
        if key not in action or not isinstance(action[key], list):
            raise ValueError(f"step {step}: action.{key} must be list")
    return action


def _prior_hand_count(steps: list[Any], step: int, seat: int) -> int:
    if step == 0:
        return 0
    previous = steps[step - 1]
    if not isinstance(previous, list) or seat >= len(previous):
        raise ValueError(f"step {step-1}: missing seat {seat}")
    row = previous[seat]
    if not isinstance(row, dict):
        raise ValueError(f"step {step-1}: seat row must be object")
    obs = row.get("observation")
    if not isinstance(obs, dict):
        raise ValueError(f"step {step-1}: observation must be object")
    farms = obs.get("farms")
    if not isinstance(farms, list) or seat >= len(farms) or not isinstance(farms[seat], dict):
        raise ValueError(f"step {step-1}: observation.farms[{seat}] missing")
    hands = farms[seat].get("hands")
    if not isinstance(hands, list):
        raise ValueError(f"step {step-1}: observation.farms[{seat}].hands must be list")
    return len(hands)


def _normalize_hand_opcode(row: Any) -> str:
    if not isinstance(row, list) or not row or not isinstance(row[0], str):
        return "<MALFORMED>"
    op = row[0]
    return "MOVE" if op in MOVE_OPS else op


@dataclass(frozen=True)
class ReplayFingerprint:
    episode_id: int
    agent_name: str
    seat: int
    steps: int
    transport: dict[str, Any]
    component_values: dict[str, Any]
    component_sha256: dict[str, str]
    hand_profile: dict[str, Any]
    market_profile: dict[str, Any]

    def public_dict(self, *, include_component_values: bool = False) -> dict[str, Any]:
        out = {
            "schema": SCHEMA,
            "episode_id": self.episode_id,
            "agent_name": self.agent_name,
            "seat": self.seat,
            "steps": self.steps,
            "transport": self.transport,
            "component_sha256": self.component_sha256,
            "hand_profile": self.hand_profile,
            "market_profile": self.market_profile,
        }
        if include_component_values:
            out["component_values"] = self.component_values
        return out


def fingerprint_replay(
    replay: dict[str, Any],
    *,
    transport: dict[str, Any],
    agent_name: str,
    expected_steps: int = 720,
    expected_seat: int | None = None,
) -> ReplayFingerprint:
    seat = find_agent_seat(replay, agent_name)
    if expected_seat is not None and seat != expected_seat:
        raise ValueError(f"agent seat drift: {seat} != {expected_seat}")
    steps = replay.get("steps")
    if not isinstance(steps, list):
        raise ValueError("steps must be list")
    if len(steps) != expected_steps:
        raise ValueError(f"step cardinality drift: {len(steps)} != {expected_steps}")

    farmer_stream: list[Any] = []
    hand_stream: list[Any] = []
    prior_hand_counts: list[int] = []
    reachable_by_step: list[list[Any]] = []
    unreachable_by_step: list[list[Any]] = []
    full_market: list[list[Any]] = []
    non_sell_market: list[list[Any]] = []
    sell_market: list[list[Any]] = []
    empty_market_rows: list[int] = []

    reachable_opcode_counts: Counter[str] = Counter()
    unreachable_opcode_counts: Counter[str] = Counter()
    total_submitted_hands = 0
    total_reachable_hands = 0
    total_unreachable_hands = 0
    market_opcode_counts: Counter[str] = Counter()

    for k, step_rows in enumerate(steps):
        if not isinstance(step_rows, list) or seat >= len(step_rows):
            raise ValueError(f"step {k}: missing seat {seat}")
        row = step_rows[seat]
        if not isinstance(row, dict):
            raise ValueError(f"step {k}: seat row must be object")
        action = _validate_action(row.get("action"), k)

        farmer = action["farmer"]
        hands = action["hands"]
        market = action["market"]
        farmer_stream.append(farmer)
        hand_stream.append(hands)

        prior_count = _prior_hand_count(steps, k, seat)
        prior_hand_counts.append(prior_count)
        reachable_count = min(prior_count, len(hands))
        reachable = hands[:reachable_count]
        unreachable = hands[reachable_count:]
        reachable_by_step.append(reachable)
        unreachable_by_step.append(unreachable)
        total_submitted_hands += len(hands)
        total_reachable_hands += len(reachable)
        total_unreachable_hands += len(unreachable)
        reachable_opcode_counts.update(_normalize_hand_opcode(x) for x in reachable)
        unreachable_opcode_counts.update(_normalize_hand_opcode(x) for x in unreachable)

        full_market.append(market)
        ns: list[Any] = []
        ss: list[Any] = []
        empty_count = 0
        for market_row in market:
            if not market_row:
                empty_count += 1
                market_opcode_counts["<EMPTY>"] += 1
                continue
            if not isinstance(market_row, list) or not isinstance(market_row[0], str):
                raise ValueError(f"step {k}: malformed market row")
            op = market_row[0]
            market_opcode_counts[op] += 1
            if op == "SELL":
                ss.append(market_row)
            else:
                ns.append(market_row)
        non_sell_market.append(ns)
        sell_market.append(ss)
        empty_market_rows.append(empty_count)

    info = replay.get("info")
    if not isinstance(info, dict):
        raise ValueError("missing info object")
    episode_id = _require_int(info.get("EpisodeId"), "info.EpisodeId")
    components = {
        "farmer": farmer_stream,
        "hands_submitted": hand_stream,
        "prior_hand_counts": prior_hand_counts,
        "hands_reachable": reachable_by_step,
        "hands_unreachable": unreachable_by_step,
        "market_full": full_market,
        "market_non_sell": non_sell_market,
        "market_sell": sell_market,
        "market_empty_rows": empty_market_rows,
    }
    return ReplayFingerprint(
        episode_id=episode_id,
        agent_name=agent_name,
        seat=seat,
        steps=len(steps),
        transport=transport,
        component_values=components,
        component_sha256={name: digest(value) for name, value in components.items()},
        hand_profile={
            "submitted_rows": total_submitted_hands,
            "reachable_rows": total_reachable_hands,
            "unreachable_rows": total_unreachable_hands,
            "reachable_opcode_counts": dict(sorted(reachable_opcode_counts.items())),
            "unreachable_opcode_counts": dict(sorted(unreachable_opcode_counts.items())),
        },
        market_profile={
            "opcode_counts": dict(sorted(market_opcode_counts.items())),
            "empty_step_count": sum(1 for rows in full_market if not rows),
            "steps_with_empty_rows": sum(1 for count in empty_market_rows if count),
        },
    )


def differing_steps(left: ReplayFingerprint, right: ReplayFingerprint, component: str) -> list[int]:
    a = left.component_values[component]
    b = right.component_values[component]
    if len(a) != len(b):
        raise ValueError(f"{component}: component step cardinalities differ")
    return [i for i, (x, y) in enumerate(zip(a, b)) if x != y]


def compare_fingerprints(left: ReplayFingerprint, right: ReplayFingerprint) -> dict[str, Any]:
    components = sorted(left.component_values)
    if components != sorted(right.component_values):
        raise ValueError("component sets differ")
    diffs = {name: differing_steps(left, right, name) for name in components}
    return {
        "left_episode": left.episode_id,
        "right_episode": right.episode_id,
        "same_seat": left.seat == right.seat,
        "steps": left.steps,
        "component_diff_steps": diffs,
        "component_diff_counts": {name: len(indices) for name, indices in diffs.items()},
    }


def load_manifest(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != "titan-controller-fingerprint-corpus-v1":
        raise ValueError("unexpected corpus manifest schema")
    rows = value.get("replays")
    if not isinstance(rows, list) or not rows:
        raise ValueError("corpus manifest replays must be a non-empty list")
    expected_steps = value.get("expected_steps", 720)
    if type(expected_steps) is not int or expected_steps <= 0:
        raise ValueError("expected_steps must be a positive true integer")
    ids: set[int] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("corpus row must be object")
        eid = _require_int(row.get("episode_id"), "corpus episode_id")
        if eid in ids:
            raise ValueError(f"duplicate corpus episode: {eid}")
        ids.add(eid)
        sha = row.get("sha256")
        if not isinstance(sha, str) or len(sha) != 64:
            raise ValueError(f"episode {eid}: invalid sha256")
        try:
            int(sha, 16)
        except ValueError as exc:
            raise ValueError(f"episode {eid}: invalid sha256") from exc
        if sha != sha.lower():
            raise ValueError(f"episode {eid}: sha256 must be lowercase hex")
        seat = row.get("seat")
        if type(seat) is not int or seat < 0:
            raise ValueError(f"episode {eid}: seat must be a nonnegative true integer")
        filename = row.get("filename")
        if not isinstance(filename, str) or not filename or Path(filename).name != filename:
            raise ValueError(f"episode {eid}: filename must be a single basename")
        role = row.get("role")
        if not isinstance(role, str) or not role:
            raise ValueError(f"episode {eid}: role required")
        declared_bytes = row.get("bytes")
        if declared_bytes is not None and (type(declared_bytes) is not int or declared_bytes <= 0):
            raise ValueError(f"episode {eid}: bytes must be a positive true integer")

    for pair in value.get("comparisons", []):
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("comparisons entries must be [left,right]")
        left = _require_int(pair[0], "comparison left episode")
        right = _require_int(pair[1], "comparison right episode")
        if left not in ids or right not in ids:
            raise ValueError("comparison references unknown episode")
    return value


def analyze_manifest(manifest_path: Path, corpus_dir: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    agent_name = manifest.get("agent_name")
    if not isinstance(agent_name, str) or not agent_name:
        raise ValueError("manifest agent_name required")

    fingerprints: dict[int, ReplayFingerprint] = {}
    roles: dict[int, str] = {}
    for row in manifest["replays"]:
        eid = row["episode_id"]
        replay, transport = read_replay_gzip(corpus_dir / row["filename"], row["sha256"])
        if row.get("bytes") is not None and transport["bytes"] != row["bytes"]:
            raise ValueError(
                f"episode {eid}: transport byte size drift: "
                f"{transport['bytes']} != {row['bytes']}"
            )
        fp = fingerprint_replay(
            replay,
            transport=transport,
            agent_name=agent_name,
            expected_steps=manifest.get("expected_steps", 720),
            expected_seat=row["seat"],
        )
        if fp.episode_id != eid:
            raise ValueError(f"episode id mismatch: file says {fp.episode_id}, manifest says {eid}")
        fingerprints[eid] = fp
        roles[eid] = row["role"]

    comparisons = []
    for pair in manifest.get("comparisons", []):
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("comparisons entries must be [left,right]")
        a, b = pair
        comparisons.append(compare_fingerprints(fingerprints[a], fingerprints[b]))

    out = {
        "schema": SCHEMA,
        "manifest_sha256": sha256_bytes(manifest_path.read_bytes()),
        "agent_name": agent_name,
        "episodes": {
            str(eid): {**fp.public_dict(), "role": roles[eid]}
            for eid, fp in sorted(fingerprints.items())
        },
        "comparisons": comparisons,
    }
    out["evidence_sha256"] = digest(out)
    return out


def verify_evidence(manifest_path: Path, corpus_dir: Path, evidence_path: Path) -> dict[str, Any]:
    actual = analyze_manifest(manifest_path, corpus_dir)
    expected = json.loads(evidence_path.read_text(encoding="utf-8"))
    if actual != expected:
        raise ValueError("evidence drift: regenerated report does not match checked-in evidence")
    return actual


def verify_report_seal(report: dict[str, Any]) -> bool:
    """Verify the report's self-seal without requiring access to the replay corpus."""
    expected = report.get("evidence_sha256")
    if not isinstance(expected, str) or len(expected) != 64:
        return False
    unsigned = dict(report)
    unsigned.pop("evidence_sha256", None)
    return digest(unsigned) == expected


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--corpus-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-evidence", type=Path)
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.verify_evidence:
        report = verify_evidence(args.manifest, args.corpus_dir, args.verify_evidence)
    else:
        report = analyze_manifest(args.manifest, args.corpus_dir)

    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
