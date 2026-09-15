#!/usr/bin/env python3
"""Deterministic proposal compliance gate.

Keeps bid teams from treating polished prose as evidence. The gate is deliberately
buyer-neutral: requirements and evidence are supplied as JSON at runtime.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

PLACEHOLDER_RE = re.compile(r"(?:\bTBD\b|\bTODO\b|\[\s*(?:INSERT|TBD|TODO)[^\]]*\]|<[^>]*(?:TBD|TODO|INSERT)[^>]*>)", re.I)
VALID_EVIDENCE = {"available", "pending", "missing", "not_applicable"}
VALID_REQ_TYPES = {"mandatory", "scored", "informational"}


@dataclass(frozen=True)
class GateResult:
    requirement_id: str
    section: str
    requirement_type: str
    disposition: str
    evidence_status: str
    missing_evidence: tuple[str, ...]
    owner_gate: bool
    notes: tuple[str, ...]


def _load(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _validate_payload(requirements: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> None:
    ids: set[str] = set()
    for req in requirements:
        rid = str(req.get("id", "")).strip()
        if not rid:
            raise ValueError("every requirement needs a non-empty id")
        if rid in ids:
            raise ValueError(f"duplicate requirement id: {rid}")
        ids.add(rid)
        kind = str(req.get("type", "mandatory"))
        if kind not in VALID_REQ_TYPES:
            raise ValueError(f"{rid}: invalid type {kind!r}")
        if not isinstance(req.get("statement", ""), str):
            raise ValueError(f"{rid}: statement must be text")
        ev = req.get("evidence", [])
        if not isinstance(ev, list) or not all(isinstance(x, str) and x.strip() for x in ev):
            raise ValueError(f"{rid}: evidence must be a list of non-empty ids")

    evid_ids: set[str] = set()
    for item in evidence:
        eid = str(item.get("id", "")).strip()
        if not eid:
            raise ValueError("every evidence item needs a non-empty id")
        if eid in evid_ids:
            raise ValueError(f"duplicate evidence id: {eid}")
        evid_ids.add(eid)
        status = str(item.get("status", "missing"))
        if status not in VALID_EVIDENCE:
            raise ValueError(f"{eid}: invalid status {status!r}")


def evaluate(requirements: list[dict[str, Any]], evidence: list[dict[str, Any]]) -> list[GateResult]:
    _validate_payload(requirements, evidence)
    evid = {str(x["id"]): x for x in evidence}
    results: list[GateResult] = []

    for req in requirements:
        rid = str(req["id"])
        kind = str(req.get("type", "mandatory"))
        required_evidence = [str(x) for x in req.get("evidence", [])]
        missing: list[str] = []
        pending: list[str] = []
        available: list[str] = []
        for eid in required_evidence:
            item = evid.get(eid)
            if item is None or item.get("status", "missing") == "missing":
                missing.append(eid)
            elif item.get("status") == "pending":
                pending.append(eid)
            elif item.get("status") == "available":
                available.append(eid)

        response = str(req.get("response", "") or "").strip()
        notes: list[str] = []
        owner_gate = bool(req.get("owner_gate", False))
        response_required = bool(req.get("response_required", True))

        if response_required and not response:
            notes.append("response missing")
        elif PLACEHOLDER_RE.search(response):
            notes.append("response contains placeholder text")

        if missing:
            notes.append("required evidence missing")
        if pending:
            notes.append("required evidence pending")
        if owner_gate:
            notes.append("owner/authorized-human gate")

        if missing:
            ev_status = "missing"
        elif pending:
            ev_status = "pending"
        elif required_evidence and len(available) == len(required_evidence):
            ev_status = "available"
        elif not required_evidence:
            ev_status = "not_required"
        else:
            ev_status = "not_applicable"

        response_bad = response_required and (not response or bool(PLACEHOLDER_RE.search(response)))
        if kind == "mandatory" and (missing or pending or response_bad or owner_gate):
            disposition = "BLOCKED"
        elif kind == "scored" and (missing or pending or response_bad or owner_gate):
            disposition = "AT_RISK"
        elif response_bad:
            disposition = "INCOMPLETE"
        else:
            disposition = "READY"

        results.append(GateResult(
            requirement_id=rid,
            section=str(req.get("section", "")),
            requirement_type=kind,
            disposition=disposition,
            evidence_status=ev_status,
            missing_evidence=tuple(missing + pending),
            owner_gate=owner_gate,
            notes=tuple(notes),
        ))
    return results


def summarize(results: Iterable[GateResult]) -> dict[str, Any]:
    rows = list(results)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.disposition] = counts.get(row.disposition, 0) + 1
    blocking = [r.requirement_id for r in rows if r.disposition == "BLOCKED"]
    owner = [r.requirement_id for r in rows if r.owner_gate]
    ready = [r for r in rows if r.disposition == "READY"]
    score = round((len(ready) / len(rows) * 100.0), 1) if rows else 100.0
    return {
        "total": len(rows),
        "counts": dict(sorted(counts.items())),
        "readiness_percent": score,
        "submission_ready": not blocking and not owner,
        "blocking_requirements": blocking,
        "owner_gates": owner,
    }


def render_markdown(requirements: list[dict[str, Any]], results: list[GateResult]) -> str:
    req_map = {str(r["id"]): r for r in requirements}
    summary = summarize(results)
    lines = [
        "# Proposal compliance gate",
        "",
        f"**Readiness:** {summary['readiness_percent']}%  ",
        f"**Submission ready:** {'YES' if summary['submission_ready'] else 'NO'}  ",
        f"**Blocked:** {len(summary['blocking_requirements'])}  ",
        f"**Owner gates:** {len(summary['owner_gates'])}",
        "",
        "| ID | Section | Type | Disposition | Evidence | Owner gate | Requirement |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in results:
        req = req_map[row.requirement_id]
        statement = str(req.get("statement", "")).replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {row.requirement_id} | {row.section} | {row.requirement_type} | **{row.disposition}** | "
            f"{row.evidence_status} | {'YES' if row.owner_gate else 'no'} | {statement} |"
        )
    if summary["blocking_requirements"]:
        lines += ["", "## Blocking requirements", ""]
        for rid in summary["blocking_requirements"]:
            row = next(x for x in results if x.requirement_id == rid)
            req = req_map[rid]
            detail = "; ".join(row.notes) or "blocked"
            lines.append(f"- **{rid}** — {req.get('statement','')} ({detail})")
    if summary["owner_gates"]:
        lines += ["", "## Authorized-human gates", ""]
        for rid in summary["owner_gates"]:
            lines.append(f"- **{rid}** — {req_map[rid].get('statement','')}")
    return "\n".join(lines) + "\n"


def render_skeleton(requirements: list[dict[str, Any]]) -> str:
    sections: dict[str, list[dict[str, Any]]] = {}
    for req in requirements:
        sections.setdefault(str(req.get("section", "General")), []).append(req)
    lines = ["# Proposal response skeleton", "", "> Generated from the requirement register. Do not treat placeholders as evidence.", ""]
    for section, items in sections.items():
        lines += [f"## {section}", ""]
        for req in items:
            lines += [f"### {req['id']}: {req['statement']}", "", "[TBD — evidence-backed response required]", ""]
    return "\n".join(lines)


def render_draft(requirements: list[dict[str, Any]]) -> str:
    """Render current requirement responses without promoting placeholders to facts."""
    sections: dict[str, list[dict[str, Any]]] = {}
    for req in requirements:
        sections.setdefault(str(req.get("section", "General")), []).append(req)
    lines = [
        "# Evidence-backed proposal draft",
        "",
        "> Working draft only. Owner-gated facts and missing evidence remain explicitly unresolved.",
        "",
    ]
    for section, items in sections.items():
        lines += [f"## {section}", ""]
        for req in items:
            response = str(req.get("response", "") or "").strip() or "[TBD — evidence-backed response required]"
            gate = " **[OWNER GATE]**" if req.get("owner_gate") else ""
            lines += [f"### {req['id']}{gate}", f"**Requirement:** {req['statement']}", "", response, ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("requirements", help="requirements JSON file")
    p.add_argument("evidence", help="evidence inventory JSON file")
    p.add_argument("--json-out", help="write machine-readable gate report")
    p.add_argument("--markdown-out", help="write Markdown compliance matrix")
    p.add_argument("--skeleton-out", help="write response skeleton")
    p.add_argument("--draft-out", help="write current evidence-backed response draft")
    p.add_argument("--check", action="store_true", help="exit 2 unless submission_ready")
    args = p.parse_args(argv)

    req_payload = _load(args.requirements)
    ev_payload = _load(args.evidence)
    requirements = req_payload["requirements"] if isinstance(req_payload, dict) else req_payload
    evidence = ev_payload["evidence"] if isinstance(ev_payload, dict) else ev_payload
    results = evaluate(requirements, evidence)
    summary = summarize(results)
    report = {"summary": summary, "results": [asdict(r) for r in results]}

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.markdown_out:
        Path(args.markdown_out).write_text(render_markdown(requirements, results), encoding="utf-8")
    if args.skeleton_out:
        Path(args.skeleton_out).write_text(render_skeleton(requirements), encoding="utf-8")
    if args.draft_out:
        Path(args.draft_out).write_text(render_draft(requirements), encoding="utf-8")

    print(json.dumps(summary, sort_keys=True))
    if args.check and not summary["submission_ready"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
