#!/usr/bin/env python3
"""Deterministic cross-episode recurrence report for replay-loss-autopsy extracts.

Research tooling only. The comparator consumes canonical extractor JSON and
reports exact descriptive tokens that recur across episodes. It does not infer
causality, economics, opponent identity, policy intent, or gameplay value.

Inputs are comparable only when all extractor outputs bind the same three raw
CSV byte snapshots. Mixed snapshots fail closed instead of being silently
compared.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

INPUT_SCHEMA = "titan.v4.replay-loss-autopsy.v1"
OUTPUT_SCHEMA = "titan.v4.replay-loss-autopsy.multiloss.v1"
SOURCE_NAMES = ("farmer_actions", "market_orders", "matches_meta")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class CompareError(ValueError):
    pass


def _plain_int(value: Any, field: str, *, minimum: int | None = None) -> int:
    if type(value) is not int:
        raise CompareError(f"{field} must be a plain integer")
    if minimum is not None and value < minimum:
        raise CompareError(f"{field} must be >= {minimum}")
    return value


def _opt_plain_int(value: Any, field: str) -> int | None:
    if value is None:
        return None
    return _plain_int(value, field)


def _string(value: Any, field: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise CompareError(f"{field} must be a string")
    if not allow_empty and not value:
        raise CompareError(f"{field} must be nonempty")
    return value


def _opt_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _string(value, field, allow_empty=True)


def _source_identity(payload: dict[str, Any], index: int) -> tuple[tuple[str, int], ...]:
    inputs = payload.get("inputs")
    if not isinstance(inputs, dict):
        raise CompareError(f"extract[{index}].inputs must be an object")
    identity: list[tuple[str, int]] = []
    for name in SOURCE_NAMES:
        row = inputs.get(name)
        if not isinstance(row, dict):
            raise CompareError(f"extract[{index}].inputs.{name} must be an object")
        digest = row.get("sha256")
        if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
            raise CompareError(
                f"extract[{index}].inputs.{name}.sha256 must be lowercase sha256"
            )
        byte_count = _plain_int(
            row.get("bytes"), f"extract[{index}].inputs.{name}.bytes", minimum=0
        )
        path = row.get("path")
        if not isinstance(path, str) or not path:
            raise CompareError(f"extract[{index}].inputs.{name}.path must be nonempty")
        identity.append((digest, byte_count))
    return tuple(identity)


def _validate_farmer_summary(rows: Any, index: int) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise CompareError(f"extract[{index}].farmer_summary must be a list")
    out: list[dict[str, Any]] = []
    for j, row in enumerate(rows):
        if not isinstance(row, dict):
            raise CompareError(f"extract[{index}].farmer_summary[{j}] must be an object")
        out.append(
            {
                "player": _string(
                    row.get("player"), f"extract[{index}].farmer_summary[{j}].player",
                    allow_empty=True,
                ),
                "day": _opt_plain_int(
                    row.get("day"), f"extract[{index}].farmer_summary[{j}].day"
                ),
                "verb": _string(
                    row.get("verb"), f"extract[{index}].farmer_summary[{j}].verb",
                    allow_empty=True,
                ),
                "target": _opt_string(
                    row.get("target"), f"extract[{index}].farmer_summary[{j}].target"
                ),
                "rows": _plain_int(
                    row.get("rows"), f"extract[{index}].farmer_summary[{j}].rows",
                    minimum=1,
                ),
            }
        )
    return out


def _validate_market_summary(rows: Any, index: int) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        raise CompareError(f"extract[{index}].market_summary must be a list")
    out: list[dict[str, Any]] = []
    for j, row in enumerate(rows):
        if not isinstance(row, dict):
            raise CompareError(f"extract[{index}].market_summary[{j}] must be an object")
        out.append(
            {
                "player": _string(
                    row.get("player"), f"extract[{index}].market_summary[{j}].player",
                    allow_empty=True,
                ),
                "day": _opt_plain_int(
                    row.get("day"), f"extract[{index}].market_summary[{j}].day"
                ),
                "verb": _string(
                    row.get("verb"), f"extract[{index}].market_summary[{j}].verb",
                    allow_empty=True,
                ),
                "item": _opt_string(
                    row.get("item"), f"extract[{index}].market_summary[{j}].item"
                ),
                "rows": _plain_int(
                    row.get("rows"), f"extract[{index}].market_summary[{j}].rows",
                    minimum=1,
                ),
                "explicit_qty_sum": _plain_int(
                    row.get("explicit_qty_sum"),
                    f"extract[{index}].market_summary[{j}].explicit_qty_sum",
                ),
            }
        )
    return out


def _validate_tail(tail: Any, index: int, max_step: int | None) -> list[dict[str, Any]]:
    if not isinstance(tail, dict):
        raise CompareError(f"extract[{index}].tail must be an object")
    _plain_int(
        tail.get("requested_callbacks"),
        f"extract[{index}].tail.requested_callbacks",
        minimum=0,
    )
    _opt_plain_int(tail.get("start_step"), f"extract[{index}].tail.start_step")
    events = tail.get("events")
    if not isinstance(events, list):
        raise CompareError(f"extract[{index}].tail.events must be a list")
    out: list[dict[str, Any]] = []
    for j, event in enumerate(events):
        if not isinstance(event, dict):
            raise CompareError(f"extract[{index}].tail.events[{j}] must be an object")
        kind = event.get("kind")
        if kind not in {"farmer_action", "market_order"}:
            raise CompareError(f"extract[{index}].tail.events[{j}].kind unsupported")
        step = _opt_plain_int(
            event.get("step"), f"extract[{index}].tail.events[{j}].step"
        )
        player = _string(
            event.get("player_raw"),
            f"extract[{index}].tail.events[{j}].player_raw",
            allow_empty=True,
        )
        verb = _string(
            event.get("verb"), f"extract[{index}].tail.events[{j}].verb",
            allow_empty=True,
        )
        qty = _opt_plain_int(
            event.get("qty"), f"extract[{index}].tail.events[{j}].qty"
        )
        qty_raw = _opt_string(
            event.get("qty_raw"), f"extract[{index}].tail.events[{j}].qty_raw"
        )
        target_key = "target" if kind == "farmer_action" else "item"
        target = _opt_string(
            event.get(target_key),
            f"extract[{index}].tail.events[{j}].{target_key}",
        )
        relative_step = (
            step - max_step if step is not None and max_step is not None else None
        )
        out.append(
            {
                "kind": kind,
                "player": player,
                "relative_step": relative_step,
                "verb": verb,
                "target": target,
                "qty": qty,
                "qty_raw": qty_raw,
            }
        )
    return out


def _validate_extract(payload: Any, index: int) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise CompareError(f"extract[{index}] must be an object")
    if payload.get("schema") != INPUT_SCHEMA:
        raise CompareError(
            f"extract[{index}].schema must be exactly {INPUT_SCHEMA!r}"
        )
    episode = _string(payload.get("episode"), f"extract[{index}].episode")
    source_identity = _source_identity(payload, index)

    coverage = payload.get("coverage")
    if not isinstance(coverage, dict):
        raise CompareError(f"extract[{index}].coverage must be an object")
    max_step = _opt_plain_int(
        coverage.get("max_step"), f"extract[{index}].coverage.max_step"
    )

    farmer = _validate_farmer_summary(payload.get("farmer_summary"), index)
    market = _validate_market_summary(payload.get("market_summary"), index)
    tail = _validate_tail(payload.get("tail"), index, max_step)
    return {
        "episode": episode,
        "source_identity": source_identity,
        "farmer_summary": farmer,
        "market_summary": market,
        "tail": tail,
    }


def _sort_nullable(value: Any) -> tuple[int, str]:
    return (1, "") if value is None else (0, str(value))


def _repeated_farmer(
    extracts: list[dict[str, Any]], min_episodes: int
) -> list[dict[str, Any]]:
    seen: dict[tuple[Any, ...], dict[str, int]] = defaultdict(dict)
    for extract in extracts:
        episode = extract["episode"]
        for row in extract["farmer_summary"]:
            key = (row["player"], row["day"], row["verb"], row["target"])
            seen[key][episode] = row["rows"]
    out: list[dict[str, Any]] = []
    for key, by_episode in seen.items():
        if len(by_episode) < min_episodes:
            continue
        player, day, verb, target = key
        out.append(
            {
                "player": player,
                "day": day,
                "verb": verb,
                "target": target,
                "episode_count": len(by_episode),
                "episodes": [
                    {"episode": episode, "rows": by_episode[episode]}
                    for episode in sorted(by_episode)
                ],
            }
        )
    out.sort(
        key=lambda row: (
            row["player"],
            _sort_nullable(row["day"]),
            row["verb"],
            _sort_nullable(row["target"]),
        )
    )
    return out


def _repeated_market(
    extracts: list[dict[str, Any]], min_episodes: int
) -> list[dict[str, Any]]:
    seen: dict[tuple[Any, ...], dict[str, tuple[int, int]]] = defaultdict(dict)
    for extract in extracts:
        episode = extract["episode"]
        for row in extract["market_summary"]:
            key = (row["player"], row["day"], row["verb"], row["item"])
            seen[key][episode] = (row["rows"], row["explicit_qty_sum"])
    out: list[dict[str, Any]] = []
    for key, by_episode in seen.items():
        if len(by_episode) < min_episodes:
            continue
        player, day, verb, item = key
        out.append(
            {
                "player": player,
                "day": day,
                "verb": verb,
                "item": item,
                "episode_count": len(by_episode),
                "episodes": [
                    {
                        "episode": episode,
                        "rows": by_episode[episode][0],
                        "explicit_qty_sum": by_episode[episode][1],
                    }
                    for episode in sorted(by_episode)
                ],
            }
        )
    out.sort(
        key=lambda row: (
            row["player"],
            _sort_nullable(row["day"]),
            row["verb"],
            _sort_nullable(row["item"]),
        )
    )
    return out


def _repeated_tail(
    extracts: list[dict[str, Any]], min_episodes: int
) -> list[dict[str, Any]]:
    seen: dict[tuple[Any, ...], set[str]] = defaultdict(set)
    for extract in extracts:
        episode = extract["episode"]
        for row in extract["tail"]:
            if row["relative_step"] is None:
                continue
            key = (
                row["kind"],
                row["player"],
                row["relative_step"],
                row["verb"],
                row["target"],
                row["qty"],
                row["qty_raw"],
            )
            seen[key].add(episode)
    out: list[dict[str, Any]] = []
    for key, episodes in seen.items():
        if len(episodes) < min_episodes:
            continue
        kind, player, relative_step, verb, target, qty, qty_raw = key
        out.append(
            {
                "kind": kind,
                "player": player,
                "relative_step": relative_step,
                "verb": verb,
                "target": target,
                "qty": qty,
                "qty_raw": qty_raw,
                "episode_count": len(episodes),
                "episodes": sorted(episodes),
            }
        )
    out.sort(
        key=lambda row: (
            row["relative_step"],
            row["kind"],
            row["player"],
            row["verb"],
            _sort_nullable(row["target"]),
            _sort_nullable(row["qty"]),
            _sort_nullable(row["qty_raw"]),
        )
    )
    return out


def compare_extracts(
    payloads: Iterable[dict[str, Any]], *, min_episodes: int = 2
) -> dict[str, Any]:
    min_episodes = _plain_int(min_episodes, "min_episodes", minimum=2)
    extracts = [_validate_extract(payload, i) for i, payload in enumerate(payloads)]
    if len(extracts) < min_episodes:
        raise CompareError(
            f"need at least {min_episodes} extracts; received {len(extracts)}"
        )

    episodes = [extract["episode"] for extract in extracts]
    if len(episodes) != len(set(episodes)):
        raise CompareError("episode ids must be unique")

    reference_identity = extracts[0]["source_identity"]
    if any(extract["source_identity"] != reference_identity for extract in extracts[1:]):
        raise CompareError(
            "input source snapshot mismatch; recurrence requires identical raw CSV hashes and byte lengths"
        )

    source_snapshot = {
        name: {"sha256": reference_identity[i][0], "bytes": reference_identity[i][1]}
        for i, name in enumerate(SOURCE_NAMES)
    }
    return {
        "schema": OUTPUT_SCHEMA,
        "episode_count": len(extracts),
        "episodes": sorted(episodes),
        "min_episodes": min_episodes,
        "source_snapshot": source_snapshot,
        "repeated_farmer_summary": _repeated_farmer(extracts, min_episodes),
        "repeated_market_summary": _repeated_market(extracts, min_episodes),
        "repeated_tail_events": _repeated_tail(extracts, min_episodes),
        "limits": [
            "Only exact descriptive fields already present in canonical replay-loss-autopsy extracts are compared.",
            "All extracts must bind identical farmer_actions, market_orders, and matches_meta byte snapshots.",
            "Tail recurrence uses relative callback offset from each extract's reported max_step; it does not infer equivalent game state.",
            "No cash, tile state, inventory, opponent identity, economics, policy intent, mechanism attribution, or causal credit is inferred.",
            "A repeated token is routing evidence only and is not evidence that changing that token would improve score.",
        ],
    }


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise CompareError(f"duplicate JSON key {key!r}")
        out[key] = value
    return out


def load_extract(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle, object_pairs_hook=_no_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise CompareError(f"{path}: invalid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise CompareError(f"{path}: JSON root must be an object")
    return payload


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("extracts", nargs="+", type=Path)
    parser.add_argument("--min-episodes", type=int, default=2)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        payloads = [load_extract(path) for path in args.extracts]
        report = compare_extracts(payloads, min_episodes=args.min_episodes)
    except (OSError, CompareError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    text = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    if args.output is not None:
        try:
            args.output.write_text(text, encoding="utf-8")
        except OSError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
