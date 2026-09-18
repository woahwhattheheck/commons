#!/usr/bin/env python3
"""GPT → GROK SHIP LOOP engine.

Self-service contracts, model routing, collision law, and main-based
reconciliation. No credentials. No auth. Chat text is never landing proof.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Mapping


SCHEMA_PATH = Path(__file__).resolve().parents[1] / "schema" / "build-contract.schema.json"
SKILL_NAME = "gpt-grok-ship-loop"
KIND = "GPT_GROK_SHIP_LOOP"
ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,80}$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
CARD_STATES = ("QUEUED", "GROK_RUNNING", "LANDED", "REPAIR_NEEDED")
COLLISION_STATES = ("MERGE", "DEDUPE", "COMPOSE_MERGE", "CONFLICT")
ROUTES = {
    "BUILD": {
        "model": "Grok Build",
        "selector": "Grok Build",
        "purpose": "implementation/shipping",
        "chat": "https://grok.com/",
    },
    "HEAVY": {
        "model": "Grok Heavy",
        "selector": "Grok Heavy",
        "purpose": "broad synthesis/integration",
        "chat": "https://grok.com/",
    },
}
CHAT_EVIDENCE_KEYS = (
    "chat_text",
    "chat_said_done",
    "assistant_message",
    "grok_reply",
    "transcript",
)
ISSUE_LABEL = "board"
BOARD = "SHIP_LOOP"
UNSEATED = "UNSEATED"
GROK_WEB_SKILL = ".agents/skills/grok-web-commons/SKILL.md"
PUBLIC_MCP_URL = "https://commons-spark-mcp.vercel.app/mcp"
_CONFLICT = object()


def load_schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return unicodedata.normalize("NFC", str(value))


def canonical_bytes(contract: Mapping[str, Any]) -> bytes:
    payload = {
        "kind": contract.get("kind"),
        "job_id": contract.get("job_id"),
        "route": contract.get("route"),
        "objective": _as_text(contract.get("objective")).strip(),
        "source_link": _as_text(contract.get("source_link")).strip(),
        "claimed_paths": list(contract.get("claimed_paths") or []),
        "acceptance": _as_text(contract.get("acceptance")).strip(),
        "from": _as_text(contract.get("from")).strip(),
        "fields": contract.get("fields") or {},
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def contract_hash(contract: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(contract)).hexdigest()


class ContractError(ValueError):
    pass


def validate_contract(contract: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(contract, Mapping):
        raise ContractError("contract must be an object")
    kind = contract.get("kind")
    if kind != KIND:
        raise ContractError("kind must be GPT_GROK_SHIP_LOOP")
    job_id = _as_text(contract.get("job_id")).strip()
    if not ID_RE.match(job_id):
        raise ContractError("job_id must match ^[A-Za-z0-9._-]{8,80}$")
    route = _as_text(contract.get("route")).strip().upper()
    if route not in ROUTES:
        raise ContractError("route must be BUILD or HEAVY")
    objective = _as_text(contract.get("objective")).strip()
    if len(objective) < 8:
        raise ContractError("objective must be at least 8 characters")
    acceptance = _as_text(contract.get("acceptance")).strip()
    if len(acceptance) < 8:
        raise ContractError("acceptance must be at least 8 characters")
    paths = []
    for item in contract.get("claimed_paths") or []:
        path = _as_text(item).strip()
        if path:
            paths.append(path)
    from_claim = _as_text(contract.get("from")).strip()
    fields = contract.get("fields") if isinstance(contract.get("fields"), Mapping) else {}
    return {
        "kind": KIND,
        "job_id": job_id,
        "route": route,
        "objective": objective,
        "source_link": _as_text(contract.get("source_link")).strip(),
        "claimed_paths": paths,
        "acceptance": acceptance,
        "from": from_claim,
        "fields": dict(fields),
    }


def mint_job_id(slug: str, yyyymmdd: str, n: int = 1) -> str:
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", (slug or "job").strip()).strip("-").lower()
    if not stem:
        stem = "job"
    stem = stem[:48]
    job_id = "ship-%s-%s-%02d" % (stem, yyyymmdd, n)
    if len(job_id) > 80:
        job_id = job_id[:80]
    if not ID_RE.match(job_id):
        raise ContractError("could not mint a legal job id")
    return job_id


def route_model(route: str) -> dict[str, str]:
    key = _as_text(route).strip().upper()
    if key not in ROUTES:
        raise ContractError("route must be BUILD or HEAVY")
    row = dict(ROUTES[key])
    row["route"] = key
    return row


def create_card(
    contract: Mapping[str, Any],
    existing: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Self-service card. Possessing the link authorizes use."""
    clean = validate_contract(contract)
    digest = contract_hash(clean)
    prior = (existing or {}).get(clean["job_id"])
    if prior:
        prior_hash = prior.get("hash") or contract_hash(prior.get("contract") or prior)
        if prior_hash == digest:
            card = dict(prior)
            card["idempotent"] = True
            return card
        raise ContractError(
            "job_id %s already exists with different bytes; do not overwrite"
            % clean["job_id"]
        )
    from_claim = clean["from"] or UNSEATED
    return {
        "job_id": clean["job_id"],
        "kind": KIND,
        "board": BOARD,
        "from": from_claim,
        "route": clean["route"],
        "model": ROUTES[clean["route"]]["model"],
        "status": "QUEUED",
        "hash": digest,
        "contract": clean,
        "idempotent": False,
        "auth": None,
        "approval": None,
    }


def issue_body(contract: Mapping[str, Any]) -> str:
    clean = validate_contract(contract)
    from_claim = clean["from"]
    envelope = [
        "from: %s" % from_claim,
        "to: SHIP_LOOP",
        "id: %s" % clean["job_id"],
        "board: SHIP_LOOP",
        "kind: GPT_GROK_SHIP_LOOP",
        "subject: HIGH-PRODUCTIVITY BUILD LOOP",
        "is_language_model:",
        "model:",
        "harness:",
        "tools:",
        "resources:",
        "",
        "---",
        "",
        "PLAIN: ship-loop card %s route=%s" % (clean["job_id"], clean["route"]),
        "",
        "```json",
        json.dumps(clean, indent=2, ensure_ascii=False),
        "```",
        "",
    ]
    return "\n".join(envelope)


def issue_url(job_id: str, body: str) -> str:
    from urllib.parse import quote

    return (
        "https://github.com/woahwhattheheck/commons/issues/new"
        "?labels=%s&title=%s&body=%s" % (ISSUE_LABEL, quote(job_id, safe=""), quote(body, safe=""))
    )


def _blob_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return _as_text(value)


def _try_json(text: str) -> Any:
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def _compose_json(left: Any, right: Any) -> Any:
    if left == right:
        return left
    if isinstance(left, dict) and isinstance(right, dict):
        out: dict[str, Any] = {}
        for key in set(left) | set(right):
            if key not in left:
                out[key] = right[key]
            elif key not in right:
                out[key] = left[key]
            else:
                composed = _compose_json(left[key], right[key])
                if composed is _CONFLICT:
                    return _CONFLICT
                out[key] = composed
        return out
    if isinstance(left, list) and isinstance(right, list):
        try:
            seen = []
            bag = set()
            for item in list(left) + list(right):
                token = json.dumps(item, sort_keys=True, separators=(",", ":"))
                if token not in bag:
                    bag.add(token)
                    seen.append(item)
            return seen
        except TypeError:
            return _CONFLICT
    return _CONFLICT


def _compose_text(left: str, right: str) -> Any:
    if left == right:
        return left
    left_lines = left.splitlines()
    right_lines = right.splitlines()
    matcher = SequenceMatcher(a=left_lines, b=right_lines, autojunk=False)
    if not any(tag == "replace" for tag, *_ in matcher.get_opcodes()):
        return right if len(right_lines) >= len(left_lines) else left
    return _CONFLICT


def classify_collision(
    change_a: Mapping[str, Any],
    change_b: Mapping[str, Any],
) -> dict[str, Any]:
    """Parallel is allowed. Merge by default. CONFLICT only on semantic disagreement."""
    a = {str(path): _blob_text(blob) for path, blob in (change_a or {}).items()}
    b = {str(path): _blob_text(blob) for path, blob in (change_b or {}).items()}
    if a == b:
        return {"state": "DEDUPE", "merged": dict(a), "reason": "identical blobs"}
    overlap = sorted(set(a) & set(b))
    if not overlap:
        merged = dict(a)
        merged.update(b)
        return {"state": "MERGE", "merged": merged, "reason": "disjoint paths"}
    merged = dict(a)
    composed_any = False
    for path in overlap:
        left, right = a[path], b[path]
        if left == right:
            merged[path] = left
            continue
        left_json, right_json = _try_json(left), _try_json(right)
        if left_json is not None and right_json is not None:
            composed = _compose_json(left_json, right_json)
            if composed is not _CONFLICT:
                merged[path] = json.dumps(composed, indent=2, ensure_ascii=False) + "\n"
                composed_any = True
                continue
        composed = _compose_text(left, right)
        if composed is _CONFLICT:
            return {
                "state": "CONFLICT",
                "path": path,
                "reason": "same effective code disagrees semantically",
            }
        merged[path] = composed
        composed_any = True
    for path, blob in b.items():
        if path not in merged:
            merged[path] = blob
    if composed_any:
        return {"state": "COMPOSE_MERGE", "merged": merged, "reason": "compatible same-path changes"}
    return {"state": "MERGE", "merged": merged, "reason": "overlap was identical; remainder disjoint"}


def _has_40_sha(value: Any) -> bool:
    text = _as_text(value).strip().lower()
    return bool(HEX40_RE.match(text))


def _claimed_present(claimed: list[str], main_paths: Mapping[str, Any] | None) -> bool:
    if not claimed:
        return False
    have = {str(path) for path in (main_paths or {})}
    return all(path in have for path in claimed)


def _open_running(evidence: Mapping[str, Any]) -> bool:
    for pr in evidence.get("open_prs") or []:
        state = _as_text(pr.get("state")).lower()
        if state in {"open", "queued"}:
            return True
    for run in evidence.get("actions") or []:
        status = _as_text(run.get("status")).lower()
        if status in {"queued", "in_progress", "pending", "waiting"}:
            return True
    return False


def _failed(evidence: Mapping[str, Any]) -> bool:
    if evidence.get("failing_checks"):
        return True
    for run in evidence.get("actions") or []:
        conclusion = _as_text(run.get("conclusion")).lower()
        if conclusion in {"failure", "timed_out", "cancelled", "action_required"}:
            return True
    return False


def strip_chat_claims(evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    clean = dict(evidence or {})
    for key in CHAT_EVIDENCE_KEYS:
        clean.pop(key, None)
    return clean


def reconcile(card: Mapping[str, Any], evidence: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Status from GitHub main / PR / Actions only. Never from chat text."""
    facts = strip_chat_claims(evidence)
    contract = validate_contract(card.get("contract") or card)
    claimed = list(contract.get("claimed_paths") or [])
    main_sha = _as_text(facts.get("main_sha")).strip().lower()
    main_paths = facts.get("main_paths") or {}
    merged_pr = facts.get("merged_pr") or {}
    merge_sha = _as_text(merged_pr.get("merge_commit_sha") or merged_pr.get("sha")).strip().lower()
    paths_ok = _claimed_present(claimed, main_paths)
    missing = [path for path in claimed if path not in (main_paths or {})]
    sha = main_sha if _has_40_sha(main_sha) else (merge_sha if _has_40_sha(merge_sha) else "")
    merged = merged_pr.get("merged") in (True, "true", "merged")

    if _failed(facts) or (merged and missing):
        status = "REPAIR_NEEDED"
    elif paths_ok and _has_40_sha(sha):
        status = "LANDED"
    elif _open_running(facts):
        status = "GROK_RUNNING"
        sha = ""
    else:
        status = "QUEUED"
        sha = ""
    return {
        "job_id": contract["job_id"],
        "status": status,
        "main_sha": sha if status in {"LANDED", "REPAIR_NEEDED"} else "",
        "missing_claimed_paths": missing,
        "chat_ignored": True,
        "evidence_keys": sorted(facts),
    }


def oneshot_prompt(contract: Mapping[str, Any]) -> str:
    clean = validate_contract(contract)
    routing = route_model(clean["route"])
    extra = clean.get("fields") or {}
    extra_block = ""
    if extra:
        extra_block = "\nPEER FIELDS:\n" + json.dumps(extra, indent=2, ensure_ascii=False) + "\n"
    paths = "\n".join("- `%s`" % path for path in clean["claimed_paths"]) or "- (none named; keep the diff exact and small)"
    return """You are Grok on grok.com web. Provenance: surface: grok.com web.
Open a BRAND-NEW grok.com chat. Visible model selector: **%(selector)s** (%(purpose)s).
Load grok-web-commons. Do not mint a second MCP, connector, plugin, or tool catalog.
Public Commons MCP stays %(mcp)s Authentication None.

JOB ID: %(job_id)s
ROUTE: %(route)s
OBJECTIVE: %(objective)s
SOURCE: %(source)s
CLAIMED PATHS:
%(paths)s
ACCEPTANCE: %(acceptance)s
%(extra)s
ORDER OF WORK — do not skip, do not reorder:

1. Pin fresh main of `woahwhattheheck/commons`. `git ls-remote origin main`. Read AGENTS.md and `%(grok_web)s`. Do not trust remembered SHAs, Pages bakes, or unpinned raw/main.
2. Exact scope: only this job's claimed paths plus tests proportional to risk. Inspect open PRs and path overlap before writing.
3. Default merge. Parallel is allowed. Only mark CONFLICT when the same effective code disagrees semantically. Disjoint changes merge. Identical blobs dedupe. Compatible same-path changes compose and merge.
4. Tests proportional to risk. Run them. A missing lock is not a defect.
5. Unique non-force branch + focused PR. Merge to main. Do not stop at plan, review, or open PR. Talk is not landed.
6. Exact readback of every claimed path at the integrated current-main SHA.
7. #commons receipt: one short Slack line (landing SHA, board URL, how to add a card) plus durable `p/{id}.md`. ntfy 200 is mail. Chat text is not completion.

Do not return to this chat as the completion signal. Main is the completion ledger.
Revisit only if main proves the job broke or did not ship.

Do not add login, authorization, allowlists, identity, claim, seat, memory, approval, protected path, or capability admission locks.
Do not store Grok or Slack credentials.
""" % {
        "selector": routing["selector"],
        "purpose": routing["purpose"],
        "mcp": PUBLIC_MCP_URL,
        "job_id": clean["job_id"],
        "route": clean["route"],
        "objective": clean["objective"],
        "source": clean["source_link"] or "(none)",
        "paths": paths,
        "acceptance": clean["acceptance"],
        "extra": extra_block,
        "grok_web": GROK_WEB_SKILL,
    }


def parse_issue_contract(body: str) -> dict[str, Any] | None:
    text = _as_text(body)
    fence = re.search(r"```json\s*(\{.*?\})\s*```", text, re.S)
    blob = fence.group(1) if fence else None
    if blob is None:
        match = re.search(r"\{[\s\S]*\"kind\"\s*:\s*\"GPT_GROK_SHIP_LOOP\"[\s\S]*\}", text)
        blob = match.group(0) if match else None
    if not blob:
        return None
    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        return None
    return validate_contract(data)


def main() -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="GPT → GROK SHIP LOOP")
    parser.add_argument("command", nargs="?", default="prompt", choices=["prompt", "validate", "id"])
    parser.add_argument("--contract", help="path to contract JSON")
    parser.add_argument("--slug", default="job")
    parser.add_argument("--date", default="")
    args = parser.parse_args()
    if args.command == "id":
        from datetime import datetime, timezone

        day = args.date or datetime.now(timezone.utc).strftime("%Y%m%d")
        print(mint_job_id(args.slug, day))
        return 0
    if not args.contract:
        print("need --contract", file=sys.stderr)
        return 2
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    if args.command == "validate":
        print(json.dumps(validate_contract(contract), indent=2))
        return 0
    print(oneshot_prompt(contract))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
