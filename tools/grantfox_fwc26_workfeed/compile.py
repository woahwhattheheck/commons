from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REQUIRED_LABELS = {
    "grantfox oss",
    "maybe rewarded",
    "official campaign | fwc26",
}

COMMAND_PREFIXES = (
    "npm ",
    "pnpm ",
    "yarn ",
    "cargo ",
    "pytest",
    "python -m pytest",
    "go test",
    "forge ",
    "npx ",
)

CASH_RE = re.compile(
    r"(?<![\w])(?:\$\s?\d[\d,]*(?:\.\d{1,2})?|\d[\d,]*(?:\.\d{1,2})?\s*(?:USDC|USD|XLM))(?![\w])",
    re.IGNORECASE,
)

CLAIM_HINT_RE = re.compile(
    r"\b(comment|apply|claim|request assignment|wait for (?:a )?maintainer|wait for assignment)\b",
    re.IGNORECASE,
)

SECURITY_TERMS = (
    "auth",
    "authorization",
    "security",
    "multisig",
    "multi-sig",
    "settlement",
    "escrow",
    "wallet",
    "payment",
    "payout",
    "admin",
    "contract",
    "soroban",
    "solidity",
    "vrf",
    "jury",
    "slashing",
    "vault",
    "secret",
    "keypair",
    "signature",
    "private key",
    "seed phrase",
    "redaction",
    "fund-safety",
)


class WorkfeedError(ValueError):
    """Input is not safe enough to compile into a swarm workfeed."""


@dataclass(frozen=True)
class Candidate:
    key: str
    repository: str
    number: int
    title: str
    url: str
    state: str
    labels: tuple[str, ...]
    assignees: tuple[str, ...]
    observed_claimants: tuple[str, ...]
    open_pull_requests: tuple[str, ...]
    status: str
    reward_class: str
    explicit_reward_mentions: tuple[str, ...]
    claim_required: bool
    security_sensitive: bool
    commands: tuple[str, ...]
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "repository": self.repository,
            "number": self.number,
            "title": self.title,
            "url": self.url,
            "state": self.state,
            "labels": list(self.labels),
            "assignees": list(self.assignees),
            "observed_claimants": list(self.observed_claimants),
            "open_pull_requests": list(self.open_pull_requests),
            "status": self.status,
            "reward_class": self.reward_class,
            "explicit_reward_mentions": list(self.explicit_reward_mentions),
            "claim_required": self.claim_required,
            "security_sensitive": self.security_sensitive,
            "commands": list(self.commands),
            "reason": self.reason,
        }


def _norm_label(value: str) -> str:
    return " ".join(value.strip().lower().split())


def _read_records(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip()
    if not stripped:
        return []
    if stripped[0] == "[":
        value = json.loads(text)
        if not isinstance(value, list):
            raise WorkfeedError("JSON input must be an array of issue objects")
        return value
    records: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise WorkfeedError(f"invalid JSONL on line {line_no}: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise WorkfeedError(f"JSONL line {line_no} must be an object")
        records.append(value)
    return records


def _repo_number(record: dict[str, Any]) -> tuple[str, int]:
    repo = record.get("repository") or record.get("repo")
    number = record.get("number", record.get("issue_number"))
    if not isinstance(repo, str) or "/" not in repo:
        raise WorkfeedError("each issue requires repository='owner/name'")
    if isinstance(number, bool) or not isinstance(number, int) or number <= 0:
        raise WorkfeedError(f"{repo}: issue number must be a positive integer")
    return repo, number


def _labels(record: dict[str, Any]) -> tuple[str, ...]:
    raw = record.get("labels") or []
    if not isinstance(raw, list):
        raise WorkfeedError("labels must be a list")
    labels: list[str] = []
    for item in raw:
        if isinstance(item, str):
            labels.append(item)
        elif isinstance(item, dict) and isinstance(item.get("name"), str):
            labels.append(item["name"])
        else:
            raise WorkfeedError("labels entries must be strings or {'name': string}")
    return tuple(labels)


def _assignees(record: dict[str, Any]) -> tuple[str, ...]:
    raw = record.get("assignees") or []
    if not isinstance(raw, list):
        raise WorkfeedError("assignees must be a list")
    result: list[str] = []
    for item in raw:
        if isinstance(item, str):
            result.append(item)
        elif isinstance(item, dict) and isinstance(item.get("login"), str):
            result.append(item["login"])
        else:
            raise WorkfeedError("assignees entries must be strings or {'login': string}")
    return tuple(result)


def _observed_claimants(record: dict[str, Any]) -> tuple[str, ...]:
    raw = record.get("claimant_comments") or record.get("claim_comments") or []
    if not isinstance(raw, list):
        raise WorkfeedError("claimant_comments must be a list")
    result: list[str] = []
    for item in raw:
        if isinstance(item, str):
            claimant = item.strip()
        elif isinstance(item, dict):
            user = item.get("user")
            if isinstance(user, dict):
                user = user.get("login")
            claimant = str(user or item.get("login") or "").strip()
        else:
            raise WorkfeedError("claimant_comments entries must be strings or objects")
        if claimant and claimant not in result:
            result.append(claimant)
    return tuple(result)


def _open_pull_requests(record: dict[str, Any]) -> tuple[str, ...]:
    raw = record.get("open_pull_requests") or record.get("open_prs") or []
    if not isinstance(raw, list):
        raise WorkfeedError("open_pull_requests must be a list")
    result: list[str] = []
    for item in raw:
        if isinstance(item, str):
            value = item.strip()
        elif isinstance(item, dict):
            value = str(item.get("url") or item.get("html_url") or item.get("number") or "").strip()
        else:
            raise WorkfeedError("open_pull_requests entries must be strings or objects")
        if value and value not in result:
            result.append(value)
    return tuple(result)


def _commands(body: str) -> tuple[str, ...]:
    found: list[str] = []
    for command in re.findall(r"`([^`\n]+)`", body):
        normalized = command.strip()
        lower = normalized.lower()
        if any(lower.startswith(prefix) for prefix in COMMAND_PREFIXES):
            if normalized not in found:
                found.append(normalized)
    return tuple(found)


def classify(record: dict[str, Any]) -> Candidate:
    repo, number = _repo_number(record)
    key = f"{repo}#{number}"
    title = record.get("title")
    url = record.get("url") or record.get("html_url") or record.get("display_url")
    state = str(record.get("state") or "open").lower()
    body = str(record.get("body") or "")
    labels = _labels(record)
    assignees = _assignees(record)
    observed_claimants = _observed_claimants(record)
    open_pull_requests = _open_pull_requests(record)

    if not isinstance(title, str) or not title.strip():
        raise WorkfeedError(f"{key}: title is required")
    if not isinstance(url, str) or not url.startswith(("https://github.com/", "http://github.com/")):
        raise WorkfeedError(f"{key}: canonical GitHub issue URL is required")

    normalized_labels = {_norm_label(x) for x in labels}
    missing = REQUIRED_LABELS - normalized_labels

    explicit_mentions = tuple(dict.fromkeys(m.group(0).strip() for m in CASH_RE.finditer(body)))
    if explicit_mentions:
        reward_class = "EXPLICIT_AMOUNT_MENTIONED"
    elif "may be rewarded" in body.lower() or "maybe rewarded" in normalized_labels:
        reward_class = "DISCRETIONARY_CAMPAIGN_REWARD"
    else:
        reward_class = "NO_REWARD_EVIDENCE"

    claim_required = bool(CLAIM_HINT_RE.search(body))
    security_sensitive = any(term in f"{title}\n{body}".lower() for term in SECURITY_TERMS)

    if state != "open":
        status = "INELIGIBLE"
        reason = f"issue state is {state}"
    elif missing:
        status = "INELIGIBLE"
        reason = "missing required campaign labels: " + ", ".join(sorted(missing))
    elif assignees:
        status = "ASSIGNED"
        reason = "already assigned to: " + ", ".join(assignees)
    elif observed_claimants or open_pull_requests:
        status = "CLAIMED_OR_PR_OPEN"
        pieces: list[str] = []
        if observed_claimants:
            pieces.append("observed claimant(s): " + ", ".join(observed_claimants))
        if open_pull_requests:
            pieces.append("open PR(s): " + ", ".join(open_pull_requests))
        reason = "; ".join(pieces)
    elif claim_required:
        status = "CLAIM_REQUIRED"
        reason = "issue text describes an application/assignment step"
    else:
        status = "READY"
        reason = "open, campaign-labelled, and unassigned"

    return Candidate(
        key=key,
        repository=repo,
        number=number,
        title=title.strip(),
        url=url,
        state=state,
        labels=labels,
        assignees=assignees,
        observed_claimants=observed_claimants,
        open_pull_requests=open_pull_requests,
        status=status,
        reward_class=reward_class,
        explicit_reward_mentions=explicit_mentions,
        claim_required=claim_required,
        security_sensitive=security_sensitive,
        commands=_commands(body),
        reason=reason,
    )


def compile_records(records: Iterable[dict[str, Any]]) -> list[Candidate]:
    seen: set[str] = set()
    candidates: list[Candidate] = []
    for record in records:
        candidate = classify(record)
        if candidate.key in seen:
            raise WorkfeedError(f"duplicate issue key: {candidate.key}")
        seen.add(candidate.key)
        candidates.append(candidate)

    rank = {"READY": 0, "CLAIM_REQUIRED": 1, "CLAIMED_OR_PR_OPEN": 2, "ASSIGNED": 3, "INELIGIBLE": 4}
    candidates.sort(
        key=lambda c: (
            rank[c.status],
            0 if c.reward_class == "EXPLICIT_AMOUNT_MENTIONED" else 1,
            1 if c.security_sensitive else 0,
            c.repository.lower(),
            c.number,
        )
    )
    return candidates


def render_markdown(candidates: Iterable[Candidate]) -> str:
    rows = list(candidates)
    counts: dict[str, int] = {}
    for c in rows:
        counts[c.status] = counts.get(c.status, 0) + 1

    lines = [
        "# GrantFox FWC26 workfeed",
        "",
        "Generated from supplied GitHub issue snapshots. This file does **not** claim, assign, apply, contact maintainers, or guarantee payment.",
        "",
        "## Summary",
        "",
        f"- READY: {counts.get('READY', 0)}",
        f"- CLAIM_REQUIRED: {counts.get('CLAIM_REQUIRED', 0)}",
        f"- CLAIMED_OR_PR_OPEN: {counts.get('CLAIMED_OR_PR_OPEN', 0)}",
        f"- ASSIGNED: {counts.get('ASSIGNED', 0)}",
        f"- INELIGIBLE: {counts.get('INELIGIBLE', 0)}",
        "",
        "## Queue",
        "",
        "| Status | Issue | Reward evidence | Security-sensitive | Commands |",
        "|---|---|---|---:|---|",
    ]
    for c in rows:
        reward = c.reward_class
        if c.explicit_reward_mentions:
            reward += " (" + ", ".join(c.explicit_reward_mentions) + ")"
        commands = "<br>".join(f"`{cmd}`" for cmd in c.commands) or "—"
        issue = f"[{c.key}]({c.url}) — {c.title}"
        lines.append(
            f"| {c.status} | {issue} | {reward} | {'yes' if c.security_sensitive else 'no'} | {commands} |"
        )
        lines.append(f"\n> **{c.key}:** {c.reason}\n")
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(candidates: list[Candidate], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": 1,
        "authority": {
            "claims_issues": False,
            "assigns_issues": False,
            "guarantees_payment": False,
            "mutates_external_systems": False,
        },
        "issues": [c.to_dict() for c in candidates],
    }
    (out_dir / "queue.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (out_dir / "QUEUE.md").write_text(render_markdown(candidates), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile GrantFox FWC26 GitHub issue snapshots into a safe swarm workfeed."
    )
    parser.add_argument("input", type=Path, help="JSON array or JSONL issue snapshot file")
    parser.add_argument("--out-dir", type=Path, required=True, help="exclusive output directory")
    args = parser.parse_args(argv)

    if args.out_dir.exists():
        raise WorkfeedError(f"output directory already exists: {args.out_dir}")

    candidates = compile_records(_read_records(args.input))
    write_outputs(candidates, args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
