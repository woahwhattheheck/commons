"""Offline manual-observation workbench for CrowdStrike Agents of Chaos Act 3.

This module never contacts the contest. It only validates operator-entered records,
computes deterministic prompt-efficiency frontiers, and emits self-attested review
artifacts. It deliberately does not implement a tokenizer or infer sponsor scoring.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

LEDGER_SCHEMA = "crowdstrike.agents-of-chaos.manual-ledger/v1"
PACKET_SCHEMA = "crowdstrike.agents-of-chaos.frontier-packet/v1"
CONTEST = "AI Unlocked: Agents of Chaos — Act 3: The Basilisk"
AUTHORITY = "SELF_ATTESTED_ONLY"
MAX_ATTEMPTS = 10_000
MAX_PROMPT_BYTES = 20_000
MAX_FILE_BYTES = 8 * 1024 * 1024
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")

SELF_ATTESTED_KEYS = (
    "registered_account",
    "original_work",
    "english_gameplay",
    "standard_gameplay_mechanics",
)
PROHIBITED_KEYS = (
    "automated_tools_or_bots",
    "scoring_system_attack",
    "backend_exploit",
    "multiple_accounts_or_account_manipulation",
    "network_interception",
    "other_player_access",
)

OFFICIAL_RULES_URL = "https://www.crowdstrike.com/en-us/legal/ai-unlocked-agents-of-chaos-contest/"
OFFICIAL_OVERVIEW_URL = "https://www.crowdstrike.com/en-us/blog/agents-of-chaos-immersive-ai-security-challenge/"


class ValidationError(ValueError):
    """Raised when an input violates the strict workbench contract."""


def _canonical_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"value is not canonical-JSON encodable: {exc}") from exc
    return text.encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _reject_constant(value: str) -> None:
    raise ValidationError(f"non-finite JSON constant is forbidden: {value}")


def _unique_object(pairs: Iterable[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise ValidationError(f"duplicate JSON object key: {key}")
        out[key] = value
    return out


def strict_json_loads(raw: str | bytes) -> Any:
    if isinstance(raw, bytes):
        if len(raw) > MAX_FILE_BYTES:
            raise ValidationError("JSON input exceeds byte limit")
        try:
            raw = raw.decode("utf-8", "strict")
        except UnicodeDecodeError as exc:
            raise ValidationError("JSON input is not valid UTF-8") from exc
    elif not isinstance(raw, str):
        raise ValidationError("JSON input must be str or bytes")
    elif len(raw.encode("utf-8")) > MAX_FILE_BYTES:
        raise ValidationError("JSON input exceeds byte limit")
    try:
        return json.loads(raw, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    except ValidationError:
        raise
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON: {exc.msg}") from exc


def load_json_file(path: str | os.PathLike[str]) -> Any:
    p = Path(path)
    try:
        size = p.stat().st_size
    except OSError as exc:
        raise ValidationError(f"cannot stat JSON input: {exc}") from exc
    if size > MAX_FILE_BYTES:
        raise ValidationError("JSON input exceeds byte limit")
    try:
        data = p.read_bytes()
    except OSError as exc:
        raise ValidationError(f"cannot read JSON input: {exc}") from exc
    return strict_json_loads(data)


def _exact_keys(obj: dict[str, Any], expected: set[str], context: str) -> None:
    actual = set(obj)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValidationError(f"{context} fields mismatch; missing={missing} extra={extra}")


def _strict_bool(value: Any, field: str) -> bool:
    if type(value) is not bool:
        raise ValidationError(f"{field} must be a JSON boolean")
    return value


def _strict_int(value: Any, field: str, *, minimum: int, maximum: int) -> int:
    if type(value) is not int:
        raise ValidationError(f"{field} must be a JSON integer")
    if value < minimum or value > maximum:
        raise ValidationError(f"{field} out of range [{minimum}, {maximum}]")
    return value


def _strict_id(value: Any, field: str) -> str:
    if type(value) is not str or ID_RE.fullmatch(value) is None:
        raise ValidationError(f"{field} must match {ID_RE.pattern}")
    return value


def _canonical_utc(value: Any, field: str) -> str:
    if type(value) is not str:
        raise ValidationError(f"{field} must be a canonical UTC string")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValidationError(f"{field} must use YYYY-MM-DDTHH:MM:SSZ") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValidationError(f"{field} is not canonical UTC")
    return value


def _validate_assertions(attempt: dict[str, Any], attempt_id: str) -> tuple[dict[str, bool], dict[str, bool]]:
    self_attested = attempt["self_attested"]
    prohibited = attempt["prohibited_actions"]
    if type(self_attested) is not dict:
        raise ValidationError(f"attempt {attempt_id}: self_attested must be an object")
    if type(prohibited) is not dict:
        raise ValidationError(f"attempt {attempt_id}: prohibited_actions must be an object")
    _exact_keys(self_attested, set(SELF_ATTESTED_KEYS), f"attempt {attempt_id}.self_attested")
    _exact_keys(prohibited, set(PROHIBITED_KEYS), f"attempt {attempt_id}.prohibited_actions")

    normalized_attested: dict[str, bool] = {}
    for key in SELF_ATTESTED_KEYS:
        value = _strict_bool(self_attested[key], f"attempt {attempt_id}.self_attested.{key}")
        if not value:
            raise ValidationError(f"attempt {attempt_id}: self-attestation {key} must be true")
        normalized_attested[key] = value

    normalized_prohibited: dict[str, bool] = {}
    for key in PROHIBITED_KEYS:
        value = _strict_bool(prohibited[key], f"attempt {attempt_id}.prohibited_actions.{key}")
        if value:
            raise ValidationError(f"attempt {attempt_id}: prohibited action declared: {key}")
        normalized_prohibited[key] = value
    return normalized_attested, normalized_prohibited


def normalize_ledger(value: Any) -> dict[str, Any]:
    if type(value) is not dict:
        raise ValidationError("ledger must be an object")
    _exact_keys(value, {"schema", "contest", "attempts"}, "ledger")
    if value["schema"] != LEDGER_SCHEMA:
        raise ValidationError(f"unsupported ledger schema: {value['schema']!r}")
    if value["contest"] != CONTEST:
        raise ValidationError("contest identity mismatch")
    attempts = value["attempts"]
    if type(attempts) is not list:
        raise ValidationError("attempts must be an array")
    if len(attempts) > MAX_ATTEMPTS:
        raise ValidationError("too many attempts")

    normalized_attempts: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    expected_attempt_keys = {
        "attempt_id",
        "puzzle_id",
        "prompt",
        "observed_tokens",
        "success",
        "observed_at_utc",
        "self_attested",
        "prohibited_actions",
    }
    for index, attempt in enumerate(attempts):
        if type(attempt) is not dict:
            raise ValidationError(f"attempt[{index}] must be an object")
        _exact_keys(attempt, expected_attempt_keys, f"attempt[{index}]")
        attempt_id = _strict_id(attempt["attempt_id"], f"attempt[{index}].attempt_id")
        if attempt_id in seen_ids:
            raise ValidationError(f"duplicate attempt_id: {attempt_id}")
        seen_ids.add(attempt_id)
        puzzle_id = _strict_id(attempt["puzzle_id"], f"attempt {attempt_id}.puzzle_id")
        prompt = attempt["prompt"]
        if type(prompt) is not str:
            raise ValidationError(f"attempt {attempt_id}.prompt must be a string")
        prompt_bytes = prompt.encode("utf-8")
        if not prompt_bytes or len(prompt_bytes) > MAX_PROMPT_BYTES:
            raise ValidationError(f"attempt {attempt_id}.prompt byte length out of range")
        observed_tokens = _strict_int(
            attempt["observed_tokens"],
            f"attempt {attempt_id}.observed_tokens",
            minimum=1,
            maximum=1_000_000,
        )
        success = _strict_bool(attempt["success"], f"attempt {attempt_id}.success")
        observed_at_utc = _canonical_utc(attempt["observed_at_utc"], f"attempt {attempt_id}.observed_at_utc")
        self_attested, prohibited = _validate_assertions(attempt, attempt_id)
        normalized_attempts.append(
            {
                "attempt_id": attempt_id,
                "puzzle_id": puzzle_id,
                "prompt": prompt,
                "prompt_sha256": _sha256(prompt_bytes),
                "observed_tokens": observed_tokens,
                "success": success,
                "observed_at_utc": observed_at_utc,
                "self_attested": self_attested,
                "prohibited_actions": prohibited,
            }
        )

    normalized_attempts.sort(key=lambda item: item["attempt_id"])
    return {"schema": LEDGER_SCHEMA, "contest": CONTEST, "attempts": normalized_attempts}


def compile_ledger(value: Any) -> dict[str, Any]:
    normalized = normalize_ledger(value)
    puzzle_ids = sorted({attempt["puzzle_id"] for attempt in normalized["attempts"]})
    puzzles: list[dict[str, Any]] = []
    successful_total = 0

    for puzzle_id in puzzle_ids:
        rows = [attempt for attempt in normalized["attempts"] if attempt["puzzle_id"] == puzzle_id]
        successes = [attempt for attempt in rows if attempt["success"]]
        successful_total += len(successes)
        successes.sort(key=lambda item: (item["observed_tokens"], item["prompt_sha256"], item["attempt_id"]))
        best_tokens = successes[0]["observed_tokens"] if successes else None
        frontier = []
        for rank, attempt in enumerate(successes, 1):
            frontier.append(
                {
                    "rank": rank,
                    "attempt_id": attempt["attempt_id"],
                    "observed_tokens": attempt["observed_tokens"],
                    "delta_from_best": attempt["observed_tokens"] - best_tokens if best_tokens is not None else None,
                    "prompt_sha256": attempt["prompt_sha256"],
                }
            )

        by_prompt: dict[str, list[str]] = {}
        for attempt in rows:
            by_prompt.setdefault(attempt["prompt_sha256"], []).append(attempt["attempt_id"])
        duplicates = [
            {"prompt_sha256": digest, "attempt_ids": sorted(ids)}
            for digest, ids in sorted(by_prompt.items())
            if len(ids) > 1
        ]
        puzzles.append(
            {
                "puzzle_id": puzzle_id,
                "attempt_count": len(rows),
                "successful_attempt_count": len(successes),
                "failed_attempt_count": len(rows) - len(successes),
                "best_observed_tokens": best_tokens,
                "frontier": frontier,
                "duplicate_prompts": duplicates,
            }
        )

    ledger_for_digest = {
        "schema": normalized["schema"],
        "contest": normalized["contest"],
        "attempts": normalized["attempts"],
    }
    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "contest": CONTEST,
        "authority": AUTHORITY,
        "official_rules_url": OFFICIAL_RULES_URL,
        "scoring_semantics": {
            "success_source": "OPERATOR_ENTERED_OBSERVATION",
            "token_count_source": "OPERATOR_ENTERED_OBSERVATION",
            "tokenizer": "NOT_INFERRED",
            "frontier_order": "LOWER_OBSERVED_TOKENS_WITHIN_SUCCESSFUL_ATTEMPTS",
            "sponsor_score_equivalence": False,
        },
        "rules_guard": {
            "manual_entry_only": True,
            "live_contest_interaction_authority": False,
            "compliance_certificate": False,
            "required_self_attestations": list(SELF_ATTESTED_KEYS),
            "prohibited_actions": list(PROHIBITED_KEYS),
        },
        "attempt_count": len(normalized["attempts"]),
        "successful_attempt_count": successful_total,
        "ledger_sha256": _sha256(_canonical_bytes(ledger_for_digest)),
        "puzzles": puzzles,
    }
    packet["packet_sha256"] = _sha256(_canonical_bytes(packet))
    return packet


def verify_packet(ledger: Any, packet: Any) -> bool:
    if type(packet) is not dict:
        return False
    try:
        expected = compile_ledger(ledger)
    except ValidationError:
        return False
    return _canonical_bytes(expected) == _canonical_bytes(packet)


def render_markdown(packet: dict[str, Any]) -> str:
    if packet.get("schema") != PACKET_SCHEMA:
        raise ValidationError("cannot render unsupported packet schema")
    lines = [
        "# Agents of Chaos Act 3 — Manual Prompt-Efficiency Review",
        "",
        f"Authority: `{AUTHORITY}`",
        "",
        "This artifact is derived only from operator-entered observations. It does not contact the contest, infer the sponsor tokenizer, certify eligibility/compliance, or submit gameplay.",
        "",
        f"Official rules: {OFFICIAL_RULES_URL}",
        "",
        f"Ledger SHA-256: `{packet['ledger_sha256']}`",
        f"Packet SHA-256: `{packet['packet_sha256']}`",
        "",
    ]
    if not packet["puzzles"]:
        lines += ["No attempts recorded.", ""]
    for puzzle in packet["puzzles"]:
        lines += [
            f"## Puzzle `{puzzle['puzzle_id']}`",
            "",
            f"Attempts: {puzzle['attempt_count']} · successful: {puzzle['successful_attempt_count']} · failed: {puzzle['failed_attempt_count']}",
            "",
        ]
        if puzzle["frontier"]:
            lines += [
                "| Rank | Attempt | Observed tokens | Δ from best | Prompt SHA-256 |",
                "|---:|---|---:|---:|---|",
            ]
            for row in puzzle["frontier"]:
                lines.append(
                    f"| {row['rank']} | `{row['attempt_id']}` | {row['observed_tokens']} | {row['delta_from_best']} | `{row['prompt_sha256']}` |"
                )
            lines.append("")
        else:
            lines += ["No successful operator-entered attempts.", ""]
        if puzzle["duplicate_prompts"]:
            lines += ["Duplicate-prompt observations:", ""]
            for duplicate in puzzle["duplicate_prompts"]:
                joined = ", ".join(f"`{item}`" for item in duplicate["attempt_ids"])
                lines.append(f"- `{duplicate['prompt_sha256']}` → {joined}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def publish_bundle(packet: dict[str, Any], out_dir: str | os.PathLike[str]) -> dict[str, str]:
    if packet.get("schema") != PACKET_SCHEMA:
        raise ValidationError("cannot publish unsupported packet schema")
    out = Path(out_dir)
    try:
        out.mkdir(mode=0o700, parents=False, exist_ok=False)
    except FileExistsError as exc:
        raise ValidationError("output bundle directory already exists; refusing overwrite") from exc
    except OSError as exc:
        raise ValidationError(f"cannot create output bundle directory: {exc}") from exc

    files = {
        "frontier.json": _canonical_bytes(packet) + b"\n",
        "frontier.md": render_markdown(packet).encode("utf-8"),
        "receipt.sha256": (packet["packet_sha256"] + "\n").encode("ascii"),
    }
    created: list[Path] = []
    try:
        for name, data in files.items():
            path = out / name
            with path.open("xb") as handle:
                handle.write(data)
            created.append(path)
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
    except Exception:
        for path in reversed(created):
            try:
                path.unlink()
            except OSError:
                pass
        try:
            out.rmdir()
        except OSError:
            pass
        raise
    return {name: str(out / name) for name in files}
