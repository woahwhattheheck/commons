#!/usr/bin/env python3
"""Offline manual-entry prompt-efficiency workbench for CrowdStrike Agents of Chaos.

This carrier never talks to the live contest. Token counts are operator-entered
observations only. Compliance output is SELF_ATTESTED_ONLY.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

SCHEMA = "crowdstrike-aoc-manual-ledger-v1"
COMPLIANCE_KIND = "SELF_ATTESTED_ONLY"
REQUIRED_ATTEMPT_KEYS = (
    "attempt_id",
    "puzzle_id",
    "prompt_text",
    "observed_token_count",
    "outcome",
    "entry_mode",
    "declared_actions",
)
PROHIBITED_ACTIONS = frozenset(
    {
        "bot_live_interaction",
        "automated_live_interaction",
        "platform_attack",
        "backend_attack",
        "scoring_attack",
        "network_interception",
        "multi_accounting",
        "other_player_access",
    }
)
PROHIBITED_TEXT = (
    r"\bbot\b.*live|\bautomat(?:ed|ion)\b.*live|"
    r"backend.?attack|scoring.?attack|platform.?attack|"
    r"network.?intercept|multi.?account|other.?player"
)
PROHIBITED_RE = re.compile(PROHIBITED_TEXT, re.IGNORECASE)


class LedgerError(ValueError):
    pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise LedgerError(f"duplicate json key: {key}")
        seen.add(key)
        out[key] = value
    return out


def load_strict_json(text: str) -> Any:
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys)


def load_strict_json_path(path: Path) -> Any:
    return load_strict_json(path.read_text(encoding="utf-8"))


def _norm_prompt(text: str) -> str:
    return " ".join(str(text).split())


def _prompt_digest(text: str) -> str:
    return hashlib.sha256(_norm_prompt(text).encode("utf-8")).hexdigest()


def _require_keys(obj: dict[str, Any], keys: tuple[str, ...], where: str) -> None:
    missing = [k for k in keys if k not in obj]
    if missing:
        raise LedgerError(f"{where} missing keys: {missing}")


def _parse_token_count(raw: Any) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise LedgerError(f"observed_token_count must be a JSON integer, got {type(raw).__name__}")
    if raw < 0:
        raise LedgerError("observed_token_count must be >= 0")
    return raw


def _scan_prohibited(attempt: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    declared = attempt.get("declared_actions") or []
    if not isinstance(declared, list):
        raise LedgerError("declared_actions must be a list")
    for action in declared:
        if action in PROHIBITED_ACTIONS:
            hits.append(str(action))
    blob = " ".join(
        [
            str(attempt.get("prompt_text", "")),
            str(attempt.get("notes", "")),
            str(attempt.get("entry_mode", "")),
            " ".join(str(x) for x in declared),
        ]
    )
    if PROHIBITED_RE.search(blob):
        hits.append("prohibited_text_pattern")
    return sorted(set(hits))


def validate_attempt(attempt: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(attempt, dict):
        raise LedgerError("attempt must be an object")
    _require_keys(attempt, REQUIRED_ATTEMPT_KEYS, "attempt")
    if attempt.get("entry_mode") != "manual":
        raise LedgerError("entry_mode must be 'manual'")
    outcome = attempt["outcome"]
    if outcome not in {"success", "failure", "incomplete"}:
        raise LedgerError("outcome must be success|failure|incomplete")
    tokens = _parse_token_count(attempt["observed_token_count"])
    hits = _scan_prohibited(attempt)
    if hits:
        raise LedgerError(f"prohibited action declared or implied: {hits}")
    puzzle = str(attempt["puzzle_id"]).strip()
    if not puzzle:
        raise LedgerError("puzzle_id must be non-empty")
    prompt = str(attempt["prompt_text"])
    return {
        "attempt_id": str(attempt["attempt_id"]),
        "puzzle_id": puzzle,
        "prompt_text": prompt,
        "prompt_digest": _prompt_digest(prompt),
        "observed_token_count": tokens,
        "outcome": outcome,
        "entry_mode": "manual",
        "declared_actions": list(attempt["declared_actions"]),
        "notes": str(attempt.get("notes", "")),
    }


def frontier_for_puzzle(attempts: list[dict[str, Any]]) -> dict[str, Any]:
    successes = [a for a in attempts if a["outcome"] == "success"]
    if not successes:
        return {
            "puzzle_id": attempts[0]["puzzle_id"] if attempts else "",
            "best_observed_token_count": None,
            "best_attempt_ids": [],
            "successful_count": 0,
            "duplicate_prompt_groups": [],
        }
    best = min(a["observed_token_count"] for a in successes)
    best_ids = sorted(
        a["attempt_id"] for a in successes if a["observed_token_count"] == best
    )
    by_digest: dict[str, list[str]] = {}
    for a in successes:
        by_digest.setdefault(a["prompt_digest"], []).append(a["attempt_id"])
    dupes = [
        {"prompt_digest": d, "attempt_ids": sorted(ids)}
        for d, ids in sorted(by_digest.items())
        if len(ids) > 1
    ]
    return {
        "puzzle_id": successes[0]["puzzle_id"],
        "best_observed_token_count": best,
        "best_attempt_ids": best_ids,
        "successful_count": len(successes),
        "duplicate_prompt_groups": dupes,
    }


def build_receipt(ledger: dict[str, Any], frontiers: list[dict[str, Any]]) -> dict[str, Any]:
    payload = {
        "schema": SCHEMA,
        "compliance_kind": COMPLIANCE_KIND,
        "eligibility_certificate": False,
        "sponsor_compliance_certificate": False,
        "live_contest_interaction": False,
        "tokenizer": "operator_entered_observation_only",
        "attempt_count": len(ledger.get("attempts", [])),
        "frontiers": frontiers,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    payload["receipt_sha256"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return payload


def evaluate_ledger(raw: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise LedgerError("ledger must be an object")
    if raw.get("schema") != SCHEMA:
        raise LedgerError(f"unsupported schema: {raw.get('schema')}")
    attempts_raw = raw.get("attempts")
    if not isinstance(attempts_raw, list):
        raise LedgerError("attempts must be a list")
    seen_ids: set[str] = set()
    attempts: list[dict[str, Any]] = []
    for item in attempts_raw:
        parsed = validate_attempt(item)
        if parsed["attempt_id"] in seen_ids:
            raise LedgerError(f"duplicate attempt_id: {parsed['attempt_id']}")
        seen_ids.add(parsed["attempt_id"])
        attempts.append(parsed)
    by_puzzle: dict[str, list[dict[str, Any]]] = {}
    for a in attempts:
        by_puzzle.setdefault(a["puzzle_id"], []).append(a)
    frontiers = [frontier_for_puzzle(group) for _, group in sorted(by_puzzle.items())]
    for front in frontiers:
        best = front["best_observed_token_count"]
        if best is None:
            continue
        for a in by_puzzle[front["puzzle_id"]]:
            if a["outcome"] == "success":
                a["delta_from_best"] = a["observed_token_count"] - best
            else:
                a["delta_from_best"] = None
    receipt = build_receipt({"attempts": attempts}, frontiers)
    return {
        "attempts": attempts,
        "frontiers": frontiers,
        "receipt": receipt,
        "compliance_kind": COMPLIANCE_KIND,
    }


def render_markdown(result: dict[str, Any]) -> str:
    rec = result["receipt"]
    lines = [
        "# CrowdStrike Agents of Chaos — manual workbench receipt",
        "",
        f"- schema: `{rec['schema']}`",
        f"- compliance: `{rec['compliance_kind']}` (not an eligibility certificate)",
        f"- live contest interaction: `{rec['live_contest_interaction']}`",
        f"- tokenizer: `{rec['tokenizer']}`",
        f"- receipt_sha256: `{rec['receipt_sha256']}`",
        "",
        "## Frontiers",
        "",
    ]
    if not result["frontiers"]:
        lines.append("_No attempts._")
    for front in result["frontiers"]:
        lines.append(f"### {front['puzzle_id']}")
        lines.append(f"- best observed tokens: `{front['best_observed_token_count']}`")
        lines.append(f"- best attempts: `{', '.join(front['best_attempt_ids']) or 'none'}`")
        lines.append(f"- successful count: `{front['successful_count']}`")
        if front["duplicate_prompt_groups"]:
            lines.append("- duplicate successful prompts:")
            for g in front["duplicate_prompt_groups"]:
                lines.append(f"  - `{g['prompt_digest'][:12]}` → {', '.join(g['attempt_ids'])}")
        lines.append("")
    lines.extend(
        [
            "## Authority ceiling",
            "",
            "No live contest interaction, no bot/automated gameplay, no login/MFA,",
            "no prompt submission by this tool, no backend/scoring probing, no",
            "interception, no multi-accounting, no other-player access, and no",
            "prize/payment/revenue claim.",
            "",
        ]
    )
    return "\n".join(lines)


def publish(result: dict[str, Any], out_json: Path, out_md: Path) -> None:
    if out_json.exists() or out_md.exists():
        raise LedgerError("publication is create-exclusive; refuse overwrite")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    out_md.write_text(render_markdown(result), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offline CrowdStrike AOC manual workbench")
    parser.add_argument("ledger", type=Path)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    args = parser.parse_args(argv)
    try:
        raw = load_strict_json_path(args.ledger)
        result = evaluate_ledger(raw)
        if args.out_json or args.out_md:
            if not (args.out_json and args.out_md):
                raise LedgerError("both --out-json and --out-md are required to publish")
            publish(result, args.out_json, args.out_md)
        else:
            print(json.dumps(result["receipt"], indent=2, sort_keys=True))
        return 0
    except LedgerError as exc:
        print(f"LEDGER_ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
